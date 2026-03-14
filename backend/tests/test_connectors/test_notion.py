"""Tests for Notion connector — OAuth2, Polling-Sync, health check (TASK-048, TASK-049)."""

from __future__ import annotations

import base64
import json
import uuid

import httpx
import pytest

from pwbs.connectors.notion import (
    NotionConnector,
    _NOTION_AUTH_URL,
    _decode_cursor,
    _encode_cursor,
)
from pwbs.connectors.base import ConnectorConfig
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import SourceType


# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------


def _make_connector(
    access_token: str = "test-notion-token",
) -> NotionConnector:
    return NotionConnector(
        owner_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        config=ConnectorConfig(
            source_type=SourceType.NOTION,
            extra={"access_token": access_token},
        ),
    )


def _clear_settings() -> None:
    get_settings.cache_clear()


def _set_notion_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set Notion OAuth env vars and clear settings cache."""
    monkeypatch.setenv("NOTION_CLIENT_ID", "test-notion-id")
    monkeypatch.setenv("NOTION_CLIENT_SECRET", "test-notion-secret")
    _clear_settings()


# ---------------------------------------------------------------------------
# build_auth_url
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    def test_generates_valid_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_notion_env(monkeypatch)

        url = NotionConnector.build_auth_url(
            redirect_uri="http://localhost:3000/callback",
            state="csrf-token",
        )
        assert _NOTION_AUTH_URL in url
        assert "client_id=test-notion-id" in url
        assert "redirect_uri=" in url
        assert "state=csrf-token" in url
        assert "response_type=code" in url
        assert "owner=user" in url

    def test_missing_client_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NOTION_CLIENT_ID", "")
        monkeypatch.setenv("NOTION_CLIENT_SECRET", "test-notion-secret")
        _clear_settings()

        with pytest.raises(ConnectorError, match="notion_client_id"):
            NotionConnector.build_auth_url(
                redirect_uri="http://localhost:3000/callback",
                state="csrf",
            )


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestExchangeCode:
    async def test_successful_exchange(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_notion_env(monkeypatch)

        captured_headers: dict[str, str] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            headers = kwargs.get("headers", {})
            if isinstance(headers, dict):
                captured_headers.update(headers)
            return httpx.Response(
                200,
                json={
                    "access_token": "ntn_new_token_123",
                    "token_type": "bearer",
                    "bot_id": "bot-id",
                    "workspace_id": "ws-id",
                    "workspace_name": "Test Workspace",
                },
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await NotionConnector.exchange_code(
            code="auth-code-123",
            redirect_uri="http://localhost:3000/callback",
        )

        assert isinstance(tokens, OAuthTokens)
        assert tokens.access_token.get_secret_value() == "ntn_new_token_123"
        assert tokens.refresh_token is None  # Notion has no refresh tokens
        assert tokens.expires_at is None  # Notion tokens don't expire

        # Verify Basic Auth header was sent
        expected_creds = base64.b64encode(b"test-notion-id:test-notion-secret").decode()
        assert captured_headers.get("Authorization") == f"Basic {expected_creds}"

    async def test_invalid_code_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_notion_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": "invalid_grant"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="token exchange failed"):
            await NotionConnector.exchange_code(
                code="bad-code",
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_network_error_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_notion_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="network error"):
            await NotionConnector.exchange_code(
                code="code",
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_missing_access_token_in_response_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_notion_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={"bot_id": "bot-id"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="missing access_token"):
            await NotionConnector.exchange_code(
                code="code",
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_missing_credentials_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NOTION_CLIENT_ID", "")
        monkeypatch.setenv("NOTION_CLIENT_SECRET", "")
        _clear_settings()

        with pytest.raises(ConnectorError, match="not configured"):
            await NotionConnector.exchange_code(
                code="code",
                redirect_uri="http://localhost:3000/callback",
            )


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_healthy_with_valid_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(200, json={}, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        assert await conn.health_check() is True

    async def test_unhealthy_with_invalid_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(401, json={}, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        assert await conn.health_check() is False

    async def test_no_token_returns_false(self) -> None:
        conn = NotionConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.NOTION),
        )
        assert await conn.health_check() is False


# ---------------------------------------------------------------------------
# BaseConnector integration
# ---------------------------------------------------------------------------


class TestBaseConnectorIntegration:
    def test_source_type(self) -> None:
        conn = _make_connector()
        assert conn.source_type == SourceType.NOTION

    async def test_fetch_since_requires_access_token(self) -> None:
        conn = NotionConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.NOTION),
        )
        with pytest.raises(ConnectorError, match="access_token"):
            await conn.fetch_since(None)

    async def test_normalize_not_implemented(self) -> None:
        conn = _make_connector()
        with pytest.raises(NotImplementedError, match="TASK-050"):
            await conn.normalize({})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TASK-049: Cursor encoding
# ---------------------------------------------------------------------------


class TestCursorEncoding:
    def test_encode_plain_watermark(self) -> None:
        cursor = _encode_cursor(watermark="2026-03-14T10:00:00.000Z")
        assert cursor == "2026-03-14T10:00:00.000Z"

    def test_encode_with_start_cursor(self) -> None:
        cursor = _encode_cursor(
            watermark="2026-03-14T10:00:00.000Z",
            start_cursor="abc-123",
        )
        data = json.loads(cursor)
        assert data["watermark"] == "2026-03-14T10:00:00.000Z"
        assert data["start_cursor"] == "abc-123"

    def test_decode_plain_watermark(self) -> None:
        wm, sc = _decode_cursor("2026-03-14T10:00:00.000Z")
        assert wm == "2026-03-14T10:00:00.000Z"
        assert sc is None

    def test_decode_compound(self) -> None:
        encoded = _encode_cursor(
            watermark="2026-03-14T10:00:00.000Z",
            start_cursor="page-2",
        )
        wm, sc = _decode_cursor(encoded)
        assert wm == "2026-03-14T10:00:00.000Z"
        assert sc == "page-2"

    def test_decode_empty_returns_none(self) -> None:
        wm, sc = _decode_cursor("")
        assert wm is None
        assert sc is None


# ---------------------------------------------------------------------------
# TASK-049: fetch_since
# ---------------------------------------------------------------------------


def _make_search_response(
    results: list[dict[str, object]],
    *,
    has_more: bool = False,
    next_cursor: str | None = None,
) -> dict[str, object]:
    return {
        "object": "list",
        "results": results,
        "has_more": has_more,
        "next_cursor": next_cursor,
    }


def _make_page(
    page_id: str,
    last_edited: str = "2026-03-14T10:00:00.000Z",
) -> dict[str, object]:
    return {
        "object": "page",
        "id": page_id,
        "last_edited_time": last_edited,
        "properties": {"title": {"title": [{"text": {"content": f"Page {page_id}"}}]}},
    }


class TestFetchSinceInitialSync:
    """Initial full sync (cursor=None)."""

    async def test_initial_sync_fetches_all_pages(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_body: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            body = kwargs.get("json", {})
            if isinstance(body, dict):
                captured_body.update(body)
            return httpx.Response(
                200,
                json=_make_search_response(
                    [_make_page("page-1"), _make_page("page-2", "2026-03-14T12:00:00.000Z")],
                ),
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        conn = _make_connector()
        result = await conn.fetch_since(None)

        # No watermark filter on initial sync
        assert "filter" not in captured_body
        assert result.has_more is False
        # Latest watermark should be the most recent last_edited_time
        assert result.new_cursor == "2026-03-14T12:00:00.000Z"
        # Until TASK-050, events appear as errors
        assert result.error_count == 2


class TestFetchSinceIncrementalSync:
    """Incremental sync with watermark cursor."""

    async def test_incremental_sends_filter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_body: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            body = kwargs.get("json", {})
            if isinstance(body, dict):
                captured_body.update(body)
            return httpx.Response(
                200,
                json=_make_search_response(
                    [_make_page("page-3", "2026-03-14T15:00:00.000Z")],
                ),
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        conn = _make_connector()
        result = await conn.fetch_since("2026-03-14T10:00:00.000Z")

        # Should include filter with watermark
        assert "filter" in captured_body
        filt = captured_body["filter"]
        assert isinstance(filt, dict)
        assert filt["timestamp"] == "last_edited_time"
        assert filt["last_edited_time"]["after"] == "2026-03-14T10:00:00.000Z"

        assert result.new_cursor == "2026-03-14T15:00:00.000Z"

    async def test_no_new_results(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json=_make_search_response([]),
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        conn = _make_connector()
        result = await conn.fetch_since("2026-03-14T10:00:00.000Z")

        # Watermark stays the same when no new results
        assert result.new_cursor == "2026-03-14T10:00:00.000Z"
        assert result.has_more is False
        assert result.error_count == 0


class TestFetchSincePagination:
    """Pagination through large result sets."""

    async def test_has_more_returns_compound_cursor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json=_make_search_response(
                    [_make_page("page-1")],
                    has_more=True,
                    next_cursor="cursor-page-2",
                ),
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        conn = _make_connector()
        result = await conn.fetch_since(None)

        assert result.has_more is True
        assert result.new_cursor is not None
        data = json.loads(result.new_cursor)
        assert data["start_cursor"] == "cursor-page-2"

    async def test_compound_cursor_sends_start_cursor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_body: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            body = kwargs.get("json", {})
            if isinstance(body, dict):
                captured_body.update(body)
            return httpx.Response(
                200,
                json=_make_search_response(
                    [_make_page("page-2", "2026-03-14T16:00:00.000Z")],
                ),
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        compound = _encode_cursor(
            watermark="2026-03-14T10:00:00.000Z",
            start_cursor="cursor-page-2",
        )
        conn = _make_connector()
        result = await conn.fetch_since(compound)

        assert captured_body.get("start_cursor") == "cursor-page-2"
        assert result.has_more is False
        assert result.new_cursor == "2026-03-14T16:00:00.000Z"


class TestFetchSinceErrorHandling:
    """Error scenarios for fetch_since."""

    async def test_rate_limit_429_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                429,
                headers={"Retry-After": "30"},
                json={"message": "rate limited"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        conn = _make_connector()
        with pytest.raises(RateLimitError):
            await conn.fetch_since(None)

    async def test_api_error_raises_connector_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                500,
                json={"message": "internal error"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        conn = _make_connector()
        with pytest.raises(ConnectorError, match="search failed"):
            await conn.fetch_since(None)

    async def test_network_error_raises_connector_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        conn = _make_connector()
        with pytest.raises(ConnectorError, match="network error"):
            await conn.fetch_since(None)

    async def test_missing_access_token_raises(self) -> None:
        conn = NotionConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.NOTION),
        )
        with pytest.raises(ConnectorError, match="access_token"):
            await conn.fetch_since(None)
