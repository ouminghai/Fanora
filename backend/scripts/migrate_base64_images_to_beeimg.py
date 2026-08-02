"""Migrate persisted image data URLs to BeeImg-hosted URLs.

Run from backend/:
    python scripts/migrate_base64_images_to_beeimg.py --dry-run
    python scripts/migrate_base64_images_to_beeimg.py --apply
"""

import argparse
import asyncio
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.beeimg import beeimg_adapter, parse_data_url
from app.core.config import settings


@dataclass(frozen=True)
class FieldTarget:
    table: str
    id_column: str
    field: str
    is_json: bool = False


TARGETS = [
    FieldTarget("community_posts", "id", "cover_url"),
    FieldTarget("community_posts", "id", "image_urls", is_json=True),
    FieldTarget("community_replies", "id", "image_urls", is_json=True),
    FieldTarget("fan_tasks", "id", "validation_rule", is_json=True),
    FieldTarget("task_participations", "id", "submission", is_json=True),
    FieldTarget("nft_applications", "id", "image_data"),
    FieldTarget("nft_applications", "id", "story_image_urls", is_json=True),
    FieldTarget("user_profiles", "user_id", "avatar_url"),
    FieldTarget("communities", "id", "logo_url"),
]


def is_data_image(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("data:image/") and ";base64," in value[:100]


def load_json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def count_data_images(value: Any) -> int:
    value = load_json_value(value)
    if is_data_image(value):
        return 1
    if isinstance(value, list):
        return sum(count_data_images(item) for item in value)
    if isinstance(value, dict):
        return sum(count_data_images(item) for item in value.values())
    return 0


class Migrator:
    def __init__(self, *, apply: bool) -> None:
        self.apply = apply
        self.upload_cache: dict[str, str] = {}
        self.upload_count = 0

    async def replace_value(self, value: Any, *, label: str) -> tuple[Any, int]:
        value = load_json_value(value)
        if is_data_image(value):
            if not self.apply:
                return value, 1
            content, mime_type = parse_data_url(value)
            cache_key = f"{mime_type}:{hashlib.sha256(content).hexdigest()}"
            if cache_key not in self.upload_cache:
                uploaded = await beeimg_adapter.upload_bytes(content=content, mime_type=mime_type, filename=label)
                self.upload_cache[cache_key] = uploaded.url
                self.upload_count += 1
            return self.upload_cache[cache_key], 1
        if isinstance(value, list):
            changed = 0
            result = []
            for index, item in enumerate(value):
                replaced, item_changed = await self.replace_value(item, label=f"{label}-{index + 1}")
                changed += item_changed
                result.append(replaced)
            return result, changed
        if isinstance(value, dict):
            changed = 0
            result = {}
            for key, item in value.items():
                replaced, item_changed = await self.replace_value(item, label=f"{label}-{key}")
                changed += item_changed
                result[key] = replaced
            return result, changed
        return value, 0

    async def migrate_target(self, connection, target: FieldTarget) -> tuple[int, int]:
        json_value_sql = (
            "CAST(:value AS json)" if target.is_json and connection.dialect.name == "postgresql" else ":value"
        )
        rows = (
            await connection.execute(
                text(f'SELECT "{target.id_column}" AS row_id, "{target.field}" AS value FROM "{target.table}"')
            )
        ).mappings()
        changed_rows = 0
        changed_images = 0
        for row in rows:
            original = row["value"]
            replaced, image_count = await self.replace_value(
                original,
                label=f"{target.table}-{target.field}-{row['row_id']}",
            )
            if image_count == 0:
                continue
            changed_rows += 1
            changed_images += image_count
            if self.apply:
                stored_value = json.dumps(replaced, ensure_ascii=False) if target.is_json else replaced
                await connection.execute(
                    text(
                        f'UPDATE "{target.table}" SET "{target.field}" = {json_value_sql} '
                        f'WHERE "{target.id_column}" = :row_id'
                    ),
                    {"value": stored_value, "row_id": row["row_id"]},
                )
        return changed_rows, changed_images


async def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate persisted base64 image data URLs to BeeImg.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Only count rows and images; do not upload or update.")
    mode.add_argument("--apply", action="store_true", help="Upload images and update the database.")
    args = parser.parse_args()

    if args.apply and not beeimg_adapter.configured:
        print("BeeImg is not configured. Set BEEIMG_TOKEN or BEEIMG_USERNAME/BEEIMG_PASSWORD in .env first.")
        return 2

    engine = create_async_engine(settings.database_url)
    migrator = Migrator(apply=args.apply)
    totals: dict[str, tuple[int, int]] = {}
    async with engine.begin() as connection:
        for target in TARGETS:
            changed_rows, changed_images = await migrator.migrate_target(connection, target)
            totals[f"{target.table}.{target.field}"] = (changed_rows, changed_images)
    await engine.dispose()

    action = "updated" if args.apply else "would update"
    for target, (rows, images) in totals.items():
        print(f"{target}: {action} {rows} rows / {images} images")
    if args.apply:
        print(f"Uploaded {migrator.upload_count} unique images to BeeImg.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
