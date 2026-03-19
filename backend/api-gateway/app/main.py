#backend/api-gateway/app/main.py

from fastapi import FastAPI
from app.middleware.request_id import RequestIdMiddleware
from app.routers.health import router as health_router
from app.routers.proxy_auth import router as proxy_auth_router
from app.routers.root import router as root_router
from fastapi.middleware.cors import CORSMiddleware
from app.settings import get_cors_allowed_origins
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.auth_context import AuthContextMiddleware
from app.routers.whoami import router as whoami_router


def create_app() -> FastAPI:
    app = FastAPI(title="api-gateway")

    allowed_origins = get_cors_allowed_origins()
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(root_router)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthContextMiddleware)
    app.include_router(health_router)
    app.include_router(proxy_auth_router)
    app.include_router(whoami_router)
    
    return app


app = create_app()
