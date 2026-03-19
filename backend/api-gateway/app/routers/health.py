# backend/api-gateway/app/routers/health.py

from fastapi import APIRouter

router = APIRouter()


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> dict[str, str]:
    # Readiness for the gateway should not depend on the database.
    # We'll add downstream reachability checks later (short timeouts).
    return {"status": "ok"}

