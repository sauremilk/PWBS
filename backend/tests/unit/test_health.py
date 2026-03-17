"""Tests for Health-Check endpoint (TASK-114, TASK-199)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.api.v1.routes.health import (
    _check_llm_health,
    _detailed_timed_check,
    _timed_check,
    health_check,
    health_check_detailed,
)

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
        # _HEALTH_TIMEOUT wird auf 0.05 s gesetzt, damit der Test schnell laeuft
        # (statt 5+ Sekunden auf den echten Timeout zu warten).
        with patch("pwbs.api.v1.routes.health._HEALTH_TIMEOUT", 0.05):
            result = await _timed_check("slow", _make_slow_check(1.0))
        assert result["status"] == "down"
        assert result["latency_ms"] >= 0


# ---------------------------------------------------------------------------
# health_check endpoint
# ---------------------------------------------------------------------------


def _mock_all_up() -> list[Any]:
    """Patch targets for all health check functions returning True."""
    return [
        patch(
            "pwbs.api.v1.routes.health.check_postgres_health",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "pwbs.api.v1.routes.health.check_weaviate_health",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "pwbs.api.v1.routes.health.check_neo4j_health",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "pwbs.api.v1.routes.health.check_redis_health",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "pwbs.api.v1.routes.health._check_llm_health", new_callable=AsyncMock, return_value=True
        ),
        patch(
            "pwbs.api.v1.routes.health.check_queue_health",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ),
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
        with patch(
            "pwbs.api.v1.routes.health.check_postgres_health",
            new_callable=AsyncMock,
            return_value=False,
        ):
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
            patch(
                "pwbs.api.v1.routes.health.check_postgres_health",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "pwbs.api.v1.routes.health.check_weaviate_health",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "pwbs.api.v1.routes.health.check_neo4j_health",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "pwbs.api.v1.routes.health.check_redis_health",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "pwbs.api.v1.routes.health._check_llm_health",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "pwbs.api.v1.routes.health.check_queue_health",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ),
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
            patch(
                "pwbs.api.v1.routes.health.check_postgres_health",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "pwbs.api.v1.routes.health.check_weaviate_health",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "pwbs.api.v1.routes.health.check_neo4j_health",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "pwbs.api.v1.routes.health.check_redis_health",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "pwbs.api.v1.routes.health._check_llm_health",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "pwbs.api.v1.routes.health.check_queue_health",
                new_callable=AsyncMock,
                side_effect=Exception("queue down"),
            ),
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


# ---------------------------------------------------------------------------
# _detailed_timed_check (TASK-199)
# ---------------------------------------------------------------------------


class TestDetailedTimedCheck:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        result = await _detailed_timed_check("test_svc", _make_check(ok=True))
        assert result["name"] == "test_svc"
        assert result["status"] == "up"
        assert result["latency_ms"] >= 0
        assert result["details"] == "reachable"

    @pytest.mark.asyncio
    async def test_failure(self) -> None:
        result = await _detailed_timed_check("test_svc", _make_check(ok=False))
        assert result["status"] == "down"
        assert result["details"] == "health check failed"

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        result = await _detailed_timed_check("test_svc", _make_slow_check(delay=10.0))
        assert result["status"] == "down"
        assert "timeout" in result["details"]

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        async def _raise() -> bool:
            raise ConnectionError("connection refused")

        result = await _detailed_timed_check("test_svc", _raise)
        assert result["status"] == "down"
        assert "connection refused" in result["details"]


# ---------------------------------------------------------------------------
# health_check_detailed endpoint (TASK-199)
# ---------------------------------------------------------------------------


def _mock_admin_user() -> MagicMock:
    """Return a mock User with is_admin=True."""
    user = MagicMock()
    user.is_admin = True
    return user


def _mock_regular_user() -> MagicMock:
    """Return a mock User with is_admin=False."""
    user = MagicMock()
    user.is_admin = False
    return user


def _patch_detailed_deps(
    *,
    pg: bool = True,
    weaviate: bool = True,
    redis: bool = True,
    neo4j: bool = True,
    neo4j_driver_available: bool = True,
) -> list[Any]:
    """Return context-manager patches for the detailed health endpoint."""
    patches = [
        patch(
            "pwbs.api.v1.routes.health.check_postgres_health",
            new_callable=AsyncMock,
            return_value=pg,
        ),
        patch(
            "pwbs.api.v1.routes.health.check_weaviate_health",
            new_callable=AsyncMock,
            return_value=weaviate,
        ),
        patch(
            "pwbs.api.v1.routes.health.check_redis_health",
            new_callable=AsyncMock,
            return_value=redis,
        ),
        patch(
            "pwbs.api.v1.routes.health.check_neo4j_health",
            new_callable=AsyncMock,
            return_value=neo4j,
        ),
    ]
    if neo4j_driver_available:
        patches.append(
            patch(
                "pwbs.api.v1.routes.health.get_neo4j_driver",
                return_value=MagicMock(),
            )
        )
    else:
        patches.append(
            patch(
                "pwbs.api.v1.routes.health.get_neo4j_driver",
                return_value=None,
            )
        )
    return patches


class TestHealthCheckDetailed:
    @pytest.mark.asyncio
    async def test_all_healthy(self) -> None:
        patches = _patch_detailed_deps()
        for p in patches:
            p.start()
        try:
            resp = await health_check_detailed(response=MagicMock(), user=_mock_admin_user())
            assert resp.status_code == 200
            import json

            body = json.loads(resp.body)
            assert body["status"] == "healthy"
            assert "postgres" in body["dependencies"]
            assert "weaviate" in body["dependencies"]
            assert "redis" in body["dependencies"]
            assert "neo4j" in body["dependencies"]
            assert body["dependencies"]["postgres"]["status"] == "up"
            assert body["dependencies"]["neo4j"]["status"] == "up"
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_neo4j_unavailable_returns_healthy(self) -> None:
        """Neo4j driver None -> status 'unavailable', overall still healthy."""
        patches = _patch_detailed_deps(neo4j_driver_available=False)
        for p in patches:
            p.start()
        try:
            resp = await health_check_detailed(response=MagicMock(), user=_mock_admin_user())
            assert resp.status_code == 200
            import json

            body = json.loads(resp.body)
            assert body["status"] == "healthy"
            assert body["dependencies"]["neo4j"]["status"] == "unavailable"
            assert body["dependencies"]["neo4j"]["latency_ms"] == 0.0
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_postgres_down_returns_unhealthy_503(self) -> None:
        patches = _patch_detailed_deps(pg=False)
        for p in patches:
            p.start()
        try:
            resp = await health_check_detailed(response=MagicMock(), user=_mock_admin_user())
            assert resp.status_code == 503
            import json

            body = json.loads(resp.body)
            assert body["status"] == "unhealthy"
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_weaviate_down_returns_unhealthy_503(self) -> None:
        patches = _patch_detailed_deps(weaviate=False)
        for p in patches:
            p.start()
        try:
            resp = await health_check_detailed(response=MagicMock(), user=_mock_admin_user())
            assert resp.status_code == 503
            import json

            body = json.loads(resp.body)
            assert body["status"] == "unhealthy"
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_redis_down_returns_degraded(self) -> None:
        patches = _patch_detailed_deps(redis=False)
        for p in patches:
            p.start()
        try:
            resp = await health_check_detailed(response=MagicMock(), user=_mock_admin_user())
            assert resp.status_code == 200
            import json

            body = json.loads(resp.body)
            assert body["status"] == "degraded"
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_neo4j_down_returns_degraded(self) -> None:
        """Neo4j driver exists but check fails -> degraded."""
        patches = _patch_detailed_deps(neo4j=False, neo4j_driver_available=True)
        for p in patches:
            p.start()
        try:
            resp = await health_check_detailed(response=MagicMock(), user=_mock_admin_user())
            assert resp.status_code == 200
            import json

            body = json.loads(resp.body)
            assert body["status"] == "degraded"
            assert body["dependencies"]["neo4j"]["status"] == "down"
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self) -> None:
        from fastapi import HTTPException

        patches = _patch_detailed_deps()
        for p in patches:
            p.start()
        try:
            with pytest.raises(HTTPException) as exc_info:
                await health_check_detailed(response=MagicMock(), user=_mock_regular_user())
            assert exc_info.value.status_code == 403
        finally:
            for p in patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_dependencies_have_latency_and_details(self) -> None:
        patches = _patch_detailed_deps()
        for p in patches:
            p.start()
        try:
            resp = await health_check_detailed(response=MagicMock(), user=_mock_admin_user())
            import json

            body = json.loads(resp.body)
            for dep_name, dep_info in body["dependencies"].items():
                assert "latency_ms" in dep_info, f"{dep_name} missing latency_ms"
                assert "details" in dep_info, f"{dep_name} missing details"
        finally:
            for p in patches:
                p.stop()
