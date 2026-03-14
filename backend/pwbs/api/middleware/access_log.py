"""Access-log middleware -- logs duration for every API request (TASK-113, TASK-116).

Placed between RequestIDMiddleware and RateLimitMiddleware so that it
captures the complete processing time of inner middleware + handler.
Also increments the ``pwbs_http_errors_total`` Prometheus counter for
4xx/5xx responses (TASK-116).
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from pwbs.core.metrics import HTTP_ERRORS, _endpoint_group

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

        # Track HTTP errors for Prometheus (TASK-116)
        status = response.status_code
        if status >= 400:
            status_class = "4xx" if status < 500 else "5xx"
            group = _endpoint_group(request.url.path)
            HTTP_ERRORS.labels(status_class=status_class, endpoint_group=group).inc()

        return response
