"""Processing pipeline orchestration (TASK-122).

Orchestrates the processing chain via Celery signatures:
  Ingestion -> Chunking+Embedding -> NER/Entity Extraction -> (Initial Briefing)

Each step is a separate Celery task dispatched to its dedicated queue.
The chain ensures ordering while allowing independent scaling per step.

After the processing chain is dispatched, a separate initial-briefing task
is enqueued for users who have no briefings yet (first-sync experience).
"""

from __future__ import annotations

import logging

from celery import chain

from pwbs.queue.celery_app import app
from pwbs.queue.tasks.embedding import generate_embeddings
from pwbs.queue.tasks.extraction import extract_entities

logger = logging.getLogger(__name__)


@app.task(
    name="pwbs.queue.tasks.pipeline.process_documents",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="processing.embed",
)
def process_documents(
    self: object, document_ids: list[str], owner_id: str
) -> dict[str, object]:
    """Dispatch the full processing pipeline for a batch of documents.

    Pipeline chain:
      1. generate_embeddings (processing.embed queue)
      2. extract_entities (processing.extract queue)

    After dispatching the chain, enqueues an initial-briefing check.
    The briefing task is independent (not chained) so processing
    failure does not block it and vice versa.
    """
    logger.info(
        "Dispatching processing pipeline: docs=%d owner_id=%s",
        len(document_ids),
        owner_id,
    )

    # Build the processing chain
    processing_chain = chain(
        generate_embeddings.s(document_ids, owner_id),
        extract_entities.s(document_ids, owner_id),
    )

    # Dispatch asynchronously
    processing_chain.apply_async()

    # Enqueue initial briefing check (idempotent: no-op if briefings exist)
    from pwbs.queue.tasks.briefing import generate_initial_briefing

    generate_initial_briefing.delay(owner_id)
    logger.info(
        "Enqueued initial briefing check for owner_id=%s",
        owner_id,
    )

    return {
        "dispatched": len(document_ids),
        "pipeline_steps": ["embedding", "extraction", "initial_briefing_check"],
        "status": "dispatched",
    }

