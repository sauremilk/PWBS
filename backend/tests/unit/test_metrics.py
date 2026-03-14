"""Tests for pwbs.core.metrics -- Prometheus metrics (TASK-116, TASK-166)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from pwbs.core.metrics import (
    AUTH_EVENTS,
    BRIEFING_FETCHES,
    CELERY_QUEUE_DEPTH,
    CONNECTOR_SYNCS,
    DB_POOL_CHECKED_IN,
    DB_POOL_CHECKED_OUT,
    DB_POOL_OVERFLOW,
    DB_POOL_SIZE,
    EMBEDDING_BATCH_DURATION,
    HTTP_ERRORS,
    LLM_CALL_DURATION,
    SEARCH_QUERIES,
    _endpoint_group,
)

# ---------------------------------------------------------------------------
# _endpoint_group
# ---------------------------------------------------------------------------


class TestEndpointGroup:
    def test_user_path(self) -> None:
        assert _endpoint_group("/api/v1/user/settings") == "user"

    def test_briefings_path(self) -> None:
        assert _endpoint_group("/api/v1/briefings/latest") == "briefings"

    def test_admin_path(self) -> None:
        assert _endpoint_group("/api/v1/admin/health") == "admin"

    def test_search_path(self) -> None:
        assert _endpoint_group("/api/v1/search") == "search"

    def test_root_path(self) -> None:
        assert _endpoint_group("/") == "other"

    def test_short_path(self) -> None:
        assert _endpoint_group("/api") == "other"

    def test_connectors_path(self) -> None:
        assert _endpoint_group("/api/v1/connectors/google-calendar/sync") == "connectors"


# ---------------------------------------------------------------------------
# Custom counters
# ---------------------------------------------------------------------------


class TestCustomCounters:
    def test_briefing_fetches_increment(self) -> None:
        before = BRIEFING_FETCHES.labels(briefing_type="morning")._value.get()
        BRIEFING_FETCHES.labels(briefing_type="morning").inc()
        after = BRIEFING_FETCHES.labels(briefing_type="morning")._value.get()
        assert after == before + 1

    def test_search_queries_increment(self) -> None:
        before = SEARCH_QUERIES.labels(search_mode="hybrid")._value.get()
        SEARCH_QUERIES.labels(search_mode="hybrid").inc()
        after = SEARCH_QUERIES.labels(search_mode="hybrid")._value.get()
        assert after == before + 1

    def test_connector_syncs_increment(self) -> None:
        before = CONNECTOR_SYNCS.labels(
            source_type="google_calendar", status="success"
        )._value.get()
        CONNECTOR_SYNCS.labels(source_type="google_calendar", status="success").inc()
        after = CONNECTOR_SYNCS.labels(source_type="google_calendar", status="success")._value.get()
        assert after == before + 1

    def test_auth_events_increment(self) -> None:
        before = AUTH_EVENTS.labels(event_type="login")._value.get()
        AUTH_EVENTS.labels(event_type="login").inc()
        after = AUTH_EVENTS.labels(event_type="login")._value.get()
        assert after == before + 1

    def test_http_errors_increment(self) -> None:
        before = HTTP_ERRORS.labels(status_class="4xx", endpoint_group="auth")._value.get()
        HTTP_ERRORS.labels(status_class="4xx", endpoint_group="auth").inc()
        after = HTTP_ERRORS.labels(status_class="4xx", endpoint_group="auth")._value.get()
        assert after == before + 1


# ---------------------------------------------------------------------------
# setup_metrics
# ---------------------------------------------------------------------------


class TestSetupMetrics:
    def test_setup_metrics_instruments_app(self) -> None:
        from pwbs.core.metrics import setup_metrics

        mock_app = MagicMock()
        mock_app.routes = []
        mock_inst = MagicMock()
        mock_inst.instrument.return_value = mock_inst

        with patch("prometheus_fastapi_instrumentator.Instrumentator", return_value=mock_inst):
            setup_metrics(mock_app)

            mock_inst.instrument.assert_called_once_with(mock_app)
            mock_inst.expose.assert_called_once()
            call_kwargs = mock_inst.expose.call_args
            assert call_kwargs[1]["endpoint"] == "/metrics"
            assert call_kwargs[1]["include_in_schema"] is False


# ---------------------------------------------------------------------------
# AccessLogMiddleware error-tracking integration
# ---------------------------------------------------------------------------


class TestAccessLogMiddlewareErrorTracking:
    @pytest.mark.asyncio
    async def test_4xx_increments_error_counter(self) -> None:
        from pwbs.api.middleware.access_log import AccessLogMiddleware

        mw = AccessLogMiddleware(AsyncMock())
        req = MagicMock()
        req.method = "GET"
        req.url.path = "/api/v1/user/settings"
        req.state = MagicMock(spec=[])

        resp = MagicMock()
        resp.status_code = 404
        call_next = AsyncMock(return_value=resp)

        before = HTTP_ERRORS.labels(status_class="4xx", endpoint_group="user")._value.get()
        await mw.dispatch(req, call_next)
        after = HTTP_ERRORS.labels(status_class="4xx", endpoint_group="user")._value.get()
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_5xx_increments_error_counter(self) -> None:
        from pwbs.api.middleware.access_log import AccessLogMiddleware

        mw = AccessLogMiddleware(AsyncMock())
        req = MagicMock()
        req.method = "POST"
        req.url.path = "/api/v1/search"
        req.state = MagicMock(spec=[])

        resp = MagicMock()
        resp.status_code = 500
        call_next = AsyncMock(return_value=resp)

        before = HTTP_ERRORS.labels(status_class="5xx", endpoint_group="search")._value.get()
        await mw.dispatch(req, call_next)
        after = HTTP_ERRORS.labels(status_class="5xx", endpoint_group="search")._value.get()
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_200_does_not_increment_error_counter(self) -> None:
        from pwbs.api.middleware.access_log import AccessLogMiddleware

        mw = AccessLogMiddleware(AsyncMock())
        req = MagicMock()
        req.method = "GET"
        req.url.path = "/api/v1/briefings"
        req.state = MagicMock(spec=[])

        resp = MagicMock()
        resp.status_code = 200
        call_next = AsyncMock(return_value=resp)

        before = HTTP_ERRORS.labels(status_class="4xx", endpoint_group="briefings")._value.get()
        await mw.dispatch(req, call_next)
        after = HTTP_ERRORS.labels(status_class="4xx", endpoint_group="briefings")._value.get()
        assert after == before


# ---------------------------------------------------------------------------
# /metrics endpoint integration
# ---------------------------------------------------------------------------


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_endpoint_accessible(self) -> None:
        from httpx import ASGITransport, AsyncClient

        from pwbs.api.main import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/metrics")
            assert resp.status_code == 200
            body = resp.text
            # Prometheus format should contain standard metrics
            assert "http" in body.lower() or "pwbs" in body.lower()

    @pytest.mark.asyncio
    async def test_metrics_not_in_openapi_schema(self) -> None:
        from httpx import ASGITransport, AsyncClient

        from pwbs.api.main import create_app

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/openapi.json")
            paths = resp.json()["paths"]
            assert "/metrics" not in paths


# ---------------------------------------------------------------------------
# Infrastructure metrics (TASK-166)
# ---------------------------------------------------------------------------


class TestInfraMetrics:
    def test_db_pool_gauges_exist(self) -> None:
        DB_POOL_SIZE.set(20)
        assert DB_POOL_SIZE._value.get() == 20.0
        DB_POOL_CHECKED_IN.set(15)
        assert DB_POOL_CHECKED_IN._value.get() == 15.0
        DB_POOL_CHECKED_OUT.set(5)
        assert DB_POOL_CHECKED_OUT._value.get() == 5.0
        DB_POOL_OVERFLOW.set(0)
        assert DB_POOL_OVERFLOW._value.get() == 0.0

    def test_llm_call_duration_histogram(self) -> None:
        LLM_CALL_DURATION.labels(provider="claude", use_case="briefing.morning").observe(1.5)
        sample = REGISTRY.get_sample_value(
            "pwbs_llm_call_duration_seconds_count",
            {"provider": "claude", "use_case": "briefing.morning"},
        )
        assert sample is not None and sample >= 1

    def test_embedding_batch_duration_histogram(self) -> None:
        EMBEDDING_BATCH_DURATION.labels(model="all-MiniLM-L6-v2").observe(0.3)
        sample = REGISTRY.get_sample_value(
            "pwbs_embedding_batch_duration_seconds_count",
            {"model": "all-MiniLM-L6-v2"},
        )
        assert sample is not None and sample >= 1

    def test_celery_queue_depth_gauge(self) -> None:
        CELERY_QUEUE_DEPTH.labels(queue="ingestion.high").set(42)
        assert CELERY_QUEUE_DEPTH.labels(queue="ingestion.high")._value.get() == 42.0

    def test_no_owner_id_label(self) -> None:
        """Ensure no metric exposes raw owner_id (DSGVO)."""
        for metric in REGISTRY.collect():
            for sample in metric.samples:
                assert "owner_id" not in sample.labels, (
                    f"Metric {sample.name} exposes owner_id label"
                )
