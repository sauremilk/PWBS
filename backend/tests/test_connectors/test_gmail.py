"""Tests for Gmail connector -- OAuth2 + Pub/Sub + Sync (TASK-123)."""

from __future__ import annotations

import base64
import json
import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from pwbs.connectors.base import ConnectorConfig
from pwbs.connectors.gmail import (
    _GOOGLE_AUTH_URL,
    _GOOGLE_TOKEN_URL,
    GMAIL_SCOPE,
    GmailConnector,
    _decode_body_part,
    _decode_cursor,
    _encode_cursor,
    _extract_header,
    _extract_text_content,
    _raise_for_rate_limit,
)
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import SourceType

# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------


def _make_connector(
    access_token: str = "test-gmail-token",
    max_batch_size: int = 100,
) -> GmailConnector:
    return GmailConnector(
        owner_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        config=ConnectorConfig(
            source_type=SourceType.GMAIL,
            max_batch_size=max_batch_size,
            extra={"access_token": access_token},
        ),
    )


def _clear_settings() -> None:
    """Clear the cached settings so env var changes take effect."""
    get_settings.cache_clear()


def _set_google_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set Google OAuth env vars and clear settings cache."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    _clear_settings()


REDIRECT_URI = "http://localhost:3000/api/connectors/gmail/callback"
STATE_TOKEN = "csrf-state-abc123"


# ---------------------------------------------------------------------------
# build_auth_url tests
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    def test_generates_valid_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_google_env(monkeypatch)

        url = GmailConnector.build_auth_url(redirect_uri=REDIRECT_URI, state=STATE_TOKEN)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert parsed.netloc == "accounts.google.com"
        assert params["client_id"] == ["test-client-id"]
        assert params["redirect_uri"] == [REDIRECT_URI]
        assert params["response_type"] == ["code"]
        assert params["scope"] == [GMAIL_SCOPE]
        assert params["access_type"] == ["offline"]
        assert params["prompt"] == ["consent"]
        assert params["state"] == [STATE_TOKEN]

    def test_missing_client_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        with pytest.raises(ConnectorError, match="GOOGLE_CLIENT_ID"):
            GmailConnector.build_auth_url(redirect_uri=REDIRECT_URI, state=STATE_TOKEN)


# ---------------------------------------------------------------------------
# exchange_code tests
# ---------------------------------------------------------------------------


class TestExchangeCode:
    async def test_successful_exchange(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_google_env(monkeypatch)

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "access_token": "ya29.gmail-access-token",
                    "refresh_token": "1//gmail-refresh-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": GMAIL_SCOPE,
                },
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await GmailConnector.exchange_code(
            code="auth-code-123",
            redirect_uri=REDIRECT_URI,
        )
        assert isinstance(tokens, OAuthTokens)
        assert tokens.access_token.get_secret_value() == "ya29.gmail-access-token"
        assert tokens.refresh_token is not None
        assert tokens.refresh_token.get_secret_value() == "1//gmail-refresh-token"
        assert tokens.token_type == "Bearer"

    async def test_http_error_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_google_env(monkeypatch)

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": "invalid_grant"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="Gmail OAuth"):
            await GmailConnector.exchange_code(
                code="bad-code",
                redirect_uri=REDIRECT_URI,
            )

    async def test_missing_credentials_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
        _clear_settings()

        with pytest.raises(ConnectorError, match="not configured"):
            await GmailConnector.exchange_code(
                code="auth-code",
                redirect_uri=REDIRECT_URI,
            )

    async def test_rate_limit_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_google_env(monkeypatch)

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                429,
                json={},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="Gmail OAuth"):
            await GmailConnector.exchange_code(
                code="auth-code",
                redirect_uri=REDIRECT_URI,
            )


# ---------------------------------------------------------------------------
# health_check tests
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_healthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                200,
                json={"emailAddress": "test@example.com", "historyId": "12345"},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        assert await connector.health_check() is True

    async def test_unhealthy_on_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                401,
                json={"error": {"code": 401, "message": "Invalid Credentials"}},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        assert await connector.health_check() is False

    async def test_no_token_returns_false(self) -> None:
        connector = GmailConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.GMAIL),
        )
        assert await connector.health_check() is False


