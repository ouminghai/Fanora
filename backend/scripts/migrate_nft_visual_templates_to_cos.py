"""Rehost NFT visual template images on Tencent Cloud COS.

Run from backend/:
    python scripts/migrate_nft_visual_templates_to_cos.py --dry-run
    python scripts/migrate_nft_visual_templates_to_cos.py --apply
"""

# ruff: noqa: E402,I001

import argparse
import asyncio
import hashlib
import json
import mimetypes
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.cos import cos_adapter, parse_data_url
from app.core.config import settings
from app.models.base import utc_now


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp"}


@dataclass
class MigrationStats:
    rows: int = 0
    images: int = 0
    uploaded: int = 0
    skipped: int = 0
    failed: int = 0


def load_json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def is_cos_url(value: str) -> bool:
    if settings.cos_public_base_url and value.startswith(settings.cos_public_base_url.rstrip("/") + "/"):
        return True
    host = urlparse(value).netloc.lower()
    return host == f"{settings.cos_bucket}.cos.{settings.cos_region}.myqcloud.com"


def is_image_url(value: str) -> bool:
    if value.startswith("data:image/"):
        return True
    if value.startswith("/"):
        return Path(value).suffix.lower() in IMAGE_EXTENSIONS
    return value.startswith(("http://", "https://"))


def infer_filename(label: str, source: str, mime_type: str) -> str:
    if not source.startswith("data:"):
        name = Path(urlparse(source).path).name if source.startswith(("http://", "https://")) else Path(source).name
        if name:
            return name
    suffix = mimetypes.guess_extension(mime_type) or ".bin"
    return f"{label}{suffix}"


class ImageRehoster:
    def __init__(self, *, apply: bool) -> None:
        self.apply = apply
        self.cache: dict[str, str] = {}
        self.stats = MigrationStats()

    async def fetch_image(self, client: httpx.AsyncClient, source: str) -> tuple[bytes, str]:
        if source.startswith("data:image/"):
            return parse_data_url(source)
        if source.startswith("/"):
            candidates = [
                Path(__file__).resolve().parents[1] / "public" / source.lstrip("/"),
                Path(__file__).resolve().parents[2] / "frontend" / "public" / source.lstrip("/"),
            ]
            for public_file in candidates:
                if public_file.is_file():
                    mime_type = mimetypes.guess_type(public_file.name)[0] or "application/octet-stream"
                    return public_file.read_bytes(), mime_type
            raise FileNotFoundError(f"Local image does not exist: {source}")
        response = await client.get(source)
        response.raise_for_status()
        mime_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
        if not mime_type.startswith("image/"):
            mime_type = mimetypes.guess_type(urlparse(source).path)[0] or "application/octet-stream"
        return response.content, mime_type

    async def rehost_url(self, client: httpx.AsyncClient, source: str, *, label: str) -> tuple[str, bool]:
        if not is_image_url(source):
            self.stats.skipped += 1
            return source, False
        if source.startswith(("http://", "https://")) and is_cos_url(source):
            self.stats.skipped += 1
            return source, False
        self.stats.images += 1
        if not self.apply:
            return source, True
        try:
            content, mime_type = await self.fetch_image(client, source)
            cache_key = f"{mime_type}:{hashlib.sha256(content).hexdigest()}"
            if cache_key not in self.cache:
                uploaded = await cos_adapter.upload_bytes(
                    content=content,
                    mime_type=mime_type,
                    filename=infer_filename(label, source, mime_type),
                )
                self.cache[cache_key] = uploaded.url
                self.stats.uploaded += 1
            return self.cache[cache_key], True
        except Exception as error:
            self.stats.failed += 1
            print(f"Failed to migrate {label}: {source} ({error})")
            return source, False


async def migrate_templates(connection, client: httpx.AsyncClient, rehoster: ImageRehoster) -> None:
    rows = (
        await connection.execute(
            text('SELECT "id", "preview_image_url", "reference_image_urls" FROM "nft_visual_templates"')
        )
    ).mappings()
    json_value_sql = "CAST(:reference_image_urls AS json)" if connection.dialect.name == "postgresql" else ":reference_image_urls"
    for row in rows:
        row_changed = False
        preview_url, changed = await rehoster.rehost_url(
            client,
            row["preview_image_url"],
            label=f"nft-template-{row['id']}-preview",
        )
        row_changed = row_changed or changed

        references_value = load_json_value(row["reference_image_urls"])
        reference_urls: list[str] = []
        for index, item in enumerate(references_value if isinstance(references_value, list) else []):
            if not isinstance(item, str):
                reference_urls.append(item)
                continue
            next_item, item_changed = await rehoster.rehost_url(
                client,
                item,
                label=f"nft-template-{row['id']}-reference-{index + 1}",
            )
            row_changed = row_changed or item_changed
            reference_urls.append(next_item)

        if not reference_urls and preview_url:
            reference_urls = [preview_url]
            row_changed = True

        if not row_changed:
            continue

        rehoster.stats.rows += 1
        if rehoster.apply:
            await connection.execute(
                text(
                    'UPDATE "nft_visual_templates" SET "preview_image_url" = :preview_image_url, '
                    f'"reference_image_urls" = {json_value_sql}, "updated_at" = :updated_at WHERE "id" = :id'
                ),
                {
                    "id": row["id"],
                    "preview_image_url": preview_url,
                    "reference_image_urls": json.dumps(reference_urls, ensure_ascii=False),
                    "updated_at": utc_now(),
                },
            )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Rehost nft_visual_templates images on COS.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Count images that would be uploaded.")
    mode.add_argument("--apply", action="store_true", help="Upload images and update nft_visual_templates.")
    args = parser.parse_args()

    if args.apply and not cos_adapter.configured:
        print("COS is not configured. Set COS_BUCKET, COS_REGION, COS_SECRET_ID, and COS_SECRET_KEY in .env first.")
        return 2

    engine = create_async_engine(settings.database_url)
    rehoster = ImageRehoster(apply=args.apply)
    async with httpx.AsyncClient(timeout=settings.cos_timeout_seconds) as client:
        async with engine.begin() as connection:
            await migrate_templates(connection, client, rehoster)
    await engine.dispose()

    action = "updated" if args.apply else "would update"
    print(
        f"{action} rows={rehoster.stats.rows} images={rehoster.stats.images} "
        f"uploaded={rehoster.stats.uploaded} skipped={rehoster.stats.skipped} failed={rehoster.stats.failed}"
    )
    return 1 if rehoster.stats.failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
