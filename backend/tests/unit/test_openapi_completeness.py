"""OpenAPI schema completeness test (TASK-193).

Ensures every active API endpoint has summary, description and responses
documented in the generated OpenAPI schema.
"""

from __future__ import annotations

import pytest

from pwbs.api.main import create_app


@pytest.fixture
def app():
    return create_app()


class TestOpenAPICompleteness:
    """Verify that all endpoints have complete OpenAPI documentation."""

    def test_schema_has_required_keys(self, app) -> None:
        schema = app.openapi()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert schema["info"]["title"]
        assert schema["info"]["version"]

    def test_all_endpoints_have_summary(self, app) -> None:
        schema = app.openapi()
        missing = []
        for path, methods in schema["paths"].items():
            for method, op in methods.items():
                if not op.get("summary"):
                    missing.append(f"{method.upper()} {path}")
        assert not missing, f"Endpoints missing summary: {missing}"

    def test_all_endpoints_have_description(self, app) -> None:
        schema = app.openapi()
        missing = []
        for path, methods in schema["paths"].items():
            for method, op in methods.items():
                if not op.get("description"):
                    missing.append(f"{method.upper()} {path}")
        assert not missing, f"Endpoints missing description: {missing}"

    def test_all_endpoints_have_responses(self, app) -> None:
        schema = app.openapi()
        missing = []
        for path, methods in schema["paths"].items():
            for method, op in methods.items():
                if not op.get("responses"):
                    missing.append(f"{method.upper()} {path}")
        assert not missing, f"Endpoints missing responses: {missing}"

    def test_minimum_endpoint_count(self, app) -> None:
        """Ensure we haven't accidentally removed routes."""
        schema = app.openapi()
        total = sum(len(methods) for methods in schema["paths"].values())
        assert total >= 70, f"Expected >=70 operations, got {total}"
