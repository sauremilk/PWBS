"""PostgreSQL tsvector Keyword-Suche (TASK-073).

Implements keyword search using PostgreSQL's full-text search capabilities:
- ``to_tsvector`` / ``to_tsquery`` with configurable language (german/english)
- ``ts_rank_cd`` for relevance ranking
- Mandatory ``user_id`` filter for tenant isolation
- Searches over ``chunks.content_preview`` joined with ``documents.title``
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

__all__ = [
    "KeywordSearchService",
    "KeywordSearchConfig",
    "KeywordSearchResult",
]

# Map short language codes to PostgreSQL text search configurations
_PG_LANGUAGE_MAP: dict[str, str] = {
    "de": "german",
    "en": "english",
    "simple": "simple",
}

# Regex to clean query input: allow word chars, spaces, hyphens, umlauts
_QUERY_CLEAN_RE = re.compile(r"[^\w\s\-äöüÄÖÜß]", re.UNICODE)


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KeywordSearchConfig:
    """Configuration for keyword search."""

    default_language: str = "german"
    default_top_k: int = 10
    max_top_k: int = 50


@dataclass(frozen=True, slots=True)
class KeywordSearchResult:
    """A single keyword search result."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content_preview: str
    score: float
    title: str | None = None
    source_type: str | None = None


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class KeywordSearchService:
    """PostgreSQL full-text keyword search over chunks and documents.

    Parameters
    ----------
    session:
        SQLAlchemy async session (injected per request).
    config:
        Search configuration.
    """

    def __init__(
        self,
        session: AsyncSession,
        config: KeywordSearchConfig | None = None,
    ) -> None:
        self._session = session
        self._config = config or KeywordSearchConfig()

    async def search(
        self,
        query: str,
        user_id: uuid.UUID,
        *,
        top_k: int | None = None,
        language: str | None = None,
    ) -> list[KeywordSearchResult]:
        """Execute a keyword search.

        Parameters
        ----------
        query:
            The search query text.
        user_id:
            Owner ID — results are scoped to this user. **Mandatory**.
        top_k:
            Number of results to return (default: 10, max: 50).
        language:
            PostgreSQL text search config name or short code
            (``de``, ``en``, ``german``, ``english``).

        Returns
        -------
        list[KeywordSearchResult]
            Results sorted by relevance score descending.
        """
        if not query or not query.strip():
            return []

        effective_top_k = min(
            top_k or self._config.default_top_k,
            self._config.max_top_k,
        )
        pg_lang = self._resolve_language(language or self._config.default_language)
        ts_query = self._build_tsquery(query)

        if not ts_query:
            return []

        sql = text("""
            SELECT
                c.id          AS chunk_id,
                c.document_id AS document_id,
                COALESCE(c.content_preview, '') AS content_preview,
                COALESCE(d.title, '')           AS title,
                COALESCE(d.source_type, '')     AS source_type,
                ts_rank_cd(
                    to_tsvector(
                        :lang,
                        COALESCE(c.content_preview, '')
                        || ' ' || COALESCE(d.title, '')
                    ),
                    to_tsquery(:lang, :query)
                ) AS score
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.user_id = :user_id
              AND to_tsvector(
                    :lang,
                    COALESCE(c.content_preview, '')
                    || ' ' || COALESCE(d.title, '')
                  )
                  @@ to_tsquery(:lang, :query)
            ORDER BY score DESC
            LIMIT :top_k
        """)

        result = await self._session.execute(
            sql,
            {
                "lang": pg_lang,
                "query": ts_query,
                "user_id": str(user_id),
                "top_k": effective_top_k,
            },
        )

        rows = result.fetchall()
        return [
            KeywordSearchResult(
                chunk_id=uuid.UUID(str(row.chunk_id)),
                document_id=uuid.UUID(str(row.document_id)),
                content_preview=row.content_preview,
                score=float(row.score),
                title=row.title or None,
                source_type=row.source_type or None,
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_language(lang: str) -> str:
        """Resolve a language code to a PostgreSQL text search config name."""
        return _PG_LANGUAGE_MAP.get(lang, lang)

    @staticmethod
    def _build_tsquery(query: str) -> str:
        """Build a safe tsquery string from user input.

        Splits on whitespace and joins with ``&`` (AND semantics).
        Special characters are stripped to prevent injection.
        """
        cleaned = _QUERY_CLEAN_RE.sub("", query).strip()
        if not cleaned:
            return ""

        terms = cleaned.split()
        # Each term is a separate lexeme; join with AND
        return " & ".join(terms)
