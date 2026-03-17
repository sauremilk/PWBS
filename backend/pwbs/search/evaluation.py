"""Search Quality Evaluation Framework.

Provides standard Information Retrieval metrics and a benchmark harness
for measuring and comparing search quality across different configurations
(semantic-only, keyword-only, hybrid, reranked).

Metrics implemented:
- **nDCG@k** (normalized Discounted Cumulative Gain)
- **MRR** (Mean Reciprocal Rank)
- **Precision@k**
- **Recall@k**
- **MAP** (Mean Average Precision)

The framework is decoupled from the search services via a callback
interface, allowing evaluation of any search backend.

Usage::

    dataset = EvalDataset(queries=[
        EvalQuery(
            query="project timeline",
            relevant_ids={"chunk-1", "chunk-5", "chunk-9"},
            relevance_grades={"chunk-1": 3, "chunk-5": 2, "chunk-9": 1},
        ),
        ...
    ])

    async def search_fn(query: str, top_k: int) -> list[str]:
        results = await hybrid_search.search(query, owner_id, top_k=top_k)
        return [str(r.chunk_id) for r in results]

    evaluator = SearchEvaluator(dataset)
    report = await evaluator.evaluate(search_fn, top_k=10)
    print(report.summary())
"""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)

__all__ = [
    "EvalDataset",
    "EvalQuery",
    "EvalReport",
    "MetricResult",
    "SearchEvaluator",
]


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvalQuery:
    """A single evaluation query with ground-truth relevance judgments.

    Attributes
    ----------
    query:
        The search query string.
    relevant_ids:
        Set of document/chunk IDs that are relevant to this query.
    relevance_grades:
        Optional graded relevance (ID → grade, higher = more relevant).
        Used for nDCG computation.  If empty, binary relevance is assumed
        (all IDs in ``relevant_ids`` get grade 1).
    """

    query: str
    relevant_ids: frozenset[str]
    relevance_grades: dict[str, int] = field(default_factory=dict)

    def grade(self, doc_id: str) -> int:
        """Return the relevance grade for *doc_id* (0 if not relevant)."""
        if self.relevance_grades:
            return self.relevance_grades.get(doc_id, 0)
        return 1 if doc_id in self.relevant_ids else 0


@dataclass(frozen=True, slots=True)
class EvalDataset:
    """A collection of evaluation queries."""

    queries: list[EvalQuery]
    name: str = "default"


@dataclass(frozen=True, slots=True)
class MetricResult:
    """Result of a single metric across all queries.

    Attributes
    ----------
    name:
        Metric name (e.g., ``"nDCG@10"``).
    mean:
        Mean value across all queries.
    median:
        Median value across all queries.
    std:
        Standard deviation across all queries.
    per_query:
        Per-query values (index matches ``EvalDataset.queries``).
    """

    name: str
    mean: float
    median: float
    std: float
    per_query: list[float]


@dataclass(frozen=True, slots=True)
class EvalReport:
    """Complete evaluation report for one search configuration."""

    config_name: str
    metrics: list[MetricResult]
    top_k: int
    num_queries: int

    def summary(self) -> str:
        """Return a human-readable summary table."""
        lines = [
            f"Search Evaluation Report: {self.config_name}",
            f"Queries: {self.num_queries}, Top-K: {self.top_k}",
            "-" * 50,
            f"{'Metric':<20} {'Mean':>8} {'Median':>8} {'Std':>8}",
            "-" * 50,
        ]
        for m in self.metrics:
            lines.append(
                f"{m.name:<20} {m.mean:>8.4f} {m.median:>8.4f} {m.std:>8.4f}"
            )
        return "\n".join(lines)

    def metric_by_name(self, name: str) -> MetricResult | None:
        """Look up a metric result by name."""
        for m in self.metrics:
            if m.name == name:
                return m
        return None


# ------------------------------------------------------------------
# Search function protocol
# ------------------------------------------------------------------


class SearchFn(Protocol):
    """Protocol for a search function used in evaluation.

    Accepts a query string and top_k parameter, returns ordered
    list of document/chunk IDs (most relevant first).
    """

    async def __call__(self, query: str, top_k: int) -> list[str]: ...


# ------------------------------------------------------------------
# IR Metrics (stateless, pure functions)
# ------------------------------------------------------------------


def ndcg_at_k(ranked_ids: list[str], query: EvalQuery, k: int) -> float:
    """Normalized Discounted Cumulative Gain at position *k*.

    Uses graded relevance from ``query.relevance_grades`` if available,
    otherwise binary relevance.

    The DCG formula (Järvelin & Kekäläinen, 2002)::

        DCG@k = Σ_{i=1}^{k} (2^{rel_i} - 1) / log₂(i + 1)

    IDCG is the DCG of the ideal ranking (sorted by grade descending).

    Returns
    -------
    float
        nDCG@k in [0, 1].  Returns 0 if no relevant documents exist.
    """
    if not query.relevant_ids:
        return 0.0

    # DCG of the actual ranking
    dcg = 0.0
    for i, doc_id in enumerate(ranked_ids[:k]):
        rel = query.grade(doc_id)
        if rel > 0:
            dcg += (2**rel - 1) / math.log2(i + 2)  # i+2 because i is 0-based

    # Ideal DCG: sort all relevant grades descending, compute DCG
    ideal_grades = sorted(
        [query.grade(did) for did in query.relevant_ids],
        reverse=True,
    )
    idcg = 0.0
    for i, rel in enumerate(ideal_grades[:k]):
        if rel > 0:
            idcg += (2**rel - 1) / math.log2(i + 2)

    if idcg == 0.0:
        return 0.0

    return dcg / idcg


