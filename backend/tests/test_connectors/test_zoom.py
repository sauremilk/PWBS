"""Tests for Zoom connector — OAuth2 + Webhook-Receiver + Normalizer (TASK-053..055)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid

import httpx
import pytest

from pwbs.connectors.base import ConnectorConfig
from pwbs.connectors.oauth import OAuthTokens
from pwbs.connectors.zoom import (
    _ZOOM_AUTH_URL,
    _ZOOM_TOKEN_URL,
    ZOOM_SCOPES,
    ZoomConnector,
    ZoomRecordingFile,
    ZoomRecordingObject,
    ZoomWebhookEvent,
    ZoomWebhookPayload,
    _decode_recordings_cursor,
    _encode_recordings_cursor,
    _extract_participants_from_files,
    _parse_vtt,
    _raise_for_rate_limit,
    compute_url_validation_response,
    validate_zoom_webhook_signature,
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

    def test_raises_without_client_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
    async def test_successful_exchange(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_zoom_env(monkeypatch)

        expected_creds = base64.b64encode(
            b"test-zoom-id:test-zoom-secret",
        ).decode()

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
    async def test_exchange_without_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ZOOM_CLIENT_ID", "")
        monkeypatch.setenv("ZOOM_CLIENT_SECRET", "")
        _clear_settings()
        with pytest.raises(ConnectorError, match="zoom_client_id"):
            await ZoomConnector.exchange_code(
                code="some-code",
                redirect_uri="http://localhost:3000/callback",
            )

    @pytest.mark.asyncio
    async def test_exchange_invalid_code(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_zoom_env(monkeypatch)

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
    async def test_exchange_network_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_zoom_env(monkeypatch)

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="network error"):
            await ZoomConnector.exchange_code(
                code="some-code",
                redirect_uri="http://localhost:3000/callback",
            )

    @pytest.mark.asyncio
    async def test_exchange_rate_limited(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_zoom_env(monkeypatch)

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
    async def test_exchange_no_refresh_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Zoom should normally return a refresh token, but handle its absence."""
        _set_zoom_env(monkeypatch)

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
    async def test_exchange_uses_form_encoded_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Zoom token endpoint expects application/x-www-form-urlencoded."""
        _set_zoom_env(monkeypatch)

        captured_kwargs: dict[str, object] = {}

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            assert "/users/me" in url
            return httpx.Response(status_code=200, json={"id": "user-123"})

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        assert await connector.health_check() is True

    @pytest.mark.asyncio
    async def test_unhealthy_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_rate_limited_health_check(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Rate-limited response during health check — should return False."""
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
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
    async def test_fetch_since_returns_sync_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """fetch_since is now implemented — returns SyncResult (errors until TASK-055)."""
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={"meetings": [], "next_page_token": ""},
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.has_more is False

    def test_normalize_returns_unified_document(self) -> None:
        connector = _make_connector()
        raw = {
            "uuid": "m-uuid",
            "topic": "Standup",
            "start_time": "2026-03-14T10:00:00Z",
            "duration": 15,
            "transcript": "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world",
            "recording_files": [],
        }
        doc = connector.normalize(raw)
        assert doc.source_id == "m-uuid"
        assert doc.title == "Standup"
        assert "Hello world" in doc.content

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

    def test_processed_recording_ids_initialized(self) -> None:
        connector = _make_connector()
        assert connector._processed_recording_ids == set()


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


# ===========================================================================
# TASK-054: Webhook signature, models, fetch_since, process_recording
# ===========================================================================


# ---------------------------------------------------------------------------
# Webhook signature validation
# ---------------------------------------------------------------------------


