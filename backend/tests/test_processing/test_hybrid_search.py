"""Tests for Hybrid Search with RRF Fusion (TASK-074)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from pwbs.search.hybrid import (
    HybridSearchConfig,
    HybridSearchResult,
    HybridSearchService,
)
from pwbs.search.keyword import KeywordSearchResult
from pwbs.search.service import SemanticSearchResult

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

USER_ID = uuid.uuid4()


def _sem_result(
    chunk_id: uuid.UUID | None = None,
    score: float = 0.9,
    content: str = "semantic content",
    title: str = "Sem Title",
    source_type: str = "notion",
) -> SemanticSearchResult:
    return SemanticSearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        content=content,
        title=title,
        source_type=source_type,
        created_at="2026-01-01T00:00:00Z",
        score=score,
        chunk_index=0,
    )


def _kw_result(
    chunk_id: uuid.UUID | None = None,
    score: float = 0.5,
    content_preview: str = "keyword content",
    title: str = "KW Title",
    source_type: str = "notion",
) -> KeywordSearchResult:
    return KeywordSearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=uuid.uuid4(),
        content_preview=content_preview,
        score=score,
        title=title,
        source_type=source_type,
    )


def _make_service(
    semantic_results: list[SemanticSearchResult] | None = None,
    keyword_results: list[KeywordSearchResult] | None = None,
    config: HybridSearchConfig | None = None,
) -> HybridSearchService:
    sem_svc = AsyncMock()
    sem_svc.search = AsyncMock(return_value=semantic_results or [])
    kw_svc = AsyncMock()
    kw_svc.search = AsyncMock(return_value=keyword_results or [])
    return HybridSearchService(
        semantic_service=sem_svc,
        keyword_service=kw_svc,
        config=config,
    )


# ------------------------------------------------------------------
# Basic behavior
# ------------------------------------------------------------------


class TestHybridSearchBasic:
    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self) -> None:
        svc = _make_service()
        result = await svc.search("", USER_ID)
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_empty(self) -> None:
        svc = _make_service()
        result = await svc.search("   ", USER_ID)
        assert result == []

    @pytest.mark.asyncio
    async def test_no_results_returns_empty(self) -> None:
        svc = _make_service(semantic_results=[], keyword_results=[])
        result = await svc.search("test query", USER_ID)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_hybrid_search_results(self) -> None:
        cid = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid)],
            keyword_results=[],
        )
        results = await svc.search("test", USER_ID)
        assert len(results) == 1
        assert isinstance(results[0], HybridSearchResult)
        assert results[0].chunk_id == cid

    @pytest.mark.asyncio
    async def test_default_config(self) -> None:
        svc = _make_service()
        assert svc.config.semantic_weight == 0.75
        assert svc.config.keyword_weight == 0.25
        assert svc.config.rrf_k == 60
        assert svc.config.default_top_k == 10
        assert svc.config.max_top_k == 50


# ------------------------------------------------------------------
# RRF Fusion Logic
# ------------------------------------------------------------------


class TestRRFFusion:
    @pytest.mark.asyncio
    async def test_rrf_score_formula_semantic_only(self) -> None:
        """A single semantic result at rank 1: score = 0.75 * 1/(60+1)."""
        cid = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid)],
            keyword_results=[],
        )
        results = await svc.search("test", USER_ID)
        expected = 0.75 * (1.0 / (60 + 1))
        assert len(results) == 1
        assert abs(results[0].score - expected) < 1e-10

    @pytest.mark.asyncio
    async def test_rrf_score_formula_keyword_only(self) -> None:
        """A single keyword result at rank 1: score = 0.25 * 1/(60+1)."""
        cid = uuid.uuid4()
        svc = _make_service(
            semantic_results=[],
            keyword_results=[_kw_result(chunk_id=cid)],
        )
        results = await svc.search("test", USER_ID)
        expected = 0.25 * (1.0 / (60 + 1))
        assert len(results) == 1
        assert abs(results[0].score - expected) < 1e-10

    @pytest.mark.asyncio
    async def test_rrf_score_formula_both_rank1(self) -> None:
        """Same chunk at rank 1 in both lists:
        score = 0.75 * 1/(60+1) + 0.25 * 1/(60+1)."""
        cid = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid)],
            keyword_results=[_kw_result(chunk_id=cid)],
        )
        results = await svc.search("test", USER_ID)
        expected = 0.75 * (1.0 / 61) + 0.25 * (1.0 / 61)
        assert len(results) == 1
        assert abs(results[0].score - expected) < 1e-10

    @pytest.mark.asyncio
    async def test_rrf_score_multiple_ranks(self) -> None:
        """Verify rank-based scoring: rank 1 scores higher than rank 2."""
        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()
        svc = _make_service(
            semantic_results=[
                _sem_result(chunk_id=cid1, score=0.95),
                _sem_result(chunk_id=cid2, score=0.80),
            ],
            keyword_results=[],
        )
        results = await svc.search("test", USER_ID)
        assert len(results) == 2
        assert results[0].score > results[1].score
        # Rank 1: 0.75/61, Rank 2: 0.75/62
        assert abs(results[0].score - 0.75 / 61) < 1e-10
        assert abs(results[1].score - 0.75 / 62) < 1e-10

    @pytest.mark.asyncio
    async def test_custom_rrf_k(self) -> None:
        """Custom k=10 changes scores."""
        cid = uuid.uuid4()
        config = HybridSearchConfig(rrf_k=10)
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid)],
            keyword_results=[],
            config=config,
        )
        results = await svc.search("test", USER_ID)
        expected = 0.75 * (1.0 / (10 + 1))
        assert abs(results[0].score - expected) < 1e-10


# ------------------------------------------------------------------
# Deduplication
# ------------------------------------------------------------------


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_duplicate_chunks_merged(self) -> None:
        """Same chunk_id in both lists -> single result with combined score."""
        cid = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid)],
            keyword_results=[_kw_result(chunk_id=cid)],
        )
        results = await svc.search("test", USER_ID)
        assert len(results) == 1
        assert results[0].chunk_id == cid
        # Should have data from both
        assert results[0].semantic_rank == 1
        assert results[0].keyword_rank == 1

    @pytest.mark.asyncio
    async def test_different_chunks_not_merged(self) -> None:
        """Different chunk IDs stay separate."""
        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid1)],
            keyword_results=[_kw_result(chunk_id=cid2)],
        )
        results = await svc.search("test", USER_ID)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_merged_chunk_has_both_scores(self) -> None:
        """Merged result should have both original scores."""
        cid = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid, score=0.9)],
            keyword_results=[_kw_result(chunk_id=cid, score=0.5)],
        )
        results = await svc.search("test", USER_ID)
        assert results[0].semantic_score == 0.9
        assert results[0].keyword_score == 0.5


# ------------------------------------------------------------------
# Weighting
# ------------------------------------------------------------------


class TestWeighting:
    @pytest.mark.asyncio
    async def test_default_weights(self) -> None:
        """Default weights: 0.75 semantic, 0.25 keyword."""
        cid_s = uuid.uuid4()
        cid_k = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid_s)],
            keyword_results=[_kw_result(chunk_id=cid_k)],
        )
        results = await svc.search("test", USER_ID)
        sem_result = next(r for r in results if r.chunk_id == cid_s)
        kw_result = next(r for r in results if r.chunk_id == cid_k)
        assert sem_result.score > kw_result.score

    @pytest.mark.asyncio
    async def test_equal_weights(self) -> None:
        """With equal weights, same rank -> same score."""
        cid_s = uuid.uuid4()
        cid_k = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid_s)],
            keyword_results=[_kw_result(chunk_id=cid_k)],
            config=HybridSearchConfig(semantic_weight=0.5, keyword_weight=0.5),
        )
        results = await svc.search("test", USER_ID)
        # Both at rank 1 with equal weights -> same RRF score
        assert abs(results[0].score - results[1].score) < 1e-10

    @pytest.mark.asyncio
    async def test_override_weights_per_query(self) -> None:
        """Override weights on a per-query basis."""
        cid_s = uuid.uuid4()
        cid_k = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid_s)],
            keyword_results=[_kw_result(chunk_id=cid_k)],
        )
        # Flip weights: keyword heavier
        results = await svc.search(
            "test",
            USER_ID,
            semantic_weight=0.25,
            keyword_weight=0.75,
        )
        sem_result = next(r for r in results if r.chunk_id == cid_s)
        kw_result_item = next(r for r in results if r.chunk_id == cid_k)
        assert kw_result_item.score > sem_result.score

    @pytest.mark.asyncio
    async def test_zero_semantic_weight(self) -> None:
        """Zero semantic weight -> only keyword results contribute."""
        cid_s = uuid.uuid4()
        cid_k = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid_s)],
            keyword_results=[_kw_result(chunk_id=cid_k)],
            config=HybridSearchConfig(semantic_weight=0.0, keyword_weight=1.0),
        )
        results = await svc.search("test", USER_ID)
        sem_result = next(r for r in results if r.chunk_id == cid_s)
        assert sem_result.score == 0.0

    @pytest.mark.asyncio
    async def test_zero_keyword_weight(self) -> None:
        """Zero keyword weight -> only semantic results contribute."""
        cid_s = uuid.uuid4()
        cid_k = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid_s)],
            keyword_results=[_kw_result(chunk_id=cid_k)],
            config=HybridSearchConfig(semantic_weight=1.0, keyword_weight=0.0),
        )
        results = await svc.search("test", USER_ID)
        kw_res = next(r for r in results if r.chunk_id == cid_k)
        assert kw_res.score == 0.0


# ------------------------------------------------------------------
# Top-K and ranking
# ------------------------------------------------------------------


class TestTopKAndRanking:
    @pytest.mark.asyncio
    async def test_top_k_limits_results(self) -> None:
        """top_k should limit final results."""
        cids = [uuid.uuid4() for _ in range(5)]
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=c) for c in cids],
            keyword_results=[],
        )
        results = await svc.search("test", USER_ID, top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_max_top_k_respected(self) -> None:
        """top_k cannot exceed max_top_k."""
        cids = [uuid.uuid4() for _ in range(5)]
        config = HybridSearchConfig(max_top_k=3)
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=c) for c in cids],
            keyword_results=[],
            config=config,
        )
        results = await svc.search("test", USER_ID, top_k=100)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_results_sorted_by_score_descending(self) -> None:
        """Results must be sorted by score descending."""
        cids = [uuid.uuid4() for _ in range(5)]
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=c) for c in cids],
            keyword_results=[],
        )
        results = await svc.search("test", USER_ID)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


# ------------------------------------------------------------------
# User isolation
# ------------------------------------------------------------------


class TestUserIsolation:
    @pytest.mark.asyncio
    async def test_user_id_passed_to_both_services(self) -> None:
        """user_id must be forwarded to both sub-services."""
        sem_svc = AsyncMock()
        sem_svc.search = AsyncMock(return_value=[])
        kw_svc = AsyncMock()
        kw_svc.search = AsyncMock(return_value=[])
        svc = HybridSearchService(sem_svc, kw_svc)

        uid = uuid.uuid4()
        await svc.search("test query", uid)

        sem_svc.search.assert_called_once()
        kw_svc.search.assert_called_once()
        # Verify user_id passed
        assert (
            sem_svc.search.call_args.kwargs.get("user_id") == uid
            or sem_svc.search.call_args[1].get("user_id") == uid
            or (len(sem_svc.search.call_args[0]) > 1 and sem_svc.search.call_args[0][1] == uid)
        )
        assert (
            kw_svc.search.call_args.kwargs.get("user_id") == uid
            or kw_svc.search.call_args[1].get("user_id") == uid
            or (len(kw_svc.search.call_args[0]) > 1 and kw_svc.search.call_args[0][1] == uid)
        )


# ------------------------------------------------------------------
# Candidate multiplier
# ------------------------------------------------------------------


class TestCandidateMultiplier:
    @pytest.mark.asyncio
    async def test_candidate_multiplier_increases_fetch(self) -> None:
        """Candidate multiplier asks for more from sub-services."""
        sem_svc = AsyncMock()
        sem_svc.search = AsyncMock(return_value=[])
        kw_svc = AsyncMock()
        kw_svc.search = AsyncMock(return_value=[])
        config = HybridSearchConfig(candidate_multiplier=3.0, default_top_k=10)
        svc = HybridSearchService(sem_svc, kw_svc, config)

        await svc.search("test", USER_ID)

        # candidate_k = min(10 * 3.0, 50) = 30
        sem_call = sem_svc.search.call_args
        assert sem_call.kwargs.get("top_k") == 30 or (len(sem_call[0]) > 2 and sem_call[0][2] == 30)

    @pytest.mark.asyncio
    async def test_candidate_multiplier_capped_at_max(self) -> None:
        """Candidate k should not exceed max_top_k."""
        sem_svc = AsyncMock()
        sem_svc.search = AsyncMock(return_value=[])
        kw_svc = AsyncMock()
        kw_svc.search = AsyncMock(return_value=[])
        config = HybridSearchConfig(
            candidate_multiplier=10.0,
            default_top_k=10,
            max_top_k=50,
        )
        svc = HybridSearchService(sem_svc, kw_svc, config)

        await svc.search("test", USER_ID)

        sem_call = sem_svc.search.call_args
        fetched_k = sem_call.kwargs.get("top_k")
        assert fetched_k is not None
        assert fetched_k <= 50


# ------------------------------------------------------------------
# Result metadata
# ------------------------------------------------------------------


class TestResultMetadata:
    @pytest.mark.asyncio
    async def test_semantic_only_result_metadata(self) -> None:
        """Semantic-only result has None keyword fields."""
        cid = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid, score=0.95, title="My Title")],
            keyword_results=[],
        )
        results = await svc.search("test", USER_ID)
        r = results[0]
        assert r.semantic_score == 0.95
        assert r.semantic_rank == 1
        assert r.keyword_score is None
        assert r.keyword_rank is None
        assert r.title == "My Title"

    @pytest.mark.asyncio
    async def test_keyword_only_result_metadata(self) -> None:
        """Keyword-only result has None semantic fields."""
        cid = uuid.uuid4()
        svc = _make_service(
            semantic_results=[],
            keyword_results=[_kw_result(chunk_id=cid, score=0.6, title="KW Doc")],
        )
        results = await svc.search("test", USER_ID)
        r = results[0]
        assert r.keyword_score == 0.6
        assert r.keyword_rank == 1
        assert r.semantic_score is None
        assert r.semantic_rank is None
        assert r.title == "KW Doc"

    @pytest.mark.asyncio
    async def test_source_type_preserved(self) -> None:
        """Source type from original results is preserved."""
        cid = uuid.uuid4()
        svc = _make_service(
            semantic_results=[_sem_result(chunk_id=cid, source_type="google_calendar")],
            keyword_results=[],
        )
        results = await svc.search("test", USER_ID)
        assert results[0].source_type == "google_calendar"
