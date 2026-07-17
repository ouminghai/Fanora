"""Reliable Alembic migration runner for remote PostgreSQL connections."""

import time
from collections.abc import Callable
from pathlib import Path

from alembic.config import Config
from sqlalchemy.exc import OperationalError

from alembic import command
from app.core.config import settings
from app.core.logging import logger


def upgrade_to_head() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_dir / "alembic.ini")), "head")


def run_migrations_with_retry(
    migrate: Callable[[], None] = upgrade_to_head,
    *,
    max_attempts: int = settings.migration_max_attempts,
    base_delay_seconds: float = settings.migration_retry_delay_seconds,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Retry transient connection failures without hiding persistent errors."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(1, max_attempts + 1):
        try:
            migrate()
            logger.info("database_migrations_complete", attempt=attempt)
            return
        except OperationalError:
            if attempt == max_attempts:
                logger.exception("database_migrations_failed", attempt=attempt)
                raise
            delay = base_delay_seconds * attempt
            logger.warning(
                "database_migration_connection_retry",
                attempt=attempt,
                max_attempts=max_attempts,
                retry_in_seconds=delay,
            )
            sleep(delay)


if __name__ == "__main__":
    run_migrations_with_retry()
