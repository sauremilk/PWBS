"""PWBS application settings.

Pydantic v2 Settings class that loads and validates all configuration
from environment variables / .env file. Secrets use SecretStr to prevent
accidental exposure in logs or repr output.

TASK-012: Pydantic Settings-Konfigurationsklasse implementieren
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration.

    All values are read from environment variables (or .env file).
    Required fields without a default will cause a startup error with
    a clear message if not set.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    #  General 
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    #  PostgreSQL 
    database_url: str = "postgresql+asyncpg://pwbs:pwbs_dev@localhost:5432/pwbs"
    db_pool_min: int = 5
    db_pool_max: int = 20
    weaviate_url: str = "http://localhost:8080"

    #  Neo4j 
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("dev_password")

    #  Redis 
    redis_url: str = "redis://localhost:6379/0"

    #  LLM APIs 
    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")

    #  Authentication 
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    #  Encryption (Envelope Encryption, AES-256) 
    encryption_master_key: SecretStr

    #  OAuth2 Connector Credentials (all optional) 
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    notion_client_id: str = ""
    notion_client_secret: SecretStr = SecretStr("")
    zoom_client_id: str = ""
    zoom_client_secret: SecretStr = SecretStr("")
    slack_client_id: str = ""
    slack_client_secret: SecretStr = SecretStr("")

    #  Derived / computed properties 

    @property
    def debug(self) -> bool:
        """True in development environment."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> Settings:
        """Ensure critical secrets are set in non-development environments."""
        if self.environment != "development":
            if not self.jwt_secret_key.get_secret_value():
                raise ValueError("JWT_SECRET_KEY must be set in non-development environments")
            if self.jwt_secret_key.get_secret_value() == "changeme-generate-a-secure-random-string":
                raise ValueError("JWT_SECRET_KEY must be changed from default in non-development environments")
            if not self.encryption_master_key.get_secret_value():
                raise ValueError(
                    "ENCRYPTION_MASTER_KEY must be set in non-development environments"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton.

    Call `get_settings.cache_clear()` in tests to reset.
    """
    return Settings()  # type: ignore[call-arg]
