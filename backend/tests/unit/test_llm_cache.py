"""Tests for LLM Response Cache (TASK-187).

All Redis calls are mocked – no real network access.
"""

from __future__ import annotations

import json
import math
import time
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from pwbs.services.llm_cache import (
    DEFAULT_TTLS,
    LLM_CACHE_REQUESTS,
    SIMILARITY_THRESHOLD,
    CachedLLMResponse,
    CacheResult,
    _cosine_similarity,
    _embedding_hash,
    _filter_hash,
    _scope_key,
    llm_cache_get,
    llm_cache_invalidate_owner,
    llm_cache_invalidate_type,
    llm_cache_set,
)

OWNER = UUID("00000000-0000-0000-0000-000000000001")
EMB = [0.1, 0.2, 0.3, 0.4, 0.5]
# An embedding very close to EMB (should exceed 0.95 similarity)
EMB_SIMILAR = [0.1001, 0.2001, 0.3001, 0.4001, 0.5001]
# A completely different embedding
EMB_DIFFERENT = [-0.5, 0.0, 0.5, -0.3, 0.8]


def _make_entry(embedding: list[float] | None = None) -> str:
    """Create a JSON cache entry for mocking."""
    return json.dumps(
        {
            "content": "cached answer",
            "provider": "claude",
            "model": "claude-sonnet-4-20250514",
            "embedding": embedding or EMB,
            "created_at": time.time(),
            "metadata": {"source": "test"},
        }
    )


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        assert _cosine_similarity(EMB, EMB) == pytest.approx(1.0)

    def test_similar_vectors_above_threshold(self) -> None:
        sim = _cosine_similarity(EMB, EMB_SIMILAR)
        assert sim >= SIMILARITY_THRESHOLD

    def test_different_vectors_below_threshold(self) -> None:
        sim = _cosine_similarity(EMB, EMB_DIFFERENT)
        assert sim < SIMILARITY_THRESHOLD

    def test_zero_vector(self) -> None:
        assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_empty_vectors(self) -> None:
        assert _cosine_similarity([], []) == 0.0

    def test_mismatched_lengths(self) -> None:
        assert _cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_orthogonal_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_filter_hash_none(self) -> None:
        assert _filter_hash(None) == "nf"

    def test_filter_hash_empty(self) -> None:
        assert _filter_hash({}) == "nf"

    def test_filter_hash_deterministic(self) -> None:
        h1 = _filter_hash({"a": 1, "b": 2})
        h2 = _filter_hash({"b": 2, "a": 1})
        assert h1 == h2

    def test_filter_hash_different(self) -> None:
        assert _filter_hash({"a": 1}) != _filter_hash({"a": 2})

    def test_embedding_hash_deterministic(self) -> None:
        assert _embedding_hash(EMB) == _embedding_hash(EMB)

    def test_embedding_hash_different(self) -> None:
        assert _embedding_hash(EMB) != _embedding_hash(EMB_DIFFERENT)

    def test_scope_key(self) -> None:
        key = _scope_key("uid1", "search")
        assert key == "pwbs:llm_cache:uid1:search"


# ---------------------------------------------------------------------------
# llm_cache_get – fast path (exact hash match)
# ---------------------------------------------------------------------------


