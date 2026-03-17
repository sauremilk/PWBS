"""Correlation-ID middleware -- request tracing across all layers (TASK-196).

Generates or accepts a correlation ID (UUID4) via the `X-Request-ID` header.
The ID is propagated through `contextvars` so that every log entry within
the request lifecycle carries the `correlation_id` field.

Supersedes the earlier `RequestIDMiddleware` (TASK-037) by additionally
exposing a dedicated `correlation_id_var` context variable and ensuring
the `correlation_id` field appears in structured JSON logs.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from pwbs.core.logging import correlation_id_var, request_id_var


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to every HTTP request/response cycle.

    Behaviour:
    - If the incoming request carries an `X-Request-ID` header, that
      value is reused (allows end-to-end tracing across services).
    - Otherwise a new UUID4 is generated.
    - The ID is stored on `request.state.correlation_id` **and**
      `request.state.request_id` (backward compatibility).
    - Both `correlation_id_var` and `request_id_var` context
      variables are set so that structlog processors include the ID
      in every log entry as `correlation_id`.
    - The response `X-Request-ID` header echoes the correlation ID.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        cid = request.headers.get("x-request-id") or str(uuid.uuid4())

        # Expose on request.state for downstream middleware / handlers
        request.state.correlation_id = cid
        request.state.request_id = cid  # backward compat

        # Set context variables for structured logging propagation
        token_cid = correlation_id_var.set(cid)
        token_rid = request_id_var.set(cid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = cid
            return response
        finally:
            correlation_id_var.reset(token_cid)
            request_id_var.reset(token_rid)
