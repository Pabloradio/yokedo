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
    base_url = get_auth_service_base_url()
    target_url = f"{base_url}/{full_path}"

    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    body = await request.body()
    outgoing_headers = _filter_headers(request.headers.items())

    request_id = getattr(request.state, "request_id", None)
    if request_id:
        outgoing_headers[REQUEST_ID_HEADER] = request_id

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