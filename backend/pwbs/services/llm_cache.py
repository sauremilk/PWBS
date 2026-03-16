"""LLM Response Cache with semantic matching (TASK-187).

Redis-backed cache for LLM responses.  Similar queries (cosine similarity
>= 0.95) return the cached answer.  TTL is configurable per query type
(``search`` vs ``briefing``).  Owner-scoped invalidation ensures fresh
results after new document ingestion.

Usage::

    from pwbs.services.llm_cache import llm_cache_get, llm_cache_set

    result = await llm_cache_get(owner_id, embedding, "search", filters)
    if result.hit:
        return result.response
    # … call LLM …
    await llm_cache_set(owner_id, embedding, content, provider, model, "search")
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from prometheus_client import Counter

from pwbs.db.redis_client import get_redis_client

logger = logging.getLogger(__name__)

__all__ = [
    "CacheResult",
    "CachedLLMResponse",
    "LLM_CACHE_REQUESTS",
    "SIMILARITY_THRESHOLD",
    "llm_cache_get",
    "llm_cache_invalidate_owner",
    "llm_cache_invalidate_type",
    "llm_cache_set",
]

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

LLM_CACHE_REQUESTS = Counter(
    "pwbs_llm_cache_requests_total",
    "Total LLM cache lookups (compute hit ratio via result label)",
    ["query_type", "result"],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_TTLS: dict[str, int] = {
    "search": 600,  # 10 min
    "briefing": 3600,  # 1 hour
    "extraction": 86400,  # 24 hours
}

_MAX_ENTRIES_PER_SCOPE = 100

SIMILARITY_THRESHOLD = 0.95


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CachedLLMResponse:
    """A cached LLM response entry."""

    content: str
    provider: str
    model: str
    query_type: str
    created_at: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CacheResult:
    """Result of a cache lookup."""

    hit: bool
    response: CachedLLMResponse | None = None
    similarity: float = 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _filter_hash(filters: dict[str, Any] | None) -> str:
    if not filters:
        return "nf"
    raw = json.dumps(filters, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _embedding_hash(embedding: list[float]) -> str:
    """Short hash of a quantised embedding for exact-match fast path."""
    quantized = ",".join(f"{v:.4f}" for v in embedding)
    return hashlib.sha256(quantized.encode()).hexdigest()[:16]


def _scope_key(owner_id: str, query_type: str) -> str:
    return f"pwbs:llm_cache:{owner_id}:{query_type}"


def _deserialise_entry(raw: str, query_type: str) -> CachedLLMResponse:
    entry = json.loads(raw)
    return CachedLLMResponse(
        content=entry["content"],
        provider=entry["provider"],
        model=entry["model"],
        query_type=query_type,
        created_at=entry["created_at"],
        metadata=entry.get("metadata", {}),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def llm_cache_get(
    owner_id: UUID,
    embedding: list[float],
    query_type: str = "search",
    filters: dict[str, Any] | None = None,
) -> CacheResult:
    """Look up a cached LLM response by semantic similarity.

    Fast path: exact embedding-hash match (< 5 ms).
    Slow path: cosine-similarity scan over recent entries.

    Args:
        owner_id: User ID (tenant isolation).
        embedding: Query embedding vector.
        query_type: ``"search"`` | ``"briefing"`` | ``"extraction"``.
        filters: Optional filter dict for scoping.

    Returns:
        :class:`CacheResult` – ``hit=True`` when a match was found.
    """
    try:
        redis = get_redis_client()
        scope = _scope_key(str(owner_id), query_type)
        fh = _filter_hash(filters)
        eh = _embedding_hash(embedding)

        # --- fast path: exact hash ----------------------------------------
        exact_key = f"{scope}:{fh}:{eh}"
        raw = await redis.get(exact_key)
        if raw is not None:
            LLM_CACHE_REQUESTS.labels(query_type=query_type, result="hit").inc()
            return CacheResult(
                hit=True,
                response=_deserialise_entry(raw, query_type),
                similarity=1.0,
            )

        # --- slow path: semantic scan -------------------------------------
        index_key = f"{scope}:{fh}:index"
        entry_ids: list[str] = await redis.lrange(index_key, 0, _MAX_ENTRIES_PER_SCOPE - 1)

        for entry_id in entry_ids:
            entry_key = f"{scope}:{fh}:{entry_id}"
            raw = await redis.get(entry_key)
            if raw is None:
                continue
            entry = json.loads(raw)
            stored_emb = entry.get("embedding")
            if not stored_emb:
                continue
            sim = _cosine_similarity(embedding, stored_emb)
            if sim >= SIMILARITY_THRESHOLD:
                LLM_CACHE_REQUESTS.labels(query_type=query_type, result="hit").inc()
                return CacheResult(
                    hit=True,
                    response=_deserialise_entry(raw, query_type),
                    similarity=sim,
                )

        LLM_CACHE_REQUESTS.labels(query_type=query_type, result="miss").inc()
        return CacheResult(hit=False)

    except Exception:
        logger.debug("llm_cache_get error", exc_info=True)
        LLM_CACHE_REQUESTS.labels(query_type=query_type, result="miss").inc()
        return CacheResult(hit=False)


async def llm_cache_set(
    owner_id: UUID,
    embedding: list[float],
    content: str,
    provider: str,
    model: str,
    query_type: str = "search",
    filters: dict[str, Any] | None = None,
    ttl: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Store an LLM response in the semantic cache.

    The entry is keyed both by an exact embedding hash (fast path) and
    added to a per-scope index list for cosine-similarity lookups.
    """
    effective_ttl = ttl if ttl is not None else DEFAULT_TTLS.get(query_type, 600)
    try:
        redis = get_redis_client()
        scope = _scope_key(str(owner_id), query_type)
        fh = _filter_hash(filters)
        eh = _embedding_hash(embedding)

        entry = {
            "content": content,
            "provider": provider,
            "model": model,
            "embedding": embedding,
            "created_at": time.time(),
            "metadata": metadata or {},
        }
        payload = json.dumps(entry, default=str)

        # Store with exact-hash key
        exact_key = f"{scope}:{fh}:{eh}"
        await redis.setex(exact_key, effective_ttl, payload)

        # Maintain index list for semantic scanning
        index_key = f"{scope}:{fh}:index"
        await redis.lpush(index_key, eh)
        await redis.ltrim(index_key, 0, _MAX_ENTRIES_PER_SCOPE - 1)
        await redis.expire(index_key, effective_ttl)

    except Exception:
        logger.warning("llm_cache_set failed", exc_info=True)


