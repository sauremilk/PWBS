"""Tests for Search Result Enrichment with SourceRef (TASK-075)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.schemas.enums import SourceType
from pwbs.search.enrichment import (
    EnrichedSearchResult,
    SearchResultEnricher,
    _normalize_score,
    _safe_source_type,
    reconstruct_url,
)
from pwbs.search.hybrid import HybridSearchResult

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

USER_ID = uuid.uuid4()
NOW = datetime(2026, 3, 14, 10, 0, 0, tzinfo=UTC)


def _hybrid_result(
    chunk_id: uuid.UUID | None = None,
    content: str = "test content",
    title: str = "Test Title",
    source_type: str = "notion",
    score: float = 0.012,
    semantic_rank: int | None = 1,
    keyword_rank: int | None = None,
) -> HybridSearchResult:
    return HybridSearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        content=content,
        title=title,
        source_type=source_type,
        score=score,
        semantic_rank=semantic_rank,
        keyword_rank=keyword_rank,
    )


def _make_row(
    chunk_id: uuid.UUID,
    title: str = "Doc Title",
    source_type: str = "notion",
    source_id: str = "abc123",
    created_at: datetime = NOW,
):
    """Create a mock DB row."""
    row = MagicMock()
    row.chunk_id = str(chunk_id)
    row.title = title
    row.source_type = source_type
    row.source_id = source_id
    row.created_at = created_at
    return row


def _make_session(rows: list) -> AsyncMock:
    """Create a mock AsyncSession that returns given rows."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = rows
    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)
    return session


# ------------------------------------------------------------------
# URL Reconstruction
# ------------------------------------------------------------------


class TestReconstructUrl:
    def test_notion_url(self) -> None:
        url = reconstruct_url("notion", "page-123")
        assert url == "https://notion.so/page-123"

    def test_google_calendar_url(self) -> None:
        url = reconstruct_url("google_calendar", "evt-456")
        assert url == "https://calendar.google.com/calendar/event?eid=evt-456"

    def test_zoom_url(self) -> None:
        url = reconstruct_url("zoom", "rec-789")
        assert url == "https://zoom.us/rec/rec-789"

    def test_obsidian_returns_none(self) -> None:
        url = reconstruct_url("obsidian", "my-note.md")
        assert url is None

    def test_unknown_source_returns_none(self) -> None:
        url = reconstruct_url("unknown_source", "id123")
        assert url is None


# ------------------------------------------------------------------
# Safe SourceType conversion
# ------------------------------------------------------------------


class TestSafeSourceType:
    def test_valid_notion(self) -> None:
        assert _safe_source_type("notion") == SourceType.NOTION

    def test_valid_google_calendar(self) -> None:
        assert _safe_source_type("google_calendar") == SourceType.GOOGLE_CALENDAR

    def test_valid_zoom(self) -> None:
        assert _safe_source_type("zoom") == SourceType.ZOOM

    def test_unknown_defaults_to_notion(self) -> None:
        assert _safe_source_type("unknown") == SourceType.NOTION


# ------------------------------------------------------------------
# Score normalization
# ------------------------------------------------------------------


class TestNormalizeScore:
    def test_normal_rrf_score(self) -> None:
        assert _normalize_score(0.012) == 0.012

    def test_clamps_above_one(self) -> None:
        assert _normalize_score(1.5) == 1.0

    def test_clamps_below_zero(self) -> None:
        assert _normalize_score(-0.1) == 0.0

    def test_zero(self) -> None:
        assert _normalize_score(0.0) == 0.0

    def test_one(self) -> None:
        assert _normalize_score(1.0) == 1.0


# ------------------------------------------------------------------
# SearchResultEnricher
# ------------------------------------------------------------------


