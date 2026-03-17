"""Integration test fixtures — real PostgreSQL via Testcontainers (TASK-110).

Provides:
- ``app`` / ``client``: FastAPI app with DB dependency overridden to use
  Testcontainer PostgreSQL (Alembic-migrated).
- ``auth_headers``: Convenience fixture that registers a user and returns
  the Bearer-token header dict.
- External services (Weaviate, Neo4j, Redis, LLM) are mocked so that
  integration tests focus on the HTTP ↔ PostgreSQL round-trip.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Ensure test-env vars are set before any settings import
# ---------------------------------------------------------------------------
os.environ.setdefault("JWT_SECRET_KEY", "integration-test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30")
os.environ.setdefault("ENCRYPTION_MASTER_KEY", "integration-test-master-key")


# ---------------------------------------------------------------------------
# Session-scoped PostgreSQL engine (Testcontainers)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def _pg_engine() -> AsyncGenerator[Any, None]:
    """Start Testcontainer PostgreSQL, run Alembic, yield engine."""
    pytest.importorskip("testcontainers", reason="testcontainers not installed")
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers[postgres] not installed")

    from sqlalchemy.ext.asyncio import create_async_engine

    container = PostgresContainer("postgres:16-alpine")
    try:
        container.start()
    except Exception:
        pytest.skip("Docker not available for integration tests")

    sync_url = container.get_connection_url()
    async_url = sync_url.replace("psycopg2", "asyncpg").replace(
        "postgresql://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(async_url, echo=False)

    # Run Alembic migrations
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")

    yield engine

    await engine.dispose()
    container.stop()


@pytest_asyncio.fixture()
async def _pg_session(_pg_engine: Any) -> AsyncGenerator[Any, None]:
    """Per-test async session that rolls back after each test."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(
        _pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI app with overridden dependencies
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def client(
    _pg_session: Any,
) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient with real PostgreSQL and mocked external services."""
    from pwbs.db.postgres import get_db_session

    # Patch external services before importing main (lazy imports inside)
    mock_patches = [
        patch("pwbs.api.main.init_sentry"),
        patch("pwbs.api.main.setup_metrics"),
        # Weaviate
        patch("pwbs.db.weaviate_client.get_weaviate_client", return_value=MagicMock()),
        # Neo4j
        patch("pwbs.db.neo4j_client.get_neo4j_driver", return_value=MagicMock()),
        # Redis
        patch("pwbs.db.redis_client.get_redis_client", return_value=AsyncMock()),
    ]
    for p in mock_patches:
        p.start()

    from pwbs.api.main import create_app

    app = create_app()

    # Override DB session to use Testcontainer session
    async def _override_db() -> AsyncGenerator[Any, None]:
        yield _pg_session

    app.dependency_overrides[get_db_session] = _override_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    for p in mock_patches:
        p.stop()


# ---------------------------------------------------------------------------
# Helpers: register + authenticate
# ---------------------------------------------------------------------------

_REG_COUNTER = 0


def _unique_email() -> str:
    global _REG_COUNTER
    _REG_COUNTER += 1
    return f"inttest_{_REG_COUNTER}_{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture()
async def registered_user(client: AsyncClient) -> dict[str, Any]:
    """Register a fresh user and return {email, password, user_id, tokens}."""
    email = _unique_email()
    password = "IntTest_Passw0rd!"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "Integration Tester",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "email": email,
        "password": password,
        "user_id": data["user_id"],
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
    }


@pytest_asyncio.fixture()
async def auth_headers(registered_user: dict[str, Any]) -> dict[str, str]:
    """Authorization header for the registered user."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}
