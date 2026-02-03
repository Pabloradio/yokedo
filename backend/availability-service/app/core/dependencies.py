# app/core/dependencies.py

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an AsyncSession.

    Important:
    - This microservice must NOT import ORM models from other services (e.g. User from auth-service).
    - We only need a session bound to this service DB connection.
    """
    async with async_session() as session:
        yield session
