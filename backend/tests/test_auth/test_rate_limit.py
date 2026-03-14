"""Tests for Rate-Limiting middleware (TASK-085)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.api.middleware.rate_limit import (
    RateLimitMiddleware,
    _classify_request,
    _get_client_ip,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    path: str = "/api/v1/health",
    method: str = "GET",
    client_host: str = "127.0.0.1",
    headers: dict[str, str] | None = None,
    user_id: str | None = None,
) -> MagicMock:
    """Build a minimal Starlette-like Request mock."""
    request = MagicMock()
    request.url.path = path
    request.method = method
    request.client.host = client_host
    request.headers = headers or {}
    request.state = MagicMock()
    if user_id:
        request.state.user_id = user_id
    else:
        # getattr(request.state, "user_id", None) should return None
        del request.state.user_id
    return request


# ---------------------------------------------------------------------------
# _get_client_ip
# ---------------------------------------------------------------------------


class TestGetClientIP:
    def test_direct_ip(self) -> None:
        req = _make_request(client_host="192.168.1.1")
        assert _get_client_ip(req) == "192.168.1.1"

    def test_forwarded_for_single(self) -> None:
        req = _make_request(headers={"x-forwarded-for": "10.0.0.1"})
        assert _get_client_ip(req) == "10.0.0.1"

    def test_forwarded_for_chain(self) -> None:
        req = _make_request(headers={"x-forwarded-for": "10.0.0.1, 10.0.0.2"})
        assert _get_client_ip(req) == "10.0.0.1"

    def test_no_client(self) -> None:
        req = _make_request()
        req.client = None
        req.headers = {}
        assert _get_client_ip(req) == "unknown"


# ---------------------------------------------------------------------------
# _classify_request
# ---------------------------------------------------------------------------


class TestClassifyRequest:
    def test_auth_login(self) -> None:
        req = _make_request(path="/api/v1/auth/login", method="POST")
        cat, identifier, max_req, window = _classify_request(req)
        assert cat == "auth"
        assert identifier == "127.0.0.1"
        assert max_req == 5
        assert window == 60

    def test_auth_register(self) -> None:
        req = _make_request(path="/api/v1/auth/register", method="POST")
        cat, *_ = _classify_request(req)
        assert cat == "auth"

    def test_auth_login_trailing_slash(self) -> None:
        req = _make_request(path="/api/v1/auth/login/", method="POST")
        cat, *_ = _classify_request(req)
        assert cat == "auth"

    def test_auth_get_not_matched(self) -> None:
        """GET on login path is general, not auth category."""
        req = _make_request(path="/api/v1/auth/login", method="GET")
        cat, *_ = _classify_request(req)
        assert cat == "general"

    def test_sync_endpoint(self) -> None:
        req = _make_request(
            path="/api/v1/connectors/google-calendar/sync", method="POST"
        )
        cat, identifier, max_req, window = _classify_request(req)
        assert cat == "sync"
        assert "google-calendar" in identifier
        assert max_req == 1
        assert window == 300

    def test_sync_with_user_id(self) -> None:
        req = _make_request(
            path="/api/v1/connectors/notion/sync",
            method="POST",
            user_id="user-123",
        )
        cat, identifier, *_ = _classify_request(req)
        assert cat == "sync"
        assert identifier == "user-123:notion"

    def test_general_endpoint(self) -> None:
        req = _make_request(path="/api/v1/briefings", method="GET")
        cat, identifier, max_req, window = _classify_request(req)
        assert cat == "general"
        assert identifier == "127.0.0.1"
        assert max_req == 100
        assert window == 60

    def test_general_with_user_id(self) -> None:
        req = _make_request(
            path="/api/v1/search", method="POST", user_id="user-456"
        )
        cat, identifier, *_ = _classify_request(req)
        assert cat == "general"
        assert identifier == "user-456"


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    @pytest.fixture()
    def middleware(self) -> RateLimitMiddleware:
        dummy_app = AsyncMock()
        return RateLimitMiddleware(dummy_app)

    @pytest.fixture()
    def mock_redis(self) -> MagicMock:
        """Return a mock Redis client whose pipeline returns configurable counts."""
        redis = MagicMock()
        pipe = MagicMock()
        pipe.incr = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[1, True])
        redis.pipeline.return_value = pipe
        return redis

    @pytest.mark.asyncio
    async def test_allows_request_under_limit(
        self, middleware: RateLimitMiddleware, mock_redis: MagicMock
    ) -> None:
        """Request under limit should pass through with rate-limit headers."""
        call_next = AsyncMock()
        response = MagicMock()
        response.headers = {}
        call_next.return_value = response

        req = _make_request()

        with patch(
            "pwbs.api.middleware.rate_limit.get_redis_client",
            return_value=mock_redis,
        ):
            result = await middleware.dispatch(req, call_next)

        call_next.assert_awaited_once()
        assert result.headers["X-RateLimit-Limit"] == "100"
        assert result.headers["X-RateLimit-Remaining"] == "99"
        assert "X-RateLimit-Reset" in result.headers

    @pytest.mark.asyncio
    async def test_blocks_request_over_limit(
        self, middleware: RateLimitMiddleware, mock_redis: MagicMock
    ) -> None:
        """Request exceeding limit should return 429."""
        mock_redis.pipeline().execute = AsyncMock(return_value=[101, True])

        req = _make_request()

        with patch(
            "pwbs.api.middleware.rate_limit.get_redis_client",
            return_value=mock_redis,
        ):
            result = await middleware.dispatch(req, AsyncMock())

        assert result.status_code == 429
        assert result.headers["X-RateLimit-Remaining"] == "0"
        assert "Retry-After" in result.headers

    @pytest.mark.asyncio
    async def test_auth_endpoint_blocks_at_5(
        self, middleware: RateLimitMiddleware, mock_redis: MagicMock
    ) -> None:
        """Auth endpoints should block after 5 requests."""
        mock_redis.pipeline().execute = AsyncMock(return_value=[6, True])

        req = _make_request(path="/api/v1/auth/login", method="POST")

        with patch(
            "pwbs.api.middleware.rate_limit.get_redis_client",
            return_value=mock_redis,
        ):
            result = await middleware.dispatch(req, AsyncMock())

        assert result.status_code == 429

    @pytest.mark.asyncio
    async def test_sync_endpoint_blocks_at_1(
        self, middleware: RateLimitMiddleware, mock_redis: MagicMock
    ) -> None:
        """Sync endpoints should block after 1 request in 5 minutes."""
        mock_redis.pipeline().execute = AsyncMock(return_value=[2, True])

        req = _make_request(
            path="/api/v1/connectors/google-calendar/sync", method="POST"
        )

        with patch(
            "pwbs.api.middleware.rate_limit.get_redis_client",
            return_value=mock_redis,
        ):
            result = await middleware.dispatch(req, AsyncMock())

        assert result.status_code == 429

    @pytest.mark.asyncio
    async def test_fail_open_on_redis_error(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Redis failure should let requests through (fail-open)."""
        call_next = AsyncMock()
        response = MagicMock()
        response.headers = {}
        call_next.return_value = response

        req = _make_request()

        with patch(
            "pwbs.api.middleware.rate_limit.get_redis_client",
            side_effect=ConnectionError("Redis down"),
        ):
            result = await middleware.dispatch(req, call_next)

        call_next.assert_awaited_once()
        # Headers still present with default values
        assert result.headers["X-RateLimit-Limit"] == "100"

    @pytest.mark.asyncio
    async def test_fail_open_on_pipeline_error(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Redis pipeline error should also fail open."""
        redis = MagicMock()
        pipe = MagicMock()
        pipe.incr = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(side_effect=Exception("Redis timeout"))
        redis.pipeline.return_value = pipe

        call_next = AsyncMock()
        response = MagicMock()
        response.headers = {}
        call_next.return_value = response

        req = _make_request()

        with patch(
            "pwbs.api.middleware.rate_limit.get_redis_client",
            return_value=redis,
        ):
            result = await middleware.dispatch(req, call_next)

        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_429_response_body_structure(
        self, middleware: RateLimitMiddleware, mock_redis: MagicMock
    ) -> None:
        """429 response should contain structured error body."""
        mock_redis.pipeline().execute = AsyncMock(return_value=[101, True])

        req = _make_request()

        with patch(
            "pwbs.api.middleware.rate_limit.get_redis_client",
            return_value=mock_redis,
        ):
            result = await middleware.dispatch(req, AsyncMock())

        assert result.status_code == 429
        body = result.body.decode()
        assert "RATE_LIMIT_EXCEEDED" in body
        assert "Too many requests" in body

    @pytest.mark.asyncio
    async def test_headers_present_on_success(
        self, middleware: RateLimitMiddleware, mock_redis: MagicMock
    ) -> None:
        """All three rate-limit headers must be present on successful responses."""
        call_next = AsyncMock()
        response = MagicMock()
        response.headers = {}
        call_next.return_value = response

        req = _make_request()

        with patch(
            "pwbs.api.middleware.rate_limit.get_redis_client",
            return_value=mock_redis,
        ):
            result = await middleware.dispatch(req, call_next)

        for header in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
            assert header in result.headers, f"Missing header: {header}"