class TestSearchResultEnricher:
    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        session = _make_session([])
        enricher = SearchResultEnricher(session)
        result = await enricher.enrich([], USER_ID)
        assert result == []
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_result_enriched(self) -> None:
        cid = uuid.uuid4()
        row = _make_row(cid, title="Meeting Notes", source_type="notion", source_id="page-abc")
        session = _make_session([row])
        enricher = SearchResultEnricher(session)

        hybrid = _hybrid_result(chunk_id=cid, score=0.012)
        results = await enricher.enrich([hybrid], USER_ID)

        assert len(results) == 1
        assert isinstance(results[0], EnrichedSearchResult)
        assert results[0].chunk_id == cid
        assert results[0].source_ref.doc_title == "Meeting Notes"
        assert results[0].source_ref.source_type == SourceType.NOTION
        assert results[0].original_url == "https://notion.so/page-abc"

    @pytest.mark.asyncio
    async def test_multiple_results_preserve_order(self) -> None:
        cid1, cid2, cid3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        rows = [
            _make_row(cid1, title="Doc A", source_id="a1"),
            _make_row(cid2, title="Doc B", source_id="b2"),
            _make_row(cid3, title="Doc C", source_id="c3"),
        ]
        session = _make_session(rows)
        enricher = SearchResultEnricher(session)

        hybrids = [
            _hybrid_result(chunk_id=cid1, score=0.015),
            _hybrid_result(chunk_id=cid2, score=0.012),
            _hybrid_result(chunk_id=cid3, score=0.010),
        ]
        results = await enricher.enrich(hybrids, USER_ID)

        assert len(results) == 3
        assert [r.chunk_id for r in results] == [cid1, cid2, cid3]
        assert results[0].score > results[1].score > results[2].score

    @pytest.mark.asyncio
    async def test_missing_metadata_skips_result(self) -> None:
        cid1, cid2 = uuid.uuid4(), uuid.uuid4()
        # Only return metadata for cid1
        rows = [_make_row(cid1, title="Found Doc")]
        session = _make_session(rows)
        enricher = SearchResultEnricher(session)

        hybrids = [
            _hybrid_result(chunk_id=cid1),
            _hybrid_result(chunk_id=cid2),
        ]
        results = await enricher.enrich(hybrids, USER_ID)

        assert len(results) == 1
        assert results[0].chunk_id == cid1

    @pytest.mark.asyncio
    async def test_source_ref_fields(self) -> None:
        cid = uuid.uuid4()
        row = _make_row(
            cid,
            title="Sprint Planning",
            source_type="google_calendar",
            source_id="evt-42",
            created_at=NOW,
        )
        session = _make_session([row])
        enricher = SearchResultEnricher(session)

        hybrid = _hybrid_result(chunk_id=cid, score=0.008)
        results = await enricher.enrich([hybrid], USER_ID)

        sr = results[0].source_ref
        assert sr.chunk_id == cid
        assert sr.doc_title == "Sprint Planning"
        assert sr.source_type == SourceType.GOOGLE_CALENDAR
        assert sr.date == NOW
        assert sr.relevance == 0.008

    @pytest.mark.asyncio
    async def test_fallback_title_from_hybrid_result(self) -> None:
        """If document title is None, fall back to hybrid result title."""
        cid = uuid.uuid4()
        row = _make_row(cid, title=None, source_id="x")
        session = _make_session([row])
        enricher = SearchResultEnricher(session)

        hybrid = _hybrid_result(chunk_id=cid, title="Fallback Title")
        results = await enricher.enrich([hybrid], USER_ID)

        assert results[0].source_ref.doc_title == "Fallback Title"

    @pytest.mark.asyncio
    async def test_obsidian_has_no_url(self) -> None:
        cid = uuid.uuid4()
        row = _make_row(cid, source_type="obsidian", source_id="note.md")
        session = _make_session([row])
        enricher = SearchResultEnricher(session)

        hybrid = _hybrid_result(chunk_id=cid)
        results = await enricher.enrich([hybrid], USER_ID)

        assert results[0].original_url is None

    @pytest.mark.asyncio
    async def test_user_id_passed_to_query(self) -> None:
        session = _make_session([])
        enricher = SearchResultEnricher(session)

        cid = uuid.uuid4()
        uid = uuid.uuid4()
        await enricher.enrich([_hybrid_result(chunk_id=cid)], uid)

        session.execute.assert_called_once()
        call_params = session.execute.call_args[0][1]
        assert call_params["user_id"] == str(uid)

    @pytest.mark.asyncio
    async def test_semantic_and_keyword_ranks_preserved(self) -> None:
        cid = uuid.uuid4()
        row = _make_row(cid)
        session = _make_session([row])
        enricher = SearchResultEnricher(session)

        hybrid = _hybrid_result(chunk_id=cid, semantic_rank=2, keyword_rank=5)
        results = await enricher.enrich([hybrid], USER_ID)

        assert results[0].semantic_rank == 2
        assert results[0].keyword_rank == 5

    @pytest.mark.asyncio
    async def test_score_normalization_applied(self) -> None:
        """SourceRef.relevance is clamped to [0, 1]."""
        cid = uuid.uuid4()
        row = _make_row(cid)
        session = _make_session([row])
        enricher = SearchResultEnricher(session)

        hybrid = _hybrid_result(chunk_id=cid, score=0.5)
        results = await enricher.enrich([hybrid], USER_ID)

        assert 0.0 <= results[0].source_ref.relevance <= 1.0

    @pytest.mark.asyncio
    async def test_content_from_hybrid_result(self) -> None:
        cid = uuid.uuid4()
        row = _make_row(cid)
        session = _make_session([row])
        enricher = SearchResultEnricher(session)

        hybrid = _hybrid_result(chunk_id=cid, content="Original chunk text")
        results = await enricher.enrich([hybrid], USER_ID)

        assert results[0].content == "Original chunk text"
