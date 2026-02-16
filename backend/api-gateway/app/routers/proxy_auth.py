from __future__ import annotations

from typing import Iterable

import httpx
from fastapi import APIRouter, Request, Response

from app.settings import get_auth_service_base_url

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


@router.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy_auth(request: Request, full_path: str) -> Response:
    """
    Reverse-proxy requests from:
      /api/auth/<full_path>
    to:
      {AUTH_SERVICE_BASE_URL}/<full_path>

    We keep the original Authorization header (Bearer token) as-is.
    """
    base_url = get_auth_service_base_url()
    target_url = f"{base_url}/{full_path}"

    # Query string
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # Body (may be empty)
    body = await request.body()

    # Forward most headers (excluding hop-by-hop)
    outgoing_headers = _filter_headers(request.headers.items())

    timeout = httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        upstream = await client.request(
            method=request.method,
            url=target_url,
            headers=outgoing_headers,
            content=body,
        )

    # Return upstream response
    response_headers = _filter_headers(upstream.headers.items())
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
