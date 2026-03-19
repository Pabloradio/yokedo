# app/middleware/request_id.py

from __future__ import annotations

import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request has an X-Request-ID.
    - If client provides one, reuse it.
    - Otherwise generate a UUID4.
    The value is exposed via request.state.request_id and returned in the response headers.
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(self.HEADER_NAME)
        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers[self.HEADER_NAME] = request_id
        return response