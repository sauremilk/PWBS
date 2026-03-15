"""PWBS application settings.

Pydantic v2 Settings class that loads and validates all configuration
from environment variables / .env file. Secrets use SecretStr to prevent
accidental exposure in logs or repr output.

TASK-012: Pydantic Settings-Konfigurationsklasse implementieren
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
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
        populate_by_name=True,
    )

    #  General
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        validation_alias=AliasChoices("pwbs_log_level", "log_level"),
    )
    cors_origins: list[str] = ["http://localhost:3000"]
    trusted_hosts: list[str] = ["*"]  # restrict in production via env

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

    #  Celery (TASK-121)
    celery_broker_url: str = ""  # falls leer, wird redis_url verwendet
    celery_result_backend: str = ""  # falls leer, redis_url DB 1

    #  LLM APIs
    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    ollama_base_url: str = ""  # e.g. http://ollama:11434 for self-hosting
    ollama_model: str = "llama3.1"
    llm_provider: str = "claude"  # claude | gpt4 | ollama

    #  Authentication
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "RS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30
    jwt_private_key: SecretStr = SecretStr("")
    jwt_public_key: str = ""

    #  Sentry (TASK-115)
    sentry_dsn: str = ""  # empty = disabled
    sentry_traces_sample_rate: float = 1.0

    #  DSGVO Export (TASK-104)
    export_dir: str = "data/exports"

    #  Rate Limiting (TASK-085)
    rate_limit_general_max: int = 100
    rate_limit_general_window: int = 60  # seconds
    rate_limit_auth_max: int = 5
    rate_limit_auth_window: int = 60  # seconds
    rate_limit_sync_max: int = 1
    rate_limit_sync_window: int = 300  # 5 minutes

    #  Encryption (Envelope Encryption, AES-256)
    encryption_master_key: SecretStr

    #  OAuth2 Connector Credentials (all optional)
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    google_oauth_redirect_uri: str = "http://localhost:3000/api/connectors/google-calendar/callback"
    google_login_redirect_uri: str = "http://localhost:3000/api/auth/google/callback"
    gmail_oauth_redirect_uri: str = "http://localhost:3000/api/connectors/gmail/callback"
    gmail_pubsub_topic: str = ""  # e.g. projects/my-proj/topics/pwbs-gmail
    notion_oauth_redirect_uri: str = "http://localhost:3000/api/connectors/notion/callback"
    notion_client_id: str = ""
    notion_client_secret: SecretStr = SecretStr("")
    zoom_client_id: str = ""
    zoom_client_secret: SecretStr = SecretStr("")
    zoom_oauth_redirect_uri: str = "http://localhost:3000/api/connectors/zoom/callback"
    zoom_webhook_secret_token: str = ""
    slack_client_id: str = ""
    slack_client_secret: SecretStr = SecretStr("")
    slack_oauth_redirect_uri: str = "http://localhost:3000/api/connectors/slack/callback"
    slack_signing_secret: str = ""
    ms_client_id: str = ""
    ms_client_secret: SecretStr = SecretStr("")
    ms_tenant_id: str = "common"
    ms_oauth_redirect_uri: str = "http://localhost:3000/api/connectors/outlook-mail/callback"

    #  Stripe (TASK-137)
    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    stripe_price_id_pro: str = ""  # Stripe Price ID for the Pro plan
    stripe_free_connector_limit: int = 1
    stripe_free_search_daily_limit: int = 3

    #  Email (TASK-176)
    email_provider: str = "smtp"  # "smtp" | "sendgrid"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_use_tls: bool = True
    sendgrid_api_key: SecretStr = SecretStr("")
    email_from_address: str = "noreply@pwbs.app"
    email_from_name: str = "PWBS"
    email_unsubscribe_url: str = "http://localhost:3000/settings/notifications"
    email_impressum_url: str = "http://localhost:3000/impressum"

    #  Search Tuning (TASK-201)
    search_semantic_weight: float = 0.75
    search_keyword_weight: float = 0.25
    search_recency_boost_pct: float = 0.10  # +10% score bonus for recent docs
    search_recency_boost_days: int = 7

    #  Feature Flags (TASK-174)
    feature_flags_override: str = ""  # e.g. "flag1:true,flag2:false"

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
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from default in non-development environments"
                )
            if not self.encryption_master_key.get_secret_value():
                raise ValueError(
                    "ENCRYPTION_MASTER_KEY must be set in non-development environments"
                )
            # CORS: no wildcard in production (TASK-093)
            if "*" in self.cors_origins:
                raise ValueError(
                    "Wildcard CORS_ORIGINS not allowed in non-development environments"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton.

    Call `get_settings.cache_clear()` in tests to reset.
    """
    return Settings()  # type: ignore[call-arg]
