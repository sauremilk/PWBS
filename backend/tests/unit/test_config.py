"""Tests for pwbs.core.config Settings class (TASK-012)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from pwbs.core.config import Settings, get_settings

# Minimal kwargs required for Settings to instantiate (field names, not env var names)
MINIMAL_KWARGS: dict[str, str] = {
    "jwt_secret_key": "test-secret-key-for-unit-tests",
    "encryption_master_key": "test-master-key-for-unit-tests",
}

# Same values as env var names (for patching os.environ)
MINIMAL_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-for-unit-tests",
    "ENCRYPTION_MASTER_KEY": "test-master-key-for-unit-tests",
}


class TestSettingsDefaults:
    """Verify default values in development mode."""

    def test_defaults_with_minimal_kwargs(self) -> None:
        settings = Settings(**MINIMAL_KWARGS)  # type: ignore[arg-type]
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.cors_origins == ["http://localhost:3000"]
        assert settings.database_url == "postgresql+asyncpg://pwbs:pwbs_dev@localhost:5432/pwbs"
        assert settings.weaviate_url == "http://localhost:8080"
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.neo4j_user == "neo4j"
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_access_token_expire_minutes == 15

    def test_debug_true_in_development(self) -> None:
        settings = Settings(**MINIMAL_KWARGS)  # type: ignore[arg-type]
        assert settings.debug is True
        assert settings.is_production is False

    def test_debug_false_in_production(self) -> None:
        settings = Settings(
            environment="production",
            jwt_secret_key=SecretStr("real-prod-key"),
            encryption_master_key=SecretStr("real-prod-master-key"),
        )
        assert settings.debug is False
        assert settings.is_production is True


class TestSettingsValidation:
    """Verify validation rules."""

    def test_missing_jwt_secret_key_raises(self) -> None:
        env = {k: v for k, v in os.environ.items() if k.upper() != "JWT_SECRET_KEY"}
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValidationError):
            Settings(encryption_master_key=SecretStr("key"))  # type: ignore[call-arg]

    def test_missing_encryption_master_key_raises(self) -> None:
        env = {k: v for k, v in os.environ.items() if k.upper() != "ENCRYPTION_MASTER_KEY"}
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValidationError):
            Settings(jwt_secret_key=SecretStr("key"))  # type: ignore[call-arg]

    def test_invalid_environment_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(
                environment="invalid",  # type: ignore[arg-type]
                **MINIMAL_KWARGS,
            )

    def test_invalid_log_level_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(
                log_level="TRACE",  # type: ignore[arg-type]
                **MINIMAL_KWARGS,
            )

    def test_production_rejects_default_jwt_key(self) -> None:
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be changed"):
            Settings(
                environment="production",
                jwt_secret_key=SecretStr("changeme-generate-a-secure-random-string"),
                encryption_master_key=SecretStr("real-key"),
            )

    def test_production_rejects_empty_jwt_key(self) -> None:
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be set"):
            Settings(
                environment="production",
                jwt_secret_key=SecretStr(""),
                encryption_master_key=SecretStr("real-key"),
            )

    def test_production_rejects_empty_encryption_key(self) -> None:
        with pytest.raises(ValidationError, match="ENCRYPTION_MASTER_KEY must be set"):
            Settings(
                environment="production",
                jwt_secret_key=SecretStr("real-prod-key"),
                encryption_master_key=SecretStr(""),
            )


class TestSettingsSecretStr:
    """Verify secrets are masked in repr and logs."""

    def test_secrets_masked_in_repr(self) -> None:
        settings = Settings(**MINIMAL_KWARGS)  # type: ignore[arg-type]
        repr_str = repr(settings)
        assert "test-secret-key-for-unit-tests" not in repr_str
        assert "test-master-key-for-unit-tests" not in repr_str

    def test_secret_accessible_via_get_secret_value(self) -> None:
        settings = Settings(**MINIMAL_KWARGS)  # type: ignore[arg-type]
        assert settings.jwt_secret_key.get_secret_value() == "test-secret-key-for-unit-tests"
        assert settings.encryption_master_key.get_secret_value() == "test-master-key-for-unit-tests"

    def test_neo4j_password_is_secret(self) -> None:
        settings = Settings(**MINIMAL_KWARGS)  # type: ignore[arg-type]
        assert isinstance(settings.neo4j_password, SecretStr)
        assert settings.neo4j_password.get_secret_value() == "dev_password"


class TestGetSettings:
    """Verify singleton caching."""

    def test_get_settings_returns_same_instance(self) -> None:
        get_settings.cache_clear()
        env = {**MINIMAL_ENV}
        with patch.dict(os.environ, env, clear=False):
            s1 = get_settings()
            s2 = get_settings()
            assert s1 is s2
        get_settings.cache_clear()

    def test_cache_clear_creates_new_instance(self) -> None:
        get_settings.cache_clear()
        env = {**MINIMAL_ENV}
        with patch.dict(os.environ, env, clear=False):
            s1 = get_settings()
            get_settings.cache_clear()
            s2 = get_settings()
            assert s1 is not s2
        get_settings.cache_clear()
