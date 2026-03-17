"""Ingestion orchestration facade.

Ingestion logic lives in the Celery task layer::

    pwbs.queue.tasks.ingestion  – per-connector sync tasks
    pwbs.queue.tasks.pipeline   – end-to-end ingest → process chain

Import from those modules directly; this package is a namespace stub.
"""
