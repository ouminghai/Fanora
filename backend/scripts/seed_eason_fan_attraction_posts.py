"""Synchronize the existing Echo posts and Quests from one database to another."""

import argparse
import asyncio
import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import select

from app.adapters.beeimg import beeimg_adapter, parse_data_url
from app.core.config import settings
from app.models.community import CommunityPost, FanTask
from app.models.user import AuthIdentity, Community, User, UserProfile, UserRole, UserSession, Wallet
from app.services.product_seed import OFFICIAL_COMMUNITY_ID

# Fill these values directly when you want to run the script without passing
# SOURCE_DATABASE_URL / TARGET_DATABASE_URL in the shell.
SOURCE_DATABASE_URL = "postgresql+psycopg://fanora:fanora-local-password@127.0.0.1:5432/fanora"
TARGET_DATABASE_URL = "postgresql://postgres:==========@sakura.proxy.rlwy.net:54128/railway?sslmode=require"
TARGET_MAX_ATTEMPTS = 5
TARGET_RETRY_DELAY_SECONDS = 8
CONTINUE_ON_ROW_ERROR = True
TARGET_PROXY_ENABLED = True
TARGET_PROXY_HOST = "127.0.0.1"
TARGET_PROXY_PORT = 7892
TARGET_PROXY_TYPE = "socks5"
DATA_IMAGE_PATTERN = re.compile(r"data:image/[a-zA-Z0-9.+-]+;base64,[a-zA-Z0-9+/=]+")


@dataclass(frozen=True, slots=True)
class CommunitySnapshot:
    users: list[dict[str, Any]]
    user_profiles: list[dict[str, Any]]
    user_roles: list[dict[str, Any]]
    user_sessions: list[dict[str, Any]]
    wallets: list[dict[str, Any]]
    auth_identities: list[dict[str, Any]]
    community: dict[str, Any]
    posts: list[dict[str, Any]]
    tasks: list[dict[str, Any]]


class SnapshotImageHoster:
    def __init__(self) -> None:
        self.upload_cache: dict[str, str] = {}
        self.upload_count = 0

    async def _host_data_url(self, value: str, *, label: str) -> str:
        content, mime_type = parse_data_url(value)
        cache_key = f"{mime_type}:{hashlib.sha256(content).hexdigest()}"
        if cache_key not in self.upload_cache:
            uploaded = await beeimg_adapter.upload_bytes(content=content, mime_type=mime_type, filename=label)
            self.upload_cache[cache_key] = uploaded.url
            self.upload_count += 1
        return self.upload_cache[cache_key]

    async def replace(self, value: Any, *, label: str) -> Any:
        if isinstance(value, str):
            matches = list(DATA_IMAGE_PATTERN.finditer(value))
            if not matches:
                return value
            parts: list[str] = []
            cursor = 0
            for index, match in enumerate(matches, start=1):
                parts.append(value[cursor : match.start()])
                parts.append(await self._host_data_url(match.group(0), label=f"{label}-{index}"))
                cursor = match.end()
            parts.append(value[cursor:])
            return "".join(parts)
        if isinstance(value, list):
            return [await self.replace(item, label=f"{label}-{index}") for index, item in enumerate(value, start=1)]
        if isinstance(value, dict):
            return {key: await self.replace(item, label=f"{label}-{key}") for key, item in value.items()}
        return value

    async def host_snapshot(self, snapshot: CommunitySnapshot) -> CommunitySnapshot:
        return CommunitySnapshot(
            users=snapshot.users,
            user_profiles=await self.replace(snapshot.user_profiles, label="user-profile"),
            user_roles=snapshot.user_roles,
            user_sessions=snapshot.user_sessions,
            wallets=snapshot.wallets,
            auth_identities=snapshot.auth_identities,
            community=await self.replace(snapshot.community, label="community"),
            posts=await self.replace(snapshot.posts, label="community-post"),
            tasks=await self.replace(snapshot.tasks, label="fan-task"),
        )


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
    options = (
        {} if normalized_url.startswith("sqlite") else {"pool_pre_ping": True, "connect_args": {"connect_timeout": 30}}
    )
    return create_async_engine(normalized_url, **options)


