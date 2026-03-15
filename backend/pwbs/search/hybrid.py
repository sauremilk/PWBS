"""Hybrid-Suche mit RRF-Fusion (TASK-074).

Combines semantic results (Weaviate nearVector) with keyword results
(PostgreSQL tsvector) using Reciprocal Rank Fusion (RRF).

RRF formula:  `score = sum(1 / (k + rank_i))`  with k=60.
Weighted:     `final = semantic_weight * rrf_sem + keyword_weight * rrf_kw`

Reference: Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet
and individual Rank Learning Methods", SIGIR 2009.

ADR-010: Hybrid-Suche (Vektor + BM25) statt reiner Vektorsuche.
D4 F-011: Default 75% semantic, 25% keyword.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from pwbs.search.keyword import KeywordSearchResult, KeywordSearchService
from pwbs.search.service import SemanticSearchResult, SemanticSearchService

logger = logging.getLogger(__name__)

__all__ = [
    "HybridSearchConfig",
    "HybridSearchResult",
    "HybridSearchService",
]

# Default RRF constant from the original publication
_DEFAULT_RRF_K = 60


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HybridSearchConfig:
    """Configuration for hybrid search."""

    semantic_weight: float = 0.75
    keyword_weight: float = 0.25
    rrf_k: int = _DEFAULT_RRF_K
    default_top_k: int = 10
    max_top_k: int = 50
    # Fetch more candidates from each backend to improve fusion quality
    candidate_multiplier: float = 2.0


@dataclass(frozen=True, slots=True)
class HybridSearchResult:
    """A single result from the hybrid search fusion."""

    chunk_id: uuid.UUID
    content: str
    title: str
    source_type: str
    score: float
    semantic_score: float | None = None
    keyword_score: float | None = None
    semantic_rank: int | None = None
    keyword_rank: int | None = None
    created_at: str | None = None


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class HybridSearchService:
    """Hybrid search combining semantic and keyword results via RRF.

    Parameters
    ----------
    semantic_service:
        Weaviate semantic search service (TASK-072).
    keyword_service:
        PostgreSQL keyword search service (TASK-073).
    config:
        Hybrid search configuration.
    """

    def __init__(
        self,
        semantic_service: SemanticSearchService,
        keyword_service: KeywordSearchService,
        config: HybridSearchConfig | None = None,
    ) -> None:
        self._semantic = semantic_service
        self._keyword = keyword_service
        self._config = config or HybridSearchConfig()

    @property
    def config(self) -> HybridSearchConfig:
        return self._config

    async def search(
        self,
        query: str,
        user_id: uuid.UUID,
        *,
        top_k: int | None = None,
        semantic_weight: float | None = None,
        keyword_weight: float | None = None,
    ) -> list[HybridSearchResult]:
        """Execute a hybrid search with RRF fusion.

        Parameters
        ----------
        query:
            The search query text.
        user_id:
            Owner ID -- results are scoped to this user. **Mandatory**.
        top_k:
            Number of final results to return (default: 10, max: 50).
        semantic_weight:
            Override semantic weight for this query (default from config).
        keyword_weight:
            Override keyword weight for this query (default from config).

        Returns
        -------
        list[HybridSearchResult]
            Deduplicated, RRF-fused results sorted by score descending.
        """
        if not query or not query.strip():
            return []

        effective_top_k = min(
            top_k or self._config.default_top_k,
            self._config.max_top_k,
        )
        sem_w = semantic_weight if semantic_weight is not None else self._config.semantic_weight
        kw_w = keyword_weight if keyword_weight is not None else self._config.keyword_weight

        # Fetch more candidates from each backend than the final top_k
        candidate_k = min(
            int(effective_top_k * self._config.candidate_multiplier),
            self._config.max_top_k,
        )

        # Run both searches (could be parallelized with asyncio.gather
        # if keyword search becomes async-native; currently both are async)
        semantic_results = await self._semantic.search(
            query=query,
            user_id=user_id,
            top_k=candidate_k,
        )
        keyword_results = await self._keyword.search(
            query=query,
            user_id=user_id,
            top_k=candidate_k,
        )

        logger.debug(
            "Hybrid search: %d semantic + %d keyword candidates for query=%r",
            len(semantic_results),
            len(keyword_results),
            query[:80],
        )

        return self._fuse_rrf(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            sem_weight=sem_w,
            kw_weight=kw_w,
            top_k=effective_top_k,
        )

    # ------------------------------------------------------------------
    # RRF Fusion
    # ------------------------------------------------------------------

    def _fuse_rrf(
        self,
        semantic_results: list[SemanticSearchResult],
        keyword_results: list[KeywordSearchResult],
        sem_weight: float,
        kw_weight: float,
        top_k: int,
    ) -> list[HybridSearchResult]:
        """Fuse ranked lists using weighted Reciprocal Rank Fusion.

        RRF score for each source:  `1 / (k + rank)`
        where rank is 1-based position in the ranked list.

        Final score:  `sem_weight * rrf_sem + kw_weight * rrf_kw`
        """
        k = self._config.rrf_k

        # Collect all chunk metadata and RRF scores keyed by chunk_id
        # Each entry: {chunk_id -> _FusionCandidate}
        candidates: dict[uuid.UUID, _FusionCandidate] = {}

        # Process semantic results (1-based ranking)
        for rank, sr in enumerate(semantic_results, start=1):
            rrf_score = sem_weight * (1.0 / (k + rank))
            cid = sr.chunk_id
            if cid in candidates:
                candidates[cid].rrf_score += rrf_score
                candidates[cid].semantic_score = sr.score
                candidates[cid].semantic_rank = rank
            else:
                candidates[cid] = _FusionCandidate(
                    chunk_id=cid,
                    content=sr.content,
                    title=sr.title,
                    source_type=sr.source_type,
                    rrf_score=rrf_score,
                    semantic_score=sr.score,
                    keyword_score=None,
                    semantic_rank=rank,
                    keyword_rank=None,
                    created_at=sr.created_at,
                )

        # Process keyword results (1-based ranking)
        for rank, kr in enumerate(keyword_results, start=1):
            rrf_score = kw_weight * (1.0 / (k + rank))
            cid = kr.chunk_id
            if cid in candidates:
                candidates[cid].rrf_score += rrf_score
                candidates[cid].keyword_score = kr.score
                candidates[cid].keyword_rank = rank
            else:
                candidates[cid] = _FusionCandidate(
                    chunk_id=cid,
                    content=kr.content_preview,
                    title=kr.title or "",
                    source_type=kr.source_type or "",
                    rrf_score=rrf_score,
                    semantic_score=None,
                    keyword_score=kr.score,
                    semantic_rank=None,
                    keyword_rank=rank,
                    created_at=None,
                )

        # Sort by fused RRF score descending, take top_k
        sorted_candidates = sorted(
            candidates.values(),
            key=lambda c: c.rrf_score,
            reverse=True,
        )[:top_k]

        return [
            HybridSearchResult(
                chunk_id=c.chunk_id,
                content=c.content,
                title=c.title,
                source_type=c.source_type,
                score=c.rrf_score,
                semantic_score=c.semantic_score,
                keyword_score=c.keyword_score,
                semantic_rank=c.semantic_rank,
                keyword_rank=c.keyword_rank,
                created_at=c.created_at,
            )
            for c in sorted_candidates
        ]


# ------------------------------------------------------------------
# Internal helper
# ------------------------------------------------------------------


class _FusionCandidate:
    """Mutable accumulator for RRF score fusion."""

    __slots__ = (
        "chunk_id",
        "content",
        "title",
        "source_type",
        "rrf_score",
        "semantic_score",
        "keyword_score",
        "semantic_rank",
        "keyword_rank",
        "created_at",
    )

    def __init__(
        self,
        chunk_id: uuid.UUID,
        content: str,
        title: str,
        source_type: str,
        rrf_score: float,
        semantic_score: float | None,
        keyword_score: float | None,
        semantic_rank: int | None,
        keyword_rank: int | None,
        created_at: str | None = None,
    ) -> None:
        self.chunk_id = chunk_id
        self.content = content
        self.title = title
        self.source_type = source_type
        self.rrf_score = rrf_score
        self.semantic_score = semantic_score
        self.keyword_score = keyword_score
        self.semantic_rank = semantic_rank
        self.keyword_rank = keyword_rank
        self.created_at = created_at
