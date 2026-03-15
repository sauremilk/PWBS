"""Tests for pwbs.api.main – FastAPI app skeleton (TASK-037)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from pwbs.api.main import create_app
from pwbs.core.config import get_settings


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestAppFactory:
    """Verify the app factory creates a properly configured FastAPI instance."""

    def test_title_and_version(self) -> None:
        app = create_app()
        assert app.title == "PWBS API"
        assert app.version == "0.1.0"

    def test_cors_middleware_present(self) -> None:
        app = create_app()
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes

    def test_trusted_host_middleware_present(self) -> None:
        app = create_app()
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "TrustedHostMiddleware" in middleware_classes

    def test_request_id_middleware_present(self) -> None:
        app = create_app()
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CorrelationIdMiddleware" in middleware_classes

    def test_docs_enabled_in_development(self) -> None:
        app = create_app()
        settings = get_settings()
        if settings.debug:
            assert app.docs_url == "/docs"
            assert app.redoc_url == "/redoc"


class TestCorrelationIdMiddleware:
    """Verify the CorrelationId middleware injects X-Request-ID."""

    @pytest.mark.anyio
    async def test_response_has_request_id(self) -> None:
        app = create_app()
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/admin/health")
            assert "x-request-id" in response.headers

    @pytest.mark.anyio
    async def test_request_id_forwarded(self) -> None:
        app = create_app()
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        custom_id = "my-custom-id-123"
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/api/v1/admin/health",
                headers={"X-Request-ID": custom_id},
            )
            assert response.headers.get("x-request-id") == custom_id


class TestHealthRouterMounted:
    """Verify the health-check route is reachable."""

    @pytest.mark.anyio
    async def test_health_endpoint_responds(self) -> None:
        app = create_app()
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/admin/health")
            # Health check may return 503 because DBs are not running, but the
            # endpoint should respond (not 404 Not Found).
            assert response.status_code in (200, 503)
            data = response.json()
            assert "status" in data
