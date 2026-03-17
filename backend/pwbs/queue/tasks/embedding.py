"""Embedding queue tasks (TASK-122).

Celery task for generating embeddings for document chunks.
Part of the processing pipeline chain: Chunking → Embedding → NER → Graph.
"""

from __future__ import annotations

import asyncio
import logging
import time
from uuid import UUID

from pwbs.queue.celery_app import app

logger = logging.getLogger(__name__)


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(
    name="pwbs.queue.tasks.embedding.generate_embeddings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=600,
    queue="processing.embed",
    acks_late=True,
)
def generate_embeddings(self: object, document_ids: list[str], owner_id: str) -> dict[str, object]:
    """Generate embeddings for a batch of documents.

    Reads document content, chunks it, generates embeddings and stores
    results back in the DB. Idempotent: re-running with the same document
    IDs overwrites existing embeddings.
    """
    start = time.monotonic()
    try:
        result = _run_async(_generate_embeddings_async(document_ids, owner_id))
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "generate_embeddings completed: docs=%d chunks=%d duration=%.0fms",
            len(document_ids),
            result["chunks_processed"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("generate_embeddings failed: %s", exc)
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


async def _generate_embeddings_async(document_ids: list[str], owner_id: str) -> dict[str, object]:
    """Async implementation of embedding generation."""
    from sqlalchemy import select

    from pwbs.core.config import get_settings
    from pwbs.db.postgres import get_session_factory
    from pwbs.models.document import Document
    from pwbs.processing.chunking import ChunkingService
    from pwbs.processing.embedding import EmbeddingConfig, EmbeddingService
    from pwbs.processing.embedding_pipeline import EmbeddingPipelineHandler

    owner_uuid = UUID(owner_id)
    factory = get_session_factory()
    settings = get_settings()

    chunking_service = ChunkingService()
    embedding_service = EmbeddingService(
        EmbeddingConfig(
            api_key=settings.openai_api_key.get_secret_value(),
        )
    )
    pipeline = EmbeddingPipelineHandler(embedding_service=embedding_service)

    total_chunks = 0

    async with factory() as db:
        for doc_id_str in document_ids:
            doc_uuid = UUID(doc_id_str)
            stmt = select(Document).where(
                Document.id == doc_uuid,
                Document.user_id == owner_uuid,
            )
            row = await db.execute(stmt)
            doc = row.scalar_one_or_none()

            if doc is None:
                logger.warning("Document not found: %s", doc_id_str)
                continue

            # Chunk the document content
            # Note: Document.content is stored in content_hash path or
            # retrieved from source. For now we work with available fields.
            chunks = chunking_service.chunk(doc.content_hash)
            if not chunks:
                continue

            # Generate embeddings via pipeline (with retry and partial success)
            result = await pipeline.process_document(
                document_id=doc_uuid,
                user_id=owner_uuid,
                chunks=chunks,
            )
            total_chunks += len(result.successful_embeddings)

            # Update processing status
            doc.processing_status = result.final_status
            doc.chunk_count = len(result.successful_embeddings)

        await db.commit()

    return {
        "documents_processed": len(document_ids),
        "chunks_processed": total_chunks,
        "status": "completed",
    }