def enable_target_proxy(*, host: str, port: int, proxy_type: str) -> None:
    """Route Python TCP sockets through a local proxy before connecting to Railway Postgres."""

    try:
        import socks
    except ImportError as error:
        raise RuntimeError("PySocks is required for proxy mode. Run: uv add 'PySocks>=1.7'") from error

    proxy_types = {
        "socks5": socks.SOCKS5,
        "socks4": socks.SOCKS4,
        "http": socks.HTTP,
    }
    normalized_type = proxy_type.lower()
    if normalized_type not in proxy_types:
        raise RuntimeError("TARGET_PROXY_TYPE must be one of: socks5, socks4, http")

    socks.set_default_proxy(proxy_types[normalized_type], host, port)
    import socket

    socket.socket = socks.socksocket
    print(f"Target database proxy enabled: {normalized_type}://{host}:{port}")


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
        task.target_post_id
        for task in tasks
        if task.target_post_id is not None and task.target_post_id not in post_ids
    )
    if missing_target_post_ids:
        raise RuntimeError(
            "Source tasks reference posts outside the selected community: " + ", ".join(missing_target_post_ids)
        )

    posts_without_images = [post.id for post in posts if not post.cover_url and not post.image_urls]
    if posts_without_images:
        print("Warning: source posts do not contain images: " + ", ".join(posts_without_images))

    tasks_without_images = [task.id for task in tasks if not image_url_from_task(task)]
    if tasks_without_images:
        print("Warning: source tasks do not contain presentation images: " + ", ".join(tasks_without_images))


async def load_snapshot(source_engine: AsyncEngine, community_id: str) -> CommunitySnapshot:
    session_factory = async_sessionmaker(source_engine, expire_on_commit=False)
    async with session_factory() as session:
        community = await session.get(Community, community_id)
        if community is None:
            raise RuntimeError(f"Source community is missing: {community_id}")

        posts = (
            (
                await session.execute(
                    select(CommunityPost)
                    .where(CommunityPost.community_id == community_id)
                    .order_by(CommunityPost.created_at, CommunityPost.id)
                )
            )
            .scalars()
            .all()
        )
        tasks = (
            (
                await session.execute(
                    select(FanTask)
                    .where(FanTask.community_id == community_id)
                    .order_by(FanTask.created_at, FanTask.id)
                )
            )
            .scalars()
            .all()
        )

        content_user_ids = {
            community.owner_user_id,
            *(post.author_user_id for post in posts),
            *(task.created_by_user_id for task in tasks),
        }
        users = (await session.execute(select(User).order_by(User.created_at, User.id))).scalars().all()
        user_ids = {user.id for user in users}
        missing_content_user_ids = sorted(content_user_ids - user_ids)
        if missing_content_user_ids:
            raise RuntimeError(
                "Source database is missing content referenced users: " + ", ".join(missing_content_user_ids)
            )
        user_profiles = (
            (
                await session.execute(
                    select(UserProfile)
                    .where(UserProfile.user_id.in_(user_ids))
                    .order_by(UserProfile.created_at, UserProfile.user_id)
                )
            )
            .scalars()
            .all()
        )
        user_roles = (
            (
                await session.execute(
                    select(UserRole).where(UserRole.user_id.in_(user_ids)).order_by(UserRole.created_at, UserRole.id)
                )
            )
            .scalars()
            .all()
        )
        user_sessions = (
            (
                await session.execute(
                    select(UserSession)
                    .where(UserSession.user_id.in_(user_ids))
                    .order_by(UserSession.created_at, UserSession.id)
                )
            )
            .scalars()
            .all()
        )
        wallets = (
            (
                await session.execute(
                    select(Wallet).where(Wallet.user_id.in_(user_ids)).order_by(Wallet.created_at, Wallet.id)
                )
            )
            .scalars()
            .all()
        )
        auth_identities = (
            (
                await session.execute(
                    select(AuthIdentity)
                    .where(AuthIdentity.user_id.in_(user_ids))
                    .order_by(AuthIdentity.created_at, AuthIdentity.id)
                )
            )
            .scalars()
            .all()
        )

        validate_snapshot(users=users, community=community, posts=posts, tasks=tasks)
        return CommunitySnapshot(
            users=[user.model_dump() for user in users],
            user_profiles=[profile.model_dump() for profile in user_profiles],
            user_roles=[role.model_dump() for role in user_roles],
            user_sessions=[user_session.model_dump() for user_session in user_sessions],
            wallets=[wallet.model_dump() for wallet in wallets],
            auth_identities=[identity.model_dump() for identity in auth_identities],
            community=community.model_dump(),
            posts=[post.model_dump() for post in posts],
            tasks=[task.model_dump() for task in tasks],
        )


