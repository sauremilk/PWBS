"""Tests for Health-Check endpoint (TASK-114)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pwbs.api.v1.routes.health import _check_llm_health, _timed_check, health_check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_check(ok: bool = True) -> Any:
    """Create an async health-check function returning *ok*."""
    async def check() -> bool:
        return ok
    return check


def _make_slow_check(delay: float = 10.0) -> Any:
    """Create an async health-check that exceeds timeout."""
    async def check() -> bool:
        await asyncio.sleep(delay)
        return True
    return check


# ---------------------------------------------------------------------------
# _timed_check
# ---------------------------------------------------------------------------


class TestTimedCheck:
    @pytest.mark.asyncio
    async def test_healthy_service(self) -> None:
        result = await _timed_check("pg", _make_check(True))
        assert result["name"] == "pg"
        assert result["status"] == "up"
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_unhealthy_service(self) -> None:
        result = await _timed_check("pg", _make_check(False))
        assert result["status"] == "down"

    @pytest.mark.asyncio
    async def test_exception_returns_down(self) -> None:
        async def exploding() -> bool:
            raise ConnectionError("boom")
        result = await _timed_check("boom", exploding)
        assert result["status"] == "down"

    @pytest.mark.asyncio
    async def test_timeout_returns_down(self) -> None:
        result = await _timed_check("slow", _make_slow_check(10.0))
        assert result["status"] == "down"
        assert result["latency_ms"] >= 0


# ---------------------------------------------------------------------------
# health_check endpoint
# ---------------------------------------------------------------------------


def _mock_all_up() -> list[Any]:
    """Patch targets for all health check functions returning True."""
    return [
        patch("pwbs.api.v1.routes.health.check_postgres_health", new_callable=AsyncMock, return_value=True),
        patch("pwbs.api.v1.routes.health.check_weaviate_health", new_callable=AsyncMock, return_value=True),
        patch("pwbs.api.v1.routes.health.check_neo4j_health", new_callable=AsyncMock, return_value=True),
        patch("pwbs.api.v1.routes.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch("pwbs.api.v1.routes.health._check_llm_health", new_callable=AsyncMock, return_value=True),
        patch("pwbs.api.v1.routes.health.check_queue_health", new_callable=AsyncMock, return_value={"status": "ok"}),
    ]


class TestHealthCheckEndpoint:
    @pytest.mark.asyncio
    async def test_all_healthy_returns_200(self) -> None:
        patches = _mock_all_up()
        for p in patches:
            p.start()
        try:
            resp = await health_check()
            assert resp.status_code == 200
            import json
            body = json.loads(resp.body)
            assert body["status"] == "healthy"
            assert "postgres" in body["components"]
            assert "weaviate" in body["components"]
            assert "neo4j" in body["components"]
            assert "redis" in body["components"]
            assert "llm_api" in body["components"]
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_postgres_down_returns_503(self) -> None:
        patches = _mock_all_up()
        for p in patches:
            p.start()
        # Override postgres to be down
        with patch("pwbs.api.v1.routes.health.check_postgres_health", new_callable=AsyncMock, return_value=False):
            resp = await health_check()
            assert resp.status_code == 503
            import json
            body = json.loads(resp.body)
            assert body["status"] == "unhealthy"
        for p in patches:
            p.stop()

    @pytest.mark.asyncio
    async def test_degraded_when_non_critical_down(self) -> None:
        """PostgreSQL up + Weaviate up but Neo4j/Redis/LLM down -> degraded 200."""
        with (
            patch("pwbs.api.v1.routes.health.check_postgres_health", new_callable=AsyncMock, return_value=True),
            patch("pwbs.api.v1.routes.health.check_weaviate_health", new_callable=AsyncMock, return_value=True),
            patch("pwbs.api.v1.routes.health.check_neo4j_health", new_callable=AsyncMock, return_value=False),
            patch("pwbs.api.v1.routes.health.check_redis_health", new_callable=AsyncMock, return_value=False),
            patch("pwbs.api.v1.routes.health._check_llm_health", new_callable=AsyncMock, return_value=False),
            patch("pwbs.api.v1.routes.health.check_queue_health", new_callable=AsyncMock, return_value={"status": "ok"}),
        ):
            resp = await health_check()
            assert resp.status_code == 200
            import json
            body = json.loads(resp.body)
            assert body["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_components_have_latency_ms(self) -> None:
        patches = _mock_all_up()
        for p in patches:
            p.start()
        try:
            resp = await health_check()
            import json
            body = json.loads(resp.body)
            for name, comp in body["components"].items():
                assert "latency_ms" in comp, f"{name} missing latency_ms"
                assert isinstance(comp["latency_ms"], (int, float))
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_queue_failure_does_not_affect_status(self) -> None:
        with (
            patch("pwbs.api.v1.routes.health.check_postgres_health", new_callable=AsyncMock, return_value=True),
            patch("pwbs.api.v1.routes.health.check_weaviate_health", new_callable=AsyncMock, return_value=True),
            patch("pwbs.api.v1.routes.health.check_neo4j_health", new_callable=AsyncMock, return_value=True),
            patch("pwbs.api.v1.routes.health.check_redis_health", new_callable=AsyncMock, return_value=True),
            patch("pwbs.api.v1.routes.health._check_llm_health", new_callable=AsyncMock, return_value=True),
            patch("pwbs.api.v1.routes.health.check_queue_health", new_callable=AsyncMock, side_effect=Exception("queue down")),
        ):
            resp = await health_check()
            assert resp.status_code == 200
            import json
            body = json.loads(resp.body)
            assert body["status"] == "healthy"
            assert body["queue"]["status"] == "unavailable"


# ---------------------------------------------------------------------------
# _check_llm_health
# ---------------------------------------------------------------------------


class TestCheckLLMHealth:
    @pytest.mark.asyncio
    async def test_claude_with_valid_key(self) -> None:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200

        with (
            patch("pwbs.api.v1.routes.health.get_settings") as mock_settings,
            patch("httpx.AsyncClient") as MockClient,
        ):
            s = mock_settings.return_value
            s.llm_provider = "claude"
            s.anthropic_api_key.get_secret_value.return_value = "sk-test-key"

            client_instance = AsyncMock()
            client_instance.get.return_value = mock_resp
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await _check_llm_health()
            assert result is True

    @pytest.mark.asyncio
    async def test_claude_no_key_returns_false(self) -> None:
        with patch("pwbs.api.v1.routes.health.get_settings") as mock_settings:
            s = mock_settings.return_value
            s.llm_provider = "claude"
            s.anthropic_api_key.get_secret_value.return_value = ""
            result = await _check_llm_health()
            assert result is False

    @pytest.mark.asyncio
    async def test_ollama_reachable(self) -> None:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200

        with (
            patch("pwbs.api.v1.routes.health.get_settings") as mock_settings,
            patch("httpx.AsyncClient") as MockClient,
        ):
            s = mock_settings.return_value
            s.llm_provider = "ollama"
            s.ollama_base_url = "http://localhost:11434"

            client_instance = AsyncMock()
            client_instance.get.return_value = mock_resp
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await _check_llm_health()
            assert result is True

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_false(self) -> None:
        with patch("pwbs.api.v1.routes.health.get_settings") as mock_settings:
            s = mock_settings.return_value
            s.llm_provider = "unknown"
            result = await _check_llm_health()
            assert result is False

    @pytest.mark.asyncio
    async def test_server_error_returns_false(self) -> None:
        mock_resp = AsyncMock()
        mock_resp.status_code = 500

        with (
            patch("pwbs.api.v1.routes.health.get_settings") as mock_settings,
            patch("httpx.AsyncClient") as MockClient,
        ):
            s = mock_settings.return_value
            s.llm_provider = "claude"
            s.anthropic_api_key.get_secret_value.return_value = "sk-test-key"

            client_instance = AsyncMock()
            client_instance.get.return_value = mock_resp
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await _check_llm_health()
            assert result is False
