"""Queue health check utilities (TASK-121).

Provides functions to inspect Celery queue depth, active workers
and overall queue system health for the /api/v1/admin/health endpoint.
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis

from pwbs.core.config import get_settings
from pwbs.queue.config import ALL_QUEUE_NAMES


async def get_queue_depths(redis_client: aioredis.Redis | None = None) -> dict[str, int]:
    """Return the number of pending messages per queue.

    Uses LLEN on the Redis lists that Celery uses as queue storage.
    """
    if redis_client is None:
        settings = get_settings()
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        close_after = True
    else:
        close_after = False

    depths: dict[str, int] = {}
    try:
        for queue_name in ALL_QUEUE_NAMES:
            length: int = await redis_client.llen(queue_name)  # type: ignore[assignment]
            depths[queue_name] = length
    except Exception:
        for queue_name in ALL_QUEUE_NAMES:
            depths.setdefault(queue_name, -1)
    finally:
        if close_after:
            await redis_client.aclose()

    return depths


def get_active_workers() -> dict[str, Any]:
    """Inspect active Celery workers synchronously.

    Returns a dict of worker names to their stats, or empty dict
    if no workers are reachable.
    """
    try:
        from pwbs.queue.celery_app import app

        inspector = app.control.inspect(timeout=2.0)
        active = inspector.active()
        return active if active else {}
    except Exception:
        return {}


async def check_queue_health() -> dict[str, Any]:
    """Comprehensive queue health check for the admin endpoint.

    Returns queue depths, worker count and overall status.
    """
    depths = await get_queue_depths()
    total_pending = sum(v for v in depths.values() if v >= 0)
    any_error = any(v < 0 for v in depths.values())

    # Worker inspection is synchronous (Celery limitation);
    # run in thread to avoid blocking the event loop
    import asyncio

    workers = await asyncio.to_thread(get_active_workers)
    worker_count = len(workers)

    if any_error:
        status = "degraded"
    elif worker_count == 0:
        # No workers connected but queues accessible -> degraded
        status = "degraded"
    else:
        status = "up"

    return {
        "status": status,
        "worker_count": worker_count,
        "total_pending": total_pending,
        "queues": depths,
    }
