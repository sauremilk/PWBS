"""Quellenreferenz-Validierung in Briefings (TASK-079, TASK-200).

Post-processing step after briefing generation:
1. Extract `[Quelle: Titel, Datum]` annotations from generated text
2. Match each reference against actual documents in the database (fuzzy)
3. Resolve to chunk UUIDs for `source_chunks` persistence
4. Remove invalid references or mark as low confidence
5. Return validated text + source_chunks UUID list

TASK-200 adds BriefingValidator with embedding-based confidence scoring:
- Per-sentence cosine similarity against source chunks
- Confidence levels: high (> 0.7), medium (0.5-0.7), low (< 0.5)
- Blocks briefings without source references (fallback message)
- Blocks briefings with > 30% low-confidence sentences

D1 Section 3.5 (Step 7), D4 NF-022: 100% validated source references.
"""

from __future__ import annotations

import logging
import math
import re
import uuid
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from pwbs.processing.embedding import EmbeddingService

logger = logging.getLogger(__name__)

__all__ = [
    "BriefingSourceValidator",
    "BriefingValidator",
    "BriefingValidatorConfig",
    "ConfidenceLevel",
    "SentenceConfidence",
    "SourceValidationResult",
    "ValidatedReference",
    "ValidationResult",
]

# Minimum similarity ratio for fuzzy title matching
_MIN_FUZZY_RATIO = 0.6

# Regex matching [Quelle: Title, Date]
_SOURCE_REF_RE = re.compile(r"\[Quelle:\s*([^,\]]+),\s*([^\]]+)\]")


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
            refs.append(
                {
                    "title": match.group(1).strip(),
                    "date": match.group(2).strip(),
                    "raw": match.group(0),
                }
            )
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
            docs.append(
                {
                    "doc_id": uuid.UUID(str(row.doc_id)),
                    "title": row.title or "",
                    "created_at": row.created_at,
                    "chunk_ids": [uuid.UUID(str(cid)) for cid in chunk_ids_raw if cid],
                }
            )
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


# ------------------------------------------------------------------
# TASK-200: Confidence Scoring & Quality Validation
# ------------------------------------------------------------------

# Sentence splitting: periods, exclamation marks, question marks
# followed by whitespace or end of string. Ignores abbreviations.
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")


class ConfidenceLevel(str, Enum):
    """Confidence level for a briefing sentence."""

    HIGH = "high"  # cosine similarity > 0.7
    MEDIUM = "medium"  # 0.5 <= similarity <= 0.7
    LOW = "low"  # similarity < 0.5


@dataclass(frozen=True, slots=True)
class SentenceConfidence:
    """Confidence score for a single briefing sentence."""

    sentence: str
    confidence: float
    level: ConfidenceLevel
    nearest_chunk_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of briefing quality validation (TASK-200)."""

    is_valid: bool
    content: str
    sentence_scores: list[SentenceConfidence]
    overall_confidence: float
    low_confidence_ratio: float
    has_source_references: bool
    quality_warning: str | None = None


@dataclass(frozen=True, slots=True)
class BriefingValidatorConfig:
    """Configuration for BriefingValidator thresholds."""

    high_threshold: float = 0.7
    medium_threshold: float = 0.5
    max_low_ratio: float = 0.3
    min_sentence_length: int = 10
    fallback_message: str = (
        "Nicht genügend Quelldaten für ein vollständiges Briefing. "
        "Bitte stellen Sie sicher, dass ausreichend Datenquellen verbunden sind."
    )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, filtering out short/empty fragments."""
    raw = _SENTENCE_RE.split(text)
    return [s.strip() for s in raw if s.strip()]


