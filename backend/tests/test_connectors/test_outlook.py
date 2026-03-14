"""Tests for Outlook Mail connector (TASK-128)."""

from __future__ import annotations

import json
import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from pwbs.connectors.base import ConnectorConfig, SyncResult
from pwbs.connectors.outlook import (
    _MS_AUTH_URL,
    _MS_TOKEN_URL,
    OUTLOOK_SCOPE,
    OutlookMailConnector,
    _decode_cursor,
    _encode_cursor,
    _raise_for_rate_limit,
    _strip_html,
)
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import SourceType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OWNER_ID = uuid.uuid4()
CONNECTION_ID = uuid.uuid4()
REDIRECT_URI = "http://localhost:3000/api/connectors/outlook-mail/callback"
STATE_TOKEN = "csrf-state-outlook"


def _make_connector(
    access_token: str = "test-outlook-token",
) -> OutlookMailConnector:
    return OutlookMailConnector(
        owner_id=OWNER_ID,
        connection_id=CONNECTION_ID,
        config=ConnectorConfig(
            source_type=SourceType.OUTLOOK_MAIL,
            extra={"access_token": access_token},
        ),
    )


def _clear_settings() -> None:
    get_settings.cache_clear()


def _set_ms_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MS_CLIENT_ID", "test-ms-client-id")
    monkeypatch.setenv("MS_CLIENT_SECRET", "test-ms-secret")
    monkeypatch.setenv("MS_TENANT_ID", "test-tenant")
    _clear_settings()


def _graph_response(data: dict, *, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        json=data,
        request=httpx.Request("GET", "https://graph.microsoft.com/v1.0/test"),
    )


def _make_message(
    *,
    msg_id: str = "msg-1",
    subject: str = "Test Subject",
    conversation_id: str = "conv-1",
    from_addr: str = "alice@example.com",
    to_addrs: list[str] | None = None,
    body_html: str = "<p>Hello World</p>",
    received: str = "2026-01-15T10:00:00Z",
    has_attachments: bool = False,
) -> dict:
    to_list = to_addrs or ["bob@example.com"]
    return {
        "id": msg_id,
        "subject": subject,
        "conversationId": conversation_id,
        "from": {"emailAddress": {"address": from_addr, "name": "Alice"}},
        "toRecipients": [
            {"emailAddress": {"address": a, "name": ""}} for a in to_list
        ],
        "ccRecipients": [],
        "body": {"contentType": "html", "content": body_html},
        "receivedDateTime": received,
        "hasAttachments": has_attachments,
        "importance": "normal",
        "isRead": True,
    }


# ---------------------------------------------------------------------------
# SourceType
# ---------------------------------------------------------------------------


class TestSourceType:
    def test_outlook_mail_in_source_types(self) -> None:
        assert SourceType.OUTLOOK_MAIL.value == "outlook_mail"
        assert "outlook_mail" in [s.value for s in SourceType]


# ---------------------------------------------------------------------------
# _strip_html
# ---------------------------------------------------------------------------


class TestStripHtml:
    def test_basic_html(self) -> None:
        assert _strip_html("<p>Hello</p>") == "Hello"

    def test_br_becomes_newline(self) -> None:
        result = _strip_html("Line1<br/>Line2")
        assert "Line1" in result
        assert "Line2" in result
        assert "\n" in result

    def test_entities_decoded(self) -> None:
        assert _strip_html("&amp; &lt; &gt;") == "& < >"

    def test_style_and_script_stripped(self) -> None:
        html = "<style>body{color:red}</style><script>alert(1)</script><p>Content</p>"
        result = _strip_html(html)
        assert "Content" in result
        assert "color" not in result
        assert "alert" not in result

    def test_empty_string(self) -> None:
        assert _strip_html("") == ""

    def test_plain_text_passthrough(self) -> None:
        assert _strip_html("No HTML here") == "No HTML here"

    def test_multiple_blank_lines_collapsed(self) -> None:
        html = "<p>A</p><p></p><p></p><p></p><p>B</p>"
        result = _strip_html(html)
        assert "\n\n\n" not in result