async def merge_rows(
    session,
    model,
    rows: list[dict[str, Any]],
    label: str,
    *,
    continue_on_error: bool,
) -> int:
    """Insert missing rows and overwrite existing rows that have the same primary key."""

    written = 0
    for values in rows:
        try:
            async with session.begin_nested():
                await session.merge(model(**values))
                await session.flush()
            written += 1
        except SQLAlchemyError as error:
            identifier = values.get("id") or values.get("user_id") or "<unknown>"
            if not continue_on_error:
                raise
            print(f"Warning: skipped {label} {identifier}: {error.__class__.__name__}: {error}")
    return written


async def apply_snapshot(
    target_engine: AsyncEngine,
    snapshot: CommunitySnapshot,
    *,
    continue_on_error: bool,
) -> dict[str, int]:
    session_factory = async_sessionmaker(target_engine, expire_on_commit=False)
    written: dict[str, int] = {}
    async with session_factory() as session:
        async with session.begin():
            written["users"] = await merge_rows(
                session, User, snapshot.users, "user", continue_on_error=continue_on_error
            )
            written["user_profiles"] = await merge_rows(
                session, UserProfile, snapshot.user_profiles, "user_profile", continue_on_error=continue_on_error
            )
            written["wallets"] = await merge_rows(
                session, Wallet, snapshot.wallets, "wallet", continue_on_error=continue_on_error
            )
            written["auth_identities"] = await merge_rows(
                session,
                AuthIdentity,
                snapshot.auth_identities,
                "auth_identity",
                continue_on_error=continue_on_error,
            )
            written["user_roles"] = await merge_rows(
                session, UserRole, snapshot.user_roles, "user_role", continue_on_error=continue_on_error
            )
            written["user_sessions"] = await merge_rows(
                session, UserSession, snapshot.user_sessions, "user_session", continue_on_error=continue_on_error
            )
            written["communities"] = await merge_rows(
                session, Community, [snapshot.community], "community", continue_on_error=continue_on_error
            )
            written["community_posts"] = await merge_rows(
                session, CommunityPost, snapshot.posts, "community_post", continue_on_error=continue_on_error
            )
            written["fan_tasks"] = await merge_rows(
                session, FanTask, snapshot.tasks, "fan_task", continue_on_error=continue_on_error
            )
    return written


async def apply_snapshot_with_retries(
    target_engine: AsyncEngine,
    snapshot: CommunitySnapshot,
    *,
    max_attempts: int,
    retry_delay_seconds: float,
    continue_on_error: bool,
) -> dict[str, int]:
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Applying snapshot to target database, attempt {attempt}/{max_attempts}")
            return await apply_snapshot(target_engine, snapshot, continue_on_error=continue_on_error)
        except SQLAlchemyError as error:
            if attempt == max_attempts:
                raise
            print(f"Warning: target database write failed: {error.__class__.__name__}: {error}")
            await asyncio.sleep(retry_delay_seconds)
    raise RuntimeError("Unreachable target retry state")


