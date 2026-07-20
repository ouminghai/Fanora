"""Async SQLModel database lifecycle and health checks."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.logging import logger


def _engine_options(url: str) -> dict:
    if url.startswith("sqlite+aiosqlite:///:memory:"):
        return {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {
        "pool_pre_ping": True,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout_seconds,
        "pool_recycle": settings.database_pool_recycle_seconds,
        "connect_args": settings.postgres_connect_args,
    }


def _enable_sqlite_foreign_keys(dbapi_connection, _) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class DatabaseService:
    def __init__(self) -> None:
        self.engine: AsyncEngine = create_async_engine(settings.database_url, **_engine_options(settings.database_url))
        if settings.database_url.startswith("sqlite"):
            event.listen(self.engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def initialize(self) -> None:
        if settings.auto_create_schema:
            import app.models.database  # noqa: F401
            from app.services.product_seed import seed_product_defaults

            async with self.engine.begin() as connection:
                await connection.run_sync(SQLModel.metadata.create_all)
            async with self.session_factory() as session:
                await seed_product_defaults(session)
        logger.info("database_initialized", auto_create_schema=settings.auto_create_schema)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            yield session

    async def health_check(self) -> bool:
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            logger.exception("database_health_check_failed")
            return False

    async def close(self) -> None:
        await self.engine.dispose()


database_service = DatabaseService()


async def get_database_session() -> AsyncIterator[AsyncSession]:
    async with database_service.session() as session:
        yield session
