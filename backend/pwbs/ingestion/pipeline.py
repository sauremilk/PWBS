"""Ingestion pipeline — orchestrates fetch → normalize → deduplicate → persist.

This module encapsulates the core ingestion logic that was previously
embedded directly in the Celery task layer.  Extracting it makes the
pipeline testable without Celery infrastructure and gives the
``ingestion/`` package real substance.

The Celery tasks in ``pwbs.queue.tasks.ingestion`` delegate to this class.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.connectors.base import ConnectorConfig, SyncResult
from pwbs.connectors.registry import create_connector
from pwbs.models.connection import Connection
from pwbs.models.document import Document
from pwbs.schemas.enums import SourceType

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Result of a single connector ingestion run."""

    fetched: int
    errors: int
    has_more: bool
    document_ids: list[str]
    status: str


class IngestionPipeline:
    """Orchestrates one sync cycle for a single connector.

    Steps:
        1. Load connection + verify ownership
        2. Instantiate connector via registry
        3. Cursor-based fetch (idempotent)
        4. Deduplicate + upsert documents
        5. Update watermark
        6. Return IDs for downstream processing

    Parameters
    ----------
    db:
        An active SQLAlchemy async session (caller manages the transaction).
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def run(self, connection_id: UUID, owner_id: UUID) -> IngestionResult:
        """Execute the full ingestion pipeline for one connection."""
        connection = await self._load_connection(connection_id, owner_id)
        if connection is None:
            return IngestionResult(
                fetched=0,
                errors=0,
                has_more=False,
                document_ids=[],
                status="connection_not_found",
            )

        source_type = SourceType(connection.source_type)
        connector = self._build_connector(
            source_type,
            owner_id,
            connection_id,
            connection.config,
        )

        cursor_str = connection.watermark.isoformat() if connection.watermark else None
        sync_result = await connector.run(cursor=cursor_str)

        doc_ids = await self._upsert_documents(
            sync_result,
            source_type,
            owner_id,
        )

        if sync_result.new_cursor is not None:
            connection.watermark = datetime.now(UTC)

        await self._db.commit()

        return IngestionResult(
            fetched=sync_result.success_count,
            errors=sync_result.error_count,
            has_more=sync_result.has_more,
            document_ids=doc_ids,
            status="completed",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_connection(
        self,
        connection_id: UUID,
        owner_id: UUID,
    ) -> Connection | None:
        """Load connection with owner_id filter (tenant isolation)."""
        stmt = select(Connection).where(
            Connection.id == connection_id,
            Connection.user_id == owner_id,
        )
        row = await self._db.execute(stmt)
        return row.scalar_one_or_none()

    @staticmethod
    def _build_connector(
        source_type: SourceType,
        owner_id: UUID,
        connection_id: UUID,
        config_extra: dict | None,
    ):
        config = ConnectorConfig(
            source_type=source_type,
            extra=config_extra or {},
        )
        return create_connector(
            source_type=source_type,
            owner_id=owner_id,
            connection_id=connection_id,
            config=config,
        )

    async def _upsert_documents(
        self,
        sync_result: SyncResult,
        source_type: SourceType,
        owner_id: UUID,
    ) -> list[str]:
        """Deduplicate and upsert documents by (user_id, source_type, source_id)."""
        doc_ids: list[str] = []

        for doc in sync_result.documents:
            existing = await self._db.execute(
                select(Document).where(
                    Document.user_id == owner_id,
                    Document.source_type == source_type.value,
                    Document.source_id == doc.source_id,
                )
            )
            existing_doc = existing.scalar_one_or_none()

            if existing_doc is not None:
                existing_doc.content_hash = doc.raw_hash
                existing_doc.processing_status = "pending"
                doc_ids.append(str(existing_doc.id))
            else:
                new_doc = Document(
                    user_id=owner_id,
                    source_type=source_type.value,
                    source_id=doc.source_id,
                    title=doc.title,
                    content_hash=doc.raw_hash,
                    language=doc.language or "de",
                    processing_status="pending",
                )
                self._db.add(new_doc)
                await self._db.flush()
                doc_ids.append(str(new_doc.id))

        return doc_ids