# ---------------------------------------------------------------------------
# BaseConnector integration
# ---------------------------------------------------------------------------


class TestBaseConnectorIntegration:
    def test_source_type(self) -> None:
        connector = _make_connector()
        assert connector.source_type == SourceType.GMAIL

    async def test_fetch_since_requires_token(self) -> None:
        connector = GmailConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.GMAIL),
        )
        with pytest.raises(ConnectorError, match="access_token"):
            await connector.fetch_since(None)


# ---------------------------------------------------------------------------
# _raise_for_rate_limit helper
# ---------------------------------------------------------------------------


class TestRaiseForRateLimit:
    def test_429_raises(self) -> None:
        response = httpx.Response(
            429,
            headers={"Retry-After": "60"},
            request=httpx.Request("GET", "https://example.com"),
        )
        with pytest.raises(RateLimitError):
            _raise_for_rate_limit(response)

    def test_503_raises(self) -> None:
        response = httpx.Response(
            503,
            request=httpx.Request("GET", "https://example.com"),
        )
        with pytest.raises(RateLimitError):
            _raise_for_rate_limit(response)

    def test_200_passes(self) -> None:
        response = httpx.Response(
            200,
            request=httpx.Request("GET", "https://example.com"),
        )
        _raise_for_rate_limit(response)  # Should not raise


# ---------------------------------------------------------------------------
# Cursor encoding/decoding
# ---------------------------------------------------------------------------


class TestCursorEncoding:
    def test_roundtrip_with_page_token(self) -> None:
        cursor = _encode_cursor(history_id="12345", page_token="next-page")
        h_id, p_token = _decode_cursor(cursor)
        assert h_id == "12345"
        assert p_token == "next-page"

    def test_roundtrip_without_page_token(self) -> None:
        cursor = _encode_cursor(history_id="99999")
        h_id, p_token = _decode_cursor(cursor)
        assert h_id == "99999"
        assert p_token is None

    def test_invalid_cursor_returns_none(self) -> None:
        h_id, p_token = _decode_cursor("not-valid-base64")
        assert h_id is None
        assert p_token is None


# ---------------------------------------------------------------------------
# Header extraction
# ---------------------------------------------------------------------------


class TestExtractHeader:
    def test_finds_header_case_insensitive(self) -> None:
        headers = [
            {"name": "Subject", "value": "Hello World"},
            {"name": "From", "value": "alice@example.com"},
        ]
        assert _extract_header(headers, "subject") == "Hello World"
        assert _extract_header(headers, "FROM") == "alice@example.com"

    def test_missing_header_returns_empty(self) -> None:
        headers = [{"name": "Subject", "value": "Test"}]
        assert _extract_header(headers, "To") == ""

    def test_empty_headers(self) -> None:
        assert _extract_header([], "Subject") == ""


# ---------------------------------------------------------------------------
# Body decoding
# ---------------------------------------------------------------------------


class TestDecodeBodyPart:
    def test_decodes_base64url(self) -> None:
        text = "Hello, World!"
        encoded = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
        part = {"body": {"data": encoded}}
        assert _decode_body_part(part) == text

    def test_empty_body_returns_empty(self) -> None:
        assert _decode_body_part({}) == ""
        assert _decode_body_part({"body": {}}) == ""


# ---------------------------------------------------------------------------
# Text content extraction
# ---------------------------------------------------------------------------


class TestExtractTextContent:
    def test_simple_text_plain(self) -> None:
        text = "Plain text email body"
        encoded = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
        payload = {"mimeType": "text/plain", "body": {"data": encoded}}
        assert _extract_text_content(payload) == text

    def test_multipart_extracts_text(self) -> None:
        text = "Nested text"
        encoded = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded}},
                {"mimeType": "text/html", "body": {"data": "aHRtbA"}},
            ],
        }
        result = _extract_text_content(payload)
        assert "Nested text" in result

    def test_empty_payload(self) -> None:
        assert _extract_text_content({"mimeType": "text/plain", "body": {}}) == ""


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------


