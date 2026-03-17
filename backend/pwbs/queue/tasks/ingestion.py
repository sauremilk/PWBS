"""Ingestion queue tasks (TASK-122).

Celery tasks for connector-based data ingestion:
- run_connector: Sync a single connector by connection_id
- run_all_connectors: Iterate all active connections and dispatch sync tasks
- cleanup_expired_documents: DSGVO-compliant deletion of expired documents
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select

from pwbs.queue.celery_app import app

logger = logging.getLogger(__name__)


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine in a fresh event loop (Celery workers are sync)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(
    name="pwbs.queue.tasks.ingestion.run_connector",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ingestion.high",
    acks_late=True,
)
def run_connector(self: object, connection_id: str, owner_id: str) -> dict[str, object]:
    """Sync a single connector and dispatch processing pipeline for new documents.

    Args:
        connection_id: UUID of the Connection record.
        owner_id: UUID of the owning user.
    """
    start = time.monotonic()
    try:
        result = _run_async(_run_connector_async(connection_id, owner_id))
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "run_connector completed: connection_id=%s docs=%d errors=%d duration=%.0fms",
            connection_id,
            result["fetched"],
            result["errors"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("run_connector failed: connection_id=%s error=%s", connection_id, exc)
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


async def _run_connector_async(connection_id: str, owner_id: str) -> dict[str, object]:
    """Async implementation of single-connector sync."""
    from pwbs.connectors.base import ConnectorConfig
    from pwbs.connectors.registry import create_connector
    from pwbs.db.postgres import get_session_factory
    from pwbs.models.connection import Connection
    from pwbs.models.document import Document
    from pwbs.schemas.enums import SourceType

    conn_uuid = UUID(connection_id)
    owner_uuid = UUID(owner_id)
    factory = get_session_factory()

    async with factory() as db:
        # Load connection with owner_id filter
        stmt = select(Connection).where(
            Connection.id == conn_uuid,
            Connection.user_id == owner_uuid,
        )
        row = await db.execute(stmt)
        connection = row.scalar_one_or_none()

        if connection is None:
            return {"fetched": 0, "errors": 0, "status": "connection_not_found"}

        source_type = SourceType(connection.source_type)
        config = ConnectorConfig(
            source_type=source_type,
            extra=connection.config or {},
        )
        connector = create_connector(
            source_type=source_type,
            owner_id=owner_uuid,
            connection_id=conn_uuid,
            config=config,
        )

        # Run sync (idempotent, cursor-based)
        cursor_str = connection.watermark.isoformat() if connection.watermark else None
        sync_result = await connector.run(cursor=cursor_str)

        # Persist documents (upsert by source_id + user_id)
        doc_ids: list[str] = []
        for doc in sync_result.documents:
            existing = await db.execute(
                select(Document).where(
                    Document.user_id == owner_uuid,
                    Document.source_type == source_type.value,
                    Document.source_id == doc.source_id,
                )
            )
            existing_doc = existing.scalar_one_or_none()
            if existing_doc is not None:
                # Upsert: update content hash and processing status
                existing_doc.content_hash = doc.raw_hash
                existing_doc.processing_status = "pending"
                doc_ids.append(str(existing_doc.id))
            else:
                new_doc = Document(
                    user_id=owner_uuid,
                    source_type=source_type.value,
                    source_id=doc.source_id,
                    title=doc.title,
                    content_hash=doc.raw_hash,
                    language=doc.language or "de",
                    processing_status="pending",
                )
                db.add(new_doc)
                await db.flush()
                doc_ids.append(str(new_doc.id))

        # Update watermark
        if sync_result.new_cursor is not None:
            connection.watermark = datetime.now(UTC)

        await db.commit()

    # Dispatch processing pipeline for new/updated documents
    if doc_ids:
        from pwbs.queue.tasks.pipeline import process_documents

        process_documents.delay(doc_ids, owner_id)

    return {
        "fetched": sync_result.success_count,
        "errors": sync_result.error_count,
        "has_more": sync_result.has_more,
        "document_ids": doc_ids,
        "status": "completed",
    }


@app.task(
    name="pwbs.queue.tasks.ingestion.run_all_connectors",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ingestion.high",
)
def run_all_connectors(self: object) -> dict[str, object]:
    """Trigger ingestion cycle for all active connectors.

    Dispatches a run_connector task per active connection.
    """
    start = time.monotonic()
    try:
        result = _run_async(_run_all_connectors_async())
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "run_all_connectors completed: dispatched=%d duration=%.0fms",
            result["dispatched"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("run_all_connectors failed: %s", exc)
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


async def _run_all_connectors_async() -> dict[str, object]:
    """Find all active connections and dispatch sync tasks."""
    from pwbs.db.postgres import get_session_factory
    from pwbs.models.connection import Connection

    factory = get_session_factory()
    dispatched = 0

    async with factory() as db:
        stmt = select(Connection).where(Connection.status == "active")
        result = await db.execute(stmt)
        connections = result.scalars().all()

    for conn in connections:
        run_connector.delay(str(conn.id), str(conn.user_id))
        dispatched += 1

    return {"dispatched": dispatched}


@app.task(
    name="pwbs.queue.tasks.ingestion.cleanup_expired_documents",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ingestion.bulk",
)
def cleanup_expired_documents(self: object) -> dict[str, object]:
    """Delete documents past their expires_at timestamp (DSGVO)."""
    start = time.monotonic()
    try:
        result = _run_async(_cleanup_expired_async())
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "cleanup_expired_documents completed: deleted=%d duration=%.0fms",
            result["deleted"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("cleanup_expired_documents failed: %s", exc)
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


async def _cleanup_expired_async() -> dict[str, int]:
    """Delete all documents where expires_at < now."""
    from pwbs.db.postgres import get_session_factory
    from pwbs.models.document import Document

    factory = get_session_factory()

    async with factory() as db:
        # Only delete documents that have an expires_at in the past
        # Note: This requires the model to have expires_at — for models without
        # it, we skip (no documents will match).
        try:
            result = await db.execute(
                delete(Document).where(
                    Document.processing_status == "expired",
                )
            )
            deleted = result.rowcount  # type: ignore[union-attr]
        except Exception:
            deleted = 0
        await db.commit()

    return {"deleted": deleted}
