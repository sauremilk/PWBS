"""Tests for AssumptionTrackerService (TASK-155)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.analytics.assumption_tracker import (
    _TERMINAL_STATUSES,
    _VALID_STATUSES,
    AssumptionTrackerService,
)
from pwbs.core.exceptions import NotFoundError, ValidationError

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

OWNER_ID = uuid.uuid4()
ASSUMPTION_ID = uuid.uuid4()


def _make_assumption(
    *,
    id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    title: str = "Test hypothesis",
    description: str | None = None,
    status: str = "open",
    status_changed_at: datetime | None = None,
    status_reason: str | None = None,
    evidence: list[dict[str, Any]] | None = None,
    source_decision_id: uuid.UUID | None = None,
    source_document_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = id or uuid.uuid4()
    a.user_id = user_id or OWNER_ID
    a.title = title
    a.description = description
    a.status = status
    a.status_changed_at = status_changed_at
    a.status_reason = status_reason
    a.evidence = evidence or []
    a.source_decision_id = source_decision_id
    a.source_document_id = source_document_id
    a.created_at = created_at or datetime.now(UTC)
    a.updated_at = updated_at or datetime.now(UTC)
    return a


def _make_db(
    *,
    scalar_one_or_none: Any = None,
    scalars_all: list[Any] | None = None,
) -> AsyncMock:
    """Create a mock AsyncSession."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = scalar_one_or_none
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = scalars_all or []
    result_mock.scalars.return_value = scalars_mock
    db.execute.return_value = result_mock
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------


class TestConstants:
    def test_valid_statuses(self) -> None:
        assert "open" in _VALID_STATUSES
        assert "confirmed" in _VALID_STATUSES
        assert "refuted" in _VALID_STATUSES
        assert "revised" in _VALID_STATUSES

    def test_terminal_statuses_subset_of_valid(self) -> None:
        assert _TERMINAL_STATUSES.issubset(_VALID_STATUSES)

    def test_terminal_statuses(self) -> None:
        assert "confirmed" in _TERMINAL_STATUSES
        assert "refuted" in _TERMINAL_STATUSES
        assert "open" not in _TERMINAL_STATUSES


# ------------------------------------------------------------------
# Create
# ------------------------------------------------------------------


class TestCreate:
    @pytest.mark.asyncio
    async def test_creates_assumption_with_open_status(self) -> None:
        db = _make_db()
        svc = AssumptionTrackerService(db)

        await svc.create(owner_id=OWNER_ID, title="Hypothesis A")

        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert added.title == "Hypothesis A"
        assert added.status == "open"
        assert added.user_id == OWNER_ID
        assert added.evidence == []

    @pytest.mark.asyncio
    async def test_creates_with_description(self) -> None:
        db = _make_db()
        svc = AssumptionTrackerService(db)

        await svc.create(
            owner_id=OWNER_ID,
            title="Hypothesis B",
            description="Detailed description",
        )

        added = db.add.call_args[0][0]
        assert added.description == "Detailed description"

    @pytest.mark.asyncio
    async def test_creates_with_source_links(self) -> None:
        db = _make_db()
        svc = AssumptionTrackerService(db)
        dec_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        await svc.create(
            owner_id=OWNER_ID,
            title="Hypothesis C",
            source_decision_id=dec_id,
            source_document_id=doc_id,
        )

        added = db.add.call_args[0][0]
        assert added.source_decision_id == dec_id
        assert added.source_document_id == doc_id

    @pytest.mark.asyncio
    async def test_flush_and_refresh_called(self) -> None:
        db = _make_db()
        svc = AssumptionTrackerService(db)

        await svc.create(owner_id=OWNER_ID, title="Test")

        db.flush.assert_awaited_once()
        db.refresh.assert_awaited_once()


# ------------------------------------------------------------------
# Get
# ------------------------------------------------------------------


