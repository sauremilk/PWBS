"""Processing pipeline orchestration (TASK-122).

Orchestrates the processing chain via Celery signatures:
  Ingestion -> Chunking+Embedding -> NER/Entity Extraction

Each step is a separate Celery task dispatched to its dedicated queue.
The chain ensures ordering while allowing independent scaling per step.
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

    Uses Celery chain to ensure sequential execution while allowing
    each step to run on its dedicated worker pool.
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

    return {
        "dispatched": len(document_ids),
        "pipeline_steps": ["embedding", "extraction"],
        "status": "dispatched",
    }

