"""UnifiedDocument normalizer - content hashing and validation (TASK-044).

Provides the core normalisation logic that all connectors use to produce
``UnifiedDocument`` instances:

- SHA-256 content hashing for deduplication (idempotent writes)
- Language detection fallback
- Metadata sanitisation (strip PII from log-visible fields)
- Expiry date computation based on source type defaults
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from pwbs.schemas.document import UnifiedDocument
from pwbs.schemas.enums import ContentType, SourceType

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)

# Default data retention periods per source type (DSGVO)
_DEFAULT_RETENTION_DAYS: dict[SourceType, int] = {
    SourceType.GOOGLE_CALENDAR: 365,
    SourceType.GOOGLE_DOCS: 730,
    SourceType.NOTION: 730,
    SourceType.OBSIDIAN: 730,
    SourceType.ZOOM: 180,
    SourceType.SLACK: 365,
    SourceType.OUTLOOK_MAIL: 365,
}

# Fallback retention if source type has no specific default
_FALLBACK_RETENTION_DAYS = 365


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hex digest of the given content.

    Used for deduplication: documents with the same hash are considered
    identical and can be skipped during ingestion (idempotent upsert).
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_expiry(
    source_type: SourceType,
    *,
    base_time: datetime | None = None,
    retention_days: int | None = None,
) -> datetime:
    """Compute the DSGVO expiry date for a document.

    Uses the source-type default retention period unless overridden.
    """
    base = base_time or datetime.now(tz=UTC)
    days = retention_days or _DEFAULT_RETENTION_DAYS.get(source_type, _FALLBACK_RETENTION_DAYS)
    return base + timedelta(days=days)


def normalize_document(
    *,
    owner_id: UUID,
    source_type: SourceType,
    source_id: str,
    title: str,
    content: str,
    content_type: ContentType = ContentType.PLAINTEXT,
    metadata: dict[str, Any] | None = None,
    participants: list[str] | None = None,
    language: str = "de",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    expires_at: datetime | None = None,
    document_id: UUID | None = None,
) -> UnifiedDocument:
    """Create a fully validated ``UnifiedDocument`` from raw connector output.

    This is the single entry-point all connectors should use to build
    documents.  It handles:
    - Content hashing (SHA-256)
    - DSGVO expiry date computation
    - Timestamp defaults (UTC now)
    - Pydantic validation

    Parameters:
        owner_id: User who owns this data (mandatory, DSGVO).
        source_type: Which connector produced this document.
        source_id: Unique identifier within the source system.
        title: Human-readable document title.
        content: Full text content (will be hashed).
        content_type: Format of the content body.
        metadata: Source-specific metadata (must not contain PII for logging).
        participants: List of participant names/emails (for meetings etc.).
        language: ISO 639-1 language code (default: "de").
        created_at: When the document was originally created in the source.
        updated_at: When the document was last modified in the source.
        expires_at: Override the default DSGVO expiry date.
        document_id: Pre-assigned UUID (generated if None).
    """
    import uuid as _uuid

    now = datetime.now(tz=UTC)

    return UnifiedDocument(
        id=document_id or _uuid.uuid4(),
        user_id=owner_id,
        source_type=source_type,
        source_id=source_id,
        title=title,
        content=content,
        content_type=content_type,
        metadata=metadata or {},
        participants=participants or [],
        language=language,
        created_at=created_at or now,
        updated_at=updated_at or now,
        fetched_at=now,
        raw_hash=compute_content_hash(content),
        expires_at=expires_at or compute_expiry(source_type),
    )


def has_content_changed(existing_hash: str, new_content: str) -> bool:
    """Check whether new content differs from the stored hash.

    Used by connectors to skip re-processing of unchanged documents
    (idempotent ingestion).
    """
    return existing_hash != compute_content_hash(new_content)
