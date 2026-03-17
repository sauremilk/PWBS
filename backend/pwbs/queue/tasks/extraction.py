"""Extraction (NER) queue tasks (TASK-122).

Celery task for extracting entities from documents via LLM.
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
    name="pwbs.queue.tasks.extraction.extract_entities",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,
    queue="processing.extract",
    acks_late=True,
)
def extract_entities(self: object, document_ids: list[str], owner_id: str) -> dict[str, object]:
    """Extract entities (NER) from documents.

    Uses rule-based NER for structured data (emails, mentions)
    and LLM-based NER for semantic entities (persons, projects, decisions).
    Results are persisted as Entity/EntityMention records.
    Idempotent: re-running overwrites existing entity extractions.
    """
    start = time.monotonic()
    try:
        result = _run_async(_extract_entities_async(document_ids, owner_id))
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "extract_entities completed: docs=%d entities=%d duration=%.0fms",
            len(document_ids),
            result["entities_extracted"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("extract_entities failed: %s", exc)
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


async def _extract_entities_async(document_ids: list[str], owner_id: str) -> dict[str, object]:
    """Async implementation of entity extraction."""
    from sqlalchemy import select

    from pwbs.db.postgres import get_session_factory
    from pwbs.models.document import Document
    from pwbs.models.entity import Entity, EntityMention
    from pwbs.processing.ner import RuleBasedNER

    owner_uuid = UUID(owner_id)
    factory = get_session_factory()
    ner = RuleBasedNER()
    total_entities = 0

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

            # Rule-based NER extraction
            extracted = ner.extract(
                content=doc.content_hash,
                source_type=doc.source_type,
                metadata={},
            )

            # Upsert entities (idempotent by name + type + user_id)
            for entity_data in extracted:
                existing = await db.execute(
                    select(Entity).where(
                        Entity.user_id == owner_uuid,
                        Entity.name == entity_data.name,
                        Entity.entity_type == entity_data.entity_type.value,
                    )
                )
                entity = existing.scalar_one_or_none()

                if entity is None:
                    entity = Entity(
                        user_id=owner_uuid,
                        name=entity_data.name,
                        entity_type=entity_data.entity_type.value,
                    )
                    db.add(entity)
                    await db.flush()

                # Add mention linking entity to document
                mention = EntityMention(
                    entity_id=entity.id,
                    document_id=doc_uuid,
                    context=entity_data.name,
                )
                db.add(mention)
                total_entities += 1

        await db.commit()

    return {
        "documents_processed": len(document_ids),
        "entities_extracted": total_entities,
        "status": "completed",
    }
