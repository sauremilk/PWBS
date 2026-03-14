"""Prometheus metrics for PWBS (TASK-116, TASK-166).

Provides:
- Automatic HTTP request latency & status code metrics via
  `prometheus-fastapi-instrumentator` (p50, p95, p99 per endpoint group).
- Custom business-KPI counters (briefing_fetches, search_queries,
  connector_syncs).
- Infrastructure gauges/histograms: DB pool, LLM call duration,
  embedding batch time, Celery queue depth.
- `/metrics` endpoint for Prometheus/Grafana scraping.

All counters use `owner_id` labels only in pseudonymised form (SHA-256
prefix) to protect PII (DSGVO compliance).
"""

from __future__ import annotations

import hashlib
import logging

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom business metrics
# ---------------------------------------------------------------------------

#: Counts briefing fetch events (by type).
BRIEFING_FETCHES = Counter(
    "pwbs_briefing_fetches_total",
    "Total number of briefing fetches",
    ["briefing_type"],
)

#: Counts search query executions (by mode).
SEARCH_QUERIES = Counter(
    "pwbs_search_queries_total",
    "Total number of search queries",
    ["search_mode"],
)

#: Counts connector sync operations (by source type and success/failure).
CONNECTOR_SYNCS = Counter(
    "pwbs_connector_syncs_total",
    "Total number of connector sync operations",
    ["source_type", "status"],
)

#: Counts auth events (login, register, logout, refresh).
AUTH_EVENTS = Counter(
    "pwbs_auth_events_total",
    "Total number of authentication events",
    ["event_type"],
)

#: HTTP error rate by status class and endpoint group.
HTTP_ERRORS = Counter(
    "pwbs_http_errors_total",
    "Total number of HTTP error responses",
    ["status_class", "endpoint_group"],
)

# ---------------------------------------------------------------------------
# Infrastructure metrics (TASK-166)
# ---------------------------------------------------------------------------

#: DB connection pool utilisation.
DB_POOL_SIZE = Gauge(
    "pwbs_db_pool_size",
    "Current size of the database connection pool",
)
DB_POOL_CHECKED_IN = Gauge(
    "pwbs_db_pool_checked_in",
    "Number of idle connections in the pool",
)
DB_POOL_CHECKED_OUT = Gauge(
    "pwbs_db_pool_checked_out",
    "Number of connections currently in use",
)
DB_POOL_OVERFLOW = Gauge(
    "pwbs_db_pool_overflow",
    "Number of overflow connections currently open",
)

#: LLM call duration by provider and use-case.
LLM_CALL_DURATION = Histogram(
    "pwbs_llm_call_duration_seconds",
    "Duration of LLM API calls",
    ["provider", "use_case"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

#: Embedding batch processing time.
EMBEDDING_BATCH_DURATION = Histogram(
    "pwbs_embedding_batch_duration_seconds",
    "Duration of embedding batch processing",
    ["model"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

#: Celery queue depth by queue name.
CELERY_QUEUE_DEPTH = Gauge(
    "pwbs_celery_queue_depth",
    "Number of tasks waiting in Celery queue",
    ["queue"],
)


def _endpoint_group(path: str) -> str:
    """Extract the API endpoint group from a request path.

    `/api/v1/user/settings`  `user`
    `/api/v1/briefings/latest`  `briefings`
    `/api/v1/admin/health`  `admin`
    """
    parts = path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        return parts[2]
    return "other"


def setup_metrics(app: object) -> None:
    """Attach Prometheus instrumentation to the FastAPI *app*.

    Adds automatic request-duration histogram + `/metrics` endpoint.
    Must be called **after** all routers are mounted.
    """
    from prometheus_fastapi_instrumentator import Instrumentator

    instrumentator = Instrumentator(
        should_group_status_codes=False,  # keep individual codes
        should_ignore_untemplated=True,
        should_respect_env_var=False,  # always active
        excluded_handlers=["/metrics", "/api/v1/admin/health"],
        inprogress_name="pwbs_http_requests_inprogress",
        inprogress_labels=True,
    )

    instrumentator.instrument(app).expose(  # type: ignore[arg-type]
        app,  # type: ignore[arg-type]
        endpoint="/metrics",
        include_in_schema=False,
        tags=["monitoring"],
    )

    logger.info("Prometheus metrics enabled at /metrics")
