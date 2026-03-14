"""RequestID middleware – attaches a unique X-Request-ID to every response (TASK-037, TASK-113).

Also sets ``request.state.request_id`` and the ``request_id_var`` context
variable so that structured logging processors can include the request ID
in every log entry emitted during the request lifecycle.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from pwbs.core.logging import request_id_var


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds an ``X-Request-ID`` header to every HTTP response.

    If the incoming request already carries the header, the value is
    forwarded; otherwise a new UUID4 is generated.  The ID is also
    stored on ``request.state`` and in a :mod:`contextvars` variable
    for structured logging (TASK-113).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)
