from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.settings import settings
from app.database import engine

_ = engine # Evitar "unused import" para el engine, que se usará en el lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    print("DATABASE_URL loaded:", settings.database_url)

    yield

    # --- shutdown ---
    # (más adelante: cerrar conexiones, etc.)


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}