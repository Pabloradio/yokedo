from logging.config import fileConfig
import asyncio
from typing import Literal, Optional

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import SchemaItem

from app.core.settings import settings
from app.migrations.metadata import migration_metadata


# --- Alembic config ---
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# --- Metadata used only for Alembic autogenerate ---
target_metadata = migration_metadata


def include_object(
    object: SchemaItem,
    name: Optional[str],
    type_: Literal[
        "schema",
        "table",
        "column",
        "index",
        "unique_constraint",
        "foreign_key_constraint",
    ],
    reflected: bool,
    compare_to: Optional[SchemaItem],
) -> bool:
    if type_ == "table":
        return name in {"contact_requests", "contacts", "contact_events"}
    return True


def run_migrations_online() -> None:
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    def do_run_migrations(connection: Connection) -> None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version_contacts",
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    raise NotImplementedError("Offline migrations not supported")
else:
    run_migrations_online()