from __future__ import annotations

from typing import Iterable

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.settings import (
    get_auth_service_base_url,
    REQUEST_ID_HEADER,
    PROXY_CONNECT_TIMEOUT_SECONDS,
    PROXY_READ_TIMEOUT_SECONDS,
    INTERNAL_USER_ID_HEADER,
    INTERNAL_USER_IS_ADMIN_HEADER,
)

router = APIRouter(prefix="/api/auth", tags=["proxy-auth"])

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}


def _filter_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    filtered: dict[str, str] = {}
    for key, value in headers:
        if key.lower() in _HOP_BY_HOP_HEADERS:
            continue
        filtered[key] = value
    return filtered


@router.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_auth(request: Request, full_path: str) -> Response:

    # AUTH_SERVICE_BASE_URL must contain only the service origin, without path prefix.
    # Example: http://127.0.0.1:7000
    base_url = get_auth_service_base_url().rstrip("/")

    # FastAPI documentation endpoints live at application level, not inside the business router.
    # Business endpoints remain under /api/auth/* in auth-service.
    if full_path == "docs":
        target_url = f"{base_url}/docs"
    elif full_path == "openapi.json":
        target_url = f"{base_url}/openapi.json"
    elif full_path == "redoc":
        target_url = f"{base_url}/redoc"
    else:
        target_url = f"{base_url}/api/auth/{full_path}".rstrip("/")

    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    body = await request.body()
    outgoing_headers = _filter_headers(request.headers.items())

    request_id = getattr(request.state, "request_id", None)
    if request_id:
        # Forward request correlation header to upstream services.
        outgoing_headers[REQUEST_ID_HEADER] = request_id

    auth_user = getattr(request.state, "auth_user", None)
    if auth_user is not None:
        # Propagate trusted identity headers only after gateway-side authentication.
        # Downstream services must treat these headers as internal-only signals.
        # These headers define the authenticated identity as resolved by the gateway.
        # They are meant for trusted internal service-to-service communication only.
        outgoing_headers[INTERNAL_USER_ID_HEADER] = auth_user.user_id
        outgoing_headers[INTERNAL_USER_IS_ADMIN_HEADER] = str(auth_user.is_admin).lower()

    timeout = httpx.Timeout(
        connect=PROXY_CONNECT_TIMEOUT_SECONDS,
        read=PROXY_READ_TIMEOUT_SECONDS,
        write=PROXY_READ_TIMEOUT_SECONDS,
        pool=PROXY_CONNECT_TIMEOUT_SECONDS,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                headers=outgoing_headers,
                content=body,
            )
    except httpx.ReadTimeout:
        # Upstream accepted connection but did not respond in time
        return JSONResponse(
            status_code=504,
            content={"detail": "Upstream timeout"},
            headers={REQUEST_ID_HEADER: request_id} if request_id else None,
        )
    except httpx.RequestError:
        # Connection errors, DNS, refused, etc.
        return JSONResponse(
            status_code=502,
            content={"detail": "Upstream connection error"},
            headers={REQUEST_ID_HEADER: request_id} if request_id else None,
        )

    response_headers = _filter_headers(upstream.headers.items())
    if request_id:
        response_headers[REQUEST_ID_HEADER] = request_id

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )