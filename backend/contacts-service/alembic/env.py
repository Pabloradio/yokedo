from logging.config import fileConfig
import asyncio

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

from app.core.settings import settings
from app.models.base import Base
from sqlalchemy.engine import Connection


from typing import Optional, Literal
from sqlalchemy.schema import SchemaItem


# --- Alembic config ---
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# --- Metadata ---
target_metadata = Base.metadata


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
        return name in {"contact_requests"}
    return True


# --- Migration runner ---
def run_migrations_online():
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    async def run_async_migrations():
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


# --- Entry point ---
if context.is_offline_mode():
    raise NotImplementedError("Offline migrations not supported")
else:
    run_migrations_online()