class TestNormalize:
    async def test_normalizes_email(self) -> None:
        connector = _make_connector()
        text = "Test email body"
        encoded = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
        raw: dict[str, object] = {
            "id": "msg-123",
            "threadId": "thread-456",
            "internalDate": "1704067200000",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 00:00:00 +0000"},
                ],
                "mimeType": "text/plain",
                "body": {"data": encoded},
            },
        }
        doc = await connector.normalize(raw)
        assert doc.source_type == SourceType.GMAIL
        assert doc.source_id == "msg-123"
        assert "Test Subject" in doc.content
        assert "Test email body" in doc.content
        assert doc.metadata["thread_id"] == "thread-456"
        assert doc.metadata["from"] == "sender@example.com"
        assert doc.metadata["to"] == "recipient@example.com"

    async def test_missing_id_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ConnectorError, match="missing"):
            await connector.normalize({})


# ---------------------------------------------------------------------------
# fetch_since (initial sync)
# ---------------------------------------------------------------------------


class TestFetchSince:
    async def test_initial_sync_fetches_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()
        text = "Email body"
        encoded = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")

        call_count = {"list": 0, "get": 0, "profile": 0}

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            if url.endswith("/messages") or "/messages?" in url:
                call_count["list"] += 1
                return httpx.Response(
                    200,
                    json={
                        "messages": [{"id": "msg-001", "threadId": "t-001"}],
                        "resultSizeEstimate": 1,
                    },
                    request=httpx.Request("GET", url),
                )
            if "/messages/msg-001" in url:
                call_count["get"] += 1
                return httpx.Response(
                    200,
                    json={
                        "id": "msg-001",
                        "threadId": "t-001",
                        "internalDate": "1704067200000",
                        "historyId": "12345",
                        "payload": {
                            "headers": [
                                {"name": "Subject", "value": "Welcome"},
                                {"name": "From", "value": "noreply@example.com"},
                                {"name": "To", "value": "user@example.com"},
                                {"name": "Date", "value": "Mon, 1 Jan 2024 00:00:00 +0000"},
                            ],
                            "mimeType": "text/plain",
                            "body": {"data": encoded},
                        },
                    },
                    request=httpx.Request("GET", url),
                )
            if "/profile" in url:
                call_count["profile"] += 1
                return httpx.Response(
                    200,
                    json={"emailAddress": "user@example.com", "historyId": "12345"},
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert len(result.documents) == 1
        assert result.documents[0].source_id == "msg-001"
        assert result.new_cursor is not None

    async def test_incremental_sync_uses_history(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()
        text = "Updated email"
        encoded = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")

        cursor = _encode_cursor(history_id="10000")

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            if "/history" in url:
                return httpx.Response(
                    200,
                    json={
                        "history": [
                            {
                                "id": "10001",
                                "messagesAdded": [
                                    {"message": {"id": "msg-new", "threadId": "t-new"}},
                                ],
                            },
                        ],
                        "historyId": "10002",
                    },
                    request=httpx.Request("GET", url),
                )
            if "/messages/msg-new" in url:
                return httpx.Response(
                    200,
                    json={
                        "id": "msg-new",
                        "threadId": "t-new",
                        "internalDate": "1704153600000",
                        "historyId": "10002",
                        "payload": {
                            "headers": [
                                {"name": "Subject", "value": "New Email"},
                                {"name": "From", "value": "person@example.com"},
                                {"name": "To", "value": "user@example.com"},
                                {"name": "Date", "value": "Tue, 2 Jan 2024 00:00:00 +0000"},
                            ],
                            "mimeType": "text/plain",
                            "body": {"data": encoded},
                        },
                    },
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(cursor)
        assert len(result.documents) == 1
        assert result.documents[0].source_id == "msg-new"


# ---------------------------------------------------------------------------
# setup_pubsub_watch
# ---------------------------------------------------------------------------


class TestSetupPubsubWatch:
    async def test_successful_watch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GMAIL_PUBSUB_TOPIC", "projects/test/topics/gmail")
        _clear_settings()

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                200,
                json={"historyId": "99999", "expiration": "1704153600000"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        result = await GmailConnector.setup_pubsub_watch("test-token")
        assert "historyId" in result

    async def test_missing_topic_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GMAIL_PUBSUB_TOPIC", "")
        _clear_settings()

        with pytest.raises(ConnectorError, match="gmail_pubsub_topic"):
            await GmailConnector.setup_pubsub_watch("test-token")
