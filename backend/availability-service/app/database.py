from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.settings import settings

# 1. Construimos la URL de conexión (estándar para asyncpg)
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:"
    f"{settings.postgres_password}@{settings.postgres_host}:"
    f"{settings.postgres_port}/{settings.postgres_db}"
)

# 2. Creamos el motor de SQLAlchemy en modo asíncrono
engine = create_async_engine(DATABASE_URL, echo=True)

# 3. Creamos un "sessionmaker" que generará sesiones asíncronas
async_session = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

print(f"[DEBUG] DATABASE_URL = {DATABASE_URL}")


import asyncio
from sqlalchemy import text

async def test_connection():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            db_version = result.scalar()
            print(f"[SUCCESS] Connected to PostgreSQL – Version: {db_version}")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
