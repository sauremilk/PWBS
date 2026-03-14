"""Tests for OpenAPI schema generation and documentation (TASK-119)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from pwbs.api.main import create_app


@pytest.fixture
def app():
    return create_app()


class TestOpenAPISchemaAccessible:
    """AC: OpenAPI 3.1 Schema unter /api/v1/openapi.json erreichbar."""

    @pytest.mark.asyncio
    async def test_openapi_json_returns_200(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/openapi.json")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_openapi_json_is_valid_schema(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/openapi.json")
            schema = resp.json()
            # OpenAPI 3.1 required fields
            assert "openapi" in schema
            assert schema["openapi"].startswith("3.1")
            assert "info" in schema
            assert schema["info"]["title"] == "PWBS API"
            assert schema["info"]["version"] == "0.1.0"
            assert "paths" in schema

    @pytest.mark.asyncio
    async def test_openapi_schema_contains_all_paths(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/openapi.json")
            paths = resp.json()["paths"]
            # Verify key API paths are documented
            expected_paths = [
                "/api/v1/admin/health",
                "/api/v1/auth/register",
                "/api/v1/auth/login",
                "/api/v1/user/settings",
            ]
            for path in expected_paths:
                assert path in paths, f"Missing path: {path}"


class TestSwaggerUIAvailability:
    """AC: SwaggerUI und ReDoc in Development verfügbar; in Produktion deaktiviert."""

    @pytest.mark.asyncio
    async def test_swagger_ui_available_in_dev(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/docs")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_available_in_dev(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/redoc")
            assert resp.status_code == 200


class TestErrorResponsesDocumented:
    """AC: Fehler-Codes in der API-Dokumentation."""

    @pytest.mark.asyncio
    async def test_auth_routes_have_error_responses(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/openapi.json")
            paths = resp.json()["paths"]
            # User settings (authenticated) should have 401, 500 responses
            user_settings = paths.get("/api/v1/user/settings", {})
            get_responses = user_settings.get("get", {}).get("responses", {})
            assert "401" in get_responses, "Missing 401 response doc"
            assert "500" in get_responses, "Missing 500 response doc"

    @pytest.mark.asyncio
    async def test_health_has_common_responses(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/openapi.json")
            paths = resp.json()["paths"]
            health = paths.get("/api/v1/admin/health", {})
            get_responses = health.get("get", {}).get("responses", {})
            assert "500" in get_responses

    @pytest.mark.asyncio
    async def test_error_response_schema_in_components(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/openapi.json")
            schema = resp.json()
            schemas = schema.get("components", {}).get("schemas", {})
            assert "ErrorResponse" in schemas
            err_schema = schemas["ErrorResponse"]
            # Verify ErrorResponse has code and message fields
            props = err_schema.get("properties", {})
            assert "code" in props
            assert "message" in props


class TestOpenAPISchemaValidity:
    """AC: Schema ist valide."""

    @pytest.mark.asyncio
    async def test_all_paths_have_operations(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/openapi.json")
            paths = resp.json()["paths"]
            http_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
            for path, path_item in paths.items():
                operations = [k for k in path_item if k in http_methods]
                assert len(operations) > 0, f"Path {path} has no HTTP operations"

    @pytest.mark.asyncio
    async def test_all_operations_have_responses(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/openapi.json")
            paths = resp.json()["paths"]
            http_methods = {"get", "post", "put", "patch", "delete"}
            for path, path_item in paths.items():
                for method in http_methods:
                    if method in path_item:
                        operation = path_item[method]
                        assert "responses" in operation, (
                            f"{method.upper()} {path} missing responses"
                        )

    @pytest.mark.asyncio
    async def test_schema_has_tags(self, app) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/openapi.json")
            paths = resp.json()["paths"]
            http_methods = {"get", "post", "put", "patch", "delete"}
            for path, path_item in paths.items():
                for method in http_methods:
                    if method in path_item:
                        operation = path_item[method]
                        assert "tags" in operation and len(operation["tags"]) > 0, (
                            f"{method.upper()} {path} missing tags"
                        )


class TestCommonSchemaModule:
    """Unit tests for pwbs.schemas.common module."""

    def test_error_response_model(self) -> None:
        from pwbs.schemas.common import ErrorResponse

        resp = ErrorResponse(code="TEST_ERROR", message="Something failed")
        assert resp.code == "TEST_ERROR"
        assert resp.message == "Something failed"
        assert resp.detail is None

    def test_error_response_with_detail(self) -> None:
        from pwbs.schemas.common import ErrorResponse

        resp = ErrorResponse(code="E", message="M", detail="extra info")
        assert resp.detail == "extra info"

    def test_auth_responses_keys(self) -> None:
        from pwbs.schemas.common import AUTH_RESPONSES

        assert 401 in AUTH_RESPONSES
        assert 403 in AUTH_RESPONSES

    def test_common_responses_keys(self) -> None:
        from pwbs.schemas.common import COMMON_RESPONSES

        assert 422 in COMMON_RESPONSES
        assert 429 in COMMON_RESPONSES
        assert 500 in COMMON_RESPONSES
