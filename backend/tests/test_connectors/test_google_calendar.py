"""Tests for Google Calendar OAuth2 flow (TASK-045)."""

from __future__ import annotations

import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from pwbs.connectors.google_calendar import (
    GOOGLE_CALENDAR_SCOPE,
    GoogleCalendarConnector,
    _GOOGLE_AUTH_URL,
    _GOOGLE_TOKEN_URL,
)
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.exceptions import ConnectorError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REDIRECT_URI = "http://localhost:3000/api/connectors/google-calendar/callback"
STATE_TOKEN = "csrf-state-abc123"


# ---------------------------------------------------------------------------
# build_auth_url tests
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    def test_generates_valid_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        url = GoogleCalendarConnector.build_auth_url(
            redirect_uri=REDIRECT_URI, state=STATE_TOKEN
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert parsed.netloc == "accounts.google.com"
        assert params["client_id"] == ["test-client-id"]
        assert params["redirect_uri"] == [REDIRECT_URI]
        assert params["response_type"] == ["code"]
        assert params["scope"] == [GOOGLE_CALENDAR_SCOPE]
        assert params["access_type"] == ["offline"]
        assert params["prompt"] == ["consent"]
        assert params["state"] == [STATE_TOKEN]

    def test_missing_client_id_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        with pytest.raises(ConnectorError, match="GOOGLE_CLIENT_ID"):
            GoogleCalendarConnector.build_auth_url(
                redirect_uri=REDIRECT_URI, state=STATE_TOKEN
            )


# ---------------------------------------------------------------------------
# exchange_code tests
# ---------------------------------------------------------------------------


class TestExchangeCode:
    async def test_successful_exchange(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "access_token": "ya29.access-token",
                    "refresh_token": "1//refresh-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": GOOGLE_CALENDAR_SCOPE,
                },
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await GoogleCalendarConnector.exchange_code(
            code="auth-code-123",
            redirect_uri=REDIRECT_URI,
        )
        assert isinstance(tokens, OAuthTokens)
        assert tokens.access_token.get_secret_value() == "ya29.access-token"
        assert tokens.refresh_token is not None
        assert tokens.refresh_token.get_secret_value() == "1//refresh-token"
        assert tokens.token_type == "Bearer"
        assert tokens.scope == GOOGLE_CALENDAR_SCOPE
        assert tokens.expires_at is not None
        assert not tokens.is_expired

    async def test_exchange_without_refresh_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Google may omit refresh_token on re-authorization."""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "access_token": "ya29.access-only",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await GoogleCalendarConnector.exchange_code(
            code="auth-code-456",
            redirect_uri=REDIRECT_URI,
        )
        assert tokens.access_token.get_secret_value() == "ya29.access-only"
        assert tokens.refresh_token is None

    async def test_invalid_code_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            resp = httpx.Response(
                400,
                json={
                    "error": "invalid_grant",
                    "error_description": "Bad Request",
                },
                request=httpx.Request("POST", url),
            )
            resp.raise_for_status()
            return resp  # unreachable

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="code exchange failed"):
            await GoogleCalendarConnector.exchange_code(
                code="bad-code",
                redirect_uri=REDIRECT_URI,
            )

    async def test_network_error_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="network error"):
            await GoogleCalendarConnector.exchange_code(
                code="code",
                redirect_uri=REDIRECT_URI,
            )

    async def test_missing_access_token_in_response_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={"token_type": "Bearer"},  # no access_token
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="missing access_token"):
            await GoogleCalendarConnector.exchange_code(
                code="code",
                redirect_uri=REDIRECT_URI,
            )

    async def test_missing_credentials_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
        _clear_settings()

        with pytest.raises(ConnectorError, match="credentials not configured"):
            await GoogleCalendarConnector.exchange_code(
                code="code",
                redirect_uri=REDIRECT_URI,
            )


# ---------------------------------------------------------------------------
# health_check tests
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_healthy_with_valid_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={"kind": "calendar#calendarList", "items": []},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        from pwbs.connectors.base import ConnectorConfig

        conn = GoogleCalendarConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(
                source_type=SourceType.GOOGLE_CALENDAR,
                extra={"access_token": "valid-token"},
            ),
        )
        assert await conn.health_check() is True

    async def test_unhealthy_with_expired_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                401,
                json={"error": {"code": 401, "message": "Invalid Credentials"}},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        from pwbs.connectors.base import ConnectorConfig

        conn = GoogleCalendarConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(
                source_type=SourceType.GOOGLE_CALENDAR,
                extra={"access_token": "expired-token"},
            ),
        )
        assert await conn.health_check() is False

    async def test_no_token_returns_false(self) -> None:
        from pwbs.connectors.base import ConnectorConfig

        conn = GoogleCalendarConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR),
        )
        assert await conn.health_check() is False


# ---------------------------------------------------------------------------
# BaseConnector integration tests
# ---------------------------------------------------------------------------


class TestBaseConnectorIntegration:
    def test_source_type(self) -> None:
        conn = GoogleCalendarConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR),
        )
        assert conn.source_type == SourceType.GOOGLE_CALENDAR

    async def test_fetch_since_not_implemented(self) -> None:
        conn = GoogleCalendarConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR),
        )
        with pytest.raises(NotImplementedError, match="TASK-046"):
            await conn.fetch_since(None)

    async def test_normalize_not_implemented(self) -> None:
        conn = GoogleCalendarConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR),
        )
        with pytest.raises(NotImplementedError, match="TASK-047"):
            await conn.normalize({})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from pwbs.connectors.base import ConnectorConfig  # noqa: E402
from pwbs.core.config import get_settings  # noqa: E402
from pwbs.schemas.enums import SourceType  # noqa: E402


def _clear_settings() -> None:
    """Clear the cached settings so env var changes take effect."""
    get_settings.cache_clear()
