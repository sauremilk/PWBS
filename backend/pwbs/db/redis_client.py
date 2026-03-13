"""Redis async client singleton and health check (TASK-030)."""

from __future__ import annotations

import redis.asyncio as aioredis

from pwbs.core.config import get_settings

_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    global _client
    if _client is None:
        settings = get_settings()
        _client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _client


async def check_redis_health() -> bool:
    try:
        client = get_redis_client()
        return await client.ping()
    except Exception:
        return False


async def close_redis_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None