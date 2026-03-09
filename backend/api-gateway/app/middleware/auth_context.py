# app/middleware/auth_context.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.settings import (
    AUTH_CONTEXT_CACHE_MAX_ENTRIES,
    AUTH_CONTEXT_CACHE_TTL_SECONDS,
    AUTH_TOKEN_VALIDATION_PATH,
    PROXY_CONNECT_TIMEOUT_SECONDS,
    PROXY_READ_TIMEOUT_SECONDS,
    get_auth_service_base_url,
)
from app.settings import REQUEST_ID_HEADER


@dataclass(frozen=True)
class AuthUserContext:
    # Minimal identity context propagated through the gateway.
    user_id: str
    is_admin: bool = False


@dataclass
class _CachedAuthContext:
    expires_at_epoch: float
    context: AuthUserContext


class AuthContextMiddleware(BaseHTTPMiddleware):
    """
    Gateway authentication middleware (MVP).

    Design choice:
    - The gateway does NOT verify JWT signature locally.
    - It delegates validation to auth-service by calling a protected endpoint (AUTH_TOKEN_VALIDATION_PATH).
      This avoids duplicating crypto/JWT logic across services and keeps auth-service as the source of truth.

    Behaviour:
    - Protects /api/* except /api/auth/* (login/register/docs/refresh remain public).
    - On success, stores AuthUserContext in request.state.auth_user.
    - On failure, returns 401/403 with JSON payload.
    - Adds basic request-id propagation to error responses.

    Security note:
    - Internal identity headers such as X-User-ID and X-User-Is-Admin are trusted
      only inside the backend network and only when injected by the gateway.
    - Downstream services must not trust client-provided versions of these headers
      if they are ever exposed directly outside the trusted network.

    Limitations (accepted for MVP):
    - In-memory cache: per-process and resets on restart.
    - If gateway is replicated, cache is per replica.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._cache: dict[str, _CachedAuthContext] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Public paths (no JWT required)
        if self._is_public_path(path):
            return await call_next(request)

        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return self._json_error(request, status_code=401, detail="Missing bearer token")

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return self._json_error(request, status_code=401, detail="Missing bearer token")

        cached = self._cache_get(token)
        if cached is not None:
            request.state.auth_user = cached
            return await call_next(request)

        context = await self._validate_token_via_auth_service(request, auth_header)
        if context is None:
            # _validate_token_via_auth_service already returned an error response
            # by raising a handled path; we return 401 here as a safe fallback.
            return self._json_error(request, status_code=401, detail="Invalid token")

        self._cache_set(token, context)
        request.state.auth_user = context
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        # Root + health checks should never require auth
        if path == "/" or path.startswith("/health/"):
            return True

        # Allow auth-service endpoints through the gateway without requiring a token
        # (login/register/refresh/docs/openapi, etc.)
        if path.startswith("/api/auth/"):
            return True

        return False

    async def _validate_token_via_auth_service(self, request: Request, auth_header: str) -> AuthUserContext | None:
        base_url = get_auth_service_base_url()
        url = f"{base_url}{AUTH_TOKEN_VALIDATION_PATH}"

        timeout = httpx.Timeout(
            connect=PROXY_CONNECT_TIMEOUT_SECONDS,
            read=PROXY_READ_TIMEOUT_SECONDS,
            write=PROXY_READ_TIMEOUT_SECONDS,
            pool=PROXY_CONNECT_TIMEOUT_SECONDS,
        )

        headers = {"authorization": auth_header}

        # Propagate request id to auth-service for traceability
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            headers[REQUEST_ID_HEADER] = request_id

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                upstream = await client.get(url, headers=headers)
        except httpx.ReadTimeout:
            return None  # handled by caller fallback
        except httpx.RequestError:
            return None  # handled by caller fallback

        if upstream.status_code == 200:
            payload: Any = upstream.json()

            # We expect auth-service to return user info from /me.
            # Keep this flexible: only extract what we need.
            user_id = str(payload.get("id") or payload.get("user_id") or "")
            if not user_id:
                # Unexpected response contract; treat as invalid.
                return None

            is_admin = bool(payload.get("is_admin", False))
            return AuthUserContext(user_id=user_id, is_admin=is_admin)

        # Forward 401/403 semantics where possible
        if upstream.status_code in (401, 403):
            return None

        # Any other status is treated as auth failure for MVP.
        return None

    def _cache_get(self, token: str) -> AuthUserContext | None:
        if AUTH_CONTEXT_CACHE_TTL_SECONDS <= 0:
            return None

        entry = self._cache.get(token)
        if entry is None:
            return None

        now = time.time()
        if entry.expires_at_epoch <= now:
            self._cache.pop(token, None)
            return None

        return entry.context

    def _cache_set(self, token: str, context: AuthUserContext) -> None:
        if AUTH_CONTEXT_CACHE_TTL_SECONDS <= 0:
            return

        # Simple eviction to cap memory. MVP-level.
        if len(self._cache) >= AUTH_CONTEXT_CACHE_MAX_ENTRIES:
            # Remove an arbitrary item (dict FIFO-ish in CPython 3.7+).
            self._cache.pop(next(iter(self._cache)))

        self._cache[token] = _CachedAuthContext(
            expires_at_epoch=time.time() + AUTH_CONTEXT_CACHE_TTL_SECONDS,
            context=context,
        )

    def _json_error(self, request: Request, status_code: int, detail: str) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        headers = {REQUEST_ID_HEADER: request_id} if request_id else None
        return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)