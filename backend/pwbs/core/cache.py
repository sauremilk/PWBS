"""Application-level Redis caching utilities (TASK-146).

Provides a typed async cache layer on top of the Redis client for
API response caching, search result caching, and embedding caching.

Usage:
    from pwbs.core.cache import cache_get, cache_set, cache_invalidate

    result = await cache_get("search", owner_id, query_hash)
    if result is None:
        result = await expensive_search(...)
        await cache_set("search", owner_id, query_hash, result, ttl=300)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from pwbs.db.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Default TTL per cache namespace (seconds)
_DEFAULT_TTLS: dict[str, int] = {
    "search": 300,  # 5 min  search results
    "briefing": 900,  # 15 min  briefing responses
    "embedding": 3600,  # 1 h  embedding vectors
    "api": 60,  # 1 min  generic API responses
}


def _build_key(namespace: str, *parts: str) -> str:
    """Build a namespaced cache key.  ``pwbs:cache:{namespace}:{part1}:{part2}``."""
    sanitised = ":".join(str(p) for p in parts)
    return f"pwbs:cache:{namespace}:{sanitised}"


def make_hash(*values: str) -> str:
    """Deterministic SHA-256 hash for composite cache keys."""
    raw = "|".join(values)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def cache_get(namespace: str, *key_parts: str) -> Any | None:
    """Return deserialised cached value or *None* on miss / error."""
    try:
        redis = get_redis_client()
        raw = await redis.get(_build_key(namespace, *key_parts))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.debug("cache miss (error) for %s:%s", namespace, key_parts, exc_info=True)
        return None


async def cache_set(
    namespace: str,
    *key_parts: str,
    value: Any,
    ttl: int | None = None,
) -> None:
    """Serialise *value* to JSON and store with TTL."""
    effective_ttl = ttl if ttl is not None else _DEFAULT_TTLS.get(namespace, 60)
    try:
        redis = get_redis_client()
        await redis.setex(
            _build_key(namespace, *key_parts),
            effective_ttl,
            json.dumps(value, default=str),
        )
    except Exception:
        logger.warning("cache set failed for %s:%s", namespace, key_parts, exc_info=True)


async def cache_invalidate(namespace: str, *key_parts: str) -> None:
    """Delete a specific cache entry."""
    try:
        redis = get_redis_client()
        await redis.delete(_build_key(namespace, *key_parts))
    except Exception:
        logger.warning("cache invalidate failed for %s:%s", namespace, key_parts, exc_info=True)


async def cache_invalidate_namespace(namespace: str, owner_id: str) -> None:
    """Invalidate all cache entries for *owner_id* within *namespace*.

    Uses SCAN to avoid blocking Redis on large keyspaces.
    """
    pattern = _build_key(namespace, owner_id, "*")
    try:
        redis = get_redis_client()
        cursor: int | bytes = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.warning(
            "cache namespace invalidation failed for %s:%s",
            namespace,
            owner_id,
            exc_info=True,
        )
