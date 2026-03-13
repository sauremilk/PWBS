"""Tests for pwbs.schemas.briefing – Briefing, SourceRef, BriefingResponse (TASK-034)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pwbs.schemas.briefing import (
    Briefing,
    BriefingCreate,
    BriefingResponse,
    SourceRef,
)
from pwbs.schemas.enums import BriefingType, SourceType

_NOW = datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# SourceRef
# ---------------------------------------------------------------------------


class TestSourceRefValid:
    def test_minimal(self) -> None:
        ref = SourceRef(
            chunk_id=uuid4(),
            doc_title="Meeting Notes",
            source_type=SourceType.NOTION,
            date=_NOW,
            relevance=0.85,
        )
        assert ref.relevance == 0.85

    def test_boundary_relevance(self) -> None:
        ref = SourceRef(
            chunk_id=uuid4(),
            doc_title="Doc",
            source_type=SourceType.ZOOM,
            date=_NOW,
            relevance=0.0,
        )
        assert ref.relevance == 0.0
        ref2 = SourceRef(
            chunk_id=uuid4(),
            doc_title="Doc",
            source_type=SourceType.ZOOM,
            date=_NOW,
            relevance=1.0,
        )
        assert ref2.relevance == 1.0


class TestSourceRefInvalid:
    def test_relevance_above_one(self) -> None:
        with pytest.raises(ValidationError):
            SourceRef(
                chunk_id=uuid4(),
                doc_title="Doc",
                source_type=SourceType.NOTION,
                date=_NOW,
                relevance=1.1,
            )

    def test_relevance_below_zero(self) -> None:
        with pytest.raises(ValidationError):
            SourceRef(
                chunk_id=uuid4(),
                doc_title="Doc",
                source_type=SourceType.NOTION,
                date=_NOW,
                relevance=-0.1,
            )


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------


def _make_briefing(**overrides: object) -> dict:
    base: dict = {
        "id": uuid4(),
        "user_id": uuid4(),
        "briefing_type": BriefingType.MORNING,
        "title": "Morning Briefing",
        "content": "Here is your morning summary...",
        "source_chunks": [uuid4(), uuid4()],
        "generated_at": _NOW,
    }
    base.update(overrides)
    return base


class TestBriefingValid:
    def test_minimal(self) -> None:
        b = Briefing(**_make_briefing())
        assert b.source_entities is None
        assert b.trigger_context is None
        assert b.expires_at is None

    def test_all_briefing_types(self) -> None:
        for bt in BriefingType:
            b = Briefing(**_make_briefing(briefing_type=bt))
            assert b.briefing_type is bt

    def test_with_optional_fields(self) -> None:
        entities = [uuid4()]
        b = Briefing(
            **_make_briefing(
                source_entities=entities,
                trigger_context={"meeting_id": "abc-123"},
                expires_at=_NOW,
            )
        )
        assert b.source_entities == entities
        assert b.trigger_context is not None
        assert b.expires_at == _NOW

    def test_serialisation_roundtrip(self) -> None:
        b = Briefing(**_make_briefing())
        payload = b.model_dump(mode="json")
        b2 = Briefing.model_validate(payload)
        assert b2 == b


class TestBriefingInvalid:
    def test_empty_title(self) -> None:
        with pytest.raises(ValidationError):
            Briefing(**_make_briefing(title=""))

    def test_empty_content(self) -> None:
        with pytest.raises(ValidationError):
            Briefing(**_make_briefing(content=""))

    def test_invalid_briefing_type(self) -> None:
        with pytest.raises(ValidationError):
            Briefing(**_make_briefing(briefing_type="weekly"))


# ---------------------------------------------------------------------------
# BriefingCreate
# ---------------------------------------------------------------------------


class TestBriefingCreate:
    def test_valid(self) -> None:
        bc = BriefingCreate(
            user_id=uuid4(),
            briefing_type=BriefingType.MEETING_PREP,
            title="Prep",
            content="Prepare for...",
            source_chunks=[uuid4()],
        )
        assert bc.source_entities is None

    def test_missing_user_id(self) -> None:
        with pytest.raises(ValidationError):
            BriefingCreate(
                briefing_type=BriefingType.MORNING,
                title="Prep",
                content="Content",
                source_chunks=[uuid4()],
            )


# ---------------------------------------------------------------------------
# BriefingResponse
# ---------------------------------------------------------------------------


class TestBriefingResponse:
    def test_with_sources(self) -> None:
        source = SourceRef(
            chunk_id=uuid4(),
            doc_title="Notes",
            source_type=SourceType.NOTION,
            date=_NOW,
            relevance=0.9,
        )
        resp = BriefingResponse(
            **_make_briefing(),
            sources=[source],
        )
        assert len(resp.sources) == 1
        assert resp.sources[0].doc_title == "Notes"

    def test_default_empty_sources(self) -> None:
        resp = BriefingResponse(**_make_briefing())
        assert resp.sources == []


# ---------------------------------------------------------------------------
# BriefingType enum
# ---------------------------------------------------------------------------


class TestBriefingTypeEnum:
    def test_values(self) -> None:
        expected = {"morning", "meeting_prep"}
        actual = {bt.value for bt in BriefingType}
        assert actual == expected

    def test_is_str_enum(self) -> None:
        assert isinstance(BriefingType.MORNING, str)
