from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# --- Import configuration and models ---
from app.database import DATABASE_URL
from app.models.base import Base

# IMPORTANT:
# Import models so they are registered into Base.metadata
import app.models.availability  # noqa: F401

# --- Alembic config ---
config = context.config

# Use the ASYNC database URL directly (asyncpg)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# --- Logging configuration ---
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Target metadata for autogenerate ---
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures Alembic with just the database URL.
    No actual DB connection is created.
    """
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        version_table="alembic_version_availability",
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """
    Configure Alembic context and run migrations.

    This function is executed in a synchronous context,
    even though the engine is async.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="alembic_version_availability",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using an async engine.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as async_connection:
        # Run migrations in a synchronous context
        await async_connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
