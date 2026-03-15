"""DSGVO Data Export Service (TASK-104).

Collects all user data from PostgreSQL, packages it as a ZIP file
(JSON + Markdown), and tracks export job lifecycle.

DSGVO Art. 15 (Auskunftsrecht) and Art. 20 (Datenportabilitaet).
"""

from __future__ import annotations

import io
import json
import logging
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pwbs.models.audit_log import AuditLog
from pwbs.models.briefing import Briefing
from pwbs.models.chunk import Chunk
from pwbs.models.data_export import DataExport
from pwbs.models.document import Document
from pwbs.models.entity import Entity
from pwbs.models.llm_audit_log import LlmAuditLog

logger = logging.getLogger(__name__)

_EXPORT_EXPIRY_HOURS = 24
_EXPORT_EMAIL_THRESHOLD_SECONDS = 60

_EXPORT_README = """\
# PWBS Datenexport (DSGVO Art. 20)

Dieser Export enthält alle Ihre im PWBS gespeicherten Daten.

## Inhalt

| Datei/Ordner       | Format   | Beschreibung                              |
| ------------------ | -------- | ----------------------------------------- |
| `documents.json`   | JSON     | Alle importierten Dokumente (Metadaten)   |
| `entities.json`    | JSON     | Extrahierte Entitäten (Personen, Projekte)|
| `briefings.json`   | JSON     | Generierte Briefings (maschinenlesbar)    |
| `briefings/`       | Markdown | Briefings als lesbare Textdateien         |
| `chunks/`          | Markdown | Textsegmente pro Dokument                 |
| `audit_log.json`   | JSON     | Aktivitätsprotokoll (keine PII)           |
| `llm_usage.json`   | JSON     | Protokoll der KI-Nutzung                  |

## Hinweise

- Alle Daten gehören ausschließlich zu Ihrem Benutzerkonto.
- Zeitstempel sind in UTC (ISO 8601).
- Dieser Export ist 24 Stunden nach Erstellung gültig.
- Bei Fragen wenden Sie sich an den Datenschutzbeauftragten.
"""


