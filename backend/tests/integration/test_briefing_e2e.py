"""E2E Integration Test: Briefing-Generierung mit realistischen Testdaten (TASK-192).

Tests the briefing generation flow:
  3 Google Calendar docs indexed (from TASK-191 pipeline)
  -> SemanticSearch finds relevant docs
  -> BriefingGenerator with mock LLM produces morning briefing
  -> BriefingPersistenceService saves to PostgreSQL
  -> Verify: source refs, owner_id, briefing_type, timing

Uses Testcontainers for PostgreSQL and Weaviate.
LLM calls are mocked with deterministic responses.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pwbs.briefing.generator import BriefingGenerator, BriefingLLMResult, BriefingType
from pwbs.briefing.persistence import BriefingPersistenceService
from pwbs.connectors.google_calendar import GoogleCalendarConnector
from pwbs.core.llm_gateway import LLMProvider, LLMResponse, LLMUsage
from pwbs.models.briefing import Briefing as BriefingORM
from pwbs.models.chunk import Chunk
from pwbs.processing.chunking import ChunkingConfig, ChunkingService
from pwbs.processing.embedding import EmbeddingConfig, EmbeddingResult, EmbeddingService
from pwbs.prompts.registry import PromptRegistry
from pwbs.schemas.enums import BriefingType as SchemaBriefingType
from pwbs.search.service import SemanticSearchService
from pwbs.storage.weaviate import ChunkUpsertRequest, WeaviateChunkStore

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_OWNER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_EMBEDDING_DIM = 1536

# ---------------------------------------------------------------------------
# Google Calendar fixture data (same as TASK-191)
# ---------------------------------------------------------------------------

CALENDAR_EVENTS: list[dict[str, Any]] = [
    {
        "id": "evt-sprint-review-001",
        "summary": "Sprint Review \u2013 Project Phoenix",
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
        "summary": "Quarterly Planning \u2013 Project Aurora",
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
# Mock LLM response with source references
# ---------------------------------------------------------------------------

MOCK_BRIEFING_CONTENT = """\
## Morgenbriefing f\u00fcr 2026-03-16

### Heutige Termine

- **Sprint Review \u2013 Project Phoenix** (10:00\u201311:00): \
Bi-weekly Sprint Review mit Alice Mueller und Bob Schmidt. \
Letzte Ergebnisse und Roadmap werden besprochen. \
[Quelle: Sprint Review \u2013 Project Phoenix, 2026-03-16]

- **Daily Standup** (09:00\u201309:15): \
Kurzes Sync-Meeting zu Blockern und Fortschritt. \
[Quelle: Daily Standup, 2026-03-16]

### Relevante Themen

- Die Quarterly Planning f\u00fcr Project Aurora steht am 17.03. an. \
Key Topics: Budget, Hiring, Milestone Review. \
[Quelle: Quarterly Planning \u2013 Project Aurora, 2026-03-17]

### Empfehlungen

