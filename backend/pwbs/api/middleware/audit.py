"""Audit middleware -- log all mutating API operations (TASK-093).

Logs POST/PUT/PATCH/DELETE requests with user_id, path, method and
response status code.  This provides basic audit visibility; full
database-backed audit logging is planned for TASK-109.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("pwbs.audit")

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in _MUTATING_METHODS:
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "AUDIT method=%s path=%s user_id=%s status=%d duration_ms=%.1f",
            request.method,
            request.url.path,
            user_id or "anonymous",
            response.status_code,
            duration_ms,
        )
        return response
