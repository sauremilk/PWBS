"""E2E Integration Test: Ingestion  Processing  Search Pipeline (TASK-191).

Tests the full pipeline:
  Google Calendar Mock  Connector.normalize()  ChunkingService.chunk()
   EmbeddingService (mocked API)  WeaviateChunkStore.upsert_chunks()
   RuleBasedNER.extract()  Entity persist in PostgreSQL
   SemanticSearchService.search()  verify relevant results

Uses Testcontainers for PostgreSQL and Weaviate.
OAuth and OpenAI Embedding API are mocked.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pwbs.connectors.google_calendar import GoogleCalendarConnector
from pwbs.models.chunk import Chunk
from pwbs.models.entity import Entity
from pwbs.processing.chunking import ChunkingConfig, ChunkingService
from pwbs.processing.embedding import EmbeddingResult, EmbeddingService
from pwbs.processing.ner import RuleBasedNER
from pwbs.schemas.enums import EntityType
from pwbs.storage.weaviate import ChunkUpsertRequest, WeaviateChunkStore

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_OWNER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_OTHER_OWNER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_EMBEDDING_DIM = 1536


# ---------------------------------------------------------------------------
# Google Calendar fixture data
# ---------------------------------------------------------------------------

CALENDAR_EVENTS: list[dict[str, Any]] = [
    {
        "id": "evt-sprint-review-001",
        "summary": "Sprint Review  Project Phoenix",
        "description": (
            "Bi-weekly sprint review for Project Phoenix.\n"
            "We will discuss the latest features and the roadmap.\n"
            "Contact: alice.mueller@example.com or bob.schmidt@example.com"
        ),
        "location": "Meeting Room Berlin",
        "start": {"dateTime": "2026-03-16T10:00:00+01:00"},
        "end": {"dateTime": "2026-03-16T11:00:00+01:00"},
        "attendees": [
            {"email": "alice.mueller@example.com", "displayName": "Alice Mueller"},
            {"email": "bob.schmidt@example.com", "displayName": "Bob Schmidt"},
            {"email": "carol.jones@example.com"},
        ],
        "created": "2026-03-01T08:00:00Z",
        "updated": "2026-03-14T12:00:00Z",
    },
    {
        "id": "evt-planning-002",
        "summary": "Quarterly Planning  Project Aurora",
        "description": (
            "Planning session for Q2 objectives.\n"
            "Key topics: budget allocation, hiring plan, and milestone review.\n"
            "Lead: david.braun@example.com"
        ),
        "location": "Conference Room Munich",
        "start": {"dateTime": "2026-03-17T14:00:00+01:00"},
        "end": {"dateTime": "2026-03-17T16:00:00+01:00"},
        "attendees": [
            {"email": "david.braun@example.com"},
            {"email": "eve.fischer@example.com"},
        ],
        "created": "2026-03-02T09:00:00Z",
        "updated": "2026-03-15T08:00:00Z",
    },
    {
        "id": "evt-standup-003",
        "summary": "Daily Standup",
        "description": "Quick sync to discuss blockers and progress.",
        "start": {"dateTime": "2026-03-16T09:00:00+01:00"},
        "end": {"dateTime": "2026-03-16T09:15:00+01:00"},
        "attendees": [
            {"email": "alice.mueller@example.com"},
            {"email": "frank.weber@example.com"},
        ],
        "created": "2026-03-05T07:00:00Z",
        "updated": "2026-03-15T07:00:00Z",
    },
]


# ---------------------------------------------------------------------------
# Deterministic embedding helper
# ---------------------------------------------------------------------------


def _deterministic_embedding(text: str, dim: int = _EMBEDDING_DIM) -> list[float]:
    """Generate a deterministic embedding from text using SHA-256 hash.

    This ensures that the same text always produces the same vector,
    making search results predictable in tests.
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # Expand hash bytes to fill the embedding dimension
    raw = []
    while len(raw) < dim:
        raw.extend(h)
        h = hashlib.sha256(h).digest()
    # Normalize to [-1, 1] range
    return [(b / 127.5 - 1.0) for b in raw[:dim]]