class TestGet:
    @pytest.mark.asyncio
    async def test_returns_assumption(self) -> None:
        assumption = _make_assumption(id=ASSUMPTION_ID)
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)

        result = await svc.get(ASSUMPTION_ID, OWNER_ID)

        assert result is assumption

    @pytest.mark.asyncio
    async def test_raises_not_found(self) -> None:
        db = _make_db(scalar_one_or_none=None)
        svc = AssumptionTrackerService(db)

        with pytest.raises(NotFoundError) as exc_info:
            await svc.get(ASSUMPTION_ID, OWNER_ID)

        assert exc_info.value.code == "ASSUMPTION_NOT_FOUND"


# ------------------------------------------------------------------
# List
# ------------------------------------------------------------------


class TestListByOwner:
    @pytest.mark.asyncio
    async def test_returns_list(self) -> None:
        assumptions = [_make_assumption(), _make_assumption()]
        db = _make_db(scalars_all=assumptions)
        svc = AssumptionTrackerService(db)

        result = await svc.list_by_owner(OWNER_ID)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        db = _make_db(scalars_all=[])
        svc = AssumptionTrackerService(db)

        result = await svc.list_by_owner(OWNER_ID)

        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_status_filter_raises(self) -> None:
        db = _make_db()
        svc = AssumptionTrackerService(db)

        with pytest.raises(ValidationError) as exc_info:
            await svc.list_by_owner(OWNER_ID, status="invalid_status")

        assert exc_info.value.code == "INVALID_STATUS_FILTER"

    @pytest.mark.asyncio
    async def test_valid_status_filter_accepted(self) -> None:
        db = _make_db(scalars_all=[])
        svc = AssumptionTrackerService(db)

        result = await svc.list_by_owner(OWNER_ID, status="open")

        assert result == []


# ------------------------------------------------------------------
# Update status
# ------------------------------------------------------------------


class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_updates_to_confirmed(self) -> None:
        assumption = _make_assumption(id=ASSUMPTION_ID, status="open")
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)

        result = await svc.update_status(
            ASSUMPTION_ID, OWNER_ID, "confirmed", reason="Evidence found"
        )

        assert assumption.status == "confirmed"
        assert assumption.status_reason == "Evidence found"
        assert assumption.status_changed_at is not None

    @pytest.mark.asyncio
    async def test_updates_to_refuted(self) -> None:
        assumption = _make_assumption(id=ASSUMPTION_ID, status="open")
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)

        await svc.update_status(ASSUMPTION_ID, OWNER_ID, "refuted", reason="Disproved")

        assert assumption.status == "refuted"

    @pytest.mark.asyncio
    async def test_updates_to_revised(self) -> None:
        assumption = _make_assumption(id=ASSUMPTION_ID, status="open")
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)

        await svc.update_status(ASSUMPTION_ID, OWNER_ID, "revised")

        assert assumption.status == "revised"

    @pytest.mark.asyncio
    async def test_invalid_status_raises(self) -> None:
        db = _make_db()
        svc = AssumptionTrackerService(db)

        with pytest.raises(ValidationError) as exc_info:
            await svc.update_status(ASSUMPTION_ID, OWNER_ID, "invalid")

        assert exc_info.value.code == "INVALID_STATUS"

    @pytest.mark.asyncio
    async def test_terminal_status_raises(self) -> None:
        assumption = _make_assumption(id=ASSUMPTION_ID, status="confirmed")
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)

        with pytest.raises(ValidationError) as exc_info:
            await svc.update_status(ASSUMPTION_ID, OWNER_ID, "refuted")

        assert exc_info.value.code == "STATUS_TERMINAL"

    @pytest.mark.asyncio
    async def test_refuted_is_terminal(self) -> None:
        assumption = _make_assumption(id=ASSUMPTION_ID, status="refuted")
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)

        with pytest.raises(ValidationError) as exc_info:
            await svc.update_status(ASSUMPTION_ID, OWNER_ID, "open")

        assert exc_info.value.code == "STATUS_TERMINAL"

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        db = _make_db(scalar_one_or_none=None)
        svc = AssumptionTrackerService(db)

        with pytest.raises(NotFoundError):
            await svc.update_status(ASSUMPTION_ID, OWNER_ID, "confirmed")


