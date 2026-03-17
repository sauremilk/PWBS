"""Alembic env.py  async migration runner (TASK-018).

Reads DATABASE_URL from Pydantic Settings and runs migrations
using an async SQLAlchemy engine (asyncpg).
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from pwbs.core.config import get_settings

# Import all models so Base.metadata contains all tables
from pwbs.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url() -> str:
    """Get database URL from Settings, falling back to alembic.ini."""
    try:
        settings = get_settings()
        return settings.database_url
    except Exception:
        url = config.get_main_option("sqlalchemy.url")
        if url is None:
            raise RuntimeError(
                "DATABASE_URL not set and sqlalchemy.url not configured in alembic.ini"
            ) from None
        return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode  emit SQL to stdout."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations against a live connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
