"""Combined health-check endpoint (TASK-031).

GET /api/v1/admin/health  no authentication required.
Checks PostgreSQL, Weaviate, Neo4j and Redis in parallel with
a 5-second timeout per service.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter

from pwbs.db.postgres import check_postgres_health
from pwbs.db.weaviate_client import check_weaviate_health
from pwbs.db.neo4j_client import check_neo4j_health
from pwbs.db.redis_client import check_redis_health
from pwbs.queue.health import check_queue_health

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_HEALTH_TIMEOUT = 5.0  # seconds per check


async def _timed_check(name: str, check_fn: Any) -> dict[str, Any]:
    start = time.monotonic()
    try:
        ok = await asyncio.wait_for(check_fn(), timeout=_HEALTH_TIMEOUT)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {"name": name, "status": "up" if ok else "down", "latency_ms": latency_ms}
    except Exception:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {"name": name, "status": "down", "latency_ms": latency_ms}


@router.get("/health")
async def health_check() -> dict[str, Any]:
    checks = [
        _timed_check("postgres", check_postgres_health),
        _timed_check("weaviate", check_weaviate_health),
        _timed_check("neo4j", check_neo4j_health),
        _timed_check("redis", check_redis_health),
    ]
    results = await asyncio.gather(*checks)

    components = {r["name"]: {"status": r["status"], "latency_ms": r["latency_ms"]} for r in results}
    all_up = all(r["status"] == "up" for r in results)
    any_up = any(r["status"] == "up" for r in results)

    if all_up:
        overall = "healthy"
    elif any_up:
        overall = "degraded"
    else:
        overall = "unhealthy"

    # Queue status (TASK-121) – non-critical, does not affect overall status
    queue_info: dict[str, Any] = {}
    try:
        queue_info = await check_queue_health()
    except Exception:
        queue_info = {"status": "unavailable"}

    return {"status": overall, "components": components, "queue": queue_info}