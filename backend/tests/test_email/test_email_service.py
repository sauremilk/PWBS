"""Unit tests for the transactional email service (TASK-176).

Tests cover:
- Template rendering (all 3 templates)
- DSGVO compliance (Abmelde-Link, Impressum in every email)
- SMTP backend dispatch (mocked aiosmtplib)
- SendGrid backend dispatch (mocked httpx)
- Factory configuration (smtp vs sendgrid)
- Error handling (SMTP failures, SendGrid HTTP errors)
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.core.config import Settings
from pwbs.services.email import (
    EmailBackend,
    EmailMessage,
    EmailResult,
    EmailService,
    SendGridBackend,
    SmtpBackend,
    create_email_service,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "pwbs" / "templates" / "email"


def _make_settings(**overrides: Any) -> Settings:
    defaults = {
        "jwt_secret_key": "test-secret",
        "encryption_master_key": "test-master-key",
        "email_provider": "smtp",
        "smtp_host": "localhost",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "smtp_use_tls": False,
        "email_from_address": "noreply@test.pwbs.app",
        "email_from_name": "PWBS Test",
        "email_unsubscribe_url": "https://test.pwbs.app/unsubscribe",
        "email_impressum_url": "https://test.pwbs.app/impressum",
    }
    defaults.update(overrides)
    return Settings(**defaults)


class MockBackend:
    """In-memory email backend for testing."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> EmailResult:
        self.sent.append(message)
        return EmailResult(success=True, message_id="test-msg-id")


def _make_service(
    backend: EmailBackend | None = None,
    **settings_overrides: Any,
) -> tuple[EmailService, MockBackend]:
    mock_backend = MockBackend() if backend is None else None
    b = backend or mock_backend
    settings = _make_settings(**settings_overrides)
    svc = EmailService(b, settings, template_dir=_TEMPLATE_DIR)  # type: ignore[arg-type]
    return svc, mock_backend  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Template Rendering Tests
# ---------------------------------------------------------------------------


class TestWelcomeTemplate:
    @pytest.mark.asyncio
    async def test_renders_display_name(self) -> None:
        svc, backend = _make_service()
        await svc.send_welcome("user@example.com", "Max Mustermann")
        assert len(backend.sent) == 1
        assert "Max Mustermann" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_contains_dashboard_link(self) -> None:
        svc, backend = _make_service()
        await svc.send_welcome(
            "user@example.com", "Max", dashboard_url="https://app.pwbs.app/dash"
        )
        assert "https://app.pwbs.app/dash" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_subject(self) -> None:
        svc, backend = _make_service()
        await svc.send_welcome("user@example.com", "Max")
        assert backend.sent[0].subject == "Willkommen bei PWBS"


class TestPasswordResetTemplate:
    @pytest.mark.asyncio
    async def test_renders_reset_url(self) -> None:
        svc, backend = _make_service()
        await svc.send_password_reset(
            "user@example.com", "https://app.pwbs.app/reset?token=abc123"
        )
        assert "https://app.pwbs.app/reset?token=abc123" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_renders_expiry(self) -> None:
        svc, backend = _make_service()
        await svc.send_password_reset(
            "user@example.com", "https://reset", expires_in_minutes=60
        )
        assert "60 Minuten" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_subject(self) -> None:
        svc, backend = _make_service()
        await svc.send_password_reset("user@example.com", "https://reset")
        assert "Passwort" in backend.sent[0].subject