# ---------------------------------------------------------------------------
# _encode_cursor / _decode_cursor
# ---------------------------------------------------------------------------


class TestCursor:
    def test_roundtrip_delta_link(self) -> None:
        cursor = _encode_cursor(delta_link="https://graph/delta?token=abc")
        delta, page = _decode_cursor(cursor)
        assert delta == "https://graph/delta?token=abc"
        assert page is None

    def test_roundtrip_page_link(self) -> None:
        cursor = _encode_cursor(page_link="https://graph/next?skip=50")
        delta, page = _decode_cursor(cursor)
        assert delta is None
        assert page == "https://graph/next?skip=50"

    def test_roundtrip_both(self) -> None:
        cursor = _encode_cursor(
            delta_link="https://delta",
            page_link="https://page",
        )
        delta, page = _decode_cursor(cursor)
        assert delta == "https://delta"
        assert page == "https://page"

    def test_decode_invalid_returns_none(self) -> None:
        delta, page = _decode_cursor("not-json")
        assert delta is None
        assert page is None

    def test_decode_none_returns_none(self) -> None:
        delta, page = _decode_cursor(None)  # type: ignore[arg-type]
        assert delta is None
        assert page is None


# ---------------------------------------------------------------------------
# _raise_for_rate_limit
# ---------------------------------------------------------------------------


class TestRaiseForRateLimit:
    def test_429_raises(self) -> None:
        resp = httpx.Response(
            429,
            headers={"Retry-After": "30"},
            request=httpx.Request("GET", "https://test"),
        )
        with pytest.raises(RateLimitError):
            _raise_for_rate_limit(resp)

    def test_200_passes(self) -> None:
        resp = httpx.Response(200, request=httpx.Request("GET", "https://test"))
        _raise_for_rate_limit(resp)  # no exception


