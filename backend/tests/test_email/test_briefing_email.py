"""Tests for briefing email delivery (TASK-177).

Tests cover:
- EmailService.send_briefing_email template rendering
- send_briefing_emails Celery task (mocked DB + email)
- Source references in briefing email template
- User opt-in filtering (email_briefing_enabled)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
# Briefing email template tests
# ---------------------------------------------------------------------------


class TestBriefingEmailTemplate:
    @pytest.mark.asyncio
    async def test_renders_briefing_content(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_email(
            to="user@example.com",
            briefing_type="Morning",
            briefing_title="Ihr Morgenbriefing",
            briefing_content="Heute stehen 3 Meetings an.",
            briefing_url="/briefings/123",
        )
        assert len(backend.sent) == 1
        body = backend.sent[0].html_body
        assert "Heute stehen 3 Meetings an." in body

    @pytest.mark.asyncio
    async def test_renders_briefing_title(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_email(
            to="user@example.com",
            briefing_type="Weekly",
            briefing_title="Wochenbriefing KW25",
            briefing_content="Inhalt",
            briefing_url="/briefings/456",
        )
        assert "Wochenbriefing KW25" in backend.sent[0].html_body

    @pytest.mark.asyncio
    async def test_renders_source_references(self) -> None:
        svc, backend = _make_service()
        sources = [
            {"title": "Meeting mit Team A", "url": "https://notes.app/1", "source_type": "meeting"},
            {"title": "Notion Seite", "url": "https://notion.so/page", "source_type": "notion"},
        ]
        await svc.send_briefing_email(
            to="user@example.com",
            briefing_type="Morning",
            briefing_title="Briefing",
            briefing_content="Content",
            briefing_url="/briefings/789",
            sources=sources,
        )
        body = backend.sent[0].html_body
        assert "Meeting mit Team A" in body
        assert "https://notes.app/1" in body
        assert "Notion Seite" in body

    @pytest.mark.asyncio
    async def test_empty_sources(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_email(
            to="user@example.com",
            briefing_type="Morning",
            briefing_title="Briefing",
            briefing_content="Content",
            briefing_url="/briefings/789",
            sources=[],
        )
        assert len(backend.sent) == 1
        # Should render without error even with empty sources

    @pytest.mark.asyncio
    async def test_subject_contains_title(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_email(
            to="user@example.com",
            briefing_type="Morning",
            briefing_title="Morgenbriefing 2025-01-15",
            briefing_content="Content",
            briefing_url="/b/1",
        )
        assert "Morgenbriefing 2025-01-15" in backend.sent[0].subject

    @pytest.mark.asyncio
    async def test_dsgvo_footer_present(self) -> None:
        svc, backend = _make_service()
        await svc.send_briefing_email(
            to="user@example.com",
            briefing_type="Morning",
            briefing_title="Briefing",
            briefing_content="Content",
            briefing_url="/b/1",
        )
        body = backend.sent[0].html_body
        assert "Impressum" in body
        assert "unsubscribe" in body.lower() or "Einstellungen" in body


# ---------------------------------------------------------------------------
# User settings schema tests for new fields
# ---------------------------------------------------------------------------


class TestUserSettingsEmailFields:
    def test_settings_response_with_email_fields(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsResponse

        resp = UserSettingsResponse(
            user_id=uuid.uuid4(),
            email="test@example.com",
            display_name="Test",
            timezone="Europe/Berlin",
            language="de",
            briefing_auto_generate=True,
            reminder_frequency="daily",
            email_briefing_enabled=True,
            briefing_email_time="07:00",
            vertical_profile="general",
        )
        assert resp.email_briefing_enabled is True
        assert resp.briefing_email_time == "07:00"

    def test_settings_update_email_fields(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate

        update = UserSettingsUpdate(
            email_briefing_enabled=True,
            briefing_email_time="08:30",
        )
        assert update.email_briefing_enabled is True
        assert update.briefing_email_time == "08:30"

    def test_settings_update_email_fields_optional(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate

        update = UserSettingsUpdate(timezone="UTC")
        assert update.email_briefing_enabled is None
        assert update.briefing_email_time is None


# ---------------------------------------------------------------------------
# Celery task tests (mocked DB + email)
# ---------------------------------------------------------------------------


class TestSendBriefingEmailsTask:
    @pytest.mark.asyncio
    async def test_sends_to_opted_in_users(self) -> None:
        """Users with email_briefing_enabled=True receive briefing emails."""
        from pwbs.queue.tasks.briefing import _send_briefing_emails_async

        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "alice@example.com"
        user.email_briefing_enabled = True

        briefing = MagicMock()
        briefing.id = uuid.uuid4()
        briefing.title = "Morning Briefing"
        briefing.content = "Today you have 2 meetings."
        briefing.generated_at = datetime(2025, 1, 15, 6, 30, tzinfo=timezone.utc)
        briefing.source_chunks = []
        briefing.email_sent_at = None

        # Mock DB session
        mock_session = AsyncMock()

        # First call: select users, second: select briefing, third: UPDATE email_sent_at
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [user]

        briefing_result = MagicMock()
        briefing_result.scalar_one_or_none.return_value = briefing

        update_result = MagicMock()

        mock_session.execute = AsyncMock(side_effect=[users_result, briefing_result, update_result])
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        mock_email_result = EmailResult(success=True, message_id="msg-1")
        mock_email_service = MagicMock()
        mock_email_service.send_briefing_email = AsyncMock(return_value=mock_email_result)

        with (
            patch(
                "pwbs.db.postgres.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "pwbs.services.email.create_email_service",
                return_value=mock_email_service,
            ),
        ):
            result = await _send_briefing_emails_async("morning")

        assert result["emails_sent"] == 1
        assert result["emails_failed"] == 0
        mock_email_service.send_briefing_email.assert_called_once()
        call_kwargs = mock_email_service.send_briefing_email.call_args.kwargs
        assert call_kwargs["to"] == "alice@example.com"
        assert call_kwargs["briefing_content"] == "Today you have 2 meetings."

    @pytest.mark.asyncio
    async def test_skips_when_no_opted_in_users(self) -> None:
        """No emails sent when no user has email_briefing_enabled."""
        from pwbs.queue.tasks.briefing import _send_briefing_emails_async

        mock_session = AsyncMock()
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=users_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        with patch(
            "pwbs.db.postgres.get_session_factory",
            return_value=mock_factory,
        ):
            result = await _send_briefing_emails_async("morning")

        assert result["emails_sent"] == 0
        assert result["emails_failed"] == 0

    @pytest.mark.asyncio
    async def test_skips_user_without_briefing(self) -> None:
        """User opted in but no briefing exists → skip, no failure."""
        from pwbs.queue.tasks.briefing import _send_briefing_emails_async

        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "bob@example.com"
        user.email_briefing_enabled = True

        mock_session = AsyncMock()
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [user]

        briefing_result = MagicMock()
        briefing_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(side_effect=[users_result, briefing_result])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        mock_email_service = MagicMock()
        mock_email_service.send_briefing_email = AsyncMock()

        with (
            patch(
                "pwbs.db.postgres.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "pwbs.services.email.create_email_service",
                return_value=mock_email_service,
            ),
        ):
            result = await _send_briefing_emails_async("morning")

        assert result["emails_sent"] == 0
        assert result["emails_failed"] == 0
        mock_email_service.send_briefing_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_briefing_type_returns_zero(self) -> None:
        """Unknown briefing type returns immediately."""
        from pwbs.queue.tasks.briefing import _send_briefing_emails_async

        result = await _send_briefing_emails_async("unknown_type")
        assert result["emails_sent"] == 0
        assert result["emails_failed"] == 0

    @pytest.mark.asyncio
    async def test_email_failure_counted(self) -> None:
        """Failed email delivery is counted in emails_failed."""
        from pwbs.queue.tasks.briefing import _send_briefing_emails_async

        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "fail@example.com"
        user.email_briefing_enabled = True

        briefing = MagicMock()
        briefing.id = uuid.uuid4()
        briefing.title = "Briefing"
        briefing.content = "Content"
        briefing.generated_at = datetime(2025, 1, 15, 6, 30, tzinfo=timezone.utc)
        briefing.source_chunks = []
        briefing.email_sent_at = None

        mock_session = AsyncMock()
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [user]
        briefing_result = MagicMock()
        briefing_result.scalar_one_or_none.return_value = briefing

        mock_session.execute = AsyncMock(side_effect=[users_result, briefing_result])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        mock_email_service = MagicMock()
        mock_email_service.send_briefing_email = AsyncMock(
            return_value=EmailResult(success=False, error="SMTP timeout")
        )

        with (
            patch(
                "pwbs.db.postgres.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "pwbs.services.email.create_email_service",
                return_value=mock_email_service,
            ),
        ):
            result = await _send_briefing_emails_async("morning")

        assert result["emails_sent"] == 0
        assert result["emails_failed"] == 1

    @pytest.mark.asyncio
    async def test_exception_during_send_counted_as_failure(self) -> None:
        """Exception during email send is caught and counted."""
        from pwbs.queue.tasks.briefing import _send_briefing_emails_async

        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "crash@example.com"
        user.email_briefing_enabled = True

        briefing = MagicMock()
        briefing.id = uuid.uuid4()
        briefing.title = "Briefing"
        briefing.content = "Content"
        briefing.generated_at = datetime(2025, 1, 15, 6, 30, tzinfo=timezone.utc)
        briefing.source_chunks = []
        briefing.email_sent_at = None

        mock_session = AsyncMock()
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [user]
        briefing_result = MagicMock()
        briefing_result.scalar_one_or_none.return_value = briefing

        mock_session.execute = AsyncMock(side_effect=[users_result, briefing_result])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        mock_email_service = MagicMock()
        mock_email_service.send_briefing_email = AsyncMock(
            side_effect=RuntimeError("Connection lost")
        )

        with (
            patch(
                "pwbs.db.postgres.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "pwbs.services.email.create_email_service",
                return_value=mock_email_service,
            ),
        ):
            result = await _send_briefing_emails_async("morning")

        assert result["emails_sent"] == 0
        assert result["emails_failed"] == 1
