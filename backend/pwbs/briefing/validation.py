"""Quellenreferenz-Validierung in Briefings (TASK-079).

Post-processing step after briefing generation:
1. Extract `[Quelle: Titel, Datum]` annotations from generated text
2. Match each reference against actual documents in the database (fuzzy)
3. Resolve to chunk UUIDs for `source_chunks` persistence
4. Remove invalid references or mark as low confidence
5. Return validated text + source_chunks UUID list

D1 Section 3.5 (Step 7), D4 NF-022: 100% validated source references.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.core.grounding import GroundingService, SourceReference

logger = logging.getLogger(__name__)

__all__ = [
    "SourceValidationResult",
    "ValidatedReference",
    "BriefingSourceValidator",
]

# Minimum similarity ratio for fuzzy title matching
_MIN_FUZZY_RATIO = 0.6

# Regex matching [Quelle: Title, Date]
_SOURCE_REF_RE = re.compile(
    r"\[Quelle:\s*([^,\]]+),\s*([^\]]+)\]"
)


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ValidatedReference:
    """A single validated source reference."""

    title: str
    date: str
    raw: str
    document_id: uuid.UUID | None = None
    chunk_ids: list[uuid.UUID] = field(default_factory=list)
    is_valid: bool = False
    match_score: float = 0.0


@dataclass(frozen=True, slots=True)
class SourceValidationResult:
    """Result of source reference validation."""

    validated_text: str
    source_chunks: list[uuid.UUID]
    source_entities: list[uuid.UUID]
    validated_refs: list[ValidatedReference]
    removed_count: int
    total_refs: int


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class BriefingSourceValidator:
    """Validates source references in generated briefing text.

    Matches `[Quelle: Titel, Datum]` annotations against the documents
    table using fuzzy title matching, then resolves to chunk UUIDs for
    the `source_chunks` field in the briefing record.

    Parameters
    ----------
    session:
        SQLAlchemy async session for document lookups.
    min_fuzzy_ratio:
        Minimum similarity ratio for fuzzy title matching (0-1).
    remove_invalid:
        If True, remove invalid references from text. Otherwise mark them.
    """

    def __init__(
        self,
        session: AsyncSession,
        min_fuzzy_ratio: float = _MIN_FUZZY_RATIO,
        remove_invalid: bool = True,
    ) -> None:
        self._session = session
        self._min_fuzzy_ratio = min_fuzzy_ratio
        self._remove_invalid = remove_invalid

    async def validate(
        self,
        briefing_text: str,
        user_id: uuid.UUID,
    ) -> SourceValidationResult:
        """Validate all source references in the briefing text.

        Parameters
        ----------
        briefing_text:
            Generated briefing text with `[Quelle: ...]` annotations.
        user_id:
            Owner ID for database lookups.

        Returns
        -------
        SourceValidationResult
            Validated text with resolved chunk UUIDs.
        """
        # Step 1: Extract all references
        raw_refs = self._extract_references(briefing_text)

        if not raw_refs:
            return SourceValidationResult(
                validated_text=briefing_text,
                source_chunks=[],
                source_entities=[],
                validated_refs=[],
                removed_count=0,
                total_refs=0,
            )

        # Step 2: Fetch user's documents for matching
        doc_data = await self._fetch_user_documents(user_id)

        # Step 3: Match each reference against documents
        validated: list[ValidatedReference] = []
        all_chunk_ids: list[uuid.UUID] = []

        for ref in raw_refs:
            match = self._find_best_match(ref, doc_data)
            if match is not None:
                doc_id, chunk_ids, score = match
                vref = ValidatedReference(
                    title=ref["title"],
                    date=ref["date"],
                    raw=ref["raw"],
                    document_id=doc_id,
                    chunk_ids=chunk_ids,
                    is_valid=True,
                    match_score=score,
                )
                all_chunk_ids.extend(chunk_ids)
            else:
                vref = ValidatedReference(
                    title=ref["title"],
                    date=ref["date"],
                    raw=ref["raw"],
                    is_valid=False,
                )
            validated.append(vref)

        # Step 4: Build cleaned text
        validated_text = self._clean_text(briefing_text, validated)
        removed_count = sum(1 for v in validated if not v.is_valid)

        # Deduplicate chunk IDs
        unique_chunks = list(dict.fromkeys(all_chunk_ids))

        return SourceValidationResult(
            validated_text=validated_text,
            source_chunks=unique_chunks,
            source_entities=[],  # Entity resolution is future work
            validated_refs=validated,
            removed_count=removed_count,
            total_refs=len(raw_refs),
        )

    # ------------------------------------------------------------------
    # Reference extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_references(text: str) -> list[dict[str, str]]:
        """Extract all [Quelle: Title, Date] references from text."""
        refs: list[dict[str, str]] = []
        for match in _SOURCE_REF_RE.finditer(text):
            refs.append({
                "title": match.group(1).strip(),
                "date": match.group(2).strip(),
                "raw": match.group(0),
            })
        return refs

    # ------------------------------------------------------------------
    # Document fetching
    # ------------------------------------------------------------------

    async def _fetch_user_documents(
        self,
        user_id: uuid.UUID,
    ) -> list[dict]:
        """Fetch all documents for the user with their chunk IDs.

        Returns a list of dicts with: doc_id, title, created_at, chunk_ids.
        """
        sql = text("""
            SELECT
                d.id          AS doc_id,
                d.title       AS title,
                d.created_at  AS created_at,
                ARRAY_AGG(c.id) FILTER (WHERE c.id IS NOT NULL) AS chunk_ids
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            WHERE d.user_id = :user_id
            GROUP BY d.id, d.title, d.created_at
            ORDER BY d.created_at DESC
        """)

        result = await self._session.execute(
            sql,
            {"user_id": str(user_id)},
        )

        docs: list[dict] = []
        for row in result.fetchall():
            chunk_ids_raw = row.chunk_ids if row.chunk_ids else []
            docs.append({
                "doc_id": uuid.UUID(str(row.doc_id)),
                "title": row.title or "",
                "created_at": row.created_at,
                "chunk_ids": [
                    uuid.UUID(str(cid)) for cid in chunk_ids_raw if cid
                ],
            })
        return docs

    # ------------------------------------------------------------------
    # Fuzzy matching
    # ------------------------------------------------------------------

    def _find_best_match(
        self,
        ref: dict[str, str],
        documents: list[dict],
    ) -> tuple[uuid.UUID, list[uuid.UUID], float] | None:
        """Find the best matching document for a source reference.

        Uses fuzzy string matching on the title. Returns (doc_id, chunk_ids,
        match_score) or None if no match above threshold.
        """
        ref_title = ref["title"].lower().strip()
        best_score = 0.0
        best_doc: dict | None = None

        for doc in documents:
            doc_title = (doc["title"] or "").lower().strip()
            if not doc_title:
                continue

            # Exact match
            if ref_title == doc_title:
                return (doc["doc_id"], doc["chunk_ids"], 1.0)

            # Substring match (LLM often abbreviates)
            if ref_title in doc_title or doc_title in ref_title:
                score = 0.9
                if score > best_score:
                    best_score = score
                    best_doc = doc
                continue

            # Fuzzy match via SequenceMatcher
            ratio = SequenceMatcher(None, ref_title, doc_title).ratio()
            if ratio > best_score:
                best_score = ratio
                best_doc = doc

        if best_doc is not None and best_score >= self._min_fuzzy_ratio:
            return (best_doc["doc_id"], best_doc["chunk_ids"], best_score)

        return None

    # ------------------------------------------------------------------
    # Text cleaning
    # ------------------------------------------------------------------

    def _clean_text(
        self,
        text: str,
        validated: list[ValidatedReference],
    ) -> str:
        """Remove or mark invalid references in the briefing text."""
        result = text
        for vref in validated:
            if not vref.is_valid:
                if self._remove_invalid:
                    result = result.replace(vref.raw, "")
                else:
                    result = result.replace(
                        vref.raw,
                        f"{vref.raw} [WARNUNG: Quelle nicht verifiziert]",
                    )

        # Clean up double spaces from removals
        result = re.sub(r"  +", " ", result)
        return result.strip()