class TestValidateZoomWebhookSignature:
    def test_valid_signature(self) -> None:
        secret = "test-webhook-secret"
        body = b'{"event":"recording.completed"}'
        timestamp = "1704067200"
        message = f"v0:{timestamp}:{body.decode()}"
        expected_sig = (
            "v0="
            + hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        assert (
            validate_zoom_webhook_signature(
                request_body=body,
                timestamp=timestamp,
                signature=expected_sig,
                secret=secret,
            )
            is True
        )

    def test_invalid_signature(self) -> None:
        assert (
            validate_zoom_webhook_signature(
                request_body=b'{"event":"test"}',
                timestamp="123",
                signature="v0=invalid",
                secret="secret",
            )
            is False
        )

    def test_tampered_body(self) -> None:
        secret = "secret"
        body = b'{"event":"original"}'
        timestamp = "123"
        message = f"v0:{timestamp}:{body.decode()}"
        valid_sig = (
            "v0="
            + hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        # Tamper with body
        assert (
            validate_zoom_webhook_signature(
                request_body=b'{"event":"tampered"}',
                timestamp=timestamp,
                signature=valid_sig,
                secret=secret,
            )
            is False
        )


class TestComputeUrlValidationResponse:
    def test_response_format(self) -> None:
        result = compute_url_validation_response("abc123", "my-secret")
        assert result["plainToken"] == "abc123"
        assert (
            result["encryptedToken"]
            == hmac.new(
                b"my-secret",
                b"abc123",
                hashlib.sha256,
            ).hexdigest()
        )


# ---------------------------------------------------------------------------
# Cursor encoding/decoding
# ---------------------------------------------------------------------------


class TestRecordingsCursor:
    def test_encode_watermark_only(self) -> None:
        cursor = _encode_recordings_cursor(watermark="2026-01-01")
        assert cursor == "2026-01-01"

    def test_encode_with_page_token(self) -> None:
        cursor = _encode_recordings_cursor(
            watermark="2026-01-01",
            next_page_token="page-2",
        )
        data = json.loads(cursor)
        assert data["watermark"] == "2026-01-01"
        assert data["next_page_token"] == "page-2"

    def test_decode_empty(self) -> None:
        assert _decode_recordings_cursor("") == (None, None)

    def test_decode_watermark_only(self) -> None:
        assert _decode_recordings_cursor("2026-01-01") == ("2026-01-01", None)

    def test_decode_with_page_token(self) -> None:
        cursor = json.dumps({"watermark": "2026-01-01", "next_page_token": "p2"})
        assert _decode_recordings_cursor(cursor) == ("2026-01-01", "p2")

    def test_decode_invalid_json(self) -> None:
        assert _decode_recordings_cursor("{bad") == ("{bad", None)


# ---------------------------------------------------------------------------
# Webhook Pydantic models
# ---------------------------------------------------------------------------


class TestWebhookModels:
    def test_recording_file_model(self) -> None:
        rf = ZoomRecordingFile(
            id="file-1",
            recording_type="audio_transcript",
            file_type="TRANSCRIPT",
            download_url="https://zoom.us/rec/download/abc",
            status="completed",
        )
        assert rf.file_type == "TRANSCRIPT"
        assert rf.download_url == "https://zoom.us/rec/download/abc"

    def test_recording_object_model(self) -> None:
        obj = ZoomRecordingObject(
            uuid="meeting-uuid-123",
            id=12345,
            topic="Weekly Standup",
            start_time="2026-01-15T10:00:00Z",
            duration=30,
            recording_files=[
                ZoomRecordingFile(
                    id="f1",
                    recording_type="audio_transcript",
                    file_type="TRANSCRIPT",
                ),
            ],
        )
        assert obj.uuid == "meeting-uuid-123"
        assert len(obj.recording_files) == 1

    def test_webhook_event_model(self) -> None:
        event = ZoomWebhookEvent(
            event="recording.completed",
            payload=ZoomWebhookPayload(
                account_id="acc-123",
                object=ZoomRecordingObject(
                    uuid="m-uuid",
                    id=1,
                    topic="Test",
                ),
            ),
            event_ts=1704067200000,
        )
        assert event.event == "recording.completed"
        assert event.payload is not None
        assert event.payload.object.uuid == "m-uuid"

    def test_webhook_event_from_json(self) -> None:
        raw = {
            "event": "recording.completed",
            "payload": {
                "account_id": "acc-1",
                "object": {
                    "uuid": "uuid-1",
                    "id": 100,
                    "topic": "Demo",
                    "start_time": "2026-03-14T09:00:00Z",
                    "duration": 45,
                    "recording_files": [
                        {
                            "id": "rf-1",
                            "recording_type": "audio_transcript",
                            "file_type": "TRANSCRIPT",
                            "download_url": "https://zoom.us/download/rf-1",
                            "status": "completed",
                            "file_size": 5000,
                        },
                    ],
                },
            },
            "event_ts": 1710406800000,
        }
        event = ZoomWebhookEvent(**raw)
        assert event.payload is not None
        assert event.payload.object.recording_files[0].file_type == "TRANSCRIPT"


# ---------------------------------------------------------------------------
# fetch_transcript
# ---------------------------------------------------------------------------


def _make_recordings_response(
    meetings: list[dict[str, object]] | None = None,
    next_page_token: str = "",
) -> dict[str, object]:
    """Build a mock Zoom recordings API response."""
    return {
        "meetings": meetings or [],
        "next_page_token": next_page_token,
        "page_count": 1,
        "page_size": 30,
        "total_records": len(meetings or []),
    }


def _make_meeting(
    meeting_uuid: str = "meeting-uuid-1",
    meeting_id: int = 12345,
    topic: str = "Test Meeting",
    has_transcript: bool = True,
) -> dict[str, object]:
    """Build a minimal Zoom meeting dict with recording files."""
    files: list[dict[str, str]] = []
    if has_transcript:
        files.append(
            {
                "id": f"file-{meeting_uuid}",
                "recording_type": "audio_transcript",
                "file_type": "TRANSCRIPT",
                "download_url": f"https://zoom.us/rec/download/{meeting_uuid}",
                "status": "completed",
            }
        )
    return {
        "uuid": meeting_uuid,
        "id": meeting_id,
        "topic": topic,
        "start_time": "2026-03-14T10:00:00Z",
        "duration": 30,
        "recording_files": files,
    }


class TestFetchTranscript:
    @pytest.mark.asyncio
    async def test_successful_download(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            assert "download" in url
            return httpx.Response(
                status_code=200,
                text="WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world",
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        content = await connector.fetch_transcript(
            "https://zoom.us/rec/download/abc",
        )
        assert "WEBVTT" in content
        assert "Hello world" in content

    @pytest.mark.asyncio
    async def test_download_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(status_code=401, text="Unauthorized")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        with pytest.raises(ConnectorError, match="download failed"):
            await connector.fetch_transcript("https://zoom.us/rec/download/abc")

    @pytest.mark.asyncio
    async def test_download_network_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("Timeout")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        with pytest.raises(ConnectorError, match="network error"):
            await connector.fetch_transcript("https://zoom.us/rec/download/abc")

    @pytest.mark.asyncio
    async def test_download_rate_limited(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                status_code=429,
                headers={"Retry-After": "10"},
                text="Rate limited",
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        with pytest.raises(RateLimitError):
            await connector.fetch_transcript("https://zoom.us/rec/download/abc")


# ---------------------------------------------------------------------------
# fetch_since (polling)
# ---------------------------------------------------------------------------


class TestFetchSince:
    @pytest.mark.asyncio
    async def test_initial_sync_no_recordings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json=_make_recordings_response(),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_fetch_with_transcript_produces_documents(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After TASK-055, recordings with transcripts produce documents."""
        connector = _make_connector()
        call_count = 0

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if "recordings" in url:
                return httpx.Response(
                    status_code=200,
                    json=_make_recordings_response(
                        meetings=[_make_meeting()],
                    ),
                )
            # Transcript download
            return httpx.Response(
                status_code=200,
                text="WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nTest",
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert result.success_count == 1
        assert result.error_count == 0
        assert result.documents[0].source_id == "meeting-uuid-1"
        assert result.documents[0].title == "Test Meeting"
        assert call_count == 2  # 1 recordings + 1 transcript

    @pytest.mark.asyncio
    async def test_incremental_sync_with_cursor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()
        captured_params: dict[str, object] = {}

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            if "recordings" in url:
                captured_params.update(kwargs.get("params", {}))  # type: ignore[union-attr]
                return httpx.Response(
                    status_code=200,
                    json=_make_recordings_response(),
                )
            return httpx.Response(status_code=200, text="transcript")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        await connector.fetch_since("2026-03-01")
        assert captured_params.get("from") == "2026-03-01"

    @pytest.mark.asyncio
    async def test_pagination(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()
        page = 0

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            nonlocal page
            if "recordings" in url:
                page += 1
                if page == 1:
                    return httpx.Response(
                        status_code=200,
                        json=_make_recordings_response(
                            meetings=[_make_meeting(meeting_uuid="m1")],
                            next_page_token="page-2",
                        ),
                    )
                return httpx.Response(
                    status_code=200,
                    json=_make_recordings_response(
                        meetings=[_make_meeting(meeting_uuid="m2")],
                    ),
                )
            return httpx.Response(status_code=200, text="transcript")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        # First page
        result1 = await connector.fetch_since(None)
        assert result1.has_more is True

        # Second page
        result2 = await connector.fetch_since(result1.new_cursor)
        assert result2.has_more is False

    @pytest.mark.asyncio
    async def test_skips_meetings_without_transcript(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json=_make_recordings_response(
                    meetings=[_make_meeting(has_transcript=False)],
                ),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_idempotency_skips_duplicate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()
        connector._processed_recording_ids.add("meeting-uuid-1")

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json=_make_recordings_response(
                    meetings=[_make_meeting()],
                ),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_transcript_download_error_captured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            if "recordings" in url:
                return httpx.Response(
                    status_code=200,
                    json=_make_recordings_response(
                        meetings=[_make_meeting()],
                    ),
                )
            # Transcript download fails
            return httpx.Response(status_code=500, text="Server Error")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert result.error_count == 1
        assert "download failed" in result.errors[0].error.lower()

    @pytest.mark.asyncio
    async def test_recordings_api_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(status_code=500, text="Internal Server Error")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        with pytest.raises(ConnectorError, match="Zoom recordings API error"):
            await connector.fetch_since(None)

    @pytest.mark.asyncio
    async def test_recordings_api_rate_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                status_code=429,
                headers={"Retry-After": "30"},
                text="Rate limited",
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        with pytest.raises(RateLimitError):
            await connector.fetch_since(None)

    @pytest.mark.asyncio
    async def test_missing_access_token(self) -> None:
        connector = ZoomConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(
                source_type=SourceType.ZOOM,
                extra={},
            ),
        )
        with pytest.raises(ConnectorError, match="Missing access_token"):
            await connector.fetch_since(None)


# ---------------------------------------------------------------------------
# process_recording_completed (webhook handler)
# ---------------------------------------------------------------------------


def _make_webhook_event(
    meeting_uuid: str = "webhook-meeting-1",
    topic: str = "Webhook Meeting",
    has_transcript: bool = True,
) -> ZoomWebhookEvent:
    """Build a recording.completed webhook event."""
    files: list[ZoomRecordingFile] = []
    if has_transcript:
        files.append(
            ZoomRecordingFile(
                id="wh-file-1",
                recording_type="audio_transcript",
                file_type="TRANSCRIPT",
                download_url=f"https://zoom.us/rec/download/{meeting_uuid}",
            )
        )
    return ZoomWebhookEvent(
        event="recording.completed",
        payload=ZoomWebhookPayload(
            account_id="acc-1",
            object=ZoomRecordingObject(
                uuid=meeting_uuid,
                id=99999,
                topic=topic,
                start_time="2026-03-14T10:00:00Z",
                duration=45,
                recording_files=files,
            ),
        ),
        event_ts=1710406800000,
    )


class TestProcessRecordingCompleted:
    @pytest.mark.asyncio
    async def test_processes_event_with_transcript(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                text="WEBVTT\n\nTranscript content here",
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        event = _make_webhook_event()
        result = await connector.process_recording_completed(event)

        assert result.success_count == 1
        assert result.error_count == 0
        assert result.documents[0].source_id == "webhook-meeting-1"
        assert result.documents[0].title == "Webhook Meeting"

    @pytest.mark.asyncio
    async def test_skips_event_without_transcript(self) -> None:
        connector = _make_connector()
        event = _make_webhook_event(has_transcript=False)

        result = await connector.process_recording_completed(event)
        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_idempotency_skips_duplicate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()
        connector._processed_recording_ids.add("webhook-meeting-1")

        result = await connector.process_recording_completed(
            _make_webhook_event(),
        )
        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_transcript_download_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connector = _make_connector()

        async def mock_get(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(status_code=500, text="Error")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        event = _make_webhook_event()
        result = await connector.process_recording_completed(event)
        assert result.error_count == 1
        assert "download failed" in result.errors[0].error.lower()

    @pytest.mark.asyncio
    async def test_none_payload_returns_empty(self) -> None:
        connector = _make_connector()
        event = ZoomWebhookEvent(event="recording.completed", payload=None)
        result = await connector.process_recording_completed(event)
        assert result.success_count == 0
        assert result.error_count == 0


# ---------------------------------------------------------------------------
# VTT parsing (TASK-055)
# ---------------------------------------------------------------------------


class TestParseVtt:
    def test_basic_vtt_with_speakers(self) -> None:
        vtt = (
            "WEBVTT\n\n"
            "1\n"
            "00:00:01.000 --> 00:00:05.000\n"
            "Alice: Hello everyone.\n\n"
            "2\n"
            "00:00:05.000 --> 00:00:10.000\n"
            "Bob: Thanks, let's start.\n"
        )
        text, speakers = _parse_vtt(vtt)
        assert "Alice: Hello everyone." in text
        assert "Bob: Thanks, let's start." in text
        assert speakers == ["Alice", "Bob"]

    def test_vtt_without_speakers(self) -> None:
        vtt = (
            "WEBVTT\n\n"
            "00:00:01.000 --> 00:00:05.000\n"
            "Just some text.\n\n"
            "00:00:05.000 --> 00:00:10.000\n"
            "More text here.\n"
        )
        text, speakers = _parse_vtt(vtt)
        assert "Just some text." in text
        assert "More text here." in text
        assert speakers == []

    def test_empty_content(self) -> None:
        text, speakers = _parse_vtt("")
        assert text == ""
        assert speakers == []

    def test_plain_text_fallback(self) -> None:
        """Non-VTT content is returned as-is."""
        text, speakers = _parse_vtt("Just plain text without VTT headers")
        assert "Just plain text" in text
        assert speakers == []

    def test_multiline_cue(self) -> None:
        vtt = (
            "WEBVTT\n\n"
            "00:00:01.000 --> 00:00:05.000\n"
            "Line one.\n"
            "Line two.\n"
        )
        text, speakers = _parse_vtt(vtt)
        assert "Line one." in text
        assert "Line two." in text


class TestExtractParticipantsFromFiles:
    def test_extracts_emails(self) -> None:
        files = [
            {"user_email": "alice@example.com", "user_name": "Alice"},
            {"user_email": "bob@example.com", "user_name": "Bob"},
        ]
        result = _extract_participants_from_files(files)
        assert "alice@example.com" in result
        assert "bob@example.com" in result

    def test_falls_back_to_name(self) -> None:
        files = [{"user_name": "Charlie"}]
        result = _extract_participants_from_files(files)
        assert "Charlie" in result

    def test_deduplicates(self) -> None:
        files = [
            {"user_email": "alice@example.com"},
            {"user_email": "alice@example.com"},
        ]
        result = _extract_participants_from_files(files)
        assert result.count("alice@example.com") == 1

    def test_empty_list(self) -> None:
        assert _extract_participants_from_files([]) == []

    def test_skips_empty_entries(self) -> None:
        files = [{"user_email": "", "user_name": ""}]
        assert _extract_participants_from_files(files) == []


# ---------------------------------------------------------------------------
# normalize() (TASK-055)
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_basic_normalize(self) -> None:
        connector = _make_connector()
        raw = {
            "uuid": "m-uuid-1",
            "topic": "Sprint Planning",
            "start_time": "2026-03-14T10:00:00Z",
            "duration": 60,
            "transcript": (
                "WEBVTT\n\n"
                "00:00:01.000 --> 00:00:05.000\n"
                "Alice: Let's plan the sprint.\n\n"
                "00:00:05.000 --> 00:00:08.000\n"
                "Bob: Sounds good.\n"
            ),
            "recording_files": [],
        }
        doc = connector.normalize(raw)
        assert doc.source_id == "m-uuid-1"
        assert doc.title == "Sprint Planning"
        assert "Let's plan the sprint." in doc.content

    def test_metadata_fields(self) -> None:
        connector = _make_connector()
        raw = {
            "uuid": "m-uuid-2",
            "topic": "Retro",
            "start_time": "2026-03-14T10:00:00Z",
            "duration": 45,
            "transcript": "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello",
            "recording_files": [],
        }
        doc = connector.normalize(raw)
        assert doc.metadata["duration_minutes"] == 45
        assert doc.metadata["start_time"] == "2026-03-14T10:00:00Z"
        assert doc.metadata["end_time"] != ""
        assert doc.metadata["participant_count"] == 0

    def test_speakers_in_metadata(self) -> None:
        connector = _make_connector()
        raw = {
            "uuid": "m-uuid-3",
            "topic": "1:1",
            "start_time": "2026-03-14T10:00:00Z",
            "duration": 30,
            "transcript": (
                "WEBVTT\n\n"
                "00:00:01.000 --> 00:00:03.000\n"
                "Alice: Hi\n\n"
                "00:00:03.000 --> 00:00:05.000\n"
                "Bob: Hey\n"
            ),
            "recording_files": [],
        }
        doc = connector.normalize(raw)
        assert "speakers" in doc.metadata
        assert set(doc.metadata["speakers"]) == {"Alice", "Bob"}

    def test_participants_from_files_and_vtt(self) -> None:
        connector = _make_connector()
        raw = {
            "uuid": "m-uuid-4",
            "topic": "Team Call",
            "start_time": "2026-03-14T10:00:00Z",
            "duration": 20,
            "transcript": (
                "WEBVTT\n\n"
                "00:00:01.000 --> 00:00:03.000\n"
                "Charlie: Hello\n"
            ),
            "recording_files": [
                {"user_email": "alice@example.com"},
            ],
        }
        doc = connector.normalize(raw)
        assert "alice@example.com" in doc.participants
        assert "Charlie" in doc.participants

    def test_missing_uuid_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ConnectorError, match="missing 'uuid'"):
            connector.normalize({"topic": "No UUID"})

    def test_empty_transcript(self) -> None:
        connector = _make_connector()
        raw = {
            "uuid": "m-uuid-5",
            "topic": "Silent Meeting",
            "start_time": "2026-03-14T10:00:00Z",
            "duration": 5,
            "transcript": "",
            "recording_files": [],
        }
        doc = connector.normalize(raw)
        assert doc.content == ""
        assert doc.source_id == "m-uuid-5"

    def test_default_title_when_missing(self) -> None:
        connector = _make_connector()
        raw = {
            "uuid": "m-uuid-6",
            "topic": "",
            "start_time": "2026-03-14T10:00:00Z",
            "duration": 10,
            "transcript": "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHi",
            "recording_files": [],
        }
        doc = connector.normalize(raw)
        assert doc.title == "(Kein Titel)"

    def test_created_at_parsed(self) -> None:
        connector = _make_connector()
        raw = {
            "uuid": "m-uuid-7",
            "topic": "Timed",
            "start_time": "2026-03-14T10:00:00Z",
            "duration": 15,
            "transcript": "Hello",
            "recording_files": [],
        }
        doc = connector.normalize(raw)
        assert doc.created_at.year == 2026
        assert doc.created_at.month == 3
        assert doc.created_at.day == 14
