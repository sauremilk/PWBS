"""Shared pytest fixtures for PWBS backend tests (TASK-108).

Provides:
- Environment setup for all tests (JWT keys, encryption master key)
- Mock fixtures for unit tests (LLM, Weaviate, Neo4j, Redis)
- Session-scoped DB fixtures for integration tests (Testcontainers)
- Function-scoped cleanup fixtures

All external dependencies (databases, LLM, HTTP) must be mocked in unit tests.
No real network access in unit tests.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from pwbs.core.config import get_settings

# ---------------------------------------------------------------------------
# Required env vars for Settings instantiation in test mode.
# Set early via pytest_configure so module-level code like
# ``app = create_app()`` can resolve Settings at import time.
# ---------------------------------------------------------------------------

_TEST_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-for-unit-tests",
    "JWT_ALGORITHM": "HS256",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "30",
    "ENCRYPTION_MASTER_KEY": "test-master-key-for-unit-tests",
}


def pytest_configure(config: pytest.Config) -> None:
    """Set required environment variables before test collection."""
    for key, value in _TEST_ENV.items():
        os.environ.setdefault(key, value)
    # Ensure Settings cache is clear so tests start fresh
    get_settings.cache_clear()


@pytest.fixture()
def anyio_backend() -> str:
    """Use asyncio as the default async backend."""
    return "asyncio"


# ---------------------------------------------------------------------------
# Shared test user fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_user_id() -> uuid.UUID:
    """Stable UUID for test user across a single test."""
    return uuid.uuid4()


@pytest.fixture()
def mock_user(test_user_id: uuid.UUID) -> MagicMock:
    """A pre-built mock User object for route-level tests."""
    user = MagicMock()
    user.id = test_user_id
    user.email = "testuser@example.com"
    user.display_name = "Test User"
    user.password_hash = "$argon2id$v=19$m=65536,t=3,p=4$fake"
    user.deletion_scheduled_at = None
    user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return user


# ---------------------------------------------------------------------------
# Mock async DB session fixture (unit tests)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_db() -> AsyncMock:
    """An AsyncMock that mimics an SQLAlchemy AsyncSession.

    Provides pre-configured execute, commit, flush, rollback, add, delete.
    """
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Mock request fixture (for routes that need Request object)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_request() -> MagicMock:
    """A pre-built mock FastAPI Request with headers and client info."""
    request = MagicMock()
    request.headers = {}
    request.client.host = "127.0.0.1"
    return request


# ---------------------------------------------------------------------------
# Mock LLM fixtures (unit tests — no network access)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_llm_response() -> MagicMock:
    """A mock LLM response with typical structure."""
    response = MagicMock()
    response.content = [MagicMock(text="Mock LLM response text")]
    response.model = "claude-test"
    response.usage = MagicMock(input_tokens=100, output_tokens=50)
    response.stop_reason = "end_turn"
    return response


@pytest.fixture()
def mock_anthropic_client(mock_llm_response: MagicMock) -> MagicMock:
    """A mock Anthropic client that returns the mock LLM response."""
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=mock_llm_response)
    return client


@pytest.fixture()
def mock_openai_client(mock_llm_response: MagicMock) -> MagicMock:
    """A mock OpenAI client that returns a mock completion."""
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = "Mock OpenAI response"
    response.choices = [choice]
    response.model = "gpt-4-test"
    response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


# ---------------------------------------------------------------------------
# Mock Weaviate fixture (unit tests)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_weaviate_client() -> MagicMock:
    """A mock Weaviate client with collection/tenant chain."""
    client = MagicMock()
    client.is_connected.return_value = True
    client.is_ready.return_value = True
    client.collections.exists.return_value = True

    collection = MagicMock()
    client.collections.get.return_value = collection

    tenant_col = MagicMock()
    collection.with_tenant.return_value = tenant_col

    batch_ctx = MagicMock()
    tenant_col.batch.dynamic.return_value.__enter__ = MagicMock(return_value=batch_ctx)
    tenant_col.batch.dynamic.return_value.__exit__ = MagicMock(return_value=False)
    tenant_col.batch.failed_objects = []

    collection.tenants.get.return_value = {}

    return client


# ---------------------------------------------------------------------------
# Mock Neo4j fixture (unit tests)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_neo4j_driver() -> MagicMock:
    """A mock Neo4j async driver with session context manager."""
    mock_session = AsyncMock()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    driver = MagicMock()
    driver.session.return_value = mock_ctx
    driver.verify_connectivity = AsyncMock()
    return driver


@pytest.fixture()
def mock_neo4j_session(mock_neo4j_driver: MagicMock) -> AsyncMock:
    """Get the mock session from the mock driver (convenience)."""
    return mock_neo4j_driver.session.return_value.__aenter__.return_value


# ---------------------------------------------------------------------------
# Mock Redis fixture (unit tests)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_redis_client() -> AsyncMock:
    """A mock async Redis client."""
    client = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.scan_iter = AsyncMock(return_value=iter([]))
    return client


# ---------------------------------------------------------------------------
# Session-scoped PostgreSQL fixture for integration tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def pg_engine() -> AsyncGenerator[Any, None]:
    """Session-scoped async engine connected to a Testcontainer PostgreSQL.

    Runs Alembic migrations on startup. Yields the engine.
    Skips if testcontainers is not installed or Docker is not available.
    """
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
    # Convert to asyncpg URL
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
async def pg_session(pg_engine: Any) -> AsyncGenerator[Any, None]:
    """Function-scoped async session for integration tests.

    Each test gets its own session that is rolled back after the test.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Session-scoped fakeredis fixture for integration-like Redis tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def fake_redis() -> AsyncGenerator[Any, None]:
    """Function-scoped fakeredis async client (no real Redis needed)."""
    try:
        import fakeredis.aioredis
    except ImportError:
        pytest.skip("fakeredis not installed")

    server = fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.aclose()