class TestLlmCacheGetFastPath:
    @pytest.mark.asyncio
    async def test_exact_hit(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = _make_entry()

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            result = await llm_cache_get(OWNER, EMB, "search")

        assert result.hit is True
        assert result.similarity == 1.0
        assert result.response is not None
        assert result.response.content == "cached answer"
        assert result.response.provider == "claude"
        assert result.response.query_type == "search"

    @pytest.mark.asyncio
    async def test_miss_no_index(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.lrange.return_value = []

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            result = await llm_cache_get(OWNER, EMB, "search")

        assert result.hit is False
        assert result.response is None


# ---------------------------------------------------------------------------
# llm_cache_get – slow path (semantic scan)
# ---------------------------------------------------------------------------


class TestLlmCacheGetSlowPath:
    @pytest.mark.asyncio
    async def test_semantic_hit(self) -> None:
        """Similar embedding (>= 0.95) should return cached entry."""
        mock_redis = AsyncMock()
        eh = _embedding_hash(EMB)

        # exact-hash misses
        mock_redis.get.side_effect = [None, _make_entry(EMB)]
        mock_redis.lrange.return_value = [eh]

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            result = await llm_cache_get(OWNER, EMB_SIMILAR, "search")

        assert result.hit is True
        assert result.similarity >= SIMILARITY_THRESHOLD

    @pytest.mark.asyncio
    async def test_semantic_miss_different_embedding(self) -> None:
        """Very different embedding should not match."""
        mock_redis = AsyncMock()
        eh = _embedding_hash(EMB)

        mock_redis.get.side_effect = [None, _make_entry(EMB)]
        mock_redis.lrange.return_value = [eh]

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            result = await llm_cache_get(OWNER, EMB_DIFFERENT, "search")

        assert result.hit is False

    @pytest.mark.asyncio
    async def test_expired_entries_skipped(self) -> None:
        """Entries whose keys have expired (None) are skipped."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = [None, None]  # exact miss, entry expired
        mock_redis.lrange.return_value = ["stale_hash"]

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            result = await llm_cache_get(OWNER, EMB, "search")

        assert result.hit is False


# ---------------------------------------------------------------------------
# llm_cache_get – error handling
# ---------------------------------------------------------------------------


class TestLlmCacheGetErrors:
    @pytest.mark.asyncio
    async def test_redis_error_returns_miss(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            result = await llm_cache_get(OWNER, EMB, "search")

        assert result.hit is False


# ---------------------------------------------------------------------------
# llm_cache_set
# ---------------------------------------------------------------------------


class TestLlmCacheSet:
    @pytest.mark.asyncio
    async def test_stores_entry(self) -> None:
        mock_redis = AsyncMock()
        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            await llm_cache_set(
                OWNER,
                EMB,
                "answer",
                "claude",
                "claude-sonnet-4-20250514",
                "search",
            )

        assert mock_redis.setex.await_count == 1
        assert mock_redis.lpush.await_count == 1
        assert mock_redis.ltrim.await_count == 1
        assert mock_redis.expire.await_count == 1

    @pytest.mark.asyncio
    async def test_default_ttl_search(self) -> None:
        mock_redis = AsyncMock()
        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            await llm_cache_set(
                OWNER,
                EMB,
                "answer",
                "claude",
                "model",
                "search",
            )

        ttl_used = mock_redis.setex.call_args[0][1]
        assert ttl_used == DEFAULT_TTLS["search"]

    @pytest.mark.asyncio
    async def test_default_ttl_briefing(self) -> None:
        mock_redis = AsyncMock()
        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            await llm_cache_set(
                OWNER,
                EMB,
                "answer",
                "claude",
                "model",
                "briefing",
            )

        ttl_used = mock_redis.setex.call_args[0][1]
        assert ttl_used == DEFAULT_TTLS["briefing"]

    @pytest.mark.asyncio
    async def test_custom_ttl(self) -> None:
        mock_redis = AsyncMock()
        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            await llm_cache_set(
                OWNER,
                EMB,
                "answer",
                "claude",
                "model",
                "search",
                ttl=42,
            )

        ttl_used = mock_redis.setex.call_args[0][1]
        assert ttl_used == 42

    @pytest.mark.asyncio
    async def test_with_filters(self) -> None:
        mock_redis = AsyncMock()
        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            await llm_cache_set(
                OWNER,
                EMB,
                "answer",
                "claude",
                "model",
                filters={"source": "notion"},
            )

        key = mock_redis.setex.call_args[0][0]
        assert "nf" not in key  # filter hash is NOT "nf"

    @pytest.mark.asyncio
    async def test_error_does_not_raise(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = ConnectionError("Redis down")
        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            await llm_cache_set(OWNER, EMB, "x", "c", "m")


# ---------------------------------------------------------------------------
# llm_cache_invalidate_owner
# ---------------------------------------------------------------------------


class TestLlmCacheInvalidateOwner:
    @pytest.mark.asyncio
    async def test_scans_and_deletes(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = [
            (42, [b"pwbs:llm_cache:uid:search:k1"]),
            (0, []),
        ]
        mock_redis.delete.return_value = 1

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            deleted = await llm_cache_invalidate_owner(OWNER)

        assert deleted == 1
        assert mock_redis.scan.await_count == 2

    @pytest.mark.asyncio
    async def test_no_keys(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.return_value = (0, [])

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            deleted = await llm_cache_invalidate_owner(OWNER)

        assert deleted == 0
        mock_redis.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_error_returns_zero(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = ConnectionError("Redis down")

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            deleted = await llm_cache_invalidate_owner(OWNER)

        assert deleted == 0


# ---------------------------------------------------------------------------
# llm_cache_invalidate_type
# ---------------------------------------------------------------------------


class TestLlmCacheInvalidateType:
    @pytest.mark.asyncio
    async def test_scans_correct_pattern(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.return_value = (0, [])

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            await llm_cache_invalidate_type(OWNER, "briefing")

        pattern = mock_redis.scan.call_args[1]["match"]
        assert "briefing" in pattern
        assert str(OWNER) in pattern

    @pytest.mark.asyncio
    async def test_error_returns_zero(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = ConnectionError("Redis down")

        with patch("pwbs.services.llm_cache.get_redis_client", return_value=mock_redis):
            deleted = await llm_cache_invalidate_type(OWNER, "search")

        assert deleted == 0


# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------


class TestPrometheusMetrics:
    def test_counter_registered(self) -> None:
        from prometheus_client import REGISTRY

        sample = REGISTRY.get_sample_value(
            "pwbs_llm_cache_requests_total",
            {"query_type": "search", "result": "hit"},
        )
        # Counter exists (may be 0 or >0 depending on test order)
        assert sample is not None or sample == 0.0

    def test_no_owner_id_in_labels(self) -> None:
        """DSGVO: owner_id must never appear as a Prometheus label."""
        from prometheus_client import REGISTRY

        for metric in REGISTRY.collect():
            for sample in metric.samples:
                if "llm_cache" in sample.name:
                    assert "owner_id" not in sample.labels
