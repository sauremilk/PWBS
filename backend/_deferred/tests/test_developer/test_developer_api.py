"""Tests for API Key service and Developer/Public API routes (TASK-150)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from pwbs.developer.api_key_service import (
    ApiKeyError,
    _MAX_KEYS_PER_USER,
    _hash_key,
    generate_raw_key,
)


# ---------------------------------------------------------------------------
# Unit tests: key generation and hashing
# ---------------------------------------------------------------------------


class TestGenerateRawKey:
    def test_prefix(self) -> None:
        key = generate_raw_key()
        assert key.startswith("pwbs_")

    def test_length_reasonable(self) -> None:
        key = generate_raw_key()
        assert len(key) > 20

    def test_unique(self) -> None:
        keys = {generate_raw_key() for _ in range(50)}
        assert len(keys) == 50


class TestHashKey:
    def test_deterministic(self) -> None:
        key = "pwbs_test_key_123"
        assert _hash_key(key) == _hash_key(key)

    def test_sha256_format(self) -> None:
        h = _hash_key("pwbs_test_key_123")
        assert len(h) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_keys_different_hashes(self) -> None:
        h1 = _hash_key("pwbs_key_a")
        h2 = _hash_key("pwbs_key_b")
        assert h1 != h2


# ---------------------------------------------------------------------------
# Unit tests: ApiKey model
# ---------------------------------------------------------------------------


class TestApiKeyModel:
    def test_import(self) -> None:
        from pwbs.models.api_key import ApiKey
        assert ApiKey.__tablename__ == "api_keys"

    def test_table_columns(self) -> None:
        from pwbs.models.api_key import ApiKey
        columns = {c.name for c in ApiKey.__table__.columns}
        expected = {
            "id", "owner_id", "key_hash", "key_prefix", "name",
            "scopes", "rate_limit_per_minute", "is_active",
            "last_used_at", "usage_count", "expires_at",
            "created_at", "updated_at",
        }
        assert expected.issubset(columns)


# ---------------------------------------------------------------------------
# Unit tests: Developer route schemas
# ---------------------------------------------------------------------------


class TestDeveloperSchemas:
    def test_create_key_request_validation(self) -> None:
        from pwbs.api.v1.routes.developer import CreateKeyRequest

        req = CreateKeyRequest(name="My Key", scopes=["read", "search"])
        assert req.name == "My Key"
        assert req.rate_limit_per_minute == 60

    def test_create_key_request_min_name(self) -> None:
        from pwbs.api.v1.routes.developer import CreateKeyRequest

        with pytest.raises(Exception):
            CreateKeyRequest(name="", scopes=["read"])

    def test_create_key_request_max_rate(self) -> None:
        from pwbs.api.v1.routes.developer import CreateKeyRequest

        with pytest.raises(Exception):
            CreateKeyRequest(name="x", rate_limit_per_minute=9999)

    def test_api_key_response_model(self) -> None:
        from pwbs.api.v1.routes.developer import ApiKeyResponse

        data = {
            "id": uuid.uuid4(),
            "name": "Test",
            "key_prefix": "pwbs_abc",
            "scopes": ["read"],
            "rate_limit_per_minute": 60,
            "is_active": True,
            "usage_count": 0,
            "last_used_at": None,
            "created_at": datetime.now(timezone.utc),
            "expires_at": None,
        }
        resp = ApiKeyResponse(**data)
        assert resp.name == "Test"

    def test_api_docs_response(self) -> None:
        from pwbs.api.v1.routes.developer import ApiDocsResponse

        resp = ApiDocsResponse(
            openapi_url="/api/v1/openapi.json",
            docs_url="/api/v1/public/docs",
            version="1.0.0",
            available_scopes=["read"],
            rate_limit_info="60/min",
        )
        assert resp.version == "1.0.0"


# ---------------------------------------------------------------------------
# Unit tests: Public API route schemas
# ---------------------------------------------------------------------------


class TestPublicApiSchemas:
    def test_ingest_request_validation(self) -> None:
        from pwbs.api.v1.routes.public_api import IngestDocumentRequest

        req = IngestDocumentRequest(title="Test", content="Hello world")
        assert req.source_type == "api_upload"
        assert req.metadata is None

    def test_ingest_request_min_title(self) -> None:
        from pwbs.api.v1.routes.public_api import IngestDocumentRequest

        with pytest.raises(Exception):
            IngestDocumentRequest(title="", content="x")

    def test_ingest_request_min_content(self) -> None:
        from pwbs.api.v1.routes.public_api import IngestDocumentRequest

        with pytest.raises(Exception):
            IngestDocumentRequest(title="x", content="")

    def test_search_response(self) -> None:
        from pwbs.api.v1.routes.public_api import PublicSearchResponse

        resp = PublicSearchResponse(results=[], total=0, query="test")
        assert resp.total == 0

    def test_entity_list_response(self) -> None:
        from pwbs.api.v1.routes.public_api import PublicEntityListResponse

        resp = PublicEntityListResponse(entities=[], total=0)
        assert resp.total == 0

    def test_briefings_response(self) -> None:
        from pwbs.api.v1.routes.public_api import PublicBriefingsResponse

        resp = PublicBriefingsResponse(briefings=[])
        assert len(resp.briefings) == 0


# ---------------------------------------------------------------------------
# Unit tests: API Key auth dependency
# ---------------------------------------------------------------------------


class TestApiKeyAuthDependency:
    def test_import(self) -> None:
        from pwbs.api.dependencies.api_key_auth import get_api_key_user
        assert callable(get_api_key_user)


# ---------------------------------------------------------------------------
# Unit tests: migration
# ---------------------------------------------------------------------------


class TestMigration:
    def test_migration_revision(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "m0014",
            "migrations/versions/0014_add_api_keys.py",
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        assert mod.revision == "0014"
        assert mod.down_revision == "0013"


# ---------------------------------------------------------------------------
# Unit tests: service error paths
# ---------------------------------------------------------------------------


class TestApiKeyServiceErrors:
    def test_api_key_error_is_pwbs_error(self) -> None:
        from pwbs.core.exceptions import PWBSError
        err = ApiKeyError("test", code="TEST")
        assert isinstance(err, PWBSError)

    def test_api_key_error_code(self) -> None:
        err = ApiKeyError("msg", code="MY_CODE")
        assert err.code == "MY_CODE"

    def test_max_keys_constant(self) -> None:
        assert _MAX_KEYS_PER_USER == 10


# ---------------------------------------------------------------------------
# Unit tests: developer __init__
# ---------------------------------------------------------------------------


class TestDeveloperPackage:
    def test_import(self) -> None:
        import pwbs.developer
        assert hasattr(pwbs.developer, "__name__")


# ---------------------------------------------------------------------------
# Unit tests: router registration in main app
# ---------------------------------------------------------------------------


class TestRouterRegistration:
    def test_developer_router_mounted(self) -> None:
        from pwbs.api.main import create_app

        app = create_app()
        paths = [r.path for r in app.routes]
        assert any("/api/v1/developer" in p for p in paths)

    def test_public_api_router_mounted(self) -> None:
        from pwbs.api.main import create_app

        app = create_app()
        paths = [r.path for r in app.routes]
        assert any("/api/v1/public" in p for p in paths)


# ---------------------------------------------------------------------------
# Unit tests: scope validation in developer routes
# ---------------------------------------------------------------------------


class TestScopeValidation:
    def test_valid_scopes(self) -> None:
        from pwbs.api.v1.routes.developer import CreateKeyRequest

        req = CreateKeyRequest(name="key", scopes=["read", "write", "search", "briefings"])
        assert len(req.scopes) == 4

    def test_default_scope(self) -> None:
        from pwbs.api.v1.routes.developer import CreateKeyRequest

        req = CreateKeyRequest(name="key")
        assert req.scopes == ["read"]


# ---------------------------------------------------------------------------
# Unit tests: hashing security properties
# ---------------------------------------------------------------------------


class TestHashingSecurity:
    def test_no_raw_key_in_hash(self) -> None:
        """Ensure the hash doesn't contain the raw key (not identity)."""
        raw = "pwbs_secret_test_key"
        h = _hash_key(raw)
        assert raw not in h

    def test_hash_is_consistent(self) -> None:
        raw = generate_raw_key()
        h1 = _hash_key(raw)
        h2 = _hash_key(raw)
        assert h1 == h2
