"""Performance test fixtures: synthetic data and threshold loading (TASK-170).

Provides fixtures for generating synthetic documents, chunks, and entities
for benchmark measurements. Supports both testcontainer PostgreSQL (local)
and CI service-based PostgreSQL (via PERF_USE_SERVICE_DB / DATABASE_URL).
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
import yaml

# ---------------------------------------------------------------------------
# Threshold loading
# ---------------------------------------------------------------------------

_THRESHOLDS_PATH = Path(__file__).parent / "thresholds.yaml"


def load_thresholds() -> dict[str, Any]:
    """Load performance thresholds from YAML config."""
    with open(_THRESHOLDS_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def perf_thresholds() -> dict[str, Any]:
    """Session-scoped performance thresholds."""
    return load_thresholds()


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------


def _generate_documents(
    user_id: uuid.UUID,
    count: int = 100,
) -> list[dict[str, Any]]:
    """Generate synthetic document dicts for bulk insertion."""
    source_types = ["google_calendar", "notion", "slack", "obsidian", "zoom"]
    docs = []
    for i in range(count):
        content = f"Synthetic document {i} for performance testing. " * 20
        docs.append(
            {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "source_type": source_types[i % len(source_types)],
                "source_id": f"perf-doc-{i}",
                "title": f"Performance Test Document {i}",
                "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                "language": "de",
                "chunk_count": 10,
                "processing_status": "completed",
                "visibility": "private",
            }
        )
    return docs


def _generate_chunks(
    user_id: uuid.UUID,
    documents: list[dict[str, Any]],
    chunks_per_doc: int = 10,
) -> list[dict[str, Any]]:
    """Generate synthetic chunk dicts for bulk insertion."""
    chunks = []
    for doc in documents:
        for j in range(chunks_per_doc):
            chunks.append(
                {
                    "id": uuid.uuid4(),
                    "document_id": doc["id"],
                    "user_id": user_id,
                    "chunk_index": j,
                    "token_count": 256,
                    "content_preview": (
                        f"Chunk {j} of doc {doc['source_id']}: synthetic content for benchmarks."
                    ),
                }
            )
    return chunks


def _generate_entities(
    user_id: uuid.UUID,
    count: int = 50,
) -> list[dict[str, Any]]:
    """Generate synthetic entity dicts for bulk insertion."""
    entity_types = ["person", "project", "topic", "decision"]
    entities = []
    for i in range(count):
        name = f"Entity-{i}"
        entities.append(
            {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "entity_type": entity_types[i % len(entity_types)],
                "name": name,
                "normalized_name": name.lower(),
            }
        )
    return entities


# ---------------------------------------------------------------------------
# Database fixtures (integration — require testcontainers)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def perf_pg_engine() -> Any:
    """Session-scoped Postgres engine for performance tests.

    In CI (PERF_USE_SERVICE_DB=true), uses DATABASE_URL from environment.
    Locally, starts a testcontainer and runs Alembic migrations.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    use_service_db = os.environ.get("PERF_USE_SERVICE_DB", "").lower() == "true"

    if use_service_db:
        # CI mode: use the service-provided PostgreSQL
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            pytest.skip("PERF_USE_SERVICE_DB=true but DATABASE_URL not set")

        engine = create_async_engine(db_url, echo=False, pool_size=5)

        # Run Alembic migrations against service DB
        sync_url = db_url.replace("asyncpg", "psycopg2").replace(
            "postgresql+psycopg2", "postgresql"
        )
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")

        yield engine
        await engine.dispose()
    else:
        # Local mode: testcontainer
        pytest.importorskip("testcontainers", reason="testcontainers not installed")
        try:
            from testcontainers.postgres import PostgresContainer
        except ImportError:
            pytest.skip("testcontainers[postgres] not installed")

        container = PostgresContainer("postgres:16-alpine")
        try:
            container.start()
        except Exception:
            pytest.skip("Docker not available for performance tests")

        sync_url = container.get_connection_url()
        async_url = sync_url.replace("psycopg2", "asyncpg").replace(
            "postgresql://", "postgresql+asyncpg://"
        )

        engine = create_async_engine(async_url, echo=False, pool_size=5)

        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")

        yield engine
        await engine.dispose()
        container.stop()


@pytest_asyncio.fixture(scope="session")
async def perf_synthetic_data(perf_pg_engine: Any) -> dict[str, Any]:
    """Populate the performance test DB with synthetic data.

    Returns metadata about the generated data (user_id, counts).
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(perf_pg_engine, class_=AsyncSession, expire_on_commit=False)

    user_id = uuid.uuid4()

    async with factory() as session:
        # Create test user
        await session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, display_name) "
                "VALUES (:id, :email, :pw, :name)"
            ),
            {
                "id": user_id,
                "email": "perf-test@pwbs.local",
                "pw": "$argon2id$v=19$m=65536,t=3,p=4$perf-test-hash",
                "name": "Perf Test User",
            },
        )

        # Insert documents
        documents = _generate_documents(user_id, count=100)
        for doc in documents:
            await session.execute(
                text(
                    "INSERT INTO documents (id, user_id, source_type, source_id, "
                    "title, content_hash, language, chunk_count, processing_status, visibility) "
                    "VALUES (:id, :user_id, :source_type, :source_id, :title, "
                    ":content_hash, :language, :chunk_count, :processing_status, :visibility)"
                ),
                doc,
            )

        # Insert chunks
        chunks = _generate_chunks(user_id, documents, chunks_per_doc=10)
        for chunk in chunks:
            await session.execute(
                text(
                    "INSERT INTO chunks (id, document_id, user_id, chunk_index, "
                    "token_count, content_preview) "
                    "VALUES (:id, :document_id, :user_id, :chunk_index, "
                    ":token_count, :content_preview)"
                ),
                chunk,
            )

        # Insert entities
        entities = _generate_entities(user_id, count=50)
        for entity in entities:
            await session.execute(
                text(
                    "INSERT INTO entities (id, user_id, entity_type, name, normalized_name) "
                    "VALUES (:id, :user_id, :entity_type, :name, :normalized_name)"
                ),
                entity,
            )

        await session.commit()

    return {
        "user_id": user_id,
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "entity_count": len(entities),
    }


@pytest_asyncio.fixture()
async def perf_session(perf_pg_engine: Any) -> Any:
    """Function-scoped async session for performance tests (no rollback)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(perf_pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
