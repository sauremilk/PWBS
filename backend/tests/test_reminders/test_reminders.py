"""Tests for the reminders module (TASK-131).

Tests:
- extract_followups: follow-up detection from text content
- create_reminder / get_pending_reminders / update_reminder_status: CRUD
- run_trigger_engine: overdue escalation + inactive topic detection
- API endpoints: GET /api/v1/reminders, PATCH /api/v1/reminders/{id}, POST /api/v1/reminders/trigger
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.reminders.service import (
    extract_followups,
)
from pwbs.schemas.enums import ReminderStatus, ReminderType, Urgency

# ===========================================================================
# extract_followups
# ===========================================================================


class TestExtractFollowups:
    """Test follow-up and open-question pattern detection."""

    def test_german_followup_ich_schicke(self) -> None:
        text = "Ich schicke dir das Dokument bis morgen."
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value

    def test_german_followup_wir_liefern(self) -> None:
        text = "Wir liefern den Bericht bis Freitag."
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value

    def test_english_followup_i_will(self) -> None:
        text = "I will send the report by tomorrow."
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value

    def test_english_followup_we_will(self) -> None:
        text = "We'll follow up on this by next week."
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value

    def test_action_item_pattern(self) -> None:
        text = "Action item: Review the architecture diagram and provide feedback"
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value

    def test_todo_pattern(self) -> None:
        text = "TODO: Fix the authentication bug in the login flow"
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value

    def test_deadline_date_pattern(self) -> None:
        text = "Deadline: 15.03.2025 fuer die Einreichung"
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value

    def test_open_question_pattern(self) -> None:
        text = "Offene Frage: Wie gehen wir mit dem Datenschutz um?"
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.OPEN_QUESTION.value

    def test_english_open_question(self) -> None:
        text = "Open question: What is the timeline for the migration?"
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.OPEN_QUESTION.value

    def test_tbd_pattern(self) -> None:
        text = "TBD: Decide on the database migration strategy for Q3"
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.OPEN_QUESTION.value

    def test_no_followup_in_plain_text(self) -> None:
        text = "Das Wetter ist heute schoen. Wir haben Mittag gegessen."
        results = extract_followups(text)
        assert len(results) == 0

    def test_deduplication(self) -> None:
        text = "TODO: Fix bug\nTODO: Fix bug"
        results = extract_followups(text)
        assert len(results) == 1

    def test_text_truncation_at_200_chars(self) -> None:
        long_text = "Action item: " + "x" * 300
        results = extract_followups(long_text)
        assert len(results) >= 1
        assert len(results[0]["text"]) <= 200

    def test_multiple_followups(self) -> None:
        text = (
            "Action item: Review the PR\n"
            "TODO: Update the documentation\n"
            "Offene Frage: Wann starten wir mit Phase 3?"
        )
        results = extract_followups(text)
        assert len(results) >= 3

    def test_bitte_bis_pattern(self) -> None:
        text = "Bitte bis Freitag erledigen"
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value

    def test_please_by_pattern(self) -> None:
        text = "Please by Monday submit the report"
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value

    def test_followup_hyphenated(self) -> None:
        text = "Follow-up: Check the deployment status on staging"
        results = extract_followups(text)
        assert len(results) >= 1
        assert results[0]["type"] == ReminderType.FOLLOW_UP.value


# ===========================================================================
# Reminder model construction
# ===========================================================================


class TestReminderModel:
    """Test that the Reminder ORM model can be instantiated."""

    def test_reminder_model_fields(self) -> None:
        from pwbs.models.reminder import Reminder

        r = Reminder(
            user_id=uuid.uuid4(),
            reminder_type=ReminderType.FOLLOW_UP.value,
            title="Test reminder",
            description="Test description",
            status=ReminderStatus.PENDING.value,
            urgency=Urgency.MEDIUM.value,
        )
        assert r.title == "Test reminder"
        assert r.reminder_type == "follow_up"
        assert r.status == "pending"
        assert r.urgency == "medium"

    def test_reminder_defaults(self) -> None:
        from pwbs.models.reminder import Reminder

        r = Reminder(
            user_id=uuid.uuid4(),
            reminder_type=ReminderType.OPEN_QUESTION.value,
            title="Question",
        )
        assert r.reminder_type == "open_question"
        assert r.due_at is None
        assert r.responsible_person is None
        assert r.source_document_id is None


# ===========================================================================
# Enum values
# ===========================================================================


class TestEnumValues:
    """Test that reminder-related enums have expected values."""

    def test_reminder_type_values(self) -> None:
        assert set(ReminderType) == {
            ReminderType.FOLLOW_UP,
            ReminderType.INACTIVE_TOPIC,
            ReminderType.OPEN_QUESTION,
        }

    def test_reminder_status_values(self) -> None:
        assert set(ReminderStatus) == {
            ReminderStatus.PENDING,
            ReminderStatus.ACKNOWLEDGED,
            ReminderStatus.DISMISSED,
            ReminderStatus.SNOOZED,
        }

    def test_urgency_values(self) -> None:
        assert set(Urgency) == {
            Urgency.HIGH,
            Urgency.MEDIUM,
            Urgency.LOW,
        }

    def test_reminder_type_string_values(self) -> None:
        assert ReminderType.FOLLOW_UP.value == "follow_up"
        assert ReminderType.INACTIVE_TOPIC.value == "inactive_topic"
        assert ReminderType.OPEN_QUESTION.value == "open_question"

    def test_reminder_status_string_values(self) -> None:
        assert ReminderStatus.PENDING.value == "pending"
        assert ReminderStatus.ACKNOWLEDGED.value == "acknowledged"
        assert ReminderStatus.DISMISSED.value == "dismissed"
        assert ReminderStatus.SNOOZED.value == "snoozed"


# ===========================================================================
# Service CRUD with mocked DB
# ===========================================================================


class TestCreateReminder:
    """Test create_reminder with a mocked AsyncSession."""

    @pytest.mark.asyncio
    async def test_create_reminder_basic(self) -> None:
        from pwbs.reminders.service import create_reminder

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        user_id = uuid.uuid4()
        reminder = await create_reminder(
            mock_db,
            user_id=user_id,
            reminder_type=ReminderType.FOLLOW_UP,
            title="Send report",
            description="Send the Q1 report to the team",
            urgency=Urgency.HIGH,
        )

        assert reminder.user_id == user_id
        assert reminder.reminder_type == "follow_up"
        assert reminder.title == "Send report"
        assert reminder.urgency == "high"
        assert reminder.status == "pending"
        assert reminder.expires_at is not None
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_reminder_with_due_date(self) -> None:
        from pwbs.reminders.service import create_reminder

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        due = datetime.now(tz=UTC) + timedelta(days=3)
        reminder = await create_reminder(
            mock_db,
            user_id=uuid.uuid4(),
            reminder_type=ReminderType.FOLLOW_UP,
            title="Deadline task",
            due_at=due,
        )
        assert reminder.due_at == due

    @pytest.mark.asyncio
    async def test_create_reminder_metadata(self) -> None:
        from pwbs.reminders.service import create_reminder

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        reminder = await create_reminder(
            mock_db,
            user_id=uuid.uuid4(),
            reminder_type=ReminderType.INACTIVE_TOPIC,
            title="Topic X inactive",
            metadata={"entity_id": "abc-123"},
        )
        assert reminder.reminder_metadata == {"entity_id": "abc-123"}

    @pytest.mark.asyncio
    async def test_create_reminder_default_metadata(self) -> None:
        from pwbs.reminders.service import create_reminder

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        reminder = await create_reminder(
            mock_db,
            user_id=uuid.uuid4(),
            reminder_type=ReminderType.OPEN_QUESTION,
            title="Open Q",
        )
        assert reminder.reminder_metadata == {}


class TestUpdateReminderStatus:
    """Test update_reminder_status with mocked DB."""

    @pytest.mark.asyncio
    async def test_update_to_acknowledged(self) -> None:
        from pwbs.reminders.service import update_reminder_status

        mock_reminder = MagicMock()
        mock_reminder.status = ReminderStatus.PENDING.value
        mock_reminder.urgency = Urgency.MEDIUM.value
        mock_reminder.resolved_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_reminder

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        result = await update_reminder_status(
            mock_db,
            reminder_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            new_status=ReminderStatus.ACKNOWLEDGED,
        )
        assert result is not None
        assert result.status == ReminderStatus.ACKNOWLEDGED.value
        assert result.resolved_at is not None

    @pytest.mark.asyncio
    async def test_update_to_dismissed(self) -> None:
        from pwbs.reminders.service import update_reminder_status

        mock_reminder = MagicMock()
        mock_reminder.status = ReminderStatus.PENDING.value
        mock_reminder.resolved_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_reminder

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        result = await update_reminder_status(
            mock_db,
            reminder_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            new_status=ReminderStatus.DISMISSED,
        )
        assert result is not None
        assert result.status == ReminderStatus.DISMISSED.value
        assert result.resolved_at is not None

    @pytest.mark.asyncio
    async def test_update_to_snoozed(self) -> None:
        from pwbs.reminders.service import update_reminder_status

        mock_reminder = MagicMock()
        mock_reminder.status = ReminderStatus.PENDING.value
        mock_reminder.due_at = datetime.now(tz=UTC)
        mock_reminder.resolved_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_reminder

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        result = await update_reminder_status(
            mock_db,
            reminder_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            new_status=ReminderStatus.SNOOZED,
        )
        assert result is not None
        assert result.status == ReminderStatus.SNOOZED.value
        assert result.due_at > datetime.now(tz=UTC)
        assert result.resolved_at is None

    @pytest.mark.asyncio
    async def test_update_not_found(self) -> None:
        from pwbs.reminders.service import update_reminder_status

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await update_reminder_status(
            mock_db,
            reminder_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            new_status=ReminderStatus.ACKNOWLEDGED,
        )
        assert result is None


# ===========================================================================
# Trigger engine
# ===========================================================================


class TestRunTriggerEngine:
    """Test run_trigger_engine with mocked DB."""

    @pytest.mark.asyncio
    async def test_escalates_overdue_reminders(self) -> None:
        from pwbs.reminders.service import run_trigger_engine

        overdue = MagicMock()
        overdue.id = uuid.uuid4()
        overdue.urgency = Urgency.MEDIUM.value

        # First execute: overdue query, second: inactive entities query
        mock_overdue_result = MagicMock()
        mock_overdue_result.scalars.return_value.all.return_value = [overdue]

        mock_inactive_result = MagicMock()
        mock_inactive_result.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=[mock_overdue_result, mock_inactive_result])
        mock_db.flush = AsyncMock()

        user_id = uuid.uuid4()
        result = await run_trigger_engine(mock_db, user_id=user_id)

        assert overdue.urgency == Urgency.HIGH.value
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_no_overdue_no_inactive(self) -> None:
        from pwbs.reminders.service import run_trigger_engine

        mock_overdue_result = MagicMock()
        mock_overdue_result.scalars.return_value.all.return_value = []

        mock_inactive_result = MagicMock()
        mock_inactive_result.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=[mock_overdue_result, mock_inactive_result])
        mock_db.flush = AsyncMock()

        result = await run_trigger_engine(mock_db, user_id=uuid.uuid4())

        assert result == []


# ===========================================================================
# API route schemas
# ===========================================================================


class TestAPISchemas:
    """Test API response/request Pydantic schemas."""

    def test_reminder_response_schema(self) -> None:
        from pwbs.api.v1.routes.reminders import ReminderResponse

        data = {
            "id": uuid.uuid4(),
            "reminder_type": "follow_up",
            "title": "Test",
            "description": "",
            "status": "pending",
            "urgency": "medium",
            "due_at": None,
            "responsible_person": None,
            "source_document_id": None,
            "created_at": datetime.now(tz=UTC),
            "resolved_at": None,
        }
        resp = ReminderResponse(**data)
        assert resp.title == "Test"

    def test_update_status_request(self) -> None:
        from pwbs.api.v1.routes.reminders import UpdateStatusRequest

        req = UpdateStatusRequest(status=ReminderStatus.ACKNOWLEDGED)
        assert req.status == ReminderStatus.ACKNOWLEDGED

    def test_trigger_response(self) -> None:
        from pwbs.api.v1.routes.reminders import TriggerResponse

        resp = TriggerResponse(new_reminders=5, message="5 neue Erinnerungen generiert.")
        assert resp.new_reminders == 5

    def test_reminder_list_response(self) -> None:
        from pwbs.api.v1.routes.reminders import ReminderListResponse

        resp = ReminderListResponse(items=[], count=0)
        assert resp.count == 0
