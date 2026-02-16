#backend/api-gateway/app/main.py

from fastapi import FastAPI

from app.routers.health import router as health_router
from app.routers.proxy_auth import router as proxy_auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="api-gateway")
    app.include_router(health_router)
    app.include_router(proxy_auth_router)
    return app


app = create_app()
