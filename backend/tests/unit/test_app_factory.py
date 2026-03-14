"""Tests for FastAPI app factory and exception handlers (TASK-109).

Covers create_app(), exception handlers (PWBSError, validation, unhandled),
and basic route registration verification.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pwbs.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    PWBSError,
    RateLimitError,
)


@pytest.fixture()
def client() -> TestClient:
    """Create a fresh test client with all DB connections mocked."""
    with (
        patch("pwbs.api.main.get_settings") as mock_settings,
        patch("pwbs.api.main.setup_logging"),
        patch("pwbs.api.main.init_sentry"),
    ):
        settings = mock_settings.return_value
        settings.environment = "development"
        settings.debug = True
        settings.is_production = False
        settings.log_level = "INFO"
        settings.cors_origins = ["http://localhost:3000"]
        settings.trusted_hosts = ["*"]
        settings.sentry_dsn = ""
        settings.sentry_traces_sample_rate = 0.0
        # Reimport to get a fresh app with mocked settings
        from pwbs.api.main import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)


class TestCreateApp:
    def test_app_title(self, client: TestClient) -> None:
        assert client.app.title == "PWBS API"  # type: ignore[union-attr]

    def test_docs_available_in_debug(self, client: TestClient) -> None:
        assert client.app.docs_url == "/docs"  # type: ignore[union-attr]

    def test_health_route_registered(self, client: TestClient) -> None:
        routes = [r.path for r in client.app.routes]  # type: ignore[union-attr]
        assert "/api/v1/admin/health" in routes


class TestPWBSErrorHandler:
    def test_authentication_error_401(self, client: TestClient) -> None:
        async def _raise(db: object = None) -> None:
            raise AuthenticationError("bad token", code="INVALID_TOKEN")

        client.app.add_api_route("/test-auth-err", _raise)  # type: ignore[union-attr]
        resp = client.get("/test-auth-err")
        assert resp.status_code == 401
        body = resp.json()
        assert body["code"] == "INVALID_TOKEN"

    def test_authorization_error_403(self, client: TestClient) -> None:
        async def _raise(db: object = None) -> None:
            raise AuthorizationError("forbidden")

        client.app.add_api_route("/test-authz-err", _raise)  # type: ignore[union-attr]
        resp = client.get("/test-authz-err")
        assert resp.status_code == 403

    def test_not_found_error_404(self, client: TestClient) -> None:
        async def _raise(db: object = None) -> None:
            raise NotFoundError("missing")

        client.app.add_api_route("/test-notfound-err", _raise)  # type: ignore[union-attr]
        resp = client.get("/test-notfound-err")
        assert resp.status_code == 404

    def test_rate_limit_error_429(self, client: TestClient) -> None:
        async def _raise(db: object = None) -> None:
            raise RateLimitError("slow down")

        client.app.add_api_route("/test-ratelimit-err", _raise)  # type: ignore[union-attr]
        resp = client.get("/test-ratelimit-err")
        assert resp.status_code == 429

    def test_generic_pwbs_error_500(self, client: TestClient) -> None:
        async def _raise(db: object = None) -> None:
            raise PWBSError("generic error")

        client.app.add_api_route("/test-generic-err", _raise)  # type: ignore[union-attr]
        resp = client.get("/test-generic-err")
        assert resp.status_code == 500
        assert resp.json()["code"] == "PWBSError"


class TestValidationErrorHandler:
    def test_invalid_path_param_returns_422(self, client: TestClient) -> None:
        from pydantic import BaseModel

        class Body(BaseModel):
            value: int

        async def _endpoint(body: Body) -> dict:
            return {"ok": True}

        client.app.add_api_route("/test-validation", _endpoint, methods=["POST"])  # type: ignore[union-attr]
        resp = client.post("/test-validation", json={"value": "not-an-int"})
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"


class TestUnhandledErrorHandler:
    def test_unhandled_returns_500(self, client: TestClient) -> None:
        async def _raise(db: object = None) -> None:
            raise RuntimeError("unexpected boom")

        client.app.add_api_route("/test-unhandled", _raise)  # type: ignore[union-attr]
        resp = client.get("/test-unhandled")
        assert resp.status_code == 500
        assert resp.json()["code"] == "INTERNAL_ERROR"
