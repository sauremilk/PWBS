"""Tests for Slack connector (TASK-125, TASK-126)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from pwbs.connectors.base import ConnectorConfig, SyncResult
from pwbs.connectors.slack import (
    _BACKFILL_DAYS,
    SLACK_SCOPES,
    SlackConnector,
    _check_slack_error,
    _decode_cursor,
    _encode_cursor,
    _raise_for_rate_limit,
    validate_event_signature,
)
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import SourceType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

OWNER_ID = uuid4()
CONNECTION_ID = uuid4()


def _make_connector(
    *,
    access_token: str = "xoxb-test-token",
    channels: list[str] | None = None,
) -> SlackConnector:
    config = ConnectorConfig(
        source_type=SourceType.SLACK,
        extra={
            "access_token": access_token,
            "channels": channels if channels is not None else ["C123"],
        },
    )
    return SlackConnector(
        owner_id=OWNER_ID,
        connection_id=CONNECTION_ID,
        config=config,
    )


def _slack_ok_response(data: dict) -> httpx.Response:
    """Build a mock Slack API success response."""
    payload = {"ok": True, **data}
    req = httpx.Request("GET", "https://slack.com/api/test")
    return httpx.Response(200, json=payload, request=req)


def _slack_error_response(error: str = "channel_not_found") -> httpx.Response:
    req = httpx.Request("POST", "https://slack.com/api/test")
    return httpx.Response(200, json={"ok": False, "error": error}, request=req)


def _rate_limit_response() -> httpx.Response:
    req = httpx.Request("GET", "https://slack.com/api/test")
    return httpx.Response(429, headers={"Retry-After": "30"}, request=req)


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestRaiseForRateLimit:
    def test_429_raises(self) -> None:
        resp = _rate_limit_response()
        with pytest.raises(RateLimitError, match="rate-limited"):
            _raise_for_rate_limit(resp)

    def test_200_no_raise(self) -> None:
        req = httpx.Request("GET", "https://slack.com/api/test")
        resp = httpx.Response(200, json={"ok": True}, request=req)
        _raise_for_rate_limit(resp)  # should not raise


class TestCheckSlackError:
    def test_ok_response(self) -> None:
        _check_slack_error({"ok": True}, "test")

    def test_error_response(self) -> None:
        with pytest.raises(ConnectorError, match="channel_not_found"):
            _check_slack_error({"ok": False, "error": "channel_not_found"}, "test")


class TestCursorEncoding:
    def test_roundtrip(self) -> None:
        channels = {"C123": "1234.5678", "C456": "9999.0000"}
        cursor = _encode_cursor(channel_cursors=channels, oldest="100.0")
        decoded_channels, decoded_oldest = _decode_cursor(cursor)
        assert decoded_channels == channels
        assert decoded_oldest == "100.0"

    def test_empty_cursor(self) -> None:
        cursor = _encode_cursor(channel_cursors={})
        channels, oldest = _decode_cursor(cursor)
        assert channels == {}
        assert oldest is None

    def test_invalid_cursor(self) -> None:
        channels, oldest = _decode_cursor("not-base64-json")
        assert channels == {}
        assert oldest is None


class TestValidateEventSignature:
    def _sign(self, secret: str, timestamp: str, body: bytes) -> str:
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        return (
            "v0="
            + hmac.new(
                secret.encode("utf-8"),
                sig_basestring.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        )

    def test_valid_signature(self) -> None:
        secret = "test-signing-secret"
        ts = str(int(time.time()))
        body = b'{"type":"url_verification","challenge":"abc"}'
        sig = self._sign(secret, ts, body)

        assert (
            validate_event_signature(
                signing_secret=secret,
                timestamp=ts,
                body=body,
                signature=sig,
            )
            is True
        )

    def test_invalid_signature(self) -> None:
        assert (
            validate_event_signature(
                signing_secret="secret",
                timestamp=str(int(time.time())),
                body=b"hello",
                signature="v0=invalid",
            )
            is False
        )

    def test_stale_timestamp_rejected(self) -> None:
        secret = "test"
        old_ts = str(int(time.time()) - 600)  # 10 min ago
        body = b"test"
        sig = self._sign(secret, old_ts, body)

        assert (
            validate_event_signature(
                signing_secret=secret,
                timestamp=old_ts,
                body=body,
                signature=sig,
            )
            is False
        )

    def test_invalid_timestamp(self) -> None:
        assert (
            validate_event_signature(
                signing_secret="s",
                timestamp="not-a-number",
                body=b"test",
                signature="v0=x",
            )
            is False
        )


# ---------------------------------------------------------------------------
# OAuth2 flow tests
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    def test_generates_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SLACK_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("SLACK_CLIENT_SECRET", "test-secret")
        from pwbs.core.config import get_settings

        get_settings.cache_clear()

        url = SlackConnector.build_auth_url(
            redirect_uri="http://localhost/cb",
            state="test-state",
        )
        assert "slack.com/oauth/v2/authorize" in url
        assert "test-client-id" in url
        assert "channels%3Ahistory" in url or "channels:history" in url
        get_settings.cache_clear()

    def test_missing_client_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SLACK_CLIENT_ID", "")
        monkeypatch.setenv("SLACK_CLIENT_SECRET", "s")
        from pwbs.core.config import get_settings

        get_settings.cache_clear()

        with pytest.raises(ConnectorError, match="SLACK_CLIENT_ID"):
            SlackConnector.build_auth_url(redirect_uri="http://x", state="s")
        get_settings.cache_clear()


class TestExchangeCode:
    @pytest.mark.asyncio
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SLACK_CLIENT_ID", "cid")
        monkeypatch.setenv("SLACK_CLIENT_SECRET", "csecret")
        from pwbs.core.config import get_settings

        get_settings.cache_clear()

        async def mock_post(self_client, url, **kwargs):
            return _slack_ok_response(
                {
                    "access_token": "xoxb-new-token",
                    "token_type": "bot",
                    "scope": SLACK_SCOPES,
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await SlackConnector.exchange_code(
            code="auth-code",
            redirect_uri="http://localhost/cb",
        )
        assert tokens.access_token.get_secret_value() == "xoxb-new-token"
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_api_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SLACK_CLIENT_ID", "cid")
        monkeypatch.setenv("SLACK_CLIENT_SECRET", "csecret")
        from pwbs.core.config import get_settings

        get_settings.cache_clear()

        async def mock_post(self_client, url, **kwargs):
            return httpx.Response(
                200,
                json={"ok": False, "error": "invalid_code"},
                request=httpx.Request("POST", "https://test"),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="invalid_code"):
            await SlackConnector.exchange_code(
                code="bad-code",
                redirect_uri="http://localhost/cb",
            )
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Channel listing tests
# ---------------------------------------------------------------------------


class TestListChannels:
    @pytest.mark.asyncio
    async def test_lists_channels(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(self_client, url, **kwargs):
            return _slack_ok_response(
                {
                    "channels": [
                        {"id": "C1", "name": "general", "num_members": 42},
                        {"id": "C2", "name": "random", "num_members": 10},
                    ],
                    "response_metadata": {"next_cursor": ""},
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        channels = await SlackConnector.list_channels("xoxb-token")
        assert len(channels) == 2
        assert channels[0]["id"] == "C1"
        assert channels[0]["name"] == "general"


# ---------------------------------------------------------------------------
# fetch_since tests
# ---------------------------------------------------------------------------


class TestFetchSince:
    @pytest.mark.asyncio
    async def test_initial_sync(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector(channels=["C123"])

        async def mock_get(self_client, url, **kwargs):
            return _slack_ok_response(
                {
                    "messages": [
                        {"ts": "1000.001", "user": "U1", "text": "Hello world"},
                        {"ts": "1000.002", "user": "U2", "text": "Hi there"},
                    ],
                    "has_more": False,
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert isinstance(result, SyncResult)
        assert len(result.documents) == 2
        assert result.new_cursor is not None
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_incremental_sync(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector(channels=["C123"])

        initial_cursor = _encode_cursor(channel_cursors={"C123": "500.0"})

        async def mock_get(self_client, url, **kwargs):
            params = kwargs.get("params", {})
            oldest = params.get("oldest", "0")
            assert oldest == "500.0"
            return _slack_ok_response(
                {
                    "messages": [
                        {"ts": "600.001", "user": "U1", "text": "New message"},
                    ],
                    "has_more": False,
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(initial_cursor)
        assert len(result.documents) == 1

    @pytest.mark.asyncio
    async def test_no_channels_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector(channels=[])

        result = await connector.fetch_since(None)
        assert result.documents == []
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_skips_subtype_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector(channels=["C123"])

        async def mock_get(self_client, url, **kwargs):
            return _slack_ok_response(
                {
                    "messages": [
                        {"ts": "1.0", "user": "U1", "text": "normal"},
                        {"ts": "2.0", "subtype": "channel_join", "text": "joined"},
                        {
                            "ts": "3.0",
                            "subtype": "thread_broadcast",
                            "user": "U2",
                            "text": "broadcast ok",
                        },
                    ],
                    "has_more": False,
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert len(result.documents) == 2  # normal + thread_broadcast

    @pytest.mark.asyncio
    async def test_rate_limit_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector(channels=["C123"])

        async def mock_get(self_client, url, **kwargs):
            return _rate_limit_response()

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        with pytest.raises(RateLimitError):
            await connector.fetch_since(None)

    @pytest.mark.asyncio
    async def test_network_error_captured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector(channels=["C123"])

        async def mock_get(self_client, url, **kwargs):
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert len(result.errors) == 1
        assert "Network error" in result.errors[0].error


# ---------------------------------------------------------------------------
# normalize tests
# ---------------------------------------------------------------------------


class TestNormalize:
    @pytest.mark.asyncio
    async def test_basic_message(self) -> None:
        connector = _make_connector()
        doc = await connector.normalize(
            {
                "ts": "1234567890.123456",
                "_channel_id": "C123",
                "user": "U001",
                "text": "Hello PWBS!",
            }
        )
        assert doc.source_type == SourceType.SLACK
        assert doc.source_id == "C123:1234567890.123456"
        assert "Hello PWBS!" in doc.content
        assert doc.metadata["channel_id"] == "C123"
        assert doc.metadata["user_id"] == "U001"
        assert doc.user_id == OWNER_ID

    @pytest.mark.asyncio
    async def test_missing_ts_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ConnectorError, match="missing 'ts'"):
            await connector.normalize({"text": "no ts"})

    @pytest.mark.asyncio
    async def test_empty_text(self) -> None:
        connector = _make_connector()
        doc = await connector.normalize(
            {
                "ts": "1.0",
                "_channel_id": "C1",
                "user": "U1",
                "text": "",
            }
        )
        assert doc.content == "(leer)"

    @pytest.mark.asyncio
    async def test_thread_metadata(self) -> None:
        connector = _make_connector()
        doc = await connector.normalize(
            {
                "ts": "2.0",
                "_channel_id": "C1",
                "user": "U1",
                "text": "thread reply",
                "thread_ts": "1.0",
            }
        )
        assert doc.metadata["thread_ts"] == "1.0"


# ---------------------------------------------------------------------------
# health_check tests
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_post(self_client, url, **kwargs):
            return httpx.Response(
                200, json={"ok": True}, request=httpx.Request("POST", "https://test")
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        assert await connector.health_check() is True

    @pytest.mark.asyncio
    async def test_unhealthy_no_token(self) -> None:
        connector = _make_connector(access_token="")
        config = ConnectorConfig(source_type=SourceType.SLACK, extra={})
        connector._config = config  # no token
        # health_check reads from config.extra directly
        connector.config = config
        assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_unhealthy_api_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_post(self_client, url, **kwargs):
            return httpx.Response(
                200, json={"ok": False}, request=httpx.Request("POST", "https://test")
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_network_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_post(self_client, url, **kwargs):
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        assert await connector.health_check() is False


# ---------------------------------------------------------------------------
# SourceType enum test
# ---------------------------------------------------------------------------


class TestSourceTypeSlack:
    def test_slack_in_source_types(self) -> None:
        assert SourceType.SLACK.value == "slack"
        assert "slack" in [s.value for s in SourceType]


# ---------------------------------------------------------------------------
# TASK-126: Thread Resolution & Backfill tests
# ---------------------------------------------------------------------------


class TestBackfillBoundary:
    """Initial sync should limit to 90 days (TASK-126)."""

    @pytest.mark.asyncio
    async def test_initial_sync_uses_90_day_oldest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector(channels=["C123"])
        captured_params: list[dict] = []

        async def mock_get(
            self_client: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            params = kwargs.get("params", {})
            if "conversations.history" in url:
                captured_params.append(dict(params))
                return _slack_ok_response({"messages": [], "has_more": False})
            return _slack_ok_response({})

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        await connector.fetch_since(None)

        assert len(captured_params) == 1
        oldest = captured_params[0]["oldest"]
        # oldest should be a float timestamp > 0 (90 days ago)
        assert float(oldest) > 0
        import time

        now = time.time()
        expected_boundary = now - (_BACKFILL_DAYS * 86400)
        # Allow 60 seconds tolerance
        assert abs(float(oldest) - expected_boundary) < 60

    @pytest.mark.asyncio
    async def test_incremental_sync_uses_cursor_not_backfill(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector(channels=["C123"])
        captured_params: list[dict] = []
        initial_cursor = _encode_cursor(channel_cursors={"C123": "999.0"})

        async def mock_get(
            self_client: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            params = kwargs.get("params", {})
            if "conversations.history" in url:
                captured_params.append(dict(params))
                return _slack_ok_response({"messages": [], "has_more": False})
            return _slack_ok_response({})

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        await connector.fetch_since(initial_cursor)

        assert len(captured_params) == 1
        assert captured_params[0]["oldest"] == "999.0"


class TestFetchThreadReplies:
    """Tests for _fetch_thread_replies (TASK-126)."""

    @pytest.mark.asyncio
    async def test_fetches_replies_excluding_parent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(
            self_client: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return _slack_ok_response(
                {
                    "messages": [
                        {"ts": "100.0", "user": "U1", "text": "parent"},  # parent
                        {"ts": "100.1", "user": "U2", "text": "reply 1"},
                        {"ts": "100.2", "user": "U3", "text": "reply 2"},
                    ],
                    "response_metadata": {"next_cursor": ""},
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        replies = await connector._fetch_thread_replies(
            access_token="xoxb-test",
            channel_id="C123",
            thread_ts="100.0",
        )
        assert len(replies) == 2
        assert replies[0]["text"] == "reply 1"
        assert replies[1]["text"] == "reply 2"

    @pytest.mark.asyncio
    async def test_pagination(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()
        call_count = 0

        async def mock_get(
            self_client: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _slack_ok_response(
                    {
                        "messages": [
                            {"ts": "100.0", "user": "U1", "text": "parent"},
                            {"ts": "100.1", "user": "U2", "text": "reply 1"},
                        ],
                        "response_metadata": {"next_cursor": "page2"},
                    }
                )
            return _slack_ok_response(
                {
                    "messages": [
                        {"ts": "100.2", "user": "U3", "text": "reply 2"},
                    ],
                    "response_metadata": {"next_cursor": ""},
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        replies = await connector._fetch_thread_replies(
            access_token="xoxb-test",
            channel_id="C123",
            thread_ts="100.0",
        )
        assert len(replies) == 2
        assert call_count == 2


class TestNormalizeThread:
    """Tests for _normalize_thread (TASK-126)."""

    def test_merges_parent_and_replies(self) -> None:
        connector = _make_connector()
        parent = {
            "ts": "100.0",
            "user": "U1",
            "text": "Who handles this?",
            "_channel_id": "C123",
            "reply_count": 2,
        }
        replies = [
            {"ts": "100.1", "user": "U2", "text": "I'll take it"},
            {"ts": "100.2", "user": "U3", "text": "Thanks U2"},
        ]
        doc = connector._normalize_thread(
            parent_msg=parent,
            replies=replies,
            channel_id="C123",
        )
        assert doc.source_id == "C123:thread:100.0"
        assert doc.source_type == SourceType.SLACK
        assert "Who handles this?" in doc.content
        assert "I'll take it" in doc.content
        assert "Thanks U2" in doc.content
        assert doc.metadata["thread_ts"] == "100.0"
        assert doc.metadata["reply_count"] == 2
        assert doc.metadata["message_count"] == 3

    def test_participants_deduplicated(self) -> None:
        connector = _make_connector()
        parent = {"ts": "1.0", "user": "U1", "text": "a", "_channel_id": "C1"}
        replies = [
            {"ts": "2.0", "user": "U2", "text": "b"},
            {"ts": "3.0", "user": "U1", "text": "c"},  # duplicate
        ]
        doc = connector._normalize_thread(
            parent_msg=parent,
            replies=replies,
            channel_id="C1",
        )
        assert doc.participants == ["U1", "U2"]

    def test_messages_sorted_chronologically(self) -> None:
        connector = _make_connector()
        parent = {"ts": "200.0", "user": "U1", "text": "Second", "_channel_id": "C1"}
        replies = [
            {"ts": "100.0", "user": "U2", "text": "First"},
        ]
        doc = connector._normalize_thread(
            parent_msg=parent,
            replies=replies,
            channel_id="C1",
        )
        first_pos = doc.content.index("First")
        second_pos = doc.content.index("Second")
        assert first_pos < second_pos

    def test_reactions_collected(self) -> None:
        connector = _make_connector()
        parent = {
            "ts": "1.0",
            "user": "U1",
            "text": "Great idea!",
            "_channel_id": "C1",
            "reactions": [
                {"name": "thumbsup", "count": 3, "users": ["U2", "U3", "U4"]},
            ],
        }
        replies = [
            {
                "ts": "2.0",
                "user": "U2",
                "text": "Agreed",
                "reactions": [
                    {"name": "heart", "count": 1, "users": ["U1"]},
                ],
            },
        ]
        doc = connector._normalize_thread(
            parent_msg=parent,
            replies=replies,
            channel_id="C1",
        )
        assert len(doc.metadata["reactions"]) == 2
        assert doc.metadata["reactions"][0]["name"] == "thumbsup"
        assert doc.metadata["reactions"][1]["name"] == "heart"

    def test_empty_replies(self) -> None:
        connector = _make_connector()
        parent = {"ts": "1.0", "user": "U1", "text": "Solo thread", "_channel_id": "C1"}
        doc = connector._normalize_thread(
            parent_msg=parent,
            replies=[],
            channel_id="C1",
        )
        assert doc.metadata["reply_count"] == 0
        assert doc.metadata["message_count"] == 1
        assert "Solo thread" in doc.content


class TestThreadResolutionIntegration:
    """Integration tests for thread resolution during fetch_since (TASK-126)."""

    @pytest.mark.asyncio
    async def test_threaded_messages_merged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Messages with reply_count>0 get resolved into thread UDFs."""
        connector = _make_connector(channels=["C123"])

        async def mock_get(
            self_client: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "conversations.replies" in url:
                return _slack_ok_response(
                    {
                        "messages": [
                            {"ts": "100.0", "user": "U1", "text": "parent msg"},
                            {"ts": "100.1", "user": "U2", "text": "reply"},
                        ],
                        "response_metadata": {"next_cursor": ""},
                    }
                )
            # conversations.history
            return _slack_ok_response(
                {
                    "messages": [
                        {"ts": "100.0", "user": "U1", "text": "parent msg", "reply_count": 1},
                        {"ts": "200.0", "user": "U3", "text": "standalone"},
                    ],
                    "has_more": False,
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert len(result.documents) == 2

        # One thread doc, one standalone
        thread_docs = [d for d in result.documents if "thread:" in d.source_id]
        standalone_docs = [d for d in result.documents if "thread:" not in d.source_id]
        assert len(thread_docs) == 1
        assert len(standalone_docs) == 1

        thread_doc = thread_docs[0]
        assert thread_doc.source_id == "C123:thread:100.0"
        assert "parent msg" in thread_doc.content
        assert "reply" in thread_doc.content

    @pytest.mark.asyncio
    async def test_thread_resolution_error_captured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If conversations.replies fails, error is captured and standalone msgs still work."""
        connector = _make_connector(channels=["C123"])
        call_count = 0

        async def mock_get(
            self_client: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            nonlocal call_count
            if "conversations.replies" in url:
                return httpx.Response(
                    200,
                    json={"ok": False, "error": "thread_not_found"},
                    request=httpx.Request("GET", "https://test"),
                )
            return _slack_ok_response(
                {
                    "messages": [
                        {"ts": "100.0", "user": "U1", "text": "parent", "reply_count": 1},
                        {"ts": "200.0", "user": "U2", "text": "standalone"},
                    ],
                    "has_more": False,
                }
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        # Standalone message should still be there
        assert len(result.documents) == 1
        assert result.documents[0].source_id == "C123:200.0"
        # Thread error captured
        assert len(result.errors) == 1
        assert "C123:100.0" in result.errors[0].source_id


class TestNormalizeReactions:
    """Tests for reactions in normalize() (TASK-126)."""

    @pytest.mark.asyncio
    async def test_reactions_in_metadata(self) -> None:
        connector = _make_connector()
        doc = await connector.normalize(
            {
                "ts": "1.0",
                "_channel_id": "C1",
                "user": "U1",
                "text": "Check this out",
                "reactions": [
                    {"name": "fire", "count": 2, "users": ["U2", "U3"]},
                    {"name": "eyes", "count": 1, "users": ["U4"]},
                ],
            }
        )
        assert len(doc.metadata["reactions"]) == 2
        assert doc.metadata["reactions"][0]["name"] == "fire"
        assert doc.metadata["reactions"][1]["count"] == 1

    @pytest.mark.asyncio
    async def test_no_reactions_empty_list(self) -> None:
        connector = _make_connector()
        doc = await connector.normalize(
            {
                "ts": "1.0",
                "_channel_id": "C1",
                "user": "U1",
                "text": "boring msg",
            }
        )
        assert doc.metadata["reactions"] == []
