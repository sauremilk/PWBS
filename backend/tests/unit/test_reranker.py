"""Tests for SearchReranker and recency boost (TASK-201)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from pwbs.search.hybrid import HybridSearchResult
from pwbs.search.reranker import (
    RerankerConfig,
    SearchReranker,
    _recency_factor,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

_NOW = datetime(2026, 3, 20, 12, 0, 0, tzinfo=UTC)


def _make_result(
    *,
    chunk_id: uuid.UUID | None = None,
    score: float = 0.01,
    semantic_score: float | None = 0.85,
    keyword_score: float | None = None,
    semantic_rank: int | None = 1,
    keyword_rank: int | None = None,
    created_at: str | None = None,
    title: str = "Test",
) -> HybridSearchResult:
    return HybridSearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        content="content",
        title=title,
        source_type="notion",
        score=score,
        semantic_score=semantic_score,
        keyword_score=keyword_score,
        semantic_rank=semantic_rank,
        keyword_rank=keyword_rank,
        created_at=created_at,
    )


# ------------------------------------------------------------------
# _recency_factor
# ------------------------------------------------------------------


class TestRecencyFactor:
    def test_none_created_at(self) -> None:
        assert _recency_factor(None, _NOW, 7) == 0.0

    def test_invalid_date(self) -> None:
        assert _recency_factor("not-a-date", _NOW, 7) == 0.0

    def test_zero_boost_days(self) -> None:
        assert _recency_factor(_NOW.isoformat(), _NOW, 0) == 0.0

    def test_brand_new_document(self) -> None:
        """Document created right now should have factor near 1.0."""
        factor = _recency_factor(_NOW.isoformat(), _NOW, 7)
        assert factor > 0.9

    def test_at_boost_days(self) -> None:
        """Document exactly boost_days old should have factor near 0.5."""
        old = (_NOW - timedelta(days=7)).isoformat()
        factor = _recency_factor(old, _NOW, 7)
        assert 0.45 < factor < 0.55

    def test_very_old_document(self) -> None:
        """Document 30 days old with 7-day boost should be near 0."""
        old = (_NOW - timedelta(days=30)).isoformat()
        factor = _recency_factor(old, _NOW, 7)
        assert factor < 0.01

    def test_future_document(self) -> None:
        """Future timestamps are clamped to 1.0."""
        future = (_NOW + timedelta(days=1)).isoformat()
        factor = _recency_factor(future, _NOW, 7)
        assert factor == 1.0

    def test_naive_datetime(self) -> None:
        """Naive datetime strings are treated as UTC."""
        naive = datetime(2026, 3, 20, 11, 0, 0).isoformat()
        factor = _recency_factor(naive, _NOW, 7)
        assert factor > 0.9


# ------------------------------------------------------------------
# SearchReranker.rerank()
# ------------------------------------------------------------------


class TestRerankerBasic:
    def test_empty_results(self) -> None:
        reranker = SearchReranker()
        assert reranker.rerank([], top_k=10) == []

    def test_single_result(self) -> None:
        reranker = SearchReranker()
        r = _make_result()
        results = reranker.rerank([r], top_k=10, now=_NOW)
        assert len(results) == 1

    def test_top_k_limits_output(self) -> None:
        reranker = SearchReranker()
        results = [_make_result(score=0.01 * (i + 1)) for i in range(20)]
        reranked = reranker.rerank(results, top_k=5, now=_NOW)
        assert len(reranked) == 5


class TestRerankerCosineWeight:
    def test_high_semantic_score_wins(self) -> None:
        """Result with higher semantic_score should rank higher."""
        reranker = SearchReranker(
            config=RerankerConfig(
                cosine_weight=0.9,
                rrf_weight=0.1,
                recency_boost_pct=0.0,
            )
        )
        low = _make_result(score=0.02, semantic_score=0.5)
        high = _make_result(score=0.01, semantic_score=0.95)
        reranked = reranker.rerank([low, high], top_k=2, now=_NOW)
        assert reranked[0].semantic_score == 0.95

    def test_no_semantic_score_handled(self) -> None:
        """Results without semantic_score (keyword-only) get 0.0 cosine."""
        reranker = SearchReranker()
        r = _make_result(semantic_score=None)
        results = reranker.rerank([r], top_k=10, now=_NOW)
        assert len(results) == 1


class TestRerankerRecencyBoost:
    def test_recent_doc_boosted(self) -> None:
        """Recent document should outrank older one with same base score."""
        reranker = SearchReranker(
            config=RerankerConfig(
                cosine_weight=0.5,
                rrf_weight=0.5,
                recency_boost_pct=0.20,
                recency_boost_days=7,
            )
        )
        old_time = (_NOW - timedelta(days=30)).isoformat()
        new_time = _NOW.isoformat()

        old_doc = _make_result(
            score=0.02,
            semantic_score=0.80,
            created_at=old_time,
        )
        new_doc = _make_result(
            score=0.02,
            semantic_score=0.80,
            created_at=new_time,
        )
        reranked = reranker.rerank([old_doc, new_doc], top_k=2, now=_NOW)
        assert reranked[0].created_at == new_time

    def test_no_recency_boost(self) -> None:
        """With recency_boost_pct=0, order depends only on base scores."""
        reranker = SearchReranker(
            config=RerankerConfig(
                recency_boost_pct=0.0,
            )
        )
        old_time = (_NOW - timedelta(days=30)).isoformat()
        new_time = _NOW.isoformat()

        old_doc = _make_result(
            score=0.02,
            semantic_score=0.95,
            created_at=old_time,
        )
        new_doc = _make_result(
            score=0.02,
            semantic_score=0.80,
            created_at=new_time,
        )
        reranked = reranker.rerank([old_doc, new_doc], top_k=2, now=_NOW)
        # Higher semantic score wins when no recency boost
        assert reranked[0].semantic_score == 0.95


class TestRerankerScoreUpdate:
    def test_score_field_updated(self) -> None:
        """The output score field reflects the rerank composite score."""
        reranker = SearchReranker()
        r = _make_result(score=0.012, semantic_score=0.85)
        reranked = reranker.rerank([r], top_k=10, now=_NOW)
        # Score should be the composite, not the original RRF score
        assert reranked[0].score != r.score
        assert reranked[0].score > 0

    def test_scores_descending(self) -> None:
        """Output should be sorted by score descending."""
        reranker = SearchReranker()
        results = [
            _make_result(score=0.01 * (i + 1), semantic_score=0.5 + i * 0.05) for i in range(10)
        ]
        reranked = reranker.rerank(results, top_k=10, now=_NOW)
        scores = [r.score for r in reranked]
        assert scores == sorted(scores, reverse=True)


class TestRerankerConfig:
    def test_default_config(self) -> None:
        reranker = SearchReranker()
        assert reranker.config.cosine_weight == 0.6
        assert reranker.config.rrf_weight == 0.3
        assert reranker.config.recency_boost_pct == 0.10
        assert reranker.config.recency_boost_days == 7

    def test_custom_config(self) -> None:
        cfg = RerankerConfig(
            cosine_weight=0.8,
            rrf_weight=0.2,
            recency_boost_pct=0.15,
            recency_boost_days=14,
        )
        reranker = SearchReranker(config=cfg)
        assert reranker.config.cosine_weight == 0.8
        assert reranker.config.recency_boost_days == 14


class TestRerankerPreservesMetadata:
    def test_metadata_preserved(self) -> None:
        """Reranking should preserve chunk_id, content, title etc."""
        reranker = SearchReranker()
        cid = uuid.uuid4()
        r = _make_result(
            chunk_id=cid,
            title="Important",
            created_at=_NOW.isoformat(),
        )
        reranked = reranker.rerank([r], top_k=10, now=_NOW)
        assert reranked[0].chunk_id == cid
        assert reranked[0].title == "Important"
        assert reranked[0].source_type == "notion"
        assert reranked[0].created_at == _NOW.isoformat()


# ------------------------------------------------------------------
# ENV config integration (SEARCH_SEMANTIC_WEIGHT etc.)
# ------------------------------------------------------------------


class TestSearchConfigEnvVars:
    def test_settings_have_search_fields(self) -> None:
        """Verify Settings class has the TASK-201 search tuning fields."""
        from unittest.mock import patch

        from pwbs.core.config import Settings

        env = {
            "JWT_SECRET_KEY": "test-key",
            "ENCRYPTION_MASTER_KEY": "test-master",
            "SEARCH_SEMANTIC_WEIGHT": "0.80",
            "SEARCH_KEYWORD_WEIGHT": "0.20",
            "SEARCH_RECENCY_BOOST_PCT": "0.15",
            "SEARCH_RECENCY_BOOST_DAYS": "14",
        }
        with patch.dict("os.environ", env, clear=False):
            s = Settings()  # type: ignore[call-arg]
            assert s.search_semantic_weight == 0.80
            assert s.search_keyword_weight == 0.20
            assert s.search_recency_boost_pct == 0.15
            assert s.search_recency_boost_days == 14

    def test_settings_defaults(self) -> None:
        from unittest.mock import patch

        from pwbs.core.config import Settings

        env = {
            "JWT_SECRET_KEY": "test-key",
            "ENCRYPTION_MASTER_KEY": "test-master",
        }
        with patch.dict("os.environ", env, clear=False):
            s = Settings()  # type: ignore[call-arg]
            assert s.search_semantic_weight == 0.75
            assert s.search_keyword_weight == 0.25
            assert s.search_recency_boost_pct == 0.10
            assert s.search_recency_boost_days == 7
