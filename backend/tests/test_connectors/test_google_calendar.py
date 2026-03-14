"""Tests for Google Calendar OAuth2 flow + Sync logic (TASK-045, TASK-046)."""

from __future__ import annotations

import json
import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from pwbs.connectors.google_calendar import (
    _GOOGLE_AUTH_URL,
    _GOOGLE_TOKEN_URL,
    GOOGLE_CALENDAR_SCOPE,
    GoogleCalendarConnector,
    _decode_cursor,
    _encode_cursor,
)
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.exceptions import ConnectorError, RateLimitError

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

        url = GoogleCalendarConnector.build_auth_url(redirect_uri=REDIRECT_URI, state=STATE_TOKEN)
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

    def test_missing_client_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        with pytest.raises(ConnectorError, match="GOOGLE_CLIENT_ID"):
            GoogleCalendarConnector.build_auth_url(redirect_uri=REDIRECT_URI, state=STATE_TOKEN)


# ---------------------------------------------------------------------------
# exchange_code tests
# ---------------------------------------------------------------------------


class TestExchangeCode:
    async def test_successful_exchange(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

    async def test_exchange_without_refresh_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Google may omit refresh_token on re-authorization."""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

    async def test_invalid_code_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

    async def test_network_error_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

    async def test_missing_credentials_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
    async def test_healthy_with_valid_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

    async def test_unhealthy_with_expired_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

    async def test_fetch_since_requires_access_token(self) -> None:
        conn = GoogleCalendarConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR),
        )
        with pytest.raises(ConnectorError, match="access_token"):
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
# Sync logic tests (TASK-046)
# ---------------------------------------------------------------------------


def _make_connector(
    access_token: str = "test-access-token",
    max_batch_size: int = 100,
) -> GoogleCalendarConnector:
    return GoogleCalendarConnector(
        owner_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        config=ConnectorConfig(
            source_type=SourceType.GOOGLE_CALENDAR,
            max_batch_size=max_batch_size,
            extra={"access_token": access_token},
        ),
    )


class TestFetchSinceInitialSync:
    """Initial full sync (cursor=None)."""

    async def test_initial_sync_returns_events_as_errors_until_normalizer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Until TASK-047, events appear in errors since normalize raises NotImplementedError."""

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "kind": "calendar#events",
                    "items": [
                        {"id": "evt1", "summary": "Meeting 1"},
                        {"id": "evt2", "summary": "Meeting 2"},
                    ],
                    "nextSyncToken": "sync-token-abc",
                },
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        result = await conn.fetch_since(None)

        assert result.new_cursor == "sync-token-abc"
        assert result.has_more is False
        # No documents yet (normalize not implemented)
        assert result.success_count == 0
        # Events appear as errors because normalize raises NotImplementedError
        assert result.error_count == 2
        assert result.errors[0].source_id == "evt1"
        assert result.errors[1].source_id == "evt2"


class TestFetchSinceIncrementalSync:
    """Incremental sync with syncToken cursor."""

    async def test_incremental_with_sync_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured_params: dict[str, str | int] = {}

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            params = kwargs.get("params")
            if isinstance(params, dict):
                captured_params.update(params)
            return httpx.Response(
                200,
                json={
                    "items": [{"id": "evt3", "summary": "Updated"}],
                    "nextSyncToken": "sync-token-def",
                },
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        result = await conn.fetch_since("sync-token-abc")

        assert captured_params.get("syncToken") == "sync-token-abc"
        assert result.new_cursor == "sync-token-def"
        assert result.has_more is False

    async def test_gone_410_triggers_full_resync(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When syncToken is invalid, Google returns 410 Gone."""

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            resp = httpx.Response(
                410,
                json={"error": {"code": 410, "message": "syncToken invalidated"}},
                request=httpx.Request("GET", url),
            )
            resp.raise_for_status()
            return resp  # unreachable

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        result = await conn.fetch_since("old-invalid-token")

        # Signals caller to start a fresh full sync
        assert result.new_cursor is None
        assert result.has_more is True
        assert result.success_count == 0


class TestFetchSincePagination:
    """Pagination within a sync."""

    async def test_pagination_with_next_page_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "items": [{"id": "evt1"}],
                    "nextPageToken": "page-2-token",
                },
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        result = await conn.fetch_since(None)

        assert result.has_more is True
        assert result.new_cursor is not None
        # Cursor encodes the page token
        cursor_data = json.loads(result.new_cursor)
        assert cursor_data["pageToken"] == "page-2-token"

    async def test_compound_cursor_sends_page_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When a compound cursor (sync+page) is passed, pageToken is included."""
        captured_params: dict[str, str | int] = {}

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            params = kwargs.get("params")
            if isinstance(params, dict):
                captured_params.update(params)
            return httpx.Response(
                200,
                json={
                    "items": [],
                    "nextSyncToken": "sync-final",
                },
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        compound_cursor = _encode_cursor(sync_token="sync-abc", page_token="page-2")
        result = await conn.fetch_since(compound_cursor)

        assert captured_params.get("pageToken") == "page-2"
        assert captured_params.get("syncToken") == "sync-abc"
        assert result.new_cursor == "sync-final"
        assert result.has_more is False


class TestFetchSinceErrorHandling:
    """Error handling in sync."""

    async def test_rate_limit_429_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                429,
                json={"error": {"code": 429}},
                headers={"Retry-After": "60"},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        with pytest.raises(RateLimitError) as exc_info:
            await conn.fetch_since(None)
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60.0

    async def test_rate_limit_503_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                503,
                json={"error": {"code": 503}},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        with pytest.raises(RateLimitError) as exc_info:
            await conn.fetch_since(None)
        assert exc_info.value.status_code == 503

    async def test_api_error_raises_connector_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            resp = httpx.Response(
                401,
                json={"error": {"code": 401, "message": "Invalid Credentials"}},
                request=httpx.Request("GET", url),
            )
            resp.raise_for_status()
            return resp

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        with pytest.raises(ConnectorError, match="HTTP 401"):
            await conn.fetch_since(None)

    async def test_network_error_raises_connector_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        with pytest.raises(ConnectorError, match="network error"):
            await conn.fetch_since(None)


class TestCursorEncoding:
    """_encode_cursor / _decode_cursor helpers."""

    def test_encode_decode_compound(self) -> None:
        encoded = _encode_cursor(sync_token="sync-abc", page_token="page-2")
        sync, page = _decode_cursor(encoded)
        assert sync == "sync-abc"
        assert page == "page-2"

    def test_decode_plain_sync_token(self) -> None:
        sync, page = _decode_cursor("sync-token-xyz")
        assert sync == "sync-token-xyz"
        assert page is None

    def test_decode_none_sync_in_compound(self) -> None:
        encoded = _encode_cursor(sync_token=None, page_token="page-1")
        sync, page = _decode_cursor(encoded)
        assert sync is None
        assert page == "page-1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from pwbs.connectors.base import ConnectorConfig  # noqa: E402
from pwbs.core.config import get_settings  # noqa: E402
from pwbs.schemas.enums import SourceType  # noqa: E402


def _clear_settings() -> None:
    """Clear the cached settings so env var changes take effect."""
    get_settings.cache_clear()
