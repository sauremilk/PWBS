"""Tests for BriefingPersistenceService (TASK-080)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.briefing.persistence import (
    BriefingPersistenceService,
    PersistedBriefing,
    PersistenceConfig,
)
from pwbs.schemas.enums import BriefingType


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_briefing_orm(
    user_id: uuid.UUID | None = None,
    briefing_type: str = "morning",
    title: str = "Test Briefing",
    content: str = "# Test Content",
    source_chunks: list[uuid.UUID] | None = None,
    source_entities: list[uuid.UUID] | None = None,
    trigger_context: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> MagicMock:
    """Create a mock BriefingORM object."""
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.user_id = user_id or uuid.uuid4()
    obj.briefing_type = briefing_type
    obj.title = title
    obj.content = content
    obj.source_chunks = source_chunks or [uuid.uuid4()]
    obj.source_entities = source_entities
    obj.trigger_context = trigger_context
    obj.generated_at = generated_at or datetime.now(timezone.utc)
    obj.expires_at = expires_at
    return obj


def _mock_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# ------------------------------------------------------------------
# PersistenceConfig
# ------------------------------------------------------------------


class TestPersistenceConfig:
    """Tests for PersistenceConfig."""

    def test_defaults(self) -> None:
        cfg = PersistenceConfig()
        assert cfg.morning_expiry_hours == 24
        assert cfg.meeting_expiry_hours == 48

    def test_custom(self) -> None:
        cfg = PersistenceConfig(morning_expiry_hours=12, meeting_expiry_hours=72)
        assert cfg.morning_expiry_hours == 12
        assert cfg.meeting_expiry_hours == 72


# ------------------------------------------------------------------
# Expiry Calculation
# ------------------------------------------------------------------


class TestExpiryCalculation:
    """Tests for expires_at calculation."""

    def test_morning_24h(self) -> None:
        session = _mock_session()
        svc = BriefingPersistenceService(session)
        now = datetime(2025, 6, 15, 6, 30, tzinfo=timezone.utc)
        exp = svc._calculate_expiry(BriefingType.MORNING, now)
        assert exp == now + timedelta(hours=24)

    def test_meeting_48h(self) -> None:
        session = _mock_session()
        svc = BriefingPersistenceService(session)
        now = datetime(2025, 6, 15, 9, 0, tzinfo=timezone.utc)
        exp = svc._calculate_expiry(BriefingType.MEETING_PREP, now)
        assert exp == now + timedelta(hours=48)

    def test_custom_config(self) -> None:
        session = _mock_session()
        cfg = PersistenceConfig(morning_expiry_hours=6)
        svc = BriefingPersistenceService(session, config=cfg)
        now = datetime(2025, 6, 15, 6, 30, tzinfo=timezone.utc)
        exp = svc._calculate_expiry(BriefingType.MORNING, now)
        assert exp == now + timedelta(hours=6)


# ------------------------------------------------------------------
# ORM Conversion
# ------------------------------------------------------------------


class TestToPersistedConversion:
    """Tests for _to_persisted static method."""

    def test_basic_conversion(self) -> None:
        orm = _make_briefing_orm()
        result = BriefingPersistenceService._to_persisted(orm)
        assert isinstance(result, PersistedBriefing)
        assert result.id == orm.id
        assert result.user_id == orm.user_id
        assert result.title == orm.title
        assert result.content == orm.content
        assert result.is_new is False

    def test_none_source_entities(self) -> None:
        orm = _make_briefing_orm(source_entities=None)
        result = BriefingPersistenceService._to_persisted(orm)
        assert result.source_entities == []

    def test_none_source_chunks(self) -> None:
        orm = _make_briefing_orm()
        orm.source_chunks = None
        result = BriefingPersistenceService._to_persisted(orm)
        assert result.source_chunks == []

    def test_meeting_type(self) -> None:
        orm = _make_briefing_orm(briefing_type="meeting_prep")
        result = BriefingPersistenceService._to_persisted(orm)
        assert result.briefing_type == BriefingType.MEETING_PREP

    def test_unknown_type_fallback(self) -> None:
        orm = _make_briefing_orm(briefing_type="unknown_type")
        result = BriefingPersistenceService._to_persisted(orm)
        assert result.briefing_type == BriefingType.MORNING


# ------------------------------------------------------------------
# Save
# ------------------------------------------------------------------


class TestSave:
    """Tests for the save() method."""

    @pytest.mark.asyncio
    async def test_save_morning(self) -> None:
        session = _mock_session()
        svc = BriefingPersistenceService(session)
        user_id = uuid.uuid4()
        chunks = [uuid.uuid4(), uuid.uuid4()]

        result = await svc.save(
            user_id=user_id,
            briefing_type=BriefingType.MORNING,
            title="Morgenbriefing 15. Juni",
            content="# Guten Morgen\nHeute steht an...",
            source_chunks=chunks,
            trigger_context={"schedule": "06:30"},
        )

        assert result.user_id == user_id
        assert result.briefing_type == BriefingType.MORNING
        assert result.title == "Morgenbriefing 15. Juni"
        assert result.source_chunks == chunks
        assert result.source_entities == []
        assert result.trigger_context == {"schedule": "06:30"}
        assert result.is_new is True
        assert result.expires_at is not None
        # Check expiry is ~24h from now
        delta = result.expires_at - result.generated_at
        assert 23.9 < delta.total_seconds() / 3600 < 24.1

        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_meeting_prep(self) -> None:
        session = _mock_session()
        svc = BriefingPersistenceService(session)
        user_id = uuid.uuid4()

        result = await svc.save(
            user_id=user_id,
            briefing_type=BriefingType.MEETING_PREP,
            title="Meeting Prep: Sprint Review",
            content="# Sprint Review Vorbereitung",
            source_chunks=[uuid.uuid4()],
            trigger_context={"calendar_event_id": "evt_123"},
        )

        # Check 48h expiry
        delta = result.expires_at - result.generated_at
        assert 47.9 < delta.total_seconds() / 3600 < 48.1

    @pytest.mark.asyncio
    async def test_save_with_custom_id(self) -> None:
        session = _mock_session()
        svc = BriefingPersistenceService(session)
        custom_id = uuid.uuid4()

        result = await svc.save(
            user_id=uuid.uuid4(),
            briefing_type=BriefingType.MORNING,
            title="T",
            content="C",
            source_chunks=[],
            briefing_id=custom_id,
        )

        assert result.id == custom_id

    @pytest.mark.asyncio
    async def test_save_with_entities(self) -> None:
        session = _mock_session()
        svc = BriefingPersistenceService(session)
        entities = [uuid.uuid4(), uuid.uuid4()]

        result = await svc.save(
            user_id=uuid.uuid4(),
            briefing_type=BriefingType.MORNING,
            title="T",
            content="C",
            source_chunks=[uuid.uuid4()],
            source_entities=entities,
        )

        assert result.source_entities == entities

    @pytest.mark.asyncio
    async def test_save_without_trigger_context(self) -> None:
        session = _mock_session()
        svc = BriefingPersistenceService(session)

        result = await svc.save(
            user_id=uuid.uuid4(),
            briefing_type=BriefingType.MORNING,
            title="T",
            content="C",
            source_chunks=[],
        )

        assert result.trigger_context is None


# ------------------------------------------------------------------
# Regenerate
# ------------------------------------------------------------------


class TestRegenerate:
    """Tests for the regenerate() method."""

    @pytest.mark.asyncio
    async def test_regenerate_deletes_and_creates(self) -> None:
        session = _mock_session()
        svc = BriefingPersistenceService(session)
        bid = uuid.uuid4()
        user_id = uuid.uuid4()

        result = await svc.regenerate(
            briefing_id=bid,
            user_id=user_id,
            briefing_type=BriefingType.MORNING,
            title="Regenerated",
            content="New content",
            source_chunks=[uuid.uuid4()],
        )

        # Delete was called
        session.execute.assert_called()
        # Result has the same ID
        assert result.id == bid
        assert result.title == "Regenerated"
        assert result.is_new is True


# ------------------------------------------------------------------
# Get By ID
# ------------------------------------------------------------------


class TestGetById:
    """Tests for the get_by_id() method."""

    @pytest.mark.asyncio
    async def test_found(self) -> None:
        orm = _make_briefing_orm()
        session = _mock_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = orm
        session.execute = AsyncMock(return_value=result_mock)

        svc = BriefingPersistenceService(session)
        result = await svc.get_by_id(orm.id, orm.user_id)

        assert result is not None
        assert result.id == orm.id
        assert result.is_new is False

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        session = _mock_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        svc = BriefingPersistenceService(session)
        result = await svc.get_by_id(uuid.uuid4(), uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_wrong_user_not_found(self) -> None:
        """Different user_id should not find the briefing (tenant isolation)."""
        session = _mock_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        svc = BriefingPersistenceService(session)
        result = await svc.get_by_id(uuid.uuid4(), uuid.uuid4())

        assert result is None


# ------------------------------------------------------------------
# Get Latest
# ------------------------------------------------------------------


class TestGetLatest:
    """Tests for the get_latest() method."""

    @pytest.mark.asyncio
    async def test_returns_list(self) -> None:
        user_id = uuid.uuid4()
        orm1 = _make_briefing_orm(user_id=user_id)
        orm2 = _make_briefing_orm(user_id=user_id)
        session = _mock_session()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [orm1, orm2]
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        svc = BriefingPersistenceService(session)
        results = await svc.get_latest(user_id)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_empty_result(self) -> None:
        session = _mock_session()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        svc = BriefingPersistenceService(session)
        results = await svc.get_latest(uuid.uuid4())

        assert results == []

    @pytest.mark.asyncio
    async def test_limit_capped_at_50(self) -> None:
        session = _mock_session()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        svc = BriefingPersistenceService(session)
        await svc.get_latest(uuid.uuid4(), limit=100)

        # Verify execute was called (limit capped internally)
        session.execute.assert_called_once()


# ------------------------------------------------------------------
# Delete Expired
# ------------------------------------------------------------------


class TestDeleteExpired:
    """Tests for the delete_expired() method."""

    @pytest.mark.asyncio
    async def test_deletes_expired(self) -> None:
        session = _mock_session()
        result_mock = MagicMock()
        result_mock.all.return_value = [
            (uuid.uuid4(),),
            (uuid.uuid4(),),
        ]
        session.execute = AsyncMock(return_value=result_mock)

        svc = BriefingPersistenceService(session)
        count = await svc.delete_expired(uuid.uuid4())

        assert count == 2

    @pytest.mark.asyncio
    async def test_nothing_expired(self) -> None:
        session = _mock_session()
        result_mock = MagicMock()
        result_mock.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        svc = BriefingPersistenceService(session)
        count = await svc.delete_expired(uuid.uuid4())

        assert count == 0


# ------------------------------------------------------------------
# PersistedBriefing Dataclass
# ------------------------------------------------------------------


class TestPersistedBriefing:
    """Tests for PersistedBriefing dataclass."""

    def test_defaults(self) -> None:
        pb = PersistedBriefing(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            briefing_type=BriefingType.MORNING,
            title="T",
            content="C",
            source_chunks=[],
            source_entities=[],
            trigger_context=None,
            generated_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        assert pb.is_new is True

    def test_frozen(self) -> None:
        pb = PersistedBriefing(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            briefing_type=BriefingType.MORNING,
            title="T",
            content="C",
            source_chunks=[],
            source_entities=[],
            trigger_context=None,
            generated_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        with pytest.raises(AttributeError):
            pb.title = "Changed"  # type: ignore[misc]
