"""Optional PostgreSQL checkpoint adapter for LangGraph runs."""

from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import settings
from app.core.logging import logger


class CheckpointManager:
    def __init__(self) -> None:
        self._pool: Any | None = None
        self._saver: AsyncPostgresSaver | None = None

    async def initialize(self) -> AsyncPostgresSaver | None:
        if not settings.checkpoint_database_url:
            logger.info("langgraph_checkpointing_disabled")
            return None
        if self._saver:
            return self._saver

        pool: Any = AsyncConnectionPool(
            conninfo=settings.checkpoint_database_url,
            open=False,
            min_size=1,
            max_size=settings.checkpoint_pool_size,
            kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row},
        )
        await pool.open(wait=True)
        saver = AsyncPostgresSaver(pool)
        if settings.checkpoint_auto_setup:
            await saver.setup()
        self._pool = pool
        self._saver = saver
        logger.info("langgraph_checkpointing_initialized")
        return saver

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("langgraph_checkpointing_closed")


checkpoint_manager = CheckpointManager()
