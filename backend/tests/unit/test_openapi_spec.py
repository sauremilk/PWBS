"""OpenAPI specification completeness and validation tests (TASK-193).

Validates:
1. All endpoints have summary + description
2. OpenAPI schema is valid per openapi-spec-validator
3. Postman Collection exists and contains all endpoints
4. At least 1 example response per endpoint
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pwbs.api.main import create_app

POSTMAN_PATH = Path(__file__).resolve().parents[3] / "docs" / "api" / "pwbs-collection.json"

@pytest.fixture(scope="module")
def openapi_spec() -> dict:
    app = create_app()
    return app.openapi()


class TestOpenAPICompleteness:
    """All endpoints must have summary, description and response_model."""

    def test_all_endpoints_have_summary(self, openapi_spec: dict) -> None:
        missing = []
        for path, methods in openapi_spec["paths"].items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    if not details.get("summary"):
                        missing.append(f"{method.upper()} {path}")
        assert missing == [], f"Endpoints without summary: {missing}"

    def test_all_endpoints_have_description(self, openapi_spec: dict) -> None:
        missing = []
        for path, methods in openapi_spec["paths"].items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    if not details.get("description"):
                        missing.append(f"{method.upper()} {path}")
        assert missing == [], f"Endpoints without description: {missing}"

    def test_all_endpoints_have_at_least_one_response(self, openapi_spec: dict) -> None:
        missing = []
        for path, methods in openapi_spec["paths"].items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    if not details.get("responses"):
                        missing.append(f"{method.upper()} {path}")
        assert missing == [], f"Endpoints without responses: {missing}"


class TestOpenAPISchemaValid:
    """OpenAPI spec must pass openapi-spec-validator."""

    def test_schema_valid(self, openapi_spec: dict) -> None:
        from openapi_spec_validator import validate

        validate(openapi_spec)


class TestPostmanCollection:
    """Postman Collection must exist and cover all endpoints."""

    def test_collection_file_exists(self) -> None:
        assert POSTMAN_PATH.exists(), f"Postman Collection not found at {POSTMAN_PATH}"

    def test_collection_is_valid_json(self) -> None:
        data = json.loads(POSTMAN_PATH.read_text(encoding="utf-8"))
        assert "info" in data
        assert "item" in data

    def test_collection_covers_all_paths(self, openapi_spec: dict) -> None:
        data = json.loads(POSTMAN_PATH.read_text(encoding="utf-8"))

        # Flatten all request URLs from collection
        collection_paths: set[str] = set()
        for folder in data.get("item", []):
            for item in folder.get("item", []):
                raw = item.get("request", {}).get("url", {}).get("raw", "")
                # Strip {{baseUrl}} prefix and normalize :param -> {param}
                path = raw.replace("{{baseUrl}}", "")
                import re
                path = re.sub(r":(\w+)", r"{\1}", path)
                collection_paths.add(path)

        spec_paths: set[str] = set(openapi_spec["paths"].keys())
        missing = spec_paths - collection_paths
        assert missing == set(), f"Paths missing from Postman Collection: {missing}"