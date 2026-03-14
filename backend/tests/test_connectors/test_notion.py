"""Tests for Notion connector — OAuth2, Polling-Sync, Normalizer (TASK-048..050)."""

from __future__ import annotations

import base64
import json
import uuid

import httpx
import pytest

from pwbs.connectors.base import ConnectorConfig
from pwbs.connectors.notion import (
    _NOTION_AUTH_URL,
    NotionConnector,
    _block_to_markdown,
    _blocks_to_markdown,
    _collect_all_mentions,
    _decode_cursor,
    _encode_cursor,
    _extract_mentions,
    _extract_page_properties,
    _extract_page_title,
    _extract_plain_text,
)
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import ContentType, SourceType

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


def _make_block(
    block_type: str,
    text: str,
    *,
    children: list[dict[str, object]] | None = None,
    **extra: object,
) -> dict[str, object]:
    """Build a minimal Notion block dict for testing."""
    block: dict[str, object] = {
        "type": block_type,
        "id": f"block-{uuid.uuid4().hex[:8]}",
        "has_children": bool(children),
        block_type: {
            "rich_text": [{"plain_text": text, "type": "text"}],
            **extra,
        },
    }
    if children:
        block["_children"] = children
    return block


def _make_raw_page(
    *,
    page_id: str = "page-abc",
    title: str = "Test Page",
    blocks: list[dict[str, object]] | None = None,
    object_type: str = "page",
    properties: dict[str, object] | None = None,
    created_time: str = "2025-01-15T10:00:00.000Z",
    last_edited_time: str = "2025-01-16T12:00:00.000Z",
) -> dict[str, object]:
    """Build a minimal raw Notion page dict (as returned by POST /search)."""
    if properties is None:
        properties = {
            "Name": {
                "type": "title",
                "title": [{"plain_text": title, "type": "text"}],
            },
        }
    raw: dict[str, object] = {
        "object": object_type,
        "id": page_id,
        "created_time": created_time,
        "last_edited_time": last_edited_time,
        "properties": properties,
    }
    if blocks is not None:
        raw["_blocks"] = blocks
    return raw


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

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(200, json={}, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        assert await conn.health_check() is True

    async def test_unhealthy_with_invalid_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

    async def test_normalize_basic_page(self) -> None:
        """normalize() converts a Notion page with blocks into UnifiedDocument."""
        conn = _make_connector()
        raw = _make_raw_page(
            page_id="page-123",
            title="Meeting Notes",
            blocks=[
                _make_block("paragraph", "First paragraph."),
                _make_block("heading_2", "Section"),
                _make_block("paragraph", "Second paragraph."),
            ],
        )
        doc = await conn.normalize(raw)  # type: ignore[arg-type]
        assert doc.source_type == SourceType.NOTION
        assert doc.source_id == "page-123"
        assert doc.title == "Meeting Notes"
        assert doc.content_type == ContentType.MARKDOWN
        assert "First paragraph." in doc.content
        assert "## Section" in doc.content
        assert "Second paragraph." in doc.content

    async def test_normalize_page_without_blocks_uses_title(self) -> None:
        conn = _make_connector()
        raw = _make_raw_page(page_id="empty-page", title="Empty Page", blocks=[])
        doc = await conn.normalize(raw)  # type: ignore[arg-type]
        assert doc.content == "Empty Page"

    async def test_normalize_missing_id_raises(self) -> None:
        conn = _make_connector()
        with pytest.raises(ConnectorError, match="missing 'id'"):
            await conn.normalize({"object": "page"})  # type: ignore[arg-type]


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
        "created_time": "2026-03-14T08:00:00.000Z",
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": f"Page {page_id}", "type": "text"}],
            },
        },
    }


async def _mock_get_empty_blocks(
    self: httpx.AsyncClient, url: str, **kwargs: object,
) -> httpx.Response:
    """Mock GET for /blocks/{id}/children — returns empty block list."""
    return httpx.Response(
        200,
        json={"object": "list", "results": [], "has_more": False, "next_cursor": None},
        request=httpx.Request("GET", url),
    )