- Vor dem Sprint Review die aktuellen Feature-Demos vorbereiten.
- Budget-Allocations f\u00fcr Q2 pr\u00fcfen.
"""


# ---------------------------------------------------------------------------
# Deterministic embedding helper (same as TASK-191)
# ---------------------------------------------------------------------------


def _deterministic_embedding(text_input: str, dim: int = _EMBEDDING_DIM) -> list[float]:
    h = hashlib.sha256(text_input.encode("utf-8")).digest()
    raw: list[int] = []
    while len(raw) < dim:
        raw.extend(h)
        h = hashlib.sha256(h).digest()
    return [(b / 127.5 - 1.0) for b in raw[:dim]]


# ---------------------------------------------------------------------------
# Testcontainer PostgreSQL
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

    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")

    yield engine
    await engine.dispose()
    container.stop()


# ---------------------------------------------------------------------------
# Testcontainer Weaviate
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
# Create test user
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def test_user(db_session: AsyncSession) -> uuid.UUID:
    user_id = _OWNER_ID
    await db_session.execute(
        text(
            "INSERT INTO users (id, email, hashed_password, display_name, is_active) "
            "VALUES (:id, :email, :pw, :name, true) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {
            "id": str(user_id),
            "email": "briefing-e2e@example.com",
            "pw": "not-a-real-hash",
            "name": "Briefing E2E Tester",
        },
    )
    await db_session.commit()
    return user_id


# ---------------------------------------------------------------------------
# Index pipeline: normalize, chunk, embed, upsert (shared setup)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def indexed_chunks(
    weaviate_client: Any,
    db_session: AsyncSession,
    test_user: uuid.UUID,
) -> list[uuid.UUID]:
    """Run the ingestion pipeline and return chunk UUIDs."""
    from pwbs.models.document import Document

    owner_id = test_user
    connector = GoogleCalendarConnector(owner_id=owner_id, access_token="mock-token")

    documents = []
    for raw_event in CALENDAR_EVENTS:
        doc = await connector.normalize(raw_event)  # type: ignore[arg-type]
        documents.append(doc)

    # Persist documents
    for doc in documents:
        doc_orm = Document(
            id=doc.id,
            user_id=owner_id,
            source_type=doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type),
            source_id=doc.source_id,
            title=doc.title,
            content_hash=doc.raw_hash,
            language=doc.language,
            processing_status="pending",
        )
        db_session.add(doc_orm)
    await db_session.commit()

    # Chunk
    chunking_svc = ChunkingService(ChunkingConfig(max_tokens=512, overlap_tokens=64))
    all_chunks: list[tuple[Any, Any]] = []
    for doc in documents:
        chunks = chunking_svc.chunk(doc.content)
        for chunk in chunks:
            all_chunks.append((doc, chunk))

    # Persist chunks
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

    # Embed + upsert to Weaviate
    store = WeaviateChunkStore(weaviate_client)
    store.ensure_collection()
    store.ensure_tenant(owner_id)

    upsert_requests = []
    embedding_results = []
    for (doc, chunk), chunk_orm in zip(all_chunks, chunk_orm_list):
        emb = _deterministic_embedding(chunk.content)
        embedding_results.append(emb)
        upsert_requests.append(
            ChunkUpsertRequest(
                chunk_id=chunk_orm.id,
                user_id=owner_id,
                document_id=doc.id,
                embedding=emb,
                content=chunk.content,
                title=doc.title,
                source_type=doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type),
                language=doc.language,
                created_at=doc.created_at,
                chunk_index=chunk.chunk_index,
            )
        )

    results = store.upsert_chunks(upsert_requests)
    assert all(r.success for r in results)

    for chunk_orm_item, upsert_result in zip(chunk_orm_list, results):
        chunk_orm_item.weaviate_id = upsert_result.weaviate_id
    await db_session.commit()

    return [c.id for c in chunk_orm_list]


# ---------------------------------------------------------------------------
# Mock LLM Gateway
# ---------------------------------------------------------------------------


def _make_mock_llm_response() -> LLMResponse:
    return LLMResponse(
        content=MOCK_BRIEFING_CONTENT,
        usage=LLMUsage(
            provider=LLMProvider.CLAUDE,
            model="claude-sonnet-4-20250514",
            input_tokens=1200,
            output_tokens=350,
            duration_ms=800.0,
            estimated_cost_usd=0.005,
        ),
        provider=LLMProvider.CLAUDE,
        model="claude-sonnet-4-20250514",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBriefingE2E:
    """Briefing generation E2E test with real DB and Weaviate."""

    async def test_morning_briefing_generation(
        self,
        weaviate_client: Any,
        db_session: AsyncSession,
        test_user: uuid.UUID,
        indexed_chunks: list[uuid.UUID],
    ) -> None:
        """AC1-4: Generate morning briefing from 3+ indexed docs,
        verify source refs, persistence, and timing."""
        owner_id = test_user
        start_time = time.monotonic()

        # --- Step 1: Semantic search to get relevant docs ---
        mock_openai = AsyncMock()

        async def _mock_embed_text(query_text: str) -> list[float]:
            return _deterministic_embedding(query_text)

        embedding_svc = EmbeddingService(api_key="fake-key", client=mock_openai)
        embedding_svc.embed_text = _mock_embed_text  # type: ignore[assignment]

        search_svc = SemanticSearchService(
            weaviate_client=weaviate_client,
            embedding_service=embedding_svc,
        )

        search_results = await search_svc.search(
            query="Sprint Review Project Phoenix Quarterly Planning Daily Standup",
            user_id=owner_id,
        )
        assert len(search_results) >= 1, "Search should return results from indexed docs"

        # --- Step 2: Build context for morning briefing template ---
        context: dict[str, Any] = {
            "date": "2026-03-16",
            "calendar_events": [
                {
                    "title": "Sprint Review \u2013 Project Phoenix",
                    "time": "10:00\u201311:00",
                    "notes": "Bi-weekly sprint review. Alice Mueller, Bob Schmidt.",
                },
                {
                    "title": "Daily Standup",
                    "time": "09:00\u201309:15",
                    "notes": "Quick sync on blockers and progress.",
                },
                {
                    "title": "Quarterly Planning \u2013 Project Aurora",
                    "time": "14:00\u201316:00",
                    "notes": "Q2 objectives: budget, hiring, milestones.",
                },
            ],
            "recent_documents": [
                {
                    "title": r.title,
                    "source": r.source_type,
                    "date": r.created_at,
                }
                for r in search_results[:5]
            ],
        }

        known_sources = [
            {"title": r.title, "source_id": str(r.chunk_id)}
            for r in search_results[:5]
        ]

        # --- Step 3: Generate briefing with mock LLM ---
        registry = PromptRegistry()
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=_make_mock_llm_response())

        generator = BriefingGenerator(mock_llm, registry)
        result = await generator.generate(
            briefing_type=BriefingType.MORNING,
            context=context,
            user_id=owner_id,
            known_sources=known_sources,
        )

        assert isinstance(result, BriefingLLMResult)
        assert result.briefing_type == BriefingType.MORNING
        assert result.content != ""

        # AC2: Verify at least 2 source references in content
        source_ref_count = result.content.count("[Quelle:")
        assert source_ref_count >= 2, (
            f"Briefing should contain >= 2 source references, found {source_ref_count}"
        )

        # --- Step 4: Persist briefing ---
        source_chunk_ids = [r.chunk_id for r in search_results[:3]]
        persistence = BriefingPersistenceService(db_session)
        persisted = await persistence.save(
            user_id=owner_id,
            briefing_type=SchemaBriefingType.MORNING,
            title="Morning Briefing",
            content=result.content,
            source_chunks=source_chunk_ids,
            trigger_context={"generated_by": "e2e_test"},
        )
        await db_session.commit()

        # AC3: Verify briefing persisted with correct owner_id and briefing_type
        stmt = select(BriefingORM).where(BriefingORM.id == persisted.id)
        db_result = await db_session.execute(stmt)
        briefing_row = db_result.scalar_one()

        assert briefing_row.user_id == owner_id
        assert briefing_row.briefing_type == "morning"
        assert briefing_row.content == result.content
        assert len(briefing_row.source_chunks) >= 1

        # AC2 continued: Verify source_chunks contain valid chunk UUIDs
        for chunk_id in briefing_row.source_chunks:
            assert chunk_id in indexed_chunks, (
                f"source_chunk {chunk_id} should be a valid indexed chunk"
            )

        # AC4: Timing check (< 15 seconds with Mock-LLM)
        elapsed = time.monotonic() - start_time
        assert elapsed < 15.0, (
            f"Briefing generation took {elapsed:.1f}s, should be < 15s with mock LLM"
        )

    async def test_briefing_source_refs_have_valid_source_ids(
        self,
        weaviate_client: Any,
        db_session: AsyncSession,
        test_user: uuid.UUID,
        indexed_chunks: list[uuid.UUID],
    ) -> None:
        """Verify that [Quelle: ...] references in the briefing match
        actual source document titles."""
        import re

        owner_id = test_user

        # Search
        mock_openai = AsyncMock()

        async def _mock_embed_text(query_text: str) -> list[float]:
            return _deterministic_embedding(query_text)

        embedding_svc = EmbeddingService(api_key="fake-key", client=mock_openai)
        embedding_svc.embed_text = _mock_embed_text  # type: ignore[assignment]

        search_svc = SemanticSearchService(
            weaviate_client=weaviate_client,
            embedding_service=embedding_svc,
        )

        search_results = await search_svc.search(
            query="Sprint Review Project Phoenix calendar events",
            user_id=owner_id,
        )

        context: dict[str, Any] = {
            "date": "2026-03-16",
            "calendar_events": [
                {"title": "Sprint Review", "time": "10:00", "notes": "Review"},
                {"title": "Daily Standup", "time": "09:00", "notes": "Sync"},
                {"title": "Quarterly Planning", "time": "14:00", "notes": "Q2"},
            ],
            "recent_documents": [
                {"title": r.title, "source": r.source_type, "date": r.created_at}
                for r in search_results[:5]
            ],
        }

        registry = PromptRegistry()
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=_make_mock_llm_response())

        generator = BriefingGenerator(mock_llm, registry)
        result = await generator.generate(
            briefing_type=BriefingType.MORNING,
            context=context,
            user_id=owner_id,
        )

        # Extract all [Quelle: TITLE, DATE] references
        refs = re.findall(r"\[Quelle:\s*([^,\]]+)", result.content)
        assert len(refs) >= 2, f"Expected >= 2 source refs, got {len(refs)}: {refs}"

        # Each reference should mention a known event title (partial match)
        known_titles = {ev["summary"].lower() for ev in CALENDAR_EVENTS}
        for ref in refs:
            ref_lower = ref.strip().lower()
            matches_any = any(
                # Check if the reference contains part of any known title
                any(word in ref_lower for word in title.split() if len(word) > 3)
                for title in known_titles
            )
            assert matches_any, (
                f"Source ref '{ref}' should match a known event title from {known_titles}"
            )

    async def test_briefing_generation_timing(
        self,
        weaviate_client: Any,
        db_session: AsyncSession,
        test_user: uuid.UUID,
        indexed_chunks: list[uuid.UUID],
    ) -> None:
        """AC4: Dedicated timing test - generation must complete in < 15s."""
        owner_id = test_user

        context: dict[str, Any] = {
            "date": "2026-03-16",
            "calendar_events": [
                {"title": "Event 1", "time": "09:00", "notes": "Note 1"},
                {"title": "Event 2", "time": "10:00", "notes": "Note 2"},
                {"title": "Event 3", "time": "14:00", "notes": "Note 3"},
            ],
            "recent_documents": [],
        }

        registry = PromptRegistry()
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=_make_mock_llm_response())

        generator = BriefingGenerator(mock_llm, registry)

        start = time.monotonic()
        result = await generator.generate(
            briefing_type=BriefingType.MORNING,
            context=context,
            user_id=owner_id,
        )
        elapsed = time.monotonic() - start

        assert result.content != ""
        assert elapsed < 15.0, f"Generation took {elapsed:.2f}s, limit is 15s"
        # With mock LLM this should be near-instant (< 1s)
        assert elapsed < 1.0, f"Mock-LLM generation should be < 1s, took {elapsed:.2f}s"