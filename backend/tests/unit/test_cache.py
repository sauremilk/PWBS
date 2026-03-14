"""Tests for Redis cache utilities (TASK-109).

Tests cache_get, cache_set, cache_invalidate, cache_invalidate_namespace,
_build_key, and make_hash.  All Redis calls are mocked.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from pwbs.core.cache import (
    _build_key,
    cache_get,
    cache_invalidate,
    cache_invalidate_namespace,
    cache_set,
    make_hash,
)  # fmt: skip

# ---------------------------------------------------------------------------
# _build_key
# ---------------------------------------------------------------------------


class TestBuildKey:
    def test_single_part(self) -> None:
        assert _build_key("search", "abc") == "pwbs:cache:search:abc"

    def test_multiple_parts(self) -> None:
        assert _build_key("search", "uid1", "hash2") == "pwbs:cache:search:uid1:hash2"

    def test_empty_namespace(self) -> None:
        assert _build_key("", "x") == "pwbs:cache::x"


# ---------------------------------------------------------------------------
# make_hash
# ---------------------------------------------------------------------------


class TestMakeHash:
    def test_deterministic(self) -> None:
        h1 = make_hash("a", "b")
        h2 = make_hash("a", "b")
        assert h1 == h2

    def test_different_inputs(self) -> None:
        assert make_hash("a") != make_hash("b")

    def test_returns_16_chars(self) -> None:
        assert len(make_hash("test")) == 16


# ---------------------------------------------------------------------------
# cache_get
# ---------------------------------------------------------------------------


class TestCacheGet:
    @pytest.mark.asyncio
    async def test_hit(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({"key": "value"})
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            result = await cache_get("search", "uid", "qhash")
        assert result == {"key": "value"}
        mock_redis.get.assert_awaited_once_with("pwbs:cache:search:uid:qhash")

    @pytest.mark.asyncio
    async def test_miss(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            result = await cache_get("search", "uid", "qhash")
        assert result is None

    @pytest.mark.asyncio
    async def test_error_returns_none(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            result = await cache_get("search", "uid", "qhash")
        assert result is None


# ---------------------------------------------------------------------------
# cache_set
# ---------------------------------------------------------------------------


class TestCacheSet:
    @pytest.mark.asyncio
    async def test_stores_json(self) -> None:
        mock_redis = AsyncMock()
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            await cache_set("search", "uid", "qhash", value={"a": 1}, ttl=120)
        mock_redis.setex.assert_awaited_once_with(
            "pwbs:cache:search:uid:qhash",
            120,
            json.dumps({"a": 1}, default=str),
        )

    @pytest.mark.asyncio
    async def test_uses_default_ttl(self) -> None:
        mock_redis = AsyncMock()
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            await cache_set("search", "uid", value=42)
        # Default TTL for "search" is 300
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 300

    @pytest.mark.asyncio
    async def test_unknown_namespace_default_ttl(self) -> None:
        mock_redis = AsyncMock()
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            await cache_set("unknown", "k", value="v")
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 60  # fallback default

    @pytest.mark.asyncio
    async def test_error_does_not_raise(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = ConnectionError("Redis down")
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            # Should not raise
            await cache_set("search", "uid", value="x")


# ---------------------------------------------------------------------------
# cache_invalidate
# ---------------------------------------------------------------------------


class TestCacheInvalidate:
    @pytest.mark.asyncio
    async def test_deletes_key(self) -> None:
        mock_redis = AsyncMock()
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            await cache_invalidate("search", "uid", "qhash")
        mock_redis.delete.assert_awaited_once_with("pwbs:cache:search:uid:qhash")

    @pytest.mark.asyncio
    async def test_error_does_not_raise(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = ConnectionError("Redis down")
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            await cache_invalidate("search", "uid")


# ---------------------------------------------------------------------------
# cache_invalidate_namespace
# ---------------------------------------------------------------------------


class TestCacheInvalidateNamespace:
    @pytest.mark.asyncio
    async def test_scans_and_deletes(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = [
            (42, [b"pwbs:cache:search:uid:k1", b"pwbs:cache:search:uid:k2"]),
            (0, []),
        ]
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            await cache_invalidate_namespace("search", "uid")
        assert mock_redis.scan.await_count == 2
        mock_redis.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_keys_found(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.return_value = (0, [])
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            await cache_invalidate_namespace("search", "uid")
        mock_redis.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_error_does_not_raise(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = ConnectionError("Redis down")
        with patch("pwbs.core.cache.get_redis_client", return_value=mock_redis):
            await cache_invalidate_namespace("search", "uid")