class TestBriefingNotificationTemplate:
    @pytest.mark.asyncio
    async def test_renders_briefing_type(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_notification(
            "user@example.com", "Morgenbriefing", "Ihr Tagesbriefing",
            "https://app.pwbs.app/briefing/1"
        )
        assert "Morgenbriefing" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_renders_briefing_link(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_notification(
            "user@example.com", "Morgenbriefing", "Titel",
            "https://app.pwbs.app/briefing/42"
        )
        assert "https://app.pwbs.app/briefing/42" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_optional_summary(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_notification(
            "user@example.com", "Typ", "Titel",
            "https://url", briefing_summary="Zusammenfassung hier"
        )
        assert "Zusammenfassung hier" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_subject_contains_type(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_notification(
            "user@example.com", "Weekly Review", "Titel", "https://url"
        )
        assert "Weekly Review" in backend.sent[0].subject


# ---------------------------------------------------------------------------
# DSGVO Compliance Tests
# ---------------------------------------------------------------------------


class TestDsgvoCompliance:
    @pytest.mark.asyncio
    async def test_welcome_contains_unsubscribe_link(self) -> None:
        svc, backend = _make_service()
        await svc.send_welcome("user@example.com", "Max")
        assert "https://test.pwbs.app/unsubscribe" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_welcome_contains_impressum_link(self) -> None:
        svc, backend = _make_service()
        await svc.send_welcome("user@example.com", "Max")
        assert "https://test.pwbs.app/impressum" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_password_reset_contains_footer(self) -> None:
        svc, backend = _make_service()
        await svc.send_password_reset("user@example.com", "https://reset")
        body = backend.sent[0].html_body
        assert "unsubscribe" in body.lower() or "Einstellungen" in body
        assert "Impressum" in body

    @pytest.mark.asyncio
    async def test_briefing_contains_footer(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_notification(
            "user@example.com", "Test", "Titel", "https://url"
        )
        body = backend.sent[0].html_body
        assert "Einstellungen" in body
        assert "Impressum" in body

    @pytest.mark.asyncio
    async def test_from_address_set(self) -> None:
        svc, backend = _make_service()
        await svc.send_welcome("user@example.com", "Max")
        assert backend.sent[0].from_address == "noreply@test.pwbs.app"
        assert backend.sent[0].from_name == "PWBS Test"

    @pytest.mark.asyncio
    async def test_unsubscribe_url_propagated(self) -> None:
        svc, backend = _make_service()
        await svc.send_welcome("user@example.com", "Max")
        assert backend.sent[0].unsubscribe_url == "https://test.pwbs.app/unsubscribe"


# ---------------------------------------------------------------------------
# SMTP Backend Tests
# ---------------------------------------------------------------------------


class TestSmtpBackend:
    @pytest.mark.asyncio
    async def test_send_success(self) -> None:
        with patch("pwbs.services.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = ("250 OK", "msg-id-123")
            backend = SmtpBackend("smtp.test.com", 587, "user", "pass", True)
            msg = EmailMessage(
                to="to@example.com",
                subject="Test",
                html_body="<p>Hello</p>",
                from_address="from@example.com",
                from_name="Test",
            )
            result = await backend.send(msg)

        assert result.success is True
        assert result.message_id == "msg-id-123"
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_failure(self) -> None:
        import aiosmtplib

        with patch("pwbs.services.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = aiosmtplib.SMTPException("Connection refused")
            backend = SmtpBackend("smtp.test.com", 587, "", "", False)
            msg = EmailMessage(
                to="to@example.com",
                subject="Test",
                html_body="<p>Hello</p>",
                from_address="from@example.com",
                from_name="Test",
            )
            result = await backend.send(msg)

        assert result.success is False
        assert "Connection refused" in (result.error or "")

    @pytest.mark.asyncio
    async def test_mime_structure(self) -> None:
        """Verify the MIME message is constructed correctly."""
        captured_args: list[Any] = []

        async def capture_send(mime, **kwargs: Any) -> tuple[str, str]:
            captured_args.append((mime, kwargs))
            return ("250 OK", "id-1")

        with patch("pwbs.services.email.aiosmtplib.send", side_effect=capture_send):
            backend = SmtpBackend("host", 25, "", "", False)
            msg = EmailMessage(
                to="user@test.com",
                subject="Subject",
                html_body="<h1>Body</h1>",
                from_address="noreply@test.com",
                from_name="Sender",
            )
            await backend.send(msg)

        mime, kwargs = captured_args[0]
        assert mime["To"] == "user@test.com"
        assert mime["Subject"] == "Subject"
        assert "Sender" in mime["From"]
        assert kwargs["hostname"] == "host"
        assert kwargs["port"] == 25

    @pytest.mark.asyncio
    async def test_list_unsubscribe_header(self) -> None:
        """Verify List-Unsubscribe header is set when unsubscribe_url is given."""
        captured_args: list[Any] = []

        async def capture_send(mime, **kwargs: Any) -> tuple[str, str]:
            captured_args.append(mime)
            return ("250 OK", "id-2")

        with patch("pwbs.services.email.aiosmtplib.send", side_effect=capture_send):
            backend = SmtpBackend("host", 25, "", "", False)
            msg = EmailMessage(
                to="user@test.com",
                subject="Test",
                html_body="<p>Hi</p>",
                from_address="noreply@test.com",
                from_name="Sender",
                unsubscribe_url="https://pwbs.app/unsubscribe",
            )
            await backend.send(msg)

        mime = captured_args[0]
        assert mime["List-Unsubscribe"] == "<https://pwbs.app/unsubscribe>"


# ---------------------------------------------------------------------------
# SendGrid Backend Tests
# ---------------------------------------------------------------------------


class TestSendGridBackend:
    @pytest.mark.asyncio
    async def test_send_success(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "sg-msg-id"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("pwbs.services.email.httpx.AsyncClient", return_value=mock_client):
            backend = SendGridBackend("sg-api-key-123")
            msg = EmailMessage(
                to="to@example.com",
                subject="Test",
                html_body="<p>Hello</p>",
                from_address="from@example.com",
                from_name="Test",
            )
            result = await backend.send(msg)

        assert result.success is True
        assert result.message_id == "sg-msg-id"

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("pwbs.services.email.httpx.AsyncClient", return_value=mock_client):
            backend = SendGridBackend("key")
            msg = EmailMessage(
                to="user@test.com",
                subject="Subj",
                html_body="<b>Hi</b>",
                from_address="noreply@test.com",
                from_name="PWBS",
            )
            await backend.send(msg)

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["personalizations"][0]["to"][0]["email"] == "user@test.com"
        assert payload["subject"] == "Subj"
        assert payload["from"]["email"] == "noreply@test.com"
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert "Bearer key" in headers["Authorization"]

    @pytest.mark.asyncio
    async def test_sendgrid_list_unsubscribe(self) -> None:
        """Verify SendGrid payload includes List-Unsubscribe header."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("pwbs.services.email.httpx.AsyncClient", return_value=mock_client):
            backend = SendGridBackend("key")
            msg = EmailMessage(
                to="user@test.com",
                subject="Test",
                html_body="<b>Hi</b>",
                from_address="noreply@test.com",
                from_name="PWBS",
                unsubscribe_url="https://pwbs.app/unsub",
            )
            await backend.send(msg)

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "headers" in payload
        assert "<https://pwbs.app/unsub>" in payload["headers"]["List-Unsubscribe"]

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=mock_response)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("pwbs.services.email.httpx.AsyncClient", return_value=mock_client):
            backend = SendGridBackend("bad-key")
            msg = EmailMessage(
                to="user@test.com",
                subject="Test",
                html_body="<p>Hi</p>",
                from_address="from@test.com",
                from_name="Test",
            )
            result = await backend.send(msg)

        assert result.success is False
        assert "403" in (result.error or "")


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------


class TestFactory:
    def test_creates_smtp_by_default(self) -> None:
        settings = _make_settings(email_provider="smtp")
        service = create_email_service(settings, template_dir=_TEMPLATE_DIR)
        assert isinstance(service._backend, SmtpBackend)

    def test_creates_sendgrid(self) -> None:
        settings = _make_settings(
            email_provider="sendgrid",
            sendgrid_api_key="sg-test-key",
        )
        service = create_email_service(settings, template_dir=_TEMPLATE_DIR)
        assert isinstance(service._backend, SendGridBackend)

    def test_sendgrid_without_key_raises(self) -> None:
        settings = _make_settings(
            email_provider="sendgrid",
            sendgrid_api_key="",
        )
        with pytest.raises(ValueError, match="SENDGRID_API_KEY"):
            create_email_service(settings, template_dir=_TEMPLATE_DIR)

    def test_custom_backend_override(self) -> None:
        mock = MockBackend()
        settings = _make_settings()
        service = create_email_service(settings, backend=mock, template_dir=_TEMPLATE_DIR)
        assert service._backend is mock