"""Embedding queue tasks (TASK-121 stubs, TASK-122 will implement fully)."""

from __future__ import annotations

from pwbs.queue.celery_app import app


@app.task(
    name="pwbs.queue.tasks.embedding.generate_embeddings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=600,
    queue="processing.embed",
)
def generate_embeddings(self: object, document_ids: list[str]) -> dict[str, str]:
    """Generate embeddings for a batch of documents."""
    raise NotImplementedError("TASK-122: Queue-Worker-Migration ausstehend")
