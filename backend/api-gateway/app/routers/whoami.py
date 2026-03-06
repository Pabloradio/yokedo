# app/routers/whoami.py

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["auth-context"])


@router.get("/whoami")
async def whoami(request: Request) -> dict[str, str]:
    # This endpoint is protected by AuthContextMiddleware.
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user is None:
        # Should not happen if middleware is working correctly.
        return {"user_id": "unknown"}
    return {"user_id": auth_user.user_id}
