# app/routers/root.py

from fastapi import APIRouter

router = APIRouter(tags=["root"])


@router.get("/")
async def root() -> dict[str, str]:
    # Minimal landing endpoint to avoid confusion when opening the gateway in a browser.
    return {"service": "api-gateway", "status": "ok"}