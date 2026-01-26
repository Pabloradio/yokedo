from logging.config import fileConfig
import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.database import DATABASE_URL
from app.migrations.metadata import migration_metadata

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = migration_metadata

# ---------------------------------------------------------------------
# Autogenerate scope control
# ---------------------------------------------------------------------

OWNED_TABLES = {
    "availability_weekly_templates",
    "availability_day_overrides",
    "availabilities",
    "alembic_version_availability",
}

EXTERNAL_TABLES = {
    "users",
    "user_sessions",
    "alembic_version_auth",
    "plan_category",
}

def include_object(object_, name, type_, reflected, compare_to):
    """
    Restrict Alembic autogenerate to objects owned by availability-service.

    - External tables are excluded even if present in metadata as stubs.
    - Only owned tables (and their columns/constraints/indexes) are considered.
    """
    if type_ == "table":
        if name in EXTERNAL_TABLES:
            return False
        return name in OWNED_TABLES

    parent_table = getattr(object_, "table", None)
    if parent_table is not None:
        return parent_table.name in OWNED_TABLES

    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        version_table="alembic_version_availability",
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="alembic_version_availability",
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as async_connection:
        await async_connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
