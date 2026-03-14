"""Tests for Zoom connector — OAuth2 flow (TASK-053)."""

from __future__ import annotations

import base64
import time
import uuid

import httpx
import pytest

from pwbs.connectors.base import ConnectorConfig
from pwbs.connectors.oauth import OAuthTokens
from pwbs.connectors.zoom import (
    ZOOM_SCOPES,
    ZoomConnector,
    _ZOOM_AUTH_URL,
    _ZOOM_TOKEN_URL,
    _raise_for_rate_limit,
)
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import SourceType

# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------


def _make_connector(
    access_token: str = "test-zoom-token",
) -> ZoomConnector:
    return ZoomConnector(
        owner_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        config=ConnectorConfig(
            source_type=SourceType.ZOOM,
            extra={"access_token": access_token},
        ),
    )


def _clear_settings() -> None:
    get_settings.cache_clear()


def _set_zoom_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set Zoom OAuth env vars and clear settings cache."""
    monkeypatch.setenv("ZOOM_CLIENT_ID", "test-zoom-id")
    monkeypatch.setenv("ZOOM_CLIENT_SECRET", "test-zoom-secret")
    _clear_settings()


# ---------------------------------------------------------------------------
# build_auth_url
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    def test_generates_valid_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_zoom_env(monkeypatch)
        url = ZoomConnector.build_auth_url(
            redirect_uri="http://localhost:3000/callback",
            state="csrf-token-123",
        )
        assert url.startswith(_ZOOM_AUTH_URL)
        assert "client_id=test-zoom-id" in url
        assert "redirect_uri=http" in url
        assert "response_type=code" in url
        assert "state=csrf-token-123" in url

    def test_raises_without_client_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ZOOM_CLIENT_ID", "")
        monkeypatch.setenv("ZOOM_CLIENT_SECRET", "test-secret")
        _clear_settings()
        with pytest.raises(ConnectorError, match="zoom_client_id"):
            ZoomConnector.build_auth_url(
                redirect_uri="http://localhost:3000/callback",
                state="test",
            )


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestExchangeCode:
    @pytest.mark.asyncio
    async def test_successful_exchange(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_zoom_env(monkeypatch)

        expected_creds = base64.b64encode(
            b"test-zoom-id:test-zoom-secret",
        ).decode()

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            assert url == _ZOOM_TOKEN_URL
            assert kwargs.get("headers", {}).get("Authorization") == f"Basic {expected_creds}"
            return httpx.Response(
                status_code=200,
                json={
                    "access_token": "zoom-access-123",
                    "refresh_token": "zoom-refresh-456",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "cloud_recording:read",
                },
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await ZoomConnector.exchange_code(
            code="auth-code-xyz",
            redirect_uri="http://localhost:3000/callback",
        )
        assert tokens.access_token.get_secret_value() == "zoom-access-123"
        assert tokens.refresh_token is not None
        assert tokens.refresh_token.get_secret_value() == "zoom-refresh-456"
        assert tokens.token_type == "Bearer"
        assert tokens.expires_at is not None
        assert tokens.expires_at > time.time()
        assert tokens.scope == "cloud_recording:read"

    @pytest.mark.asyncio
    async def test_exchange_without_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ZOOM_CLIENT_ID", "")
        monkeypatch.setenv("ZOOM_CLIENT_SECRET", "")
        _clear_settings()
        with pytest.raises(ConnectorError, match="zoom_client_id"):
            await ZoomConnector.exchange_code(
                code="some-code",
                redirect_uri="http://localhost:3000/callback",
            )

    @pytest.mark.asyncio
    async def test_exchange_invalid_code(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_zoom_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                status_code=400,
                json={"reason": "Invalid authorization code", "error": "invalid_grant"},
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="Invalid authorization code"):
            await ZoomConnector.exchange_code(
                code="bad-code",
                redirect_uri="http://localhost:3000/callback",
            )

    @pytest.mark.asyncio
    async def test_exchange_network_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_zoom_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="network error"):
            await ZoomConnector.exchange_code(
                code="some-code",
                redirect_uri="http://localhost:3000/callback",
            )

    @pytest.mark.asyncio
    async def test_exchange_rate_limited(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_zoom_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                status_code=429,
                headers={"Retry-After": "30"},
                text="Rate limit exceeded",
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(RateLimitError):
            await ZoomConnector.exchange_code(
                code="some-code",
                redirect_uri="http://localhost:3000/callback",
            )

    @pytest.mark.asyncio
    async def test_exchange_missing_access_token_in_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_zoom_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={"token_type": "Bearer"},
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="missing access_token"):
            await ZoomConnector.exchange_code(
                code="some-code",
                redirect_uri="http://localhost:3000/callback",
            )

    @pytest.mark.asyncio
    async def test_exchange_no_refresh_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Zoom should normally return a refresh token, but handle its absence."""
        _set_zoom_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={
                    "access_token": "access-only",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await ZoomConnector.exchange_code(
            code="some-code",
            redirect_uri="http://localhost:3000/callback",
        )
        assert tokens.refresh_token is None
        assert tokens.access_token.get_secret_value() == "access-only"

    @pytest.mark.asyncio
    async def test_exchange_uses_form_encoded_body(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Zoom token endpoint expects application/x-www-form-urlencoded."""
        _set_zoom_env(monkeypatch)

        captured_kwargs: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            captured_kwargs.update(kwargs)
            return httpx.Response(
                status_code=200,
                json={
                    "access_token": "test-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        await ZoomConnector.exchange_code(
            code="test-code",
            redirect_uri="http://localhost:3000/callback",
        )

        # Should use `data=` (form-encoded), not `json=`
        assert "data" in captured_kwargs
        assert "json" not in captured_kwargs
        headers = captured_kwargs.get("headers", {})
        assert headers.get("Content-Type") == "application/x-www-form-urlencoded"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            assert "/users/me" in url
            return httpx.Response(status_code=200, json={"id": "user-123"})

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        assert await connector.health_check() is True

    @pytest.mark.asyncio
    async def test_unhealthy_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(status_code=401, text="Unauthorized")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_no_access_token(self) -> None:
        connector = ZoomConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(
                source_type=SourceType.ZOOM,
                extra={},
            ),
        )
        assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_network_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_rate_limited_health_check(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rate-limited response during health check — should return False."""
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                status_code=429,
                headers={"Retry-After": "60"},
                text="Rate limited",
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        # RateLimitError is raised by _raise_for_rate_limit, which
        # propagates out of health_check (base class retry handles it)
        with pytest.raises(RateLimitError):
            await connector.health_check()


# ---------------------------------------------------------------------------
# BaseConnector integration
# ---------------------------------------------------------------------------


class TestBaseConnectorIntegration:
    def test_source_type(self) -> None:
        connector = _make_connector()
        assert connector.source_type == SourceType.ZOOM

    @pytest.mark.asyncio
    async def test_fetch_since_not_implemented(self) -> None:
        connector = _make_connector()
        with pytest.raises(NotImplementedError, match="TASK-054"):
            await connector.fetch_since(None)

    def test_normalize_not_implemented(self) -> None:
        connector = _make_connector()
        with pytest.raises(NotImplementedError, match="TASK-055"):
            connector.normalize({"id": "test"})

    def test_get_access_token(self) -> None:
        connector = _make_connector(access_token="my-token")
        assert connector._get_access_token() == "my-token"

    def test_get_access_token_missing(self) -> None:
        connector = ZoomConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(
                source_type=SourceType.ZOOM,
                extra={},
            ),
        )
        with pytest.raises(ConnectorError, match="Missing access_token"):
            connector._get_access_token()


# ---------------------------------------------------------------------------
# _raise_for_rate_limit helper
# ---------------------------------------------------------------------------


class TestRaiseForRateLimit:
    def test_raises_on_429(self) -> None:
        response = httpx.Response(
            status_code=429,
            headers={"Retry-After": "45"},
            text="Too many requests",
        )
        with pytest.raises(RateLimitError) as exc_info:
            _raise_for_rate_limit(response)
        assert exc_info.value.retry_after == 45

    def test_no_raise_on_200(self) -> None:
        response = httpx.Response(status_code=200, json={"ok": True})
        _raise_for_rate_limit(response)  # should not raise

    def test_default_retry_after(self) -> None:
        response = httpx.Response(status_code=429, text="Rate limited")
        with pytest.raises(RateLimitError) as exc_info:
            _raise_for_rate_limit(response)
        assert exc_info.value.retry_after == 60
