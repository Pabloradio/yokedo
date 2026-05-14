from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.settings import settings
from app.database import engine
from app.routers import invitations
from app.models import users_stub


_ = engine  # Avoid unused import warning; engine will be used in lifespan later.
_ = users_stub  # Register users table stub for runtime FK resolution.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    print("DATABASE_URL loaded:", settings.database_url)

    yield

    # --- shutdown ---
    # (más adelante: cerrar conexiones, etc.)


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(invitations.router)