"""Alembic environment for Fanora SQLModel tables."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models.database  # noqa: F401
from alembic import context
from app.core.config import settings

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)


def sync_database_url() -> str:
    return settings.database_url.replace("sqlite+aiosqlite", "sqlite").replace(
        "postgresql+asyncpg", "postgresql+psycopg"
    )


config.set_main_option("sqlalchemy.url", sync_database_url())
target_metadata = SQLModel.metadata


def include_object(object_, name, type_, reflected, compare_to):
    external_tables = {"checkpoint_blobs", "checkpoint_writes", "checkpoints"}
    return not (type_ == "table" and name in external_tables)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=settings.postgres_connect_args if settings.database_url.startswith("postgresql") else {},
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
