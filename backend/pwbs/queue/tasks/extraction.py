"""Extraction queue tasks (TASK-121 stubs, TASK-122 will implement fully)."""

from __future__ import annotations

from pwbs.queue.celery_app import app


@app.task(
    name="pwbs.queue.tasks.extraction.extract_entities",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,
    queue="processing.extract",
)
def extract_entities(self: object, document_ids: list[str]) -> dict[str, str]:
    """Extract entities (NER) from documents via LLM."""
    raise NotImplementedError("TASK-122: Queue-Worker-Migration ausstehend")
