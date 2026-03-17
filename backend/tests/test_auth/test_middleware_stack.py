"""Tests for API Middleware Stack (TASK-093)."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.api.middleware.audit import AuditMiddleware
from pwbs.api.middleware.auth import AuthMiddleware
from pwbs.api.middleware.security_headers import SecurityHeadersMiddleware

# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------


class TestSecurityHeadersMiddleware:
    @pytest.mark.asyncio
    async def test_adds_security_headers(self) -> None:
        mw = SecurityHeadersMiddleware(AsyncMock())
        req = MagicMock()
        resp = MagicMock()
        resp.headers = {}
        call_next = AsyncMock(return_value=resp)

        with patch("pwbs.api.middleware.security_headers.get_settings") as mock_settings:
            mock_settings.return_value.is_production = False
            result = await mw.dispatch(req, call_next)

        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Strict-Transport-Security" not in result.headers

    @pytest.mark.asyncio
    async def test_hsts_in_production(self) -> None:
        mw = SecurityHeadersMiddleware(AsyncMock())
        req = MagicMock()
        resp = MagicMock()
        resp.headers = {}
        call_next = AsyncMock(return_value=resp)

        with patch("pwbs.api.middleware.security_headers.get_settings") as mock_settings:
            mock_settings.return_value.is_production = True
            result = await mw.dispatch(req, call_next)

        assert "Strict-Transport-Security" in result.headers


# ---------------------------------------------------------------------------
# AuthMiddleware
# ---------------------------------------------------------------------------


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_sets_user_id_from_valid_jwt(self) -> None:
        mw = AuthMiddleware(AsyncMock())
        req = MagicMock()
        req.headers = {"authorization": "Bearer valid-token"}
        req.state = MagicMock()
        resp = MagicMock()
        call_next = AsyncMock(return_value=resp)

        import uuid

        uid = uuid.uuid4()
        with patch(
            "pwbs.api.middleware.auth.validate_access_token",
            return_value=MagicMock(user_id=uid),
        ):
            await mw.dispatch(req, call_next)

        assert req.state.user_id == uid
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sets_none_for_missing_header(self) -> None:
        mw = AuthMiddleware(AsyncMock())
        req = MagicMock()
        req.headers = {}
        req.state = MagicMock()
        resp = MagicMock()
        call_next = AsyncMock(return_value=resp)

        await mw.dispatch(req, call_next)
        assert req.state.user_id is None
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sets_none_for_invalid_jwt(self) -> None:
        from pwbs.core.exceptions import AuthenticationError

        mw = AuthMiddleware(AsyncMock())
        req = MagicMock()
        req.headers = {"authorization": "Bearer bad-token"}
        req.state = MagicMock()
        resp = MagicMock()
        call_next = AsyncMock(return_value=resp)

        with patch(
            "pwbs.api.middleware.auth.validate_access_token",
            side_effect=AuthenticationError("bad"),
        ):
            await mw.dispatch(req, call_next)

        assert req.state.user_id is None
        call_next.assert_awaited_once()


# ---------------------------------------------------------------------------
# AuditMiddleware
# ---------------------------------------------------------------------------


class TestAuditMiddleware:
    @pytest.mark.asyncio
    async def test_skips_get_requests(self) -> None:
        mw = AuditMiddleware(AsyncMock())
        req = MagicMock()
        req.method = "GET"
        resp = MagicMock()
        call_next = AsyncMock(return_value=resp)

        result = await mw.dispatch(req, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_logs_post_request(self, caplog: pytest.LogCaptureFixture) -> None:
        mw = AuditMiddleware(AsyncMock())
        req = MagicMock()
        req.method = "POST"
        req.url.path = "/api/v1/auth/register"
        req.state = MagicMock()
        req.state.user_id = None
        resp = MagicMock()
        resp.status_code = 201
        call_next = AsyncMock(return_value=resp)

        with caplog.at_level(logging.INFO, logger="pwbs.audit"):
            await mw.dispatch(req, call_next)

        assert any("AUDIT" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_logs_delete_request(self, caplog: pytest.LogCaptureFixture) -> None:
        mw = AuditMiddleware(AsyncMock())
        req = MagicMock()
        req.method = "DELETE"
        req.url.path = "/api/v1/documents/123"
        req.state = MagicMock()
        req.state.user_id = "user-456"
        resp = MagicMock()
        resp.status_code = 204
        call_next = AsyncMock(return_value=resp)

        with caplog.at_level(logging.INFO, logger="pwbs.audit"):
            await mw.dispatch(req, call_next)

        assert any("user-456" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Middleware Stack Registration
# ---------------------------------------------------------------------------


class TestMiddlewareStackRegistration:
    def test_all_middleware_registered(self) -> None:
        from pwbs.api.main import create_app

        app = create_app()
        names = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in names
        assert "TrustedHostMiddleware" in names
        assert "SecurityHeadersMiddleware" in names
        assert "CorrelationIdMiddleware" in names
        assert "RateLimitMiddleware" in names
        assert "AuthMiddleware" in names
        assert "AuditMiddleware" in names

    def test_middleware_order(self) -> None:
        """Verify correct outside-to-inside ordering.

        In Starlette, middleware added last is outermost.  So the list
        from `app.user_middleware` is outside-first.
        """
        from pwbs.api.main import create_app

        app = create_app()
        names = [m.cls.__name__ for m in app.user_middleware]
        # CORS should be outermost (last added = first in user_middleware)
        cors_idx = names.index("CORSMiddleware")
        audit_idx = names.index("AuditMiddleware")
        # CORS is outermost (lower index = more outer)
        assert cors_idx < audit_idx

    def test_swagger_disabled_in_production(self) -> None:
        import os

        os.environ["ENVIRONMENT"] = "production"
        os.environ["CORS_ORIGINS"] = '["https://app.example.com"]'
        os.environ["TRUSTED_HOSTS"] = '["app.example.com"]'
        from pwbs.core.config import get_settings

        get_settings.cache_clear()
        try:
            from pwbs.api.main import create_app

            app = create_app()
            assert app.docs_url is None
            assert app.redoc_url is None
        finally:
            os.environ.pop("ENVIRONMENT", None)
            os.environ.pop("CORS_ORIGINS", None)
            os.environ.pop("TRUSTED_HOSTS", None)
            get_settings.cache_clear()