def reciprocal_rank(ranked_ids: list[str], query: EvalQuery) -> float:
    """Reciprocal Rank: 1/position of the first relevant document.

    Returns 0 if no relevant document appears in the ranking.
    """
    for i, doc_id in enumerate(ranked_ids):
        if doc_id in query.relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def precision_at_k(ranked_ids: list[str], query: EvalQuery, k: int) -> float:
    """Precision@k: fraction of top-k results that are relevant."""
    if k == 0:
        return 0.0
    top_k = ranked_ids[:k]
    relevant_in_top_k = sum(1 for did in top_k if did in query.relevant_ids)
    return relevant_in_top_k / k


def recall_at_k(ranked_ids: list[str], query: EvalQuery, k: int) -> float:
    """Recall@k: fraction of relevant documents found in top-k."""
    if not query.relevant_ids:
        return 0.0
    top_k_set = set(ranked_ids[:k])
    found = sum(1 for did in query.relevant_ids if did in top_k_set)
    return found / len(query.relevant_ids)


def average_precision(ranked_ids: list[str], query: EvalQuery) -> float:
    """Average Precision (AP) for a single query.

    AP = (1/|relevant|) × Σ_{k: doc_k is relevant} Precision@k

    This is the area under the precision-recall curve.
    """
    if not query.relevant_ids:
        return 0.0

    num_relevant = 0
    sum_precision = 0.0

    for i, doc_id in enumerate(ranked_ids):
        if doc_id in query.relevant_ids:
            num_relevant += 1
            sum_precision += num_relevant / (i + 1)

    if num_relevant == 0:
        return 0.0

    return sum_precision / len(query.relevant_ids)


# ------------------------------------------------------------------
# Evaluator
# ------------------------------------------------------------------


def _aggregate(name: str, values: list[float]) -> MetricResult:
    """Compute mean/median/std from per-query values."""
    n = len(values)
    if n == 0:
        return MetricResult(name=name, mean=0.0, median=0.0, std=0.0, per_query=[])

    mean = statistics.mean(values)
    median = statistics.median(values)
    std = statistics.stdev(values) if n >= 2 else 0.0

    return MetricResult(name=name, mean=mean, median=median, std=std, per_query=values)


class SearchEvaluator:
    """Evaluates search quality against a ground-truth dataset.

    Parameters
    ----------
    dataset:
        Evaluation queries with relevance judgments.
    """

    def __init__(self, dataset: EvalDataset) -> None:
        self._dataset = dataset

    @property
    def dataset(self) -> EvalDataset:
        return self._dataset

    async def evaluate(
        self,
        search_fn: SearchFn,
        *,
        top_k: int = 10,
        config_name: str = "default",
    ) -> EvalReport:
        """Run evaluation across all queries and compute metrics.

        Parameters
        ----------
        search_fn:
            Async function ``(query, top_k) -> list[doc_id]``.
        top_k:
            Number of results to retrieve per query.
        config_name:
            Label for this configuration in the report.

        Returns
        -------
        EvalReport
            Full evaluation report with per-query and aggregate metrics.
        """
        ndcg_values: list[float] = []
        mrr_values: list[float] = []
        precision_values: list[float] = []
        recall_values: list[float] = []
        ap_values: list[float] = []

        for query in self._dataset.queries:
            ranked_ids = await search_fn(query.query, top_k)

            ndcg_values.append(ndcg_at_k(ranked_ids, query, top_k))
            mrr_values.append(reciprocal_rank(ranked_ids, query))
            precision_values.append(precision_at_k(ranked_ids, query, top_k))
            recall_values.append(recall_at_k(ranked_ids, query, top_k))
            ap_values.append(average_precision(ranked_ids, query))

        metrics = [
            _aggregate(f"nDCG@{top_k}", ndcg_values),
            _aggregate("MRR", mrr_values),
            _aggregate(f"Precision@{top_k}", precision_values),
            _aggregate(f"Recall@{top_k}", recall_values),
            _aggregate("MAP", ap_values),
        ]

        return EvalReport(
            config_name=config_name,
            metrics=metrics,
            top_k=top_k,
            num_queries=len(self._dataset.queries),
        )

    async def compare(
        self,
        configs: dict[str, SearchFn],
        *,
        top_k: int = 10,
    ) -> list[EvalReport]:
        """Evaluate multiple search configurations and return reports.

        Parameters
        ----------
        configs:
            Mapping of config name → search function.
        top_k:
            Number of results per query.

        Returns
        -------
        list[EvalReport]
            One report per configuration, in insertion order.
        """
        reports: list[EvalReport] = []
        for name, fn in configs.items():
            report = await self.evaluate(fn, top_k=top_k, config_name=name)
            reports.append(report)
            logger.info(
                "Evaluation complete: %s — nDCG@%d=%.4f, MRR=%.4f",
                name,
                top_k,
                report.metric_by_name(f"nDCG@{top_k}").mean  # type: ignore[union-attr]
                if report.metric_by_name(f"nDCG@{top_k}")
                else 0.0,
                report.metric_by_name("MRR").mean  # type: ignore[union-attr]
                if report.metric_by_name("MRR")
                else 0.0,
            )
        return reports
