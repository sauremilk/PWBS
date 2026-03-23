"""Ingestion orchestration.

Core logic: :class:`IngestionPipeline` — fetch → normalize → deduplicate → persist.

Celery integration:
    pwbs.queue.tasks.ingestion  – per-connector sync tasks
    pwbs.queue.tasks.pipeline   – end-to-end ingest → process chain
"""

from pwbs.ingestion.pipeline import IngestionPipeline, IngestionResult

__all__ = ["IngestionPipeline", "IngestionResult"]
