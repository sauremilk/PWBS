"""Suchergebnisse mit SourceRef anreichern (TASK-075).

Enriches `HybridSearchResult` items with `SourceRef` objects that carry
all information the frontend needs for source attribution:

* Document title, source type (icon mapping), creation date
* Content excerpt (chunk preview)
* Relevance score (normalised to 0-1)
* Original URL for "open original" links

D4 F-012: Ergebnisse mit Quellenangabe.  D3 Erklaerbarkeit.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.schemas.briefing import SourceRef
from pwbs.schemas.enums import SourceType
from pwbs.search.hybrid import HybridSearchResult

logger = logging.getLogger(__name__)

__all__ = [
    "EnrichedSearchResult",
    "SearchResultEnricher",
    "reconstruct_url",
]


# ------------------------------------------------------------------
# URL Reconstruction
# ------------------------------------------------------------------

# Mapping of source type to URL template.
# {source_id} is replaced with the document's original source ID.
_URL_TEMPLATES: dict[str, str] = {
    SourceType.NOTION.value: "https://notion.so/{source_id}",
    SourceType.GOOGLE_CALENDAR.value: (
        "https://calendar.google.com/calendar/event?eid={source_id}"
    ),
    # Zoom recording URLs are stored in document metadata;
    # we use a best-effort template if metadata is unavailable.
    SourceType.ZOOM.value: "https://zoom.us/rec/{source_id}",
    # Obsidian is a local file; no web URL.
}


def reconstruct_url(source_type: str, source_id: str) -> str | None:
    """Reconstruct the original URL for a document.

    Returns `None` when the source type has no known URL pattern
    (e.g. local Obsidian notes).
    """
    template = _URL_TEMPLATES.get(source_type)
    if template is None:
        return None
    return template.format(source_id=source_id)


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EnrichedSearchResult:
    """A search result enriched with SourceRef and original URL."""

    chunk_id: uuid.UUID
    content: str
    score: float
    source_ref: SourceRef
    original_url: str | None
    semantic_rank: int | None = None
    keyword_rank: int | None = None


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class SearchResultEnricher:
    """Enriches hybrid search results with SourceRef and URL metadata.

    Queries the database to fetch document metadata (source_type, source_id,
    created date) for each chunk, then builds `SourceRef` objects and
    reconstructs original URLs.

    Parameters
    ----------
    session:
        SQLAlchemy async session (injected per request).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enrich(
        self,
        results: list[HybridSearchResult],
        user_id: uuid.UUID,
    ) -> list[EnrichedSearchResult]:
        """Enrich hybrid results with SourceRef objects.

        Parameters
        ----------
        results:
            Hybrid search results, already sorted by RRF score.
        user_id:
            Owner ID for database access control.

        Returns
        -------
        list[EnrichedSearchResult]
            Enriched results in the same order (RRF-score descending).
        """
        if not results:
            return []

        chunk_ids = [r.chunk_id for r in results]
        doc_meta = await self._fetch_document_metadata(chunk_ids, user_id)

        enriched: list[EnrichedSearchResult] = []
        for result in results:
            meta = doc_meta.get(result.chunk_id)
            if meta is None:
                logger.warning(
                    "No document metadata found for chunk_id=%s, skipping",
                    result.chunk_id,
                )
                continue

            source_type_enum = _safe_source_type(meta["source_type"])
            original_url = reconstruct_url(
                meta["source_type"], meta["source_id"]
            )

            source_ref = SourceRef(
                chunk_id=result.chunk_id,
                doc_title=meta["title"] or result.title,
                source_type=source_type_enum,
                date=meta["created_at"],
                relevance=_normalize_score(result.score),
            )

            enriched.append(
                EnrichedSearchResult(
                    chunk_id=result.chunk_id,
                    content=result.content,
                    score=result.score,
                    source_ref=source_ref,
                    original_url=original_url,
                    semantic_rank=result.semantic_rank,
                    keyword_rank=result.keyword_rank,
                )
            )

        return enriched

    async def _fetch_document_metadata(
        self,
        chunk_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> dict[uuid.UUID, dict]:
        """Fetch document metadata for a list of chunk IDs.

        Returns a mapping `{chunk_id -> {title, source_type, source_id, created_at}}`.
        Only chunks belonging to the given user are returned.
        """
        if not chunk_ids:
            return {}

        sql = text("""
            SELECT
                c.id          AS chunk_id,
                d.title       AS title,
                d.source_type AS source_type,
                d.source_id   AS source_id,
                d.created_at  AS created_at
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.id = ANY(:chunk_ids)
              AND c.user_id = :user_id
        """)

        result = await self._session.execute(
            sql,
            {
                "chunk_ids": [str(cid) for cid in chunk_ids],
                "user_id": str(user_id),
            },
        )

        meta: dict[uuid.UUID, dict] = {}
        for row in result.fetchall():
            meta[uuid.UUID(str(row.chunk_id))] = {
                "title": row.title,
                "source_type": row.source_type,
                "source_id": row.source_id,
                "created_at": row.created_at,
            }
        return meta


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _safe_source_type(raw: str) -> SourceType:
    """Convert a raw source_type string to a SourceType enum.

    Falls back to the first enum member if the value is unknown.
    """
    try:
        return SourceType(raw)
    except ValueError:
        logger.warning("Unknown source_type %r, defaulting to NOTION", raw)
        return SourceType.NOTION


def _normalize_score(score: float) -> float:
    """Normalise an RRF score to [0, 1] for the SourceRef relevance field.

    RRF scores are naturally small (max ~1/61 for a single list).  We clamp
    to [0, 1] since SourceRef.relevance is bounded.
    """
    return max(0.0, min(1.0, score))