class TestFetchSinceInitialSync:
    """Initial full sync (cursor=None)."""

    async def test_initial_sync_fetches_all_pages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured_body: dict[str, object] = {}

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
        monkeypatch.setattr(httpx.AsyncClient, "get", _mock_get_empty_blocks)

        conn = _make_connector()
        result = await conn.fetch_since(None)

        # No watermark filter on initial sync
        assert "filter" not in captured_body
        assert result.has_more is False
        # Latest watermark should be the most recent last_edited_time
        assert result.new_cursor == "2026-03-14T12:00:00.000Z"
        # TASK-050: pages are now normalized into documents
        assert result.success_count == 2
        assert result.error_count == 0


class TestFetchSinceIncrementalSync:
    """Incremental sync with watermark cursor."""

    async def test_incremental_sends_filter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured_body: dict[str, object] = {}

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
        monkeypatch.setattr(httpx.AsyncClient, "get", _mock_get_empty_blocks)

        conn = _make_connector()
        result = await conn.fetch_since("2026-03-14T10:00:00.000Z")

        # Should include filter with watermark
        assert "filter" in captured_body
        filt = captured_body["filter"]
        assert isinstance(filt, dict)
        assert filt["timestamp"] == "last_edited_time"
        assert filt["last_edited_time"]["after"] == "2026-03-14T10:00:00.000Z"

        assert result.new_cursor == "2026-03-14T15:00:00.000Z"

    async def test_no_new_results(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

    async def test_has_more_returns_compound_cursor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
        monkeypatch.setattr(httpx.AsyncClient, "get", _mock_get_empty_blocks)

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

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
        monkeypatch.setattr(httpx.AsyncClient, "get", _mock_get_empty_blocks)

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

    async def test_rate_limit_429_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

    async def test_api_error_raises_connector_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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


# ---------------------------------------------------------------------------
# TASK-050: Helper functions
# ---------------------------------------------------------------------------


class TestExtractPlainText:
    def test_basic_rich_text(self) -> None:
        rt = [{"plain_text": "Hello ", "type": "text"}, {"plain_text": "World", "type": "text"}]
        assert _extract_plain_text(rt) == "Hello World"

    def test_empty_list(self) -> None:
        assert _extract_plain_text([]) == ""

    def test_non_dict_segments_skipped(self) -> None:
        assert _extract_plain_text(["bad"]) == ""  # type: ignore[list-item]


class TestBlockToMarkdown:
    def test_paragraph(self) -> None:
        block = _make_block("paragraph", "Hello world")
        assert _block_to_markdown(block) == "Hello world"

    def test_heading_1(self) -> None:
        assert _block_to_markdown(_make_block("heading_1", "Title")) == "# Title"

    def test_heading_2(self) -> None:
        assert _block_to_markdown(_make_block("heading_2", "Sub")) == "## Sub"

    def test_heading_3(self) -> None:
        assert _block_to_markdown(_make_block("heading_3", "Sub2")) == "### Sub2"

    def test_bulleted_list_item(self) -> None:
        assert _block_to_markdown(_make_block("bulleted_list_item", "Item")) == "- Item"

    def test_numbered_list_item(self) -> None:
        assert _block_to_markdown(_make_block("numbered_list_item", "Step")) == "1. Step"

    def test_to_do_unchecked(self) -> None:
        block = _make_block("to_do", "Task", checked=False)
        assert _block_to_markdown(block) == "- [ ] Task"

    def test_to_do_checked(self) -> None:
        block = _make_block("to_do", "Done", checked=True)
        assert _block_to_markdown(block) == "- [x] Done"

    def test_code_block(self) -> None:
        block = _make_block("code", "print('hi')", language="python")
        md = _block_to_markdown(block)
        assert "```python" in md
        assert "print('hi')" in md

    def test_toggle(self) -> None:
        block = _make_block("toggle", "Details")
        assert _block_to_markdown(block) == "> **Details**"

    def test_callout_with_emoji(self) -> None:
        block = _make_block("callout", "Important note", icon={"type": "emoji", "emoji": "💡"})
        md = _block_to_markdown(block)
        assert "💡" in md
        assert "Important note" in md

    def test_quote(self) -> None:
        assert _block_to_markdown(_make_block("quote", "A quote")) == "> A quote"

    def test_divider(self) -> None:
        block: dict[str, object] = {"type": "divider", "id": "div-1", "has_children": False}
        assert _block_to_markdown(block) == "---"

    def test_nested_children(self) -> None:
        child = _make_block("paragraph", "Child text")
        parent = _make_block("toggle", "Parent", children=[child])
        md = _block_to_markdown(parent)
        assert "Parent" in md
        assert "Child text" in md


class TestBlocksToMarkdown:
    def test_joins_blocks_with_double_newline(self) -> None:
        blocks = [
            _make_block("heading_1", "Title"),
            _make_block("paragraph", "Para"),
        ]
        md = _blocks_to_markdown(blocks)
        assert "# Title\n\n" in md
        assert "Para" in md

    def test_empty_blocks(self) -> None:
        assert _blocks_to_markdown([]) == ""


class TestExtractPageTitle:
    def test_extracts_title(self) -> None:
        props = {"Name": {"type": "title", "title": [{"plain_text": "My Page"}]}}
        assert _extract_page_title(props) == "My Page"

    def test_fallback_no_title(self) -> None:
        assert _extract_page_title({}) == "(Kein Titel)"

    def test_empty_title_array(self) -> None:
        props = {"Name": {"type": "title", "title": []}}
        assert _extract_page_title(props) == "(Kein Titel)"


class TestExtractPageProperties:
    def test_select_property(self) -> None:
        props = {"Status": {"type": "select", "select": {"name": "In Progress"}}}
        meta = _extract_page_properties(props)
        assert meta["Status"] == "In Progress"

    def test_multi_select_property(self) -> None:
        props = {
            "Tags": {
                "type": "multi_select",
                "multi_select": [{"name": "python"}, {"name": "backend"}],
            }
        }
        meta = _extract_page_properties(props)
        assert meta["Tags"] == ["python", "backend"]

    def test_date_property(self) -> None:
        props = {"Due": {"type": "date", "date": {"start": "2025-06-01"}}}
        meta = _extract_page_properties(props)
        assert meta["Due"] == "2025-06-01"

    def test_checkbox_property(self) -> None:
        props = {"Done": {"type": "checkbox", "checkbox": True}}
        meta = _extract_page_properties(props)
        assert meta["Done"] == "True"

    def test_title_skipped(self) -> None:
        props = {"Name": {"type": "title", "title": [{"plain_text": "Skip me"}]}}
        meta = _extract_page_properties(props)
        assert "Name" not in meta


class TestExtractMentions:
    def test_user_mention(self) -> None:
        rt = [
            {
                "type": "mention",
                "mention": {
                    "type": "user",
                    "user": {"id": "user-1", "name": "Alice"},
                },
            }
        ]
        mentions = _extract_mentions(rt)
        assert len(mentions) == 1
        assert mentions[0]["type"] == "user"
        assert mentions[0]["name"] == "Alice"

    def test_page_mention(self) -> None:
        rt = [
            {
                "type": "mention",
                "mention": {"type": "page", "page": {"id": "page-1"}},
            }
        ]
        mentions = _extract_mentions(rt)
        assert len(mentions) == 1
        assert mentions[0]["type"] == "page"
        assert mentions[0]["id"] == "page-1"

    def test_database_mention(self) -> None:
        rt = [
            {
                "type": "mention",
                "mention": {"type": "database", "database": {"id": "db-1"}},
            }
        ]
        mentions = _extract_mentions(rt)
        assert len(mentions) == 1
        assert mentions[0]["type"] == "database"

    def test_no_mentions(self) -> None:
        rt = [{"type": "text", "plain_text": "No mentions here"}]
        assert _extract_mentions(rt) == []


class TestCollectAllMentions:
    def test_nested_mentions(self) -> None:
        child = {
            "type": "paragraph",
            "id": "c1",
            "has_children": False,
            "paragraph": {
                "rich_text": [
                    {
                        "type": "mention",
                        "mention": {"type": "user", "user": {"id": "u1", "name": "Bob"}},
                    }
                ],
            },
        }
        parent = {
            "type": "toggle",
            "id": "p1",
            "has_children": True,
            "toggle": {"rich_text": [{"type": "text", "plain_text": "Toggle"}]},
            "_children": [child],
        }
        mentions = _collect_all_mentions([parent])
        assert len(mentions) == 1
        assert mentions[0]["name"] == "Bob"


# ---------------------------------------------------------------------------
# TASK-050: Normalize integration
# ---------------------------------------------------------------------------


class TestNormalize:
    async def test_database_entry(self) -> None:
        conn = _make_connector()
        raw = _make_raw_page(
            page_id="db-entry-1",
            title="DB Row",
            object_type="database",
            blocks=[_make_block("paragraph", "DB content")],
        )
        doc = await conn.normalize(raw)  # type: ignore[arg-type]
        assert doc.source_id == "db-entry-1"
        assert doc.metadata["object_type"] == "database"

    async def test_properties_in_metadata(self) -> None:
        conn = _make_connector()
        raw = _make_raw_page(
            page_id="page-props",
            title="Props Page",
            blocks=[_make_block("paragraph", "content")],
            properties={
                "Name": {"type": "title", "title": [{"plain_text": "Props Page"}]},
                "Status": {"type": "select", "select": {"name": "Done"}},
                "Tags": {
                    "type": "multi_select",
                    "multi_select": [{"name": "tag1"}, {"name": "tag2"}],
                },
            },
        )
        doc = await conn.normalize(raw)  # type: ignore[arg-type]
        assert doc.metadata["Status"] == "Done"
        assert doc.metadata["Tags"] == ["tag1", "tag2"]

    async def test_mentions_in_metadata(self) -> None:
        conn = _make_connector()
        mention_block = {
            "type": "paragraph",
            "id": "b1",
            "has_children": False,
            "paragraph": {
                "rich_text": [
                    {
                        "type": "mention",
                        "plain_text": "@Alice",
                        "mention": {
                            "type": "user",
                            "user": {"id": "u1", "name": "Alice"},
                        },
                    }
                ],
            },
        }
        raw = _make_raw_page(
            page_id="mention-page",
            title="Mentions",
            blocks=[mention_block],
        )
        doc = await conn.normalize(raw)  # type: ignore[arg-type]
        assert "mentions" in doc.metadata
        assert any(m["name"] == "Alice" for m in doc.metadata["mentions"])

    async def test_timestamps_parsed(self) -> None:
        conn = _make_connector()
        raw = _make_raw_page(
            page_id="ts-page",
            title="Timestamps",
            blocks=[_make_block("paragraph", "text")],
            created_time="2025-01-10T08:00:00.000Z",
            last_edited_time="2025-01-11T09:00:00.000Z",
        )
        doc = await conn.normalize(raw)  # type: ignore[arg-type]
        assert doc.created_at.year == 2025
        assert doc.updated_at.month == 1

    async def test_all_block_types_in_content(self) -> None:
        conn = _make_connector()
        raw = _make_raw_page(
            page_id="all-blocks",
            title="All Blocks",
            blocks=[
                _make_block("heading_1", "H1"),
                _make_block("heading_2", "H2"),
                _make_block("heading_3", "H3"),
                _make_block("paragraph", "Para"),
                _make_block("bulleted_list_item", "Bullet"),
                _make_block("numbered_list_item", "Numbered"),
                _make_block("code", "x = 1", language="python"),
                _make_block("quote", "A quote"),
                _make_block("callout", "Note", icon={"type": "emoji", "emoji": "📝"}),
            ],
        )
        doc = await conn.normalize(raw)  # type: ignore[arg-type]
        assert "# H1" in doc.content
        assert "## H2" in doc.content
        assert "### H3" in doc.content
        assert "Para" in doc.content
        assert "- Bullet" in doc.content
        assert "1. Numbered" in doc.content
        assert "```python" in doc.content
        assert "> A quote" in doc.content
        assert "📝" in doc.content