class BriefingValidator:
    """Post-generation quality validator for briefings (TASK-200).

    Validates briefing content against source chunks using
    embedding-based cosine similarity.  Assigns per-sentence
    confidence levels (high / medium / low) and blocks briefings
    that fail quality thresholds.

    Parameters
    ----------
    embedding_service:
        Service for generating text embeddings.
    config:
        Threshold configuration.  Uses sensible defaults if omitted.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        config: BriefingValidatorConfig | None = None,
    ) -> None:
        self._embedding = embedding_service
        self._config = config or BriefingValidatorConfig()

    async def validate(
        self,
        briefing: str,
        source_chunks: list[str],
        source_chunk_ids: list[uuid.UUID] | None = None,
    ) -> ValidationResult:
        """Validate briefing content against source chunks.

        Parameters
        ----------
        briefing:
            Generated briefing text.
        source_chunks:
            Text content of the source chunks used during generation.
        source_chunk_ids:
            Optional UUIDs corresponding to each source chunk
            (same order as ``source_chunks``).

        Returns
        -------
        ValidationResult
            Quality assessment with per-sentence confidence scores.
        """
        has_refs = bool(_SOURCE_REF_RE.search(briefing))

        # Block briefings without any source references
        if not has_refs or not source_chunks:
            return ValidationResult(
                is_valid=False,
                content=self._config.fallback_message,
                sentence_scores=[],
                overall_confidence=0.0,
                low_confidence_ratio=1.0,
                has_source_references=False,
                quality_warning="Briefing enthält keine Quellenreferenzen.",
            )

        # Embed source chunks
        chunk_embeddings = await self._embed_texts(source_chunks)
        chunk_ids = source_chunk_ids or [None] * len(source_chunks)  # type: ignore[list-item]

        # Split briefing into sentences and score each
        sentences = _split_sentences(briefing)
        scored: list[SentenceConfidence] = []

        for sentence in sentences:
            # Skip very short fragments (headings, bullet markers)
            if len(sentence) < self._config.min_sentence_length:
                continue

            sent_embedding = await self._embed_texts([sentence])
            if not sent_embedding or not sent_embedding[0]:
                scored.append(
                    SentenceConfidence(
                        sentence=sentence,
                        confidence=0.0,
                        level=ConfidenceLevel.LOW,
                    )
                )
                continue

            # Find closest source chunk
            best_sim = 0.0
            best_idx = 0
            for idx, chunk_emb in enumerate(chunk_embeddings):
                sim = _cosine_similarity(sent_embedding[0], chunk_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            level = self._classify(best_sim)
            scored.append(
                SentenceConfidence(
                    sentence=sentence,
                    confidence=best_sim,
                    level=level,
                    nearest_chunk_id=chunk_ids[best_idx],
                )
            )

        # Compute aggregate metrics
        if scored:
            overall = sum(s.confidence for s in scored) / len(scored)
            low_count = sum(1 for s in scored if s.level == ConfidenceLevel.LOW)
            low_ratio = low_count / len(scored)
        else:
            overall = 0.0
            low_ratio = 1.0

        # Quality gate: block if too many low-confidence sentences
        is_valid = low_ratio <= self._config.max_low_ratio
        warning = None
        if not is_valid:
            warning = (
                f"Briefing-Qualität eingeschränkt: {low_ratio:.0%} der Aussagen "
                f"haben niedrige Quellen-Konfidenz (Schwellenwert: "
                f"{self._config.max_low_ratio:.0%})."
            )

        content = briefing if is_valid else self._config.fallback_message

        return ValidationResult(
            is_valid=is_valid,
            content=content,
            sentence_scores=scored,
            overall_confidence=overall,
            low_confidence_ratio=low_ratio,
            has_source_references=has_refs,
            quality_warning=warning,
        )

    def _classify(self, similarity: float) -> ConfidenceLevel:
        """Classify a cosine similarity score into a confidence level."""
        if similarity > self._config.high_threshold:
            return ConfidenceLevel.HIGH
        if similarity >= self._config.medium_threshold:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    async def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts using the embedding service."""
        results: list[list[float]] = []
        for t in texts:
            emb = await self._embedding.embed_text(t)
            results.append(emb)
        return results