# ------------------------------------------------------------------
# Add evidence
# ------------------------------------------------------------------


class TestAddEvidence:
    @pytest.mark.asyncio
    async def test_appends_evidence_entry(self) -> None:
        assumption = _make_assumption(id=ASSUMPTION_ID, evidence=[])
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)

        await svc.add_evidence(ASSUMPTION_ID, OWNER_ID, note="New evidence found")

        assert len(assumption.evidence) == 1
        assert assumption.evidence[0]["note"] == "New evidence found"
        assert "date" in assumption.evidence[0]

    @pytest.mark.asyncio
    async def test_appends_to_existing_evidence(self) -> None:
        existing = [{"date": "2025-01-01", "note": "First"}]
        assumption = _make_assumption(id=ASSUMPTION_ID, evidence=existing)
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)

        await svc.add_evidence(ASSUMPTION_ID, OWNER_ID, note="Second entry")

        assert len(assumption.evidence) == 2
        assert assumption.evidence[1]["note"] == "Second entry"

    @pytest.mark.asyncio
    async def test_includes_source_id(self) -> None:
        assumption = _make_assumption(id=ASSUMPTION_ID, evidence=[])
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)
        src_id = uuid.uuid4()

        await svc.add_evidence(ASSUMPTION_ID, OWNER_ID, note="With source", source_id=src_id)

        assert assumption.evidence[0]["source_id"] == str(src_id)

    @pytest.mark.asyncio
    async def test_no_source_id_when_none(self) -> None:
        assumption = _make_assumption(id=ASSUMPTION_ID, evidence=[])
        db = _make_db(scalar_one_or_none=assumption)
        svc = AssumptionTrackerService(db)

        await svc.add_evidence(ASSUMPTION_ID, OWNER_ID, note="No source")

        assert "source_id" not in assumption.evidence[0]

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        db = _make_db(scalar_one_or_none=None)
        svc = AssumptionTrackerService(db)

        with pytest.raises(NotFoundError):
            await svc.add_evidence(ASSUMPTION_ID, OWNER_ID, note="Test")


# ------------------------------------------------------------------
# Timeline
# ------------------------------------------------------------------


class TestGetTimeline:
    @pytest.mark.asyncio
    async def test_returns_timeline_dict(self) -> None:
        now = datetime.now(UTC)
        assumptions = [
            _make_assumption(
                status="open",
                status_changed_at=now - timedelta(days=10),
            ),
            _make_assumption(
                status="confirmed",
                status_changed_at=now - timedelta(days=5),
            ),
        ]
        db = _make_db(scalars_all=assumptions)
        svc = AssumptionTrackerService(db)

        result = await svc.get_timeline(OWNER_ID, months=3)

        assert "total" in result
        assert "status_counts" in result
        assert "recently_changed" in result
        assert "period_months" in result
        assert result["period_months"] == 3
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_empty_assumptions(self) -> None:
        db = _make_db(scalars_all=[])
        svc = AssumptionTrackerService(db)

        result = await svc.get_timeline(OWNER_ID, months=3)

        assert result["total"] == 0
        assert result["status_counts"] == {}
        assert result["recently_changed"] == []

    @pytest.mark.asyncio
    async def test_status_counts(self) -> None:
        assumptions = [
            _make_assumption(status="open", status_changed_at=None),
            _make_assumption(status="open", status_changed_at=None),
            _make_assumption(status="confirmed", status_changed_at=None),
        ]
        db = _make_db(scalars_all=assumptions)
        svc = AssumptionTrackerService(db)

        result = await svc.get_timeline(OWNER_ID, months=3)

        assert result["status_counts"]["open"] == 2
        assert result["status_counts"]["confirmed"] == 1
