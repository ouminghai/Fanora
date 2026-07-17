import pytest
from sqlalchemy.exc import OperationalError

from app.core.migrations import run_migrations_with_retry


def transient_error() -> OperationalError:
    return OperationalError("alembic upgrade", {}, Exception("connection closed"))


def test_migration_retries_transient_database_disconnects() -> None:
    calls = 0
    delays: list[float] = []

    def migrate() -> None:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise transient_error()

    run_migrations_with_retry(
        migrate,
        max_attempts=3,
        base_delay_seconds=1,
        sleep=delays.append,
    )

    assert calls == 3
    assert delays == [1, 2]


def test_migration_stops_after_retry_budget_is_exhausted() -> None:
    calls = 0

    def migrate() -> None:
        nonlocal calls
        calls += 1
        raise transient_error()

    def no_wait(_: float) -> None:
        return None

    with pytest.raises(OperationalError):
        run_migrations_with_retry(
            migrate,
            max_attempts=2,
            base_delay_seconds=1,
            sleep=no_wait,
        )

    assert calls == 2
