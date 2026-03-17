"""Tests for Structured Logging with Correlation IDs (TASK-196).

Verifies:
- CorrelationIdMiddleware sets X-Request-ID in response
- correlation_id field appears in JSON log entries
- correlation_id propagates via contextvars in async calls
- X-Request-ID from request is echoed back
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from pwbs.api.main import create_app
from pwbs.core.logging import (
    _add_request_context,
    correlation_id_var,
    request_id_var,
    setup_logging,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestCorrelationIdMiddlewareIntegration:
    """Integration tests via HTTP client through the full middleware stack."""

    @pytest.mark.anyio
    async def test_response_has_x_request_id(self) -> None:
        app = create_app()
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/admin/health")
            assert "x-request-id" in response.headers
            # Must be a valid UUID
            uuid.UUID(response.headers["x-request-id"])

    @pytest.mark.anyio
    async def test_custom_request_id_echoed_back(self) -> None:
        """AC: Request with X-Request-ID header -> same ID in response."""
        app = create_app()
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        custom_id = "trace-abc-123-def"
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/api/v1/admin/health",
                headers={"X-Request-ID": custom_id},
            )
            assert response.headers.get("x-request-id") == custom_id


class TestCorrelationIdContextVarPropagation:
    """Verify contextvars propagation in async service calls."""

    @pytest.mark.asyncio
    async def test_correlation_id_propagates_to_nested_async(self) -> None:
        from pwbs.api.middleware.correlation import CorrelationIdMiddleware

        mw = CorrelationIdMiddleware(AsyncMock())
        req = MagicMock()
        req.headers = {"x-request-id": "nested-trace-id"}
        req.state = MagicMock()

        inner_cid = None
        inner_rid = None

        async def inner_service_call() -> None:
            nonlocal inner_cid, inner_rid
            inner_cid = correlation_id_var.get()
            inner_rid = request_id_var.get()

        async def capture_next(r: Any) -> MagicMock:
            await inner_service_call()
            resp = MagicMock()
            resp.headers = {}
            return resp

        await mw.dispatch(req, capture_next)
        assert inner_cid == "nested-trace-id"
        assert inner_rid == "nested-trace-id"

    @pytest.mark.asyncio
    async def test_contextvar_reset_after_request(self) -> None:
        from pwbs.api.middleware.correlation import CorrelationIdMiddleware

        mw = CorrelationIdMiddleware(AsyncMock())
        req = MagicMock()
        req.headers = {"x-request-id": "temp-id"}
        req.state = MagicMock()

        async def noop_next(r: Any) -> MagicMock:
            resp = MagicMock()
            resp.headers = {}
            return resp

        await mw.dispatch(req, noop_next)
        # After the middleware finishes, contextvar should be reset
        assert correlation_id_var.get() is None


class TestCorrelationIdInLogOutput:
    """Verify that correlation_id appears in structured JSON log entries."""

    def test_add_request_context_includes_correlation_id(self) -> None:
        token = correlation_id_var.set("log-trace-456")
        try:
            event_dict: dict[str, Any] = {}
            result = _add_request_context(None, "info", event_dict)
            assert result["correlation_id"] == "log-trace-456"
            assert result["request_id"] == "log-trace-456"
        finally:
            correlation_id_var.reset(token)

    def test_json_log_contains_correlation_id(self, capfd: Any) -> None:
        setup_logging("DEBUG")
        token = correlation_id_var.set("json-trace-789")
        try:
            logger = logging.getLogger("test.correlation")
            logger.info("test log entry")
            captured = capfd.readouterr()
            log_line = captured.out.strip().split("\n")[-1]
            log_data = json.loads(log_line)
            assert log_data["correlation_id"] == "json-trace-789"
        finally:
            correlation_id_var.reset(token)
