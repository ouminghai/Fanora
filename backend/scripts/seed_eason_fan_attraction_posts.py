"""Synchronize the existing Echo posts and Quests from one database to another."""

import argparse
import asyncio
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import select

from app.core.config import settings
from app.models.community import CommunityPost, FanTask
from app.models.user import Community, User, UserProfile
from app.services.product_seed import OFFICIAL_COMMUNITY_ID


@dataclass(frozen=True, slots=True)
class CommunitySnapshot:
    users: list[dict[str, Any]]
    user_profiles: list[dict[str, Any]]
    community: dict[str, Any]
    posts: list[dict[str, Any]]
    tasks: list[dict[str, Any]]


def async_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def create_engine(url: str) -> AsyncEngine:
    normalized_url = async_database_url(url)
    options = {} if normalized_url.startswith("sqlite") else {"pool_pre_ping": True}
    return create_async_engine(normalized_url, **options)


def image_url_from_task(task: FanTask) -> str:
    presentation = task.validation_rule.get("presentation", {})
    return presentation.get("image_url", "") if isinstance(presentation, dict) else ""


def validate_snapshot(
    *,
    users: list[User],
    community: Community,
    posts: list[CommunityPost],
    tasks: list[FanTask],
) -> None:
    if not posts:
        raise RuntimeError(f"Source community {community.id} has no community_posts")
    if not tasks:
        raise RuntimeError(f"Source community {community.id} has no fan_tasks")

    user_ids = {user.id for user in users}
    referenced_user_ids = {
        community.owner_user_id,
        *(post.author_user_id for post in posts),
        *(task.created_by_user_id for task in tasks),
    }
    missing_user_ids = sorted(referenced_user_ids - user_ids)
    if missing_user_ids:
        raise RuntimeError(f"Source database is missing referenced users: {', '.join(missing_user_ids)}")

    post_ids = {post.id for post in posts}
    missing_target_post_ids = sorted(
        task.target_post_id for task in tasks if task.target_post_id is not None and task.target_post_id not in post_ids
    )
    if missing_target_post_ids:
        raise RuntimeError(
            "Source tasks reference posts outside the selected community: " + ", ".join(missing_target_post_ids)
        )

    posts_without_base64 = [
        post.id for post in posts if not post.cover_url or not post.cover_url.startswith("data:image/")
    ]
    if posts_without_base64:
        raise RuntimeError(
            "Source posts do not contain Base64 cover images: " + ", ".join(posts_without_base64)
        )

    tasks_without_base64 = [task.id for task in tasks if not image_url_from_task(task).startswith("data:image/")]
    if tasks_without_base64:
        raise RuntimeError(
            "Source tasks do not contain Base64 presentation images: " + ", ".join(tasks_without_base64)
        )


async def load_snapshot(source_engine: AsyncEngine, community_id: str) -> CommunitySnapshot:
    session_factory = async_sessionmaker(source_engine, expire_on_commit=False)
    async with session_factory() as session:
        community = await session.get(Community, community_id)
        if community is None:
            raise RuntimeError(f"Source community is missing: {community_id}")

        posts = (
            await session.execute(
                select(CommunityPost)
                .where(CommunityPost.community_id == community_id)
                .order_by(CommunityPost.created_at, CommunityPost.id)
            )
        ).scalars().all()
        tasks = (
            await session.execute(
                select(FanTask).where(FanTask.community_id == community_id).order_by(FanTask.created_at, FanTask.id)
            )
        ).scalars().all()

        referenced_user_ids = {
            community.owner_user_id,
            *(post.author_user_id for post in posts),
            *(task.created_by_user_id for task in tasks),
        }
        users = (
            (
                await session.execute(
                    select(User).where(User.id.in_(referenced_user_ids)).order_by(User.created_at, User.id)
                )
            )
            .scalars()
            .all()
        )
        user_profiles = (
            (
                await session.execute(
                    select(UserProfile)
                    .where(UserProfile.user_id.in_(referenced_user_ids))
                    .order_by(UserProfile.created_at, UserProfile.user_id)
                )
            )
            .scalars()
            .all()
        )

        validate_snapshot(users=users, community=community, posts=posts, tasks=tasks)
        return CommunitySnapshot(
            users=[user.model_dump() for user in users],
            user_profiles=[profile.model_dump() for profile in user_profiles],
            community=community.model_dump(),
            posts=[post.model_dump() for post in posts],
            tasks=[task.model_dump() for task in tasks],
        )


async def apply_snapshot(target_engine: AsyncEngine, snapshot: CommunitySnapshot) -> None:
    session_factory = async_sessionmaker(target_engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            for values in snapshot.users:
                await session.merge(User(**values))
            await session.flush()

            for values in snapshot.user_profiles:
                await session.merge(UserProfile(**values))
            await session.flush()

            await session.merge(Community(**snapshot.community))
            await session.flush()

            for values in snapshot.posts:
                await session.merge(CommunityPost(**values))
            await session.flush()

            for values in snapshot.tasks:
                await session.merge(FanTask(**values))


async def synchronize(
    *,
    source_database_url: str,
    target_database_url: str | None,
    community_id: str,
    dry_run: bool,
) -> None:
    normalized_source = async_database_url(source_database_url)
    normalized_target = async_database_url(target_database_url) if target_database_url else None
    if normalized_target and normalized_source == normalized_target:
        raise RuntimeError("Source and target database URLs must be different")

    source_engine = create_engine(normalized_source)
    target_engine: AsyncEngine | None = None
    try:
        snapshot = await load_snapshot(source_engine, community_id)
        print(
            "Source snapshot validated: "
            f"users={len(snapshot.users)}, user_profiles={len(snapshot.user_profiles)}, communities=1, "
            f"community_posts={len(snapshot.posts)}, fan_tasks={len(snapshot.tasks)}"
        )
        if dry_run:
            return
        if not normalized_target:
            raise RuntimeError("Target database URL is required unless --dry-run is used")

        target_engine = create_engine(normalized_target)
        await apply_snapshot(target_engine, snapshot)
        print(
            "Database synchronization completed: "
            f"users={len(snapshot.users)}, user_profiles={len(snapshot.user_profiles)}, communities=1, "
            f"community_posts={len(snapshot.posts)}, fan_tasks={len(snapshot.tasks)}"
        )
    finally:
        await source_engine.dispose()
        if target_engine is not None:
            await target_engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-database-url",
        default=os.getenv("SOURCE_DATABASE_URL") or settings.database_url,
        help="Database containing the verified test data (default: SOURCE_DATABASE_URL or DATABASE_URL)",
    )
    parser.add_argument(
        "--target-database-url",
        default=os.getenv("TARGET_DATABASE_URL"),
        help="Destination database (default: TARGET_DATABASE_URL)",
    )
    parser.add_argument("--community-id", default=OFFICIAL_COMMUNITY_ID, help="Community data to synchronize")
    parser.add_argument("--dry-run", action="store_true", help="Validate source data without writing to the target")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(
        synchronize(
            source_database_url=arguments.source_database_url,
            target_database_url=arguments.target_database_url,
            community_id=arguments.community_id,
            dry_run=arguments.dry_run,
        )
    )
