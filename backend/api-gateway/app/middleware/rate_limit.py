# app/middleware/rate_limit.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.settings import (
    RATE_LIMIT_API_REQUESTS_PER_WINDOW,
    RATE_LIMIT_AUTH_REQUESTS_PER_WINDOW,
    RATE_LIMIT_WINDOW_SECONDS,
)
from app.settings import REQUEST_ID_HEADER


@dataclass
class _FixedWindowCounter:
    window_start_epoch: int
    count: int


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory fixed-window rate limiter.

    - Applies only to paths starting with /api/
    - Uses client IP (best-effort) as key
    - Different limits for:
        /api/auth/*  (stricter)
        /api/*       (default)
    - Returns 429 with Retry-After on limit exceeded

    Limitations (known and accepted for MVP):
    - In-memory: resets on restart.
    - Per-process: if you run multiple gateway replicas, each has its own counters.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._counters: dict[str, _FixedWindowCounter] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        limit = RATE_LIMIT_AUTH_REQUESTS_PER_WINDOW if path.startswith("/api/auth/") else RATE_LIMIT_API_REQUESTS_PER_WINDOW
        window_seconds = RATE_LIMIT_WINDOW_SECONDS

        now_epoch = int(time.time())
        window_start_epoch = now_epoch - (now_epoch % window_seconds)
        key = f"{client_ip}:{path.startswith('/api/auth/')}"  # separate buckets for auth vs general

        counter = self._counters.get(key)
        if counter is None or counter.window_start_epoch != window_start_epoch:
            counter = _FixedWindowCounter(window_start_epoch=window_start_epoch, count=0)
            self._counters[key] = counter

        counter.count += 1

        if counter.count > limit:
            retry_after = (window_start_epoch + window_seconds) - now_epoch
            request_id = getattr(request.state, "request_id", None)

            headers = {"Retry-After": str(retry_after)}
            if request_id:
                headers[REQUEST_ID_HEADER] = request_id

            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers=headers,
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """
        Best-effort client IP extraction.

        In production behind an Ingress/reverse proxy, you typically rely on X-Forwarded-For.
        For MVP we accept the risk of spoofing and keep it simple.
        """
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # X-Forwarded-For can be a chain: "client, proxy1, proxy2"
            return xff.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"