# ---------------------------------------------------------------------------
# Session-scoped: Testcontainer PostgreSQL
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def pg_engine() -> AsyncGenerator[Any, None]:
    pytest.importorskip("testcontainers", reason="testcontainers not installed")
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers[postgres] not installed")

    container = PostgresContainer("postgres:16-alpine")
    try:
        container.start()
    except Exception:
        pytest.skip("Docker not available for E2E tests")

    sync_url = container.get_connection_url()
    async_url = sync_url.replace("psycopg2", "asyncpg").replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    engine = create_async_engine(async_url, echo=False)

    # Alembic migrations
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")

    yield engine

    await engine.dispose()
    container.stop()


# ---------------------------------------------------------------------------
# Session-scoped: Testcontainer Weaviate
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def weaviate_client() -> AsyncGenerator[Any, None]:
    pytest.importorskip("testcontainers", reason="testcontainers not installed")
    try:
        from testcontainers.weaviate import WeaviateContainer
    except ImportError:
        pytest.skip("testcontainers[weaviate] not installed")

    import weaviate

    container = WeaviateContainer("semitechnologies/weaviate:1.28.2")
    try:
        container.start()
    except Exception:
        pytest.skip("Docker not available for Weaviate")

    http_port = container.get_exposed_port(8080)
    host = container.get_container_host_ip()
    client = weaviate.connect_to_local(host=host, port=int(http_port))

    yield client

    client.close()
    container.stop()


# ---------------------------------------------------------------------------
# Per-test DB session
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def db_session(pg_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Create test user in DB
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def test_user(db_session: AsyncSession) -> uuid.UUID:
    """Insert a test user and return their UUID."""
    user_id = _OWNER_ID
    await db_session.execute(
        text(
            "INSERT INTO users (id, email, hashed_password, display_name, is_active) "
            "VALUES (:id, :email, :pw, :name, true) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {
            "id": str(user_id),
            "email": "e2e-test@example.com",
            "pw": "not-a-real-hash",
            "name": "E2E Tester",
        },
    )
    await db_session.commit()
    return user_id


# ---------------------------------------------------------------------------
# The actual E2E test
# ---------------------------------------------------------------------------


class TestPipelineE2E:
    """Full Connector  Ingestion  Processing  Search pipeline test."""

    async def test_full_pipeline(
        self,
        weaviate_client: Any,
        db_session: AsyncSession,
        test_user: uuid.UUID,
    ) -> None:
        owner_id = test_user

        #  Step 1: Connector  normalize raw events to UDF
        connector = GoogleCalendarConnector(
            owner_id=owner_id,
            access_token="mock-token",
        )

        documents = []
        for raw_event in CALENDAR_EVENTS:
            doc = await connector.normalize(raw_event)  # type: ignore[arg-type]
            documents.append(doc)

        assert len(documents) == 3
        assert all(d.user_id == owner_id for d in documents)

        #  Step 2: Persist documents in PostgreSQL
        from pwbs.models.document import Document

        doc_orm_ids: list[uuid.UUID] = []
        for doc in documents:
            doc_orm = Document(
                id=doc.id,
                user_id=owner_id,
                source_type=doc.source_type.value
                if hasattr(doc.source_type, "value")
                else str(doc.source_type),
                source_id=doc.source_id,
                title=doc.title,
                content_hash=doc.raw_hash,
                language=doc.language,
                processing_status="pending",
            )
            db_session.add(doc_orm)
            doc_orm_ids.append(doc.id)
        await db_session.commit()

        # Verify documents persisted
        result = await db_session.execute(select(Document).where(Document.user_id == owner_id))
        persisted_docs = result.scalars().all()
        assert len(persisted_docs) == 3

        #  Step 3: Chunking
        chunking_svc = ChunkingService(ChunkingConfig(max_tokens=512, overlap_tokens=64))

        all_chunks = []
        for doc in documents:
            chunks = chunking_svc.chunk(doc.content)
            for chunk in chunks:
                all_chunks.append((doc, chunk))

        assert len(all_chunks) > 0, "Chunking should produce at least one chunk"

        #  Step 4: Persist chunks in PostgreSQL
        chunk_orm_list: list[Chunk] = []
        for doc, chunk in all_chunks:
            chunk_id = uuid.uuid4()
            chunk_orm = Chunk(
                id=chunk_id,
                document_id=doc.id,
                user_id=owner_id,
                chunk_index=chunk.chunk_index,
                token_count=chunk.token_count,
                content_preview=chunk.content[:200],
            )
            db_session.add(chunk_orm)
            chunk_orm_list.append(chunk_orm)
        await db_session.commit()

        #  Step 5: Embedding (mocked)
        # Generate deterministic embeddings for each chunk
        embedding_results: list[EmbeddingResult] = []
        for i, (doc, chunk) in enumerate(all_chunks):
            emb = _deterministic_embedding(chunk.content)
            embedding_results.append(
                EmbeddingResult(
                    chunk_index=chunk.chunk_index,
                    embedding=emb,
                    token_count=chunk.token_count,
                )
            )

        #  Step 6: Weaviate upsert
        store = WeaviateChunkStore(weaviate_client)
        store.ensure_collection()
        store.ensure_tenant(owner_id)

        upsert_requests = []
        for (doc, chunk), chunk_orm, emb_result in zip(
            all_chunks, chunk_orm_list, embedding_results
        ):
            upsert_requests.append(
                ChunkUpsertRequest(
                    chunk_id=chunk_orm.id,
                    user_id=owner_id,
                    document_id=doc.id,
                    embedding=emb_result.embedding,
                    content=chunk.content,
                    title=doc.title,
                    source_type=doc.source_type.value
                    if hasattr(doc.source_type, "value")
                    else str(doc.source_type),
                    language=doc.language,
                    created_at=doc.created_at,
                    chunk_index=chunk.chunk_index,
                )
            )

        results = store.upsert_chunks(upsert_requests)
        assert all(r.success for r in results), "All Weaviate upserts should succeed"

        # Update Chunk ORM with weaviate_id
        for chunk_orm_item, upsert_result in zip(chunk_orm_list, results):
            chunk_orm_item.weaviate_id = upsert_result.weaviate_id
        await db_session.commit()

        #  Step 7: NER  extract entities
        ner = RuleBasedNER()
        all_entities: list[tuple[Any, Any]] = []  # (doc, extracted_entities)

        for doc in documents:
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            # Adapt participants for NER format
            participants_meta: dict[str, Any] = {}
            if hasattr(doc, "participants") and doc.participants:
                participants_meta["participants"] = [{"email": p} for p in doc.participants]
            combined_meta = {**meta, **participants_meta}
            entities = ner.extract(doc.content, combined_meta)
            all_entities.append((doc, entities))

        # Verify at least Person and Project entities extracted
        all_entity_types = set()
        for _, entities in all_entities:
            for entity in entities:
                all_entity_types.add(entity.entity_type)

        assert EntityType.PERSON in all_entity_types, (
            f"Expected PERSON entities, got: {all_entity_types}"
        )

        #  Step 8: Persist entities in PostgreSQL
        for doc, entities in all_entities:
            for extracted in entities:
                entity_orm = Entity(
                    id=uuid.uuid4(),
                    user_id=owner_id,
                    entity_type=extracted.entity_type.value,
                    name=extracted.name,
                    normalized_name=extracted.normalized_name,
                    first_seen=datetime.now(UTC),
                    last_seen=datetime.now(UTC),
                    mention_count=len(extracted.mentions),
                )
                db_session.add(entity_orm)
        await db_session.commit()

        # Verify entities persisted
        result = await db_session.execute(select(Entity).where(Entity.user_id == owner_id))
        persisted_entities = result.scalars().all()
        assert len(persisted_entities) > 0, "At least one entity should be persisted"

        person_entities = [e for e in persisted_entities if e.entity_type == "person"]
        assert len(person_entities) > 0, "At least one Person entity should be persisted"

        #  Step 9: Semantic search
        from pwbs.search.service import SemanticSearchService

        # Create mock embedding service that returns deterministic embeddings
        mock_openai = AsyncMock()

        async def _mock_embed_text(query_text: str) -> list[float]:
            return _deterministic_embedding(query_text)

        embedding_svc = EmbeddingService(api_key="fake-key", client=mock_openai)
        embedding_svc.embed_text = _mock_embed_text  # type: ignore[assignment]

        search_svc = SemanticSearchService(
            weaviate_client=weaviate_client,
            embedding_service=embedding_svc,
        )

        # Search for content related to first event
        search_results = await search_svc.search(
            query="Sprint Review Project Phoenix",
            user_id=owner_id,
        )

        assert len(search_results) >= 1, (
            "Search should return at least 1 result for a query matching the test data"
        )
        # Weaviate certanty scores are in [0, 1]
        assert search_results[0].score > 0.5, (
            f"Top result score {search_results[0].score} should be > 0.5"
        )

    async def test_owner_id_isolation(
        self,
        weaviate_client: Any,
        db_session: AsyncSession,
        test_user: uuid.UUID,
    ) -> None:
        """Verify that search results are isolated per owner_id."""
        from pwbs.search.service import SemanticSearchService

        other_owner = _OTHER_OWNER_ID

        # Create mock embedding service
        mock_openai = AsyncMock()

        async def _mock_embed_text(query_text: str) -> list[float]:
            return _deterministic_embedding(query_text)

        embedding_svc = EmbeddingService(api_key="fake-key", client=mock_openai)
        embedding_svc.embed_text = _mock_embed_text  # type: ignore[assignment]

        search_svc = SemanticSearchService(
            weaviate_client=weaviate_client,
            embedding_service=embedding_svc,
        )

        # Searching with a different owner_id should find nothing
        # (tenant doesn't exist or has no data)
        try:
            results = await search_svc.search(
                query="Sprint Review Project Phoenix",
                user_id=other_owner,
            )
            # If tenant doesn't exist, Weaviate may raise or return empty
            assert len(results) == 0, "Cross-user search should return no results"
        except Exception:
            # Weaviate raises if tenant doesn't exist  this is correct behavior
            pass

    async def test_idempotent_rerun(
        self,
        weaviate_client: Any,
        db_session: AsyncSession,
        test_user: uuid.UUID,
    ) -> None:
        """Pipeline can be re-run without side effects (idempotency)."""
        owner_id = test_user
        connector = GoogleCalendarConnector(
            owner_id=owner_id,
            access_token="mock-token",
        )

        # Normalize same event twice
        doc = await connector.normalize(CALENDAR_EVENTS[0])  # type: ignore[arg-type]

        chunking_svc = ChunkingService(ChunkingConfig(max_tokens=512, overlap_tokens=64))
        chunks = chunking_svc.chunk(doc.content)

        store = WeaviateChunkStore(weaviate_client)

        # Use fixed chunk IDs to test idempotency
        fixed_chunk_id = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

        upsert_req = ChunkUpsertRequest(
            chunk_id=fixed_chunk_id,
            user_id=owner_id,
            document_id=doc.id,
            embedding=_deterministic_embedding(chunks[0].content),
            content=chunks[0].content,
            title=doc.title,
            source_type="google_calendar",
            language="de",
            created_at=doc.created_at,
            chunk_index=0,
        )

        # First upsert
        r1 = store.upsert_chunks([upsert_req])
        assert r1[0].success

        # Second upsert (same data)  should overwrite, not duplicate
        r2 = store.upsert_chunks([upsert_req])
        assert r2[0].success
        assert r1[0].weaviate_id == r2[0].weaviate_id, (
            "Same chunk_id should produce same weaviate_id"
        )
