"""Ingestion queue tasks (TASK-121 stubs, TASK-122 will implement fully)."""

from __future__ import annotations

from pwbs.queue.celery_app import app


@app.task(
    name="pwbs.queue.tasks.ingestion.run_all_connectors",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ingestion.high",
)
def run_all_connectors(self: object) -> dict[str, str]:
    """Trigger ingestion cycle for all active connectors.

    TASK-122 will implement the full pipeline migration.
    """
    raise NotImplementedError("TASK-122: Queue-Worker-Migration ausstehend")


@app.task(
    name="pwbs.queue.tasks.ingestion.cleanup_expired_documents",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ingestion.bulk",
)
def cleanup_expired_documents(self: object) -> dict[str, str]:
    """Delete documents past their expires_at timestamp (DSGVO)."""
    raise NotImplementedError("TASK-122: Queue-Worker-Migration ausstehend")
