"""Tests for pwbs.schemas – SearchResult, SearchRequest, SearchResponse, Connection (TASK-035)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pwbs.schemas.briefing import SourceRef
from pwbs.schemas.connector import Connection
from pwbs.schemas.enums import ConnectionStatus, SourceType
from pwbs.schemas.search import SearchFilters, SearchRequest, SearchResponse, SearchResult

_NOW = datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


class TestSearchResultValid:
    def test_minimal(self) -> None:
        sr = SearchResult(
            chunk_id=uuid4(),
            doc_title="Meeting Notes",
            source_type=SourceType.NOTION,
            date=_NOW,
            content="Some relevant text...",
            score=0.92,
        )
        assert sr.entities == []

    def test_with_entities(self) -> None:
        sr = SearchResult(
            chunk_id=uuid4(),
            doc_title="Doc",
            source_type=SourceType.ZOOM,
            date=_NOW,
            content="Content",
            score=0.5,
            entities=["Alice", "ProjectX"],
        )
        assert len(sr.entities) == 2


class TestSearchResultInvalid:
    def test_score_above_one(self) -> None:
        with pytest.raises(ValidationError):
            SearchResult(
                chunk_id=uuid4(),
                doc_title="Doc",
                source_type=SourceType.NOTION,
                date=_NOW,
                content="c",
                score=1.5,
            )

    def test_score_below_zero(self) -> None:
        with pytest.raises(ValidationError):
            SearchResult(
                chunk_id=uuid4(),
                doc_title="Doc",
                source_type=SourceType.NOTION,
                date=_NOW,
                content="c",
                score=-0.1,
            )


# ---------------------------------------------------------------------------
# SearchRequest
# ---------------------------------------------------------------------------


class TestSearchRequestValid:
    def test_defaults(self) -> None:
        req = SearchRequest(query="What happened?")
        assert req.limit == 10
        assert req.filters is None

    def test_with_filters(self) -> None:
        req = SearchRequest(
            query="meeting notes",
            filters=SearchFilters(
                source_types=[SourceType.NOTION, SourceType.GOOGLE_CALENDAR],
                date_from=_NOW,
            ),
            limit=25,
        )
        assert req.filters is not None
        assert len(req.filters.source_types) == 2  # type: ignore[arg-type]

    def test_max_limit(self) -> None:
        req = SearchRequest(query="q", limit=50)
        assert req.limit == 50


class TestSearchRequestInvalid:
    def test_empty_query(self) -> None:
        with pytest.raises(ValidationError):
            SearchRequest(query="")

    def test_limit_too_high(self) -> None:
        with pytest.raises(ValidationError):
            SearchRequest(query="q", limit=51)

    def test_limit_zero(self) -> None:
        with pytest.raises(ValidationError):
            SearchRequest(query="q", limit=0)


# ---------------------------------------------------------------------------
# SearchResponse
# ---------------------------------------------------------------------------


class TestSearchResponse:
    def test_empty_results(self) -> None:
        resp = SearchResponse(results=[])
        assert resp.answer is None
        assert resp.sources == []
        assert resp.confidence is None

    def test_with_results_and_answer(self) -> None:
        result = SearchResult(
            chunk_id=uuid4(),
            doc_title="Doc",
            source_type=SourceType.OBSIDIAN,
            date=_NOW,
            content="answer found here",
            score=0.9,
        )
        source = SourceRef(
            chunk_id=result.chunk_id,
            doc_title="Doc",
            source_type=SourceType.OBSIDIAN,
            date=_NOW,
            relevance=0.9,
        )
        resp = SearchResponse(
            results=[result],
            answer="Based on your notes...",
            sources=[source],
            confidence=0.85,
        )
        assert len(resp.results) == 1
        assert resp.answer is not None
        assert resp.confidence == 0.85


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class TestConnectionValid:
    def test_minimal(self) -> None:
        conn = Connection(
            id=uuid4(),
            user_id=uuid4(),
            source_type=SourceType.GOOGLE_CALENDAR,
            status=ConnectionStatus.ACTIVE,
            created_at=_NOW,
        )
        assert conn.watermark is None
        assert conn.config == {}

    def test_with_watermark_and_config(self) -> None:
        conn = Connection(
            id=uuid4(),
            user_id=uuid4(),
            source_type=SourceType.NOTION,
            status=ConnectionStatus.PAUSED,
            watermark=_NOW,
            config={"sync_interval": 15},
            created_at=_NOW,
        )
        assert conn.watermark == _NOW
        assert conn.config["sync_interval"] == 15

    def test_all_connection_statuses(self) -> None:
        for cs in ConnectionStatus:
            conn = Connection(
                id=uuid4(),
                user_id=uuid4(),
                source_type=SourceType.ZOOM,
                status=cs,
                created_at=_NOW,
            )
            assert conn.status is cs


class TestConnectionInvalid:
    def test_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            Connection(
                id=uuid4(),
                user_id=uuid4(),
                source_type=SourceType.ZOOM,
                status="deleted",  # type: ignore[arg-type]
                created_at=_NOW,
            )


# ---------------------------------------------------------------------------
# ConnectionStatus enum
# ---------------------------------------------------------------------------


class TestConnectionStatusEnum:
    def test_values(self) -> None:
        expected = {"active", "paused", "error", "revoked"}
        actual = {cs.value for cs in ConnectionStatus}
        assert actual == expected

    def test_is_str_enum(self) -> None:
        assert isinstance(ConnectionStatus.ACTIVE, str)
