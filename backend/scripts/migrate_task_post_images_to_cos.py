"""Rehost existing community, task, and membership images on Tencent Cloud COS.

Run from backend/:
    python scripts/migrate_task_post_images_to_cos.py --dry-run
    python scripts/migrate_task_post_images_to_cos.py --apply
"""

# ruff: noqa: E402,I001

import argparse
import asyncio
import hashlib
import json
import mimetypes
import re
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


IMAGE_MARKDOWN_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
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
        except json.JSONDecodeError:
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
    if not value.startswith(("http://", "https://")):
        return False
    path = urlparse(value).path
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS or any(host in value for host in ("beeimg", "imglnk"))


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
            public_file = Path(__file__).resolve().parents[1] / "public" / source.lstrip("/")
            if not public_file.is_file():
                raise FileNotFoundError(f"Local image does not exist: {source}")
            mime_type = mimetypes.guess_type(public_file.name)[0] or "application/octet-stream"
            return public_file.read_bytes(), mime_type
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

    async def replace_value(self, client: httpx.AsyncClient, value: Any, *, label: str) -> tuple[Any, bool]:
        value = load_json_value(value)
        if isinstance(value, str):
            next_value, changed = await self.rehost_url(client, value, label=label)
            return next_value, changed
        if isinstance(value, list):
            changed = False
            result = []
            for index, item in enumerate(value):
                next_item, item_changed = await self.replace_value(client, item, label=f"{label}-{index + 1}")
                changed = changed or item_changed
                result.append(next_item)
            return result, changed
        if isinstance(value, dict):
            changed = False
            result = {}
            for key, item in value.items():
                next_item, item_changed = await self.replace_value(client, item, label=f"{label}-{key}")
                changed = changed or item_changed
                result[key] = next_item
            return result, changed
        return value, False

    async def replace_markdown_images(self, client: httpx.AsyncClient, body: str, *, label: str) -> tuple[str, bool]:
        changed = False
        result = body
        for index, match in enumerate(list(IMAGE_MARKDOWN_RE.finditer(body))):
            source = match.group(2)
            next_url, url_changed = await self.rehost_url(client, source, label=f"{label}-body-{index + 1}")
            if url_changed and self.apply and next_url != source:
                result = result.replace(match.group(0), f"![{match.group(1)}]({next_url})")
            changed = changed or url_changed
        return result, changed


async def migrate_community_posts(connection, client: httpx.AsyncClient, rehoster: ImageRehoster) -> None:
    rows = (
        await connection.execute(text('SELECT "id", "cover_url", "image_urls", "body" FROM "community_posts"'))
    ).mappings()
    json_value_sql = "CAST(:image_urls AS json)" if connection.dialect.name == "postgresql" else ":image_urls"
    for row in rows:
        row_changed = False
        cover_url, changed = await rehoster.replace_value(client, row["cover_url"], label=f"community-post-{row['id']}-cover")
        row_changed = row_changed or changed
        image_urls, changed = await rehoster.replace_value(client, row["image_urls"], label=f"community-post-{row['id']}-image")
        row_changed = row_changed or changed
        body, changed = await rehoster.replace_markdown_images(client, row["body"] or "", label=f"community-post-{row['id']}")
        row_changed = row_changed or changed
        if not row_changed:
            continue
        rehoster.stats.rows += 1
        if rehoster.apply:
            await connection.execute(
                text(
                    f'UPDATE "community_posts" SET "cover_url" = :cover_url, "image_urls" = {json_value_sql}, '
                    '"body" = :body WHERE "id" = :id'
                ),
                {
                    "id": row["id"],
                    "cover_url": cover_url,
                    "image_urls": json.dumps(image_urls, ensure_ascii=False),
                    "body": body,
                },
            )


async def migrate_fan_tasks(connection, client: httpx.AsyncClient, rehoster: ImageRehoster) -> None:
    rows = (await connection.execute(text('SELECT "id", "validation_rule" FROM "fan_tasks"'))).mappings()
    json_value_sql = "CAST(:validation_rule AS json)" if connection.dialect.name == "postgresql" else ":validation_rule"
    for row in rows:
        validation_rule, changed = await rehoster.replace_value(
            client,
            row["validation_rule"],
            label=f"fan-task-{row['id']}",
        )
        if not changed:
            continue
        rehoster.stats.rows += 1
        if rehoster.apply:
            await connection.execute(
                text(f'UPDATE "fan_tasks" SET "validation_rule" = {json_value_sql} WHERE "id" = :id'),
                {"id": row["id"], "validation_rule": json.dumps(validation_rule, ensure_ascii=False)},
            )


async def migrate_membership_levels(connection, client: httpx.AsyncClient, rehoster: ImageRehoster) -> None:
    rows = (await connection.execute(text('SELECT "code", "badge_image_url" FROM "membership_levels"'))).mappings()
    for row in rows:
        badge_image_url, changed = await rehoster.replace_value(
            client,
            row["badge_image_url"],
            label=f"membership-level-{row['code']}",
        )
        if not changed:
            continue
        rehoster.stats.rows += 1
        if rehoster.apply:
            await connection.execute(
                text('UPDATE "membership_levels" SET "badge_image_url" = :badge_image_url WHERE "code" = :code'),
                {"code": row["code"], "badge_image_url": badge_image_url},
            )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Rehost existing community, task, and membership images on COS.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Count images that would be uploaded.")
    mode.add_argument("--apply", action="store_true", help="Upload images and update community_posts/fan_tasks/membership_levels.")
    args = parser.parse_args()

    if args.apply and not cos_adapter.configured:
        print("COS is not configured. Set COS_BUCKET, COS_REGION, COS_SECRET_ID, and COS_SECRET_KEY in .env first.")
        return 2

    engine = create_async_engine(settings.database_url)
    rehoster = ImageRehoster(apply=args.apply)
    async with httpx.AsyncClient(timeout=settings.cos_timeout_seconds) as client:
        async with engine.begin() as connection:
            await migrate_community_posts(connection, client, rehoster)
            await migrate_fan_tasks(connection, client, rehoster)
            await migrate_membership_levels(connection, client, rehoster)
    await engine.dispose()

    action = "updated" if args.apply else "would update"
    print(
        f"{action} rows={rehoster.stats.rows} images={rehoster.stats.images} "
        f"uploaded={rehoster.stats.uploaded} skipped={rehoster.stats.skipped} failed={rehoster.stats.failed}"
    )
    return 1 if rehoster.stats.failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
