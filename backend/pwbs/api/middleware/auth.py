"""Auth middleware -- passive JWT extraction for request context (TASK-093).

Tries to extract a valid JWT from the Authorization header and sets
`request.state.user_id` if successful.  Does NOT block requests --
actual enforcement is handled by FastAPI dependencies (get_current_user).

This is placed after RateLimitMiddleware so that rate limiting can use
the user_id when available.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from pwbs.core.exceptions import AuthenticationError
from pwbs.services.auth import validate_access_token

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Extract user_id from JWT and attach to request.state.

    If the token is missing or invalid the request continues without a
    user_id -- endpoint-level dependencies decide whether to reject.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        user_id = None
        auth_header = request.headers.get("authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = validate_access_token(token)
                user_id = payload.user_id
            except (AuthenticationError, Exception):
                pass

        request.state.user_id = user_id
        return await call_next(request)
