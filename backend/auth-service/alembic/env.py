from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# --- Importa configuración y modelos ---
from app.database import DATABASE_URL
from app.models.base import Base

from app.models.user import User
from app.models.user_sessions import UserSession


# --- Convierte la URL async en sync ---
SYNC_DATABASE_URL = DATABASE_URL.replace("asyncpg", "psycopg2")

# --- Configuración de Alembic ---
config = context.config
config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)

# --- Logging ---
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Importante: metadatos de los modelos ---
target_metadata = Base.metadata


def run_migrations_offline():
    """Ejecuta las migraciones en modo 'offline' (sin conexión)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Ejecuta las migraciones en modo 'online' (con conexión real)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