# ---------------------------------------------------------------------------
# build_auth_url
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    def test_generates_valid_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_ms_env(monkeypatch)

        url = OutlookMailConnector.build_auth_url(
            redirect_uri=REDIRECT_URI, state=STATE_TOKEN
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert "login.microsoftonline.com" in parsed.netloc
        assert params["client_id"] == ["test-ms-client-id"]
        assert params["redirect_uri"] == [REDIRECT_URI]
        assert params["response_type"] == ["code"]
        assert params["scope"] == [OUTLOOK_SCOPE]
        assert params["state"] == [STATE_TOKEN]

        _clear_settings()

    def test_missing_client_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MS_CLIENT_ID", "")
        monkeypatch.setenv("MS_CLIENT_SECRET", "s")
        _clear_settings()

        with pytest.raises(ConnectorError):
            OutlookMailConnector.build_auth_url(
                redirect_uri=REDIRECT_URI, state=STATE_TOKEN
            )

        _clear_settings()


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestExchangeCode:
    @pytest.mark.asyncio
    async def test_successful_exchange(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_ms_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "access_token": "outlook-access-token",
                    "refresh_token": "outlook-refresh-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": OUTLOOK_SCOPE,
                },
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await OutlookMailConnector.exchange_code(
            code="auth-code", redirect_uri=REDIRECT_URI
        )
        assert isinstance(tokens, OAuthTokens)
        assert tokens.access_token.get_secret_value() == "outlook-access-token"
        assert tokens.refresh_token.get_secret_value() == "outlook-refresh-token"
        assert tokens.expires_at is not None

        _clear_settings()

    @pytest.mark.asyncio
    async def test_http_error_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_ms_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": "invalid_grant", "error_description": "Bad code"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="code exchange failed"):
            await OutlookMailConnector.exchange_code(
                code="bad-code", redirect_uri=REDIRECT_URI
            )

        _clear_settings()

    @pytest.mark.asyncio
    async def test_missing_credentials_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MS_CLIENT_ID", "")
        monkeypatch.setenv("MS_CLIENT_SECRET", "")
        _clear_settings()

        with pytest.raises(ConnectorError, match="credentials not configured"):
            await OutlookMailConnector.exchange_code(
                code="code", redirect_uri=REDIRECT_URI
            )

        _clear_settings()

    @pytest.mark.asyncio
    async def test_rate_limit_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_ms_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                429,
                headers={"Retry-After": "60"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(RateLimitError):
            await OutlookMailConnector.exchange_code(
                code="code", redirect_uri=REDIRECT_URI
            )

        _clear_settings()


# ---------------------------------------------------------------------------
# fetch_since
# ---------------------------------------------------------------------------


class TestFetchSince:
    @pytest.mark.asyncio
    async def test_initial_delta_sync(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return _graph_response(
                {
                    "value": [
                        _make_message(msg_id="m1", conversation_id="c1"),
                        _make_message(msg_id="m2", conversation_id="c1",
                                      from_addr="bob@example.com",
                                      received="2026-01-15T10:05:00Z"),
                    ],
                    "@odata.deltaLink": "https://graph/delta?token=new",
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert isinstance(result, SyncResult)
        # Two messages in same conversation -> merged to 1 document
        assert len(result.documents) == 1
        assert result.errors == []
        assert result.has_more is False

        # Cursor should contain the delta link
        delta, page = _decode_cursor(result.new_cursor)
        assert delta == "https://graph/delta?token=new"
        assert page is None

    @pytest.mark.asyncio
    async def test_incremental_sync_uses_delta_link(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()
        saved_urls: list[str] = []

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            saved_urls.append(url)
            return _graph_response(
                {
                    "value": [_make_message()],
                    "@odata.deltaLink": "https://graph/delta?token=v2",
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        cursor = _encode_cursor(delta_link="https://graph/delta?token=v1")
        result = await connector.fetch_since(cursor)

        # Should have used the delta link from the cursor
        assert saved_urls[0] == "https://graph/delta?token=v1"
        assert len(result.documents) == 1

    @pytest.mark.asyncio
    async def test_pagination_via_next_link(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return _graph_response(
                {
                    "value": [_make_message()],
                    "@odata.nextLink": "https://graph/next?skip=50",
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert result.has_more is True

        # Cursor should contain the page link
        _, page = _decode_cursor(result.new_cursor)
        assert page == "https://graph/next?skip=50"

    @pytest.mark.asyncio
    async def test_multiple_conversations_separated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return _graph_response(
                {
                    "value": [
                        _make_message(msg_id="m1", conversation_id="conv-A"),
                        _make_message(msg_id="m2", conversation_id="conv-B",
                                      subject="Other topic"),
                    ],
                    "@odata.deltaLink": "https://delta",
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert len(result.documents) == 2
        source_ids = {d.source_id for d in result.documents}
        assert "outlook:conv:conv-A" in source_ids
        assert "outlook:conv:conv-B" in source_ids

    @pytest.mark.asyncio
    async def test_rate_limit_propagates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                429,
                headers={"Retry-After": "10"},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        with pytest.raises(RateLimitError):
            await connector.fetch_since(None)

    @pytest.mark.asyncio
    async def test_network_error_captured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert len(result.errors) == 1
        assert "Network error" in result.errors[0].error

    @pytest.mark.asyncio
    async def test_http_error_captured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                500,
                json={"error": {"code": "InternalServerError"}},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert len(result.errors) == 1
        assert "HTTP 500" in result.errors[0].error

    @pytest.mark.asyncio
    async def test_missing_token_raises(self) -> None:
        connector = _make_connector(access_token="")
        connector.config = ConnectorConfig(
            source_type=SourceType.OUTLOOK_MAIL, extra={}
        )

        with pytest.raises(ConnectorError, match="access_token missing"):
            await connector.fetch_since(None)


# ---------------------------------------------------------------------------
# _normalize_thread
# ---------------------------------------------------------------------------


class TestNormalizeThread:
    def test_merges_messages_sorted_by_time(self) -> None:
        connector = _make_connector()
        messages = [
            _make_message(
                msg_id="m2",
                received="2026-01-15T10:05:00Z",
                from_addr="bob@example.com",
                body_html="<p>Reply</p>",
            ),
            _make_message(
                msg_id="m1",
                received="2026-01-15T10:00:00Z",
                from_addr="alice@example.com",
                body_html="<p>Original</p>",
            ),
        ]

        doc = connector._normalize_thread("conv-1", messages)

        assert doc.source_id == "outlook:conv:conv-1"
        assert doc.user_id == OWNER_ID
        assert doc.source_type == SourceType.OUTLOOK_MAIL
        # Content should start with alice (earlier) before bob
        assert doc.content.index("alice@example.com") < doc.content.index(
            "bob@example.com"
        )

    def test_extracts_participants(self) -> None:
        connector = _make_connector()
        messages = [
            _make_message(
                from_addr="alice@example.com",
                to_addrs=["bob@example.com", "carol@example.com"],
            ),
        ]

        doc = connector._normalize_thread("conv-1", messages)
        parts = doc.metadata.get("participants", [])
        assert "alice@example.com" in parts
        assert "bob@example.com" in parts
        assert "carol@example.com" in parts

    def test_html_stripped_from_body(self) -> None:
        connector = _make_connector()
        messages = [
            _make_message(body_html="<b>Bold</b> <i>italic</i>"),
        ]

        doc = connector._normalize_thread("conv-1", messages)
        assert "<b>" not in doc.content
        assert "<i>" not in doc.content
        assert "Bold" in doc.content
        assert "italic" in doc.content

    def test_metadata_fields(self) -> None:
        connector = _make_connector()
        messages = [
            _make_message(has_attachments=True),
        ]

        doc = connector._normalize_thread("conv-1", messages)
        assert doc.metadata["conversation_id"] == "conv-1"
        assert doc.metadata["message_count"] == 1
        assert doc.metadata["has_attachments"] is True

    def test_subject_used_as_title(self) -> None:
        connector = _make_connector()
        messages = [_make_message(subject="Important Email")]

        doc = connector._normalize_thread("conv-1", messages)
        assert doc.title == "Important Email"

    def test_empty_subject_fallback(self) -> None:
        connector = _make_connector()
        messages = [_make_message(subject="")]

        doc = connector._normalize_thread("conv-1", messages)
        assert doc.title == "(kein Betreff)"


# ---------------------------------------------------------------------------
# normalize (single message)
# ---------------------------------------------------------------------------


class TestNormalize:
    @pytest.mark.asyncio
    async def test_normalizes_single_message(self) -> None:
        connector = _make_connector()
        raw = _make_message(msg_id="msg-single", subject="Single Email")

        doc = await connector.normalize(raw)

        assert doc.source_id == "msg-single"
        assert doc.source_type == SourceType.OUTLOOK_MAIL
        assert "Single Email" in doc.content

    @pytest.mark.asyncio
    async def test_missing_id_raises(self) -> None:
        connector = _make_connector()
        raw = _make_message()
        del raw["id"]

        with pytest.raises(ConnectorError, match="missing 'id'"):
            await connector.normalize(raw)

    @pytest.mark.asyncio
    async def test_html_body_converted(self) -> None:
        connector = _make_connector()
        raw = _make_message(body_html="<div>Rich <b>text</b></div>")

        doc = await connector.normalize(raw)
        assert "<div>" not in doc.content
        assert "Rich" in doc.content
        assert "text" in doc.content


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
            assert "/me" in url
            return httpx.Response(200, json={"id": "user-123"})

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        assert await connector.health_check() is True

    @pytest.mark.asyncio
    async def test_unhealthy_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(401, text="Unauthorized")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_no_token_returns_false(self) -> None:
        connector = _make_connector(access_token="")
        connector.config = ConnectorConfig(
            source_type=SourceType.OUTLOOK_MAIL, extra={}
        )
        assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_network_error_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        assert await connector.health_check() is False
