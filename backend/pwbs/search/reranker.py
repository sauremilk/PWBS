"""Search result reranker with Cosine-Rescore and Recency-Boost (TASK-201).

Re-ranks the top-N candidates from hybrid search down to a final top-K
using a composite score:

1. **Cosine-Rescore**: Uses the ``semantic_score`` (Weaviate certainty,
   a cosine-similarity proxy) as the primary relevance signal.
2. **RRF-Score contribution**: Retains a portion of the original RRF
   rank-based score for diversity.
3. **Recency-Boost**: Recent documents receive a configurable score
   bonus using a sigmoid decay function.

Technical Hint (TASK-201): Recency-Decay als Sigmoid-Funktion.
ADR-010: Hybrid-Suche (Vektor + BM25).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime

from pwbs.search.hybrid import HybridSearchResult

logger = logging.getLogger(__name__)

__all__ = [
    "RerankerConfig",
    "SearchReranker",
]


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RerankerConfig:
    """Configuration for the search reranker."""

    # Weight for cosine-similarity (semantic_score) in final score
    cosine_weight: float = 0.6
    # Weight for normalised RRF score in final score
    rrf_weight: float = 0.3
    # Recency boost percentage (0.10 = +10% max bonus for brand-new docs)
    recency_boost_pct: float = 0.10
    # Documents within the last N days receive the boost
    recency_boost_days: int = 7


# ------------------------------------------------------------------
# Reranker
# ------------------------------------------------------------------


class SearchReranker:
    """Re-ranks hybrid search candidates to improve precision.

    Takes the top-N candidates from ``HybridSearchService`` and produces
    a refined top-K list using composite scoring.

    Parameters
    ----------
    config:
        Reranker configuration (weights, recency settings).
    """

    def __init__(self, config: RerankerConfig | None = None) -> None:
        self._config = config or RerankerConfig()

    @property
    def config(self) -> RerankerConfig:
        return self._config

    def rerank(
        self,
        results: list[HybridSearchResult],
        *,
        top_k: int = 10,
        now: datetime | None = None,
    ) -> list[HybridSearchResult]:
        """Re-rank *results* and return the top *top_k*.

        Parameters
        ----------
        results:
            Candidates from hybrid search (typically 50).
        top_k:
            Number of final results to return.
        now:
            Reference time for recency calculation (default: utcnow).

        Returns
        -------
        list[HybridSearchResult]
            Re-ranked results with updated ``score`` field.
        """
        if not results:
            return []

        ref_time = now or datetime.now(UTC)

        # Normalise RRF scores to [0, 1] for fair weighting
        max_rrf = max(r.score for r in results)
        min_rrf = min(r.score for r in results)
        rrf_range = max_rrf - min_rrf if max_rrf > min_rrf else 1.0

        scored: list[tuple[float, HybridSearchResult]] = []
        for result in results:
            # Cosine similarity component (semantic_score is Weaviate
            # certainty in [0, 1]  effectively a cosine-similarity proxy)
            cosine_score = result.semantic_score if result.semantic_score is not None else 0.0

            # Normalised RRF component
            norm_rrf = (result.score - min_rrf) / rrf_range

            # Recency factor (sigmoid decay)
            recency = _recency_factor(
                result.created_at,
                ref_time,
                self._config.recency_boost_days,
            )

            # Composite score
            base = self._config.cosine_weight * cosine_score + self._config.rrf_weight * norm_rrf
            final_score = base * (1.0 + self._config.recency_boost_pct * recency)

            scored.append((final_score, result))

        # Sort descending by rerank score
        scored.sort(key=lambda t: t[0], reverse=True)

        # Build output with updated score
        return [
            HybridSearchResult(
                chunk_id=r.chunk_id,
                content=r.content,
                title=r.title,
                source_type=r.source_type,
                score=score,
                semantic_score=r.semantic_score,
                keyword_score=r.keyword_score,
                semantic_rank=r.semantic_rank,
                keyword_rank=r.keyword_rank,
                created_at=r.created_at,
            )
            for score, r in scored[:top_k]
        ]


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _recency_factor(
    created_at: str | None,
    now: datetime,
    boost_days: int,
) -> float:
    """Sigmoid-based recency factor in ``[0, 1]``.

    Returns a value near 1.0 for brand-new documents, 0.5 at
    *boost_days* age, and approaching 0.0 for much older documents.

    Uses the sigmoid function::

        factor = 1 / (1 + exp((age_days - boost_days) / steepness))

    where ``steepness = boost_days / 3`` controls the decay curve.
    """
    if created_at is None or boost_days <= 0:
        return 0.0

    try:
        doc_time = datetime.fromisoformat(created_at)
    except (ValueError, TypeError):
        return 0.0

    # Ensure timezone-aware comparison
    if doc_time.tzinfo is None:
        doc_time = doc_time.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    age_days = (now - doc_time).total_seconds() / 86400.0

    if age_days <= 0:
        return 1.0

    steepness = boost_days / 3.0
    if steepness <= 0:
        return 0.0

    return 1.0 / (1.0 + math.exp((age_days - boost_days) / steepness))
