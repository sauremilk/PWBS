"""Access-log middleware -- logs duration for every API request (TASK-113).

Placed between RequestIDMiddleware and RateLimitMiddleware so that it
captures the complete processing time of inner middleware + handler.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("pwbs.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and duration_ms for every request."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        # Read from request.state (set by earlier middleware, safe cross-task)
        request_id = getattr(request.state, "request_id", None)
        user_id = getattr(request.state, "user_id", None)

        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
                "user_id": str(user_id) if user_id else None,
            },
        )
        return response