async def synchronize(
    *,
    source_database_url: str,
    target_database_url: str | None,
    community_id: str,
    dry_run: bool,
    target_max_attempts: int,
    target_retry_delay_seconds: float,
    continue_on_row_error: bool,
    target_proxy_enabled: bool,
    target_proxy_host: str,
    target_proxy_port: int,
    target_proxy_type: str,
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
            f"users={len(snapshot.users)}, user_profiles={len(snapshot.user_profiles)}, "
            f"wallets={len(snapshot.wallets)}, auth_identities={len(snapshot.auth_identities)}, "
            f"user_roles={len(snapshot.user_roles)}, user_sessions={len(snapshot.user_sessions)}, communities=1, "
            f"community_posts={len(snapshot.posts)}, fan_tasks={len(snapshot.tasks)}"
        )
        if dry_run:
            return
        if not normalized_target:
            raise RuntimeError("Target database URL is required unless --dry-run is used")
        if not beeimg_adapter.configured:
            raise RuntimeError("BeeImg must be configured before synchronizing images")

        image_hoster = SnapshotImageHoster()
        snapshot = await image_hoster.host_snapshot(snapshot)
        print(f"BeeImg image hosting completed: uploaded {image_hoster.upload_count} unique images")

        if target_proxy_enabled:
            enable_target_proxy(
                host=target_proxy_host,
                port=target_proxy_port,
                proxy_type=target_proxy_type,
            )
        target_engine = create_engine(normalized_target)
        written = await apply_snapshot_with_retries(
            target_engine,
            snapshot,
            max_attempts=target_max_attempts,
            retry_delay_seconds=target_retry_delay_seconds,
            continue_on_error=continue_on_row_error,
        )
        print(
            "Database synchronization completed; rows with the same primary key were overwritten: "
            + ", ".join(f"{label}={count}" for label, count in written.items())
        )
    finally:
        await source_engine.dispose()
        if target_engine is not None:
            await target_engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-database-url",
        default=SOURCE_DATABASE_URL or os.getenv("SOURCE_DATABASE_URL") or settings.database_url,
        help="Database containing the verified test data (default: SOURCE_DATABASE_URL constant, env, or DATABASE_URL)",
    )
    parser.add_argument(
        "--target-database-url",
        default=TARGET_DATABASE_URL or os.getenv("TARGET_DATABASE_URL"),
        help="Destination database (default: TARGET_DATABASE_URL constant or env)",
    )
    parser.add_argument("--community-id", default=OFFICIAL_COMMUNITY_ID, help="Community data to synchronize")
    parser.add_argument("--dry-run", action="store_true", help="Validate source data without writing to the target")
    parser.add_argument("--target-max-attempts", type=int, default=TARGET_MAX_ATTEMPTS, help="Target write retries")
    parser.add_argument(
        "--target-retry-delay-seconds",
        type=float,
        default=TARGET_RETRY_DELAY_SECONDS,
        help="Seconds to wait between target write retries",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop on the first row write error instead of warning and continuing",
    )
    parser.add_argument(
        "--no-target-proxy",
        action="store_true",
        help="Disable the local proxy for the target Railway database",
    )
    parser.add_argument("--target-proxy-host", default=TARGET_PROXY_HOST, help="Local proxy host for target database")
    parser.add_argument("--target-proxy-port", type=int, default=TARGET_PROXY_PORT, help="Local proxy port")
    parser.add_argument(
        "--target-proxy-type",
        default=TARGET_PROXY_TYPE,
        choices=["socks5", "socks4", "http"],
        help="Local proxy protocol",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(
        synchronize(
            source_database_url=arguments.source_database_url,
            target_database_url=arguments.target_database_url,
            community_id=arguments.community_id,
            dry_run=arguments.dry_run,
            target_max_attempts=arguments.target_max_attempts,
            target_retry_delay_seconds=arguments.target_retry_delay_seconds,
            continue_on_row_error=CONTINUE_ON_ROW_ERROR and not arguments.strict,
            target_proxy_enabled=TARGET_PROXY_ENABLED and not arguments.no_target_proxy,
            target_proxy_host=arguments.target_proxy_host,
            target_proxy_port=arguments.target_proxy_port,
            target_proxy_type=arguments.target_proxy_type,
        )
    )
