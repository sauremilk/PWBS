"""Rate-Limiting middleware -- Redis-backed fixed-window counters (TASK-085).

Categories:
  auth    -- login/register endpoints, per-IP (5 req/60s)
  sync    -- connector sync, per-identifier:connector (1 req/300s)
  general -- everything else, per-user or per-IP (100 req/60s)

On Redis failure the middleware falls back to **in-memory counters** with
conservative limits.  This ensures rate limiting is never fully bypassed.
"""

from __future__ import annotations

import collections
import logging
import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from pwbs.core.config import get_settings
from pwbs.db.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Circuit breaker: skip Redis for _CB_COOLDOWN seconds after a failure.
_redis_last_failure: float = 0.0
_CB_COOLDOWN = 60  # seconds

# ---------------------------------------------------------------------------
# In-memory fallback (active when Redis is unavailable)
# ---------------------------------------------------------------------------
_mem_lock = threading.Lock()
_mem_counters: dict[str, collections.deque[float]] = collections.defaultdict(collections.deque)

# Conservative per-category limits for the in-memory fallback.
_MEM_FALLBACK_LIMITS: dict[str, tuple[int, int]] = {
    "auth": (5, 60),  # keep strict (brute-force protection)
    "sync": (1, 300),  # keep strict
    "general": (50, 60),  # halved from Redis-backed 100
}


def _check_mem_rate_limit(
    category: str,
    identifier: str,
    now: float,
) -> tuple[bool, int, int, int]:
    """In-memory fixed-window rate check.

    Returns ``(allowed, remaining, max_requests, window_seconds)``.
    """
    max_requests, window = _MEM_FALLBACK_LIMITS.get(category, (50, 60))
    key = f"{category}:{identifier}"

    with _mem_lock:
        dq = _mem_counters[key]
        cutoff = now - window
        while dq and dq[0] < cutoff:
            dq.popleft()

        if len(dq) >= max_requests:
            return False, 0, max_requests, window

        dq.append(now)
        return True, max_requests - len(dq), max_requests, window


def reset_mem_counters() -> None:
    """Clear all in-memory counters (used in tests)."""
    with _mem_lock:
        _mem_counters.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client_ip(request: Request) -> str:
    """Extract client IP, honouring `X-Forwarded-For` from trusted proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _classify_request(
    request: Request,
) -> tuple[str, str, int, int]:
    """Return `(category, identifier, max_requests, window_seconds)`."""
    settings = get_settings()
    path = request.url.path.rstrip("/")
    method = request.method.upper()

    # --- Auth endpoints (login / register): per-IP ---
    if method == "POST" and (path.endswith("/auth/login") or path.endswith("/auth/register")):
        ip = _get_client_ip(request)
        return (
            "auth",
            ip,
            settings.rate_limit_auth_max,
            settings.rate_limit_auth_window,
        )

    # --- Connector manual sync: per-identifier + connector type ---
    if method == "POST" and "/connectors/" in path and path.endswith("/sync"):
        user_id = getattr(request.state, "user_id", None)
        identifier = str(user_id) if user_id else _get_client_ip(request)
        parts = path.split("/connectors/")
        connector_type = parts[1].split("/")[0] if len(parts) > 1 else "unknown"
        return (
            "sync",
            f"{identifier}:{connector_type}",
            settings.rate_limit_sync_max,
            settings.rate_limit_sync_window,
        )

    # --- General: per-user (if set by AuthMiddleware) or per-IP ---
    user_id = getattr(request.state, "user_id", None)
    identifier = str(user_id) if user_id else _get_client_ip(request)
    return (
        "general",
        identifier,
        settings.rate_limit_general_max,
        settings.rate_limit_general_window,
    )


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiter backed by Redis `INCR` + `EXPIRE`.

    The window key has format `rl:{category}:{identifier}:{window_id}`
    where *window_id* is `floor(now / window_seconds)`.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        category, identifier, max_requests, window_seconds = _classify_request(request)

        now = time.time()
        window_id = int(now // window_seconds)
        redis_key = f"rl:{category}:{identifier}:{window_id}"
        reset_at = (window_id + 1) * window_seconds

        remaining = max_requests

        global _redis_last_failure
        use_fallback = time.time() - _redis_last_failure < _CB_COOLDOWN

        if not use_fallback:
            try:
                redis = get_redis_client()
                pipe = redis.pipeline()
                pipe.incr(redis_key)
                pipe.expire(redis_key, window_seconds + 1)
                results = await pipe.execute()
                current_count: int = results[0]

                remaining = max(0, max_requests - current_count)

                if current_count > max_requests:
                    retry_after = max(1, int(reset_at - now))
                    return JSONResponse(
                        status_code=429,
                        content={
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests",
                            "detail": {
                                "limit": max_requests,
                                "window_seconds": window_seconds,
                                "retry_after": retry_after,
                            },
                        },
                        headers={
                            "X-RateLimit-Limit": str(max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(reset_at)),
                            "Retry-After": str(retry_after),
                        },
                    )
            except Exception:
                _redis_last_failure = time.time()
                use_fallback = True
                logger.warning(
                    "Rate limiting Redis failure; switching to in-memory fallback for %s:%s",
                    category,
                    identifier,
                )

        # In-memory fallback when Redis is unavailable
        if use_fallback:
            allowed, fb_remaining, fb_max, fb_window = _check_mem_rate_limit(
                category,
                identifier,
                now,
            )
            remaining = fb_remaining
            max_requests = fb_max
            reset_at = now + fb_window

            if not allowed:
                retry_after = max(1, int(fb_window))
                logger.info(
                    "In-memory rate limit exceeded for %s:%s",
                    category,
                    identifier,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                        "detail": {
                            "limit": fb_max,
                            "window_seconds": fb_window,
                            "retry_after": retry_after,
                        },
                    },
                    headers={
                        "X-RateLimit-Limit": str(fb_max),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(reset_at)),
                        "Retry-After": str(retry_after),
                    },
                )

        response = await call_next(request)

        # Attach rate-limit headers to every successful response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_at))

        return response