async def check_running_export(user_id: uuid.UUID, db: AsyncSession) -> DataExport | None:
    """Return an in-progress export for the user, or None."""
    stmt = (
        select(DataExport)
        .where(DataExport.user_id == user_id, DataExport.status == "processing")
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_export_job(user_id: uuid.UUID, db: AsyncSession) -> DataExport:
    """Create a new export job record with status=processing."""
    export = DataExport(
        id=uuid.uuid4(),
        user_id=user_id,
        status="processing",
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)
    return export


async def get_export(
    export_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> DataExport | None:
    """Fetch an export job owned by the given user."""
    stmt = select(DataExport).where(
        DataExport.id == export_id,
        DataExport.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def run_export(
    export_id: uuid.UUID,
    user_id: uuid.UUID,
    database_url: str,
    export_dir: str,
    user_email: str | None = None,
) -> None:
    """Background task: collect all user data and create ZIP.

    Runs in its own DB session (background tasks outlive the request).
    If the export takes longer than 60 seconds and *user_email* is
    provided, a notification email is sent with the download link
    (TASK-202).
    """
    start_time = time.monotonic()
    engine = create_async_engine(database_url, pool_size=2, max_overflow=0)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            documents = await _collect_documents(user_id, session)
            chunks = await _collect_chunks(user_id, session)
            entities = await _collect_entities(user_id, session)
            briefings = await _collect_briefings(user_id, session)
            audit_entries = await _collect_audit_log(user_id, session)
            llm_usage = await _collect_llm_audit_log(user_id, session)

            zip_bytes = _build_zip(
                documents=documents,
                chunks=chunks,
                entities=entities,
                briefings=briefings,
                audit_entries=audit_entries,
                llm_usage=llm_usage,
            )

            export_path = Path(export_dir)
            export_path.mkdir(parents=True, exist_ok=True)
            file_name = f"{export_id}.zip"
            file_path = export_path / file_name
            file_path.write_bytes(zip_bytes)

            now = datetime.now(tz=timezone.utc)
            stmt = select(DataExport).where(DataExport.id == export_id)
            result = await session.execute(stmt)
            export_record = result.scalar_one()
            export_record.status = "completed"
            export_record.file_path = str(file_path)
            export_record.completed_at = now
            export_record.expires_at = now + timedelta(hours=_EXPORT_EXPIRY_HOURS)
            await session.commit()

            logger.info(
                "DSGVO export completed",
                extra={"export_id": str(export_id), "user_id": str(user_id)},
            )

            # TASK-202: Send email notification if export took > 60 seconds
            elapsed = time.monotonic() - start_time
            if elapsed > _EXPORT_EMAIL_THRESHOLD_SECONDS and user_email:
                await _send_export_email(
                    user_email=user_email,
                    export_id=export_id,
                )

    except Exception:
        logger.exception(
            "DSGVO export failed",
            extra={"export_id": str(export_id), "user_id": str(user_id)},
        )
        try:
            async with session_factory() as session:
                stmt = select(DataExport).where(DataExport.id == export_id)
                result = await session.execute(stmt)
                export_record = result.scalar_one_or_none()
                if export_record is not None:
                    export_record.status = "failed"
                    export_record.error_message = "Internal export error"
                    await session.commit()
        except Exception:
            logger.exception("Failed to update export status to failed")
    finally:
        await engine.dispose()


def is_export_expired(export: DataExport) -> bool:
    """Check if a completed export has expired (> 24h)."""
    if export.expires_at is None:
        return False
    now = datetime.now(tz=timezone.utc)
    return now > export.expires_at


# ---------------------------------------------------------------------------
# Data collectors (all filtered by user_id for tenant isolation)
# ---------------------------------------------------------------------------


async def _collect_documents(user_id: uuid.UUID, session: AsyncSession) -> list[dict[str, Any]]:
    stmt = select(Document).where(Document.user_id == user_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "source_type": r.source_type,
            "source_id": r.source_id,
            "title": r.title,
            "language": r.language,
            "chunk_count": r.chunk_count,
            "processing_status": r.processing_status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


async def _collect_chunks(user_id: uuid.UUID, session: AsyncSession) -> list[dict[str, Any]]:
    stmt = select(Chunk).where(Chunk.user_id == user_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "document_id": str(r.document_id),
            "chunk_index": r.chunk_index,
            "token_count": r.token_count,
            "content_preview": r.content_preview,
        }
        for r in rows
    ]


async def _collect_entities(user_id: uuid.UUID, session: AsyncSession) -> list[dict[str, Any]]:
    stmt = select(Entity).where(Entity.user_id == user_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "entity_type": r.entity_type,
            "name": r.name,
            "normalized_name": r.normalized_name,
            "first_seen": r.first_seen.isoformat() if r.first_seen else None,
            "last_seen": r.last_seen.isoformat() if r.last_seen else None,
        }
        for r in rows
    ]


async def _collect_briefings(user_id: uuid.UUID, session: AsyncSession) -> list[dict[str, Any]]:
    stmt = select(Briefing).where(Briefing.user_id == user_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "briefing_type": r.briefing_type,
            "title": r.title,
            "content": r.content,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
        }
        for r in rows
    ]


async def _collect_audit_log(user_id: uuid.UUID, session: AsyncSession) -> list[dict[str, Any]]:
    """Collect audit log entries.  No PII in exported metadata."""
    stmt = select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.created_at.desc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": str(r.resource_id) if r.resource_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


async def _collect_llm_audit_log(
    user_id: uuid.UUID, session: AsyncSession
) -> list[dict[str, Any]]:
    """Collect LLM audit log entries for DSGVO export."""
    stmt = (
        select(LlmAuditLog)
        .where(LlmAuditLog.owner_id == user_id)
        .order_by(LlmAuditLog.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "provider": r.provider,
            "model": r.model,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "purpose": r.purpose,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# ZIP builder
# ---------------------------------------------------------------------------


def _build_zip(
    *,
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    briefings: list[dict[str, Any]],
    audit_entries: list[dict[str, Any]],
    llm_usage: list[dict[str, Any]],
) -> bytes:
    """Build a ZIP archive with all user data."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # README.md — human-readable description of the export (TASK-202)
        zf.writestr("README.md", _EXPORT_README)

        # Documents (JSON)
        zf.writestr(
            "documents.json",
            json.dumps(documents, indent=2, ensure_ascii=False),
        )

        # Chunks (Markdown per document)
        chunks_by_doc: dict[str, list[dict[str, Any]]] = {}
        for c in chunks:
            doc_id = c["document_id"]
            chunks_by_doc.setdefault(doc_id, []).append(c)

        for doc_id, doc_chunks in chunks_by_doc.items():
            doc_chunks.sort(key=lambda x: x["chunk_index"])
            md_lines = [f"# Chunks for Document {doc_id}\n"]
            for ch in doc_chunks:
                md_lines.append(f"## Chunk {ch['chunk_index']}\n")
                md_lines.append(f"{ch.get('content_preview', '')}\n")
            zf.writestr(f"chunks/{doc_id}.md", "\n".join(md_lines))

        # Entities (JSON)
        zf.writestr(
            "entities.json",
            json.dumps(entities, indent=2, ensure_ascii=False),
        )

        # Briefings (Markdown per briefing)
        for b in briefings:
            bid = b["id"]
            md = f"# {b['title']}\n\nTyp: {b['briefing_type']}\n"
            md += f"Erstellt: {b.get('generated_at', '')}\n\n"
            md += b.get("content", "")
            zf.writestr(f"briefings/{bid}.md", md)

        # Briefings (JSON — machine-readable, TASK-202)
        zf.writestr(
            "briefings.json",
            json.dumps(briefings, indent=2, ensure_ascii=False),
        )

        # Audit Log (JSON, no PII)
        zf.writestr(
            "audit_log.json",
            json.dumps(audit_entries, indent=2, ensure_ascii=False),
        )

        # LLM Usage (JSON)
        zf.writestr(
            "llm_usage.json",
            json.dumps(llm_usage, indent=2, ensure_ascii=False),
        )

    return buf.getvalue()


# ---------------------------------------------------------------------------
# Email notification (TASK-202)
# ---------------------------------------------------------------------------


async def _send_export_email(
    user_email: str,
    export_id: uuid.UUID,
) -> None:
    """Send export-ready notification via EmailService.

    Wrapped in try/except so email failures don't fail the export.
    """
    try:
        from pwbs.services.email import create_email_service

        email_service = create_email_service()
        await email_service.send_export_ready(
            to=user_email,
            export_id=str(export_id),
        )
        logger.info(
            "Export email sent: export_id=%s to=%s",
            export_id,
            user_email,
        )
    except Exception:
        logger.exception(
            "Failed to send export email: export_id=%s",
            export_id,
        )
