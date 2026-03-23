"""Auth middleware -- passive JWT extraction for request context (TASK-093, TASK-113).

Tries to extract a valid JWT from the Authorization header and sets
`request.state.user_id` if successful.  Does NOT block requests --
actual enforcement is handled by FastAPI dependencies (get_current_user).

This is placed after RateLimitMiddleware so that rate limiting can use
the user_id when available.

Also sets the ``user_id_var`` context variable for structured logging
(TASK-113) so that all log entries within the request carry the user ID.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from pwbs.core.exceptions import AuthenticationError
from pwbs.core.logging import user_id_var
from pwbs.services.auth import validate_access_token

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Extract user_id from JWT and attach to request.state.

    If the token is missing or invalid the request continues without a
    user_id -- endpoint-level dependencies decide whether to reject.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        user_id = None
        auth_header = request.headers.get("authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = validate_access_token(token)
                user_id = payload.user_id
            except AuthenticationError as exc:
                logger.debug("JWT rejected: %s", exc)
            except Exception:
                logger.warning("Unexpected error validating JWT", exc_info=True)

        request.state.user_id = user_id
        if user_id is not None:
            user_id_var.set(str(user_id))
        return await call_next(request)
