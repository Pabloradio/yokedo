from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.settings import settings
from typing import AsyncGenerator

# --- Engine ---
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for debugging SQL
)


# --- Session factory ---
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --- Dependency ---
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session