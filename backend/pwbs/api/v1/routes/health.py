"""Health-check endpoint (TASK-031, TASK-114).

GET /api/v1/admin/health — no authentication required.
Checks PostgreSQL, Weaviate, Neo4j, Redis and LLM API in parallel with
a 5-second timeout per service.

Returns HTTP 200 when PostgreSQL and at least one search component are
reachable, HTTP 503 when PostgreSQL is not reachable (critical failure).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter
from starlette.responses import JSONResponse

from pwbs.core.config import get_settings
from pwbs.db.neo4j_client import check_neo4j_health
from pwbs.db.postgres import check_postgres_health
from pwbs.db.redis_client import check_redis_health
from pwbs.db.weaviate_client import check_weaviate_health
from pwbs.queue.health import check_queue_health
from pwbs.schemas.common import COMMON_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    responses={**COMMON_RESPONSES},
)

_HEALTH_TIMEOUT = 5.0  # seconds per check


async def _check_llm_health() -> bool:
    """Lightweight LLM API reachability check.

    Tests connectivity to the configured LLM provider without consuming
    tokens — uses the models-list endpoint (free API call).
    """
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "claude":
        api_key = settings.anthropic_api_key.get_secret_value()
        if not api_key:
            return False
        async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT) as client:
            resp = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
            return resp.status_code < 500
    elif provider == "gpt4":
        api_key = settings.openai_api_key.get_secret_value()
        if not api_key:
            return False
        async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return resp.status_code < 500
    elif provider == "ollama":
        base_url = settings.ollama_base_url
        if not base_url:
            return False
        async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT) as client:
            resp = await client.get(f"{base_url}/api/tags")
            return resp.status_code < 500
    return False


async def _timed_check(name: str, check_fn: Any) -> dict[str, Any]:
    start = time.monotonic()
    try:
        ok = await asyncio.wait_for(check_fn(), timeout=_HEALTH_TIMEOUT)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {"name": name, "status": "up" if ok else "down", "latency_ms": latency_ms}
    except Exception:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {"name": name, "status": "down", "latency_ms": latency_ms}


@router.get(
    "/health",
    summary="Health Check",
    description="Prüft PostgreSQL, Weaviate, Neo4j, Redis und LLM-API parallel "
    "mit 5s Timeout pro Service. HTTP 200 wenn PostgreSQL und mindestens eine "
    "Such-Komponente erreichbar sind, HTTP 503 bei PostgreSQL-Ausfall.",
    responses={200: {"description": "System healthy oder degraded"}, 503: {"description": "PostgreSQL nicht erreichbar"}},
)
async def health_check() -> JSONResponse:
    checks = [
        _timed_check("postgres", check_postgres_health),
        _timed_check("weaviate", check_weaviate_health),
        _timed_check("neo4j", check_neo4j_health),
        _timed_check("redis", check_redis_health),
        _timed_check("llm_api", _check_llm_health),
    ]
    results = await asyncio.gather(*checks)

    components = {
        r["name"]: {"status": r["status"], "latency_ms": r["latency_ms"]} for r in results
    }

    pg_up = components["postgres"]["status"] == "up"
    # Search is available if Weaviate is up (PostgreSQL keyword search is
    # always available when PG is up, so pg_up alone counts as one search path).
    search_up = components["weaviate"]["status"] == "up" or pg_up

    if pg_up and all(r["status"] == "up" for r in results):
        overall = "healthy"
    elif pg_up and search_up:
        overall = "degraded"
    else:
        overall = "unhealthy"

    # Queue status (TASK-121) — non-critical, does not affect overall status
    queue_info: dict[str, Any] = {}
    try:
        queue_info = await check_queue_health()
    except Exception:
        queue_info = {"status": "unavailable"}

    # HTTP 503 when PostgreSQL is unreachable (critical failure)
    status_code = 200 if pg_up else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "components": components, "queue": queue_info},
    )