async def llm_cache_invalidate_owner(owner_id: UUID) -> int:
    """Invalidate **all** LLM cache entries for *owner_id*.

    Called when new documents are ingested so the next query gets fresh
    results.  Uses ``SCAN`` to avoid blocking Redis.

    Returns:
        Number of keys deleted.
    """
    pattern = f"pwbs:llm_cache:{owner_id}:*"
    deleted = 0
    try:
        redis = get_redis_client()
        cursor: int | bytes = 0
        while True:
            cursor, keys = await redis.scan(
                cursor=cursor,
                match=pattern,
                count=200,
            )
            if keys:
                deleted += await redis.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.warning(
            "llm_cache_invalidate_owner failed for %s",
            owner_id,
            exc_info=True,
        )
    return deleted


async def llm_cache_invalidate_type(
    owner_id: UUID,
    query_type: str,
) -> int:
    """Invalidate cache entries for a specific *query_type*.

    Returns:
        Number of keys deleted.
    """
    pattern = f"pwbs:llm_cache:{owner_id}:{query_type}:*"
    deleted = 0
    try:
        redis = get_redis_client()
        cursor: int | bytes = 0
        while True:
            cursor, keys = await redis.scan(
                cursor=cursor,
                match=pattern,
                count=200,
            )
            if keys:
                deleted += await redis.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.warning(
            "llm_cache_invalidate_type failed for %s/%s",
            owner_id,
            query_type,
            exc_info=True,
        )
    return deleted
