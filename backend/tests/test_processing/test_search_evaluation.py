"""Tests for pwbs.search.evaluation – IR metrics and search evaluation.

Validates mathematical correctness of nDCG@k, MRR, Precision@k,
Recall@k, and MAP against hand-computed expected values.
"""

from __future__ import annotations

import math

import pytest

from pwbs.search.evaluation import (
    EvalDataset,
    EvalQuery,
    SearchEvaluator,
    average_precision,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _binary_query(relevant: set[str]) -> EvalQuery:
    """Create an EvalQuery with binary relevance (all rel=1)."""
    return EvalQuery(query="test", relevant_ids=frozenset(relevant))


def _graded_query(grades: dict[str, int]) -> EvalQuery:
    """Create an EvalQuery with graded relevance."""
    return EvalQuery(
        query="test",
        relevant_ids=frozenset(grades.keys()),
        relevance_grades=grades,
    )


# ---------------------------------------------------------------------------
# nDCG@k
# ---------------------------------------------------------------------------


class TestNDCG:
    """nDCG correctness; DCG formula: (2^rel - 1) / log2(i+1)."""

    def test_perfect_ranking(self) -> None:
        """Ideal ranking → nDCG = 1.0."""
        query = _graded_query({"a": 3, "b": 2, "c": 1})
        ranked = ["a", "b", "c"]
        assert ndcg_at_k(ranked, query, k=3) == pytest.approx(1.0)

    def test_inverse_ranking(self) -> None:
        """Worst possible order → nDCG < 1.0."""
        query = _graded_query({"a": 3, "b": 2, "c": 1})
        ranked = ["c", "b", "a"]
        score = ndcg_at_k(ranked, query, k=3)
        assert score < 1.0
        assert score > 0.0

    def test_no_relevant_results(self) -> None:
        query = _binary_query({"a", "b"})
        ranked = ["x", "y", "z"]
        assert ndcg_at_k(ranked, query, k=3) == 0.0

    def test_empty_relevant_set(self) -> None:
        query = _binary_query(set())
        ranked = ["a", "b"]
        assert ndcg_at_k(ranked, query, k=2) == 0.0

    def test_binary_relevance(self) -> None:
        """Binary relevance: all relevant docs have grade 1."""
        query = _binary_query({"a", "c"})
        ranked = ["a", "b", "c", "d"]
        score = ndcg_at_k(ranked, query, k=4)
        assert score > 0.0
        assert score <= 1.0

    def test_hand_computed_dcg(self) -> None:
        """Verify against hand-computed DCG values.

        Grades: a=3, b=2, c=1
        Ranking: [b, a, c]
        DCG = (2^2-1)/log2(2) + (2^3-1)/log2(3) + (2^1-1)/log2(4)
            = 3/1.0 + 7/1.585 + 1/2.0
            = 3.0 + 4.416 + 0.5
            = 7.916

        IDCG (ideal: a, b, c):
            = (2^3-1)/log2(2) + (2^2-1)/log2(3) + (2^1-1)/log2(4)
            = 7/1.0 + 3/1.585 + 1/2.0
            = 7.0 + 1.893 + 0.5
            = 9.393

        nDCG = 7.916 / 9.393 ≈ 0.8428
        """
        query = _graded_query({"a": 3, "b": 2, "c": 1})
        ranked = ["b", "a", "c"]
        score = ndcg_at_k(ranked, query, k=3)

        # Manual computation
        dcg = (2**2 - 1) / math.log2(2) + (2**3 - 1) / math.log2(3) + (2**1 - 1) / math.log2(4)
        idcg = (2**3 - 1) / math.log2(2) + (2**2 - 1) / math.log2(3) + (2**1 - 1) / math.log2(4)
        expected = dcg / idcg

        assert score == pytest.approx(expected, abs=1e-10)

    def test_k_smaller_than_ranking(self) -> None:
        """Only top-k results matter, rest is ignored."""
        query = _graded_query({"a": 3, "c": 2})
        ranked = ["x", "a", "y", "c"]
        score_k2 = ndcg_at_k(ranked, query, k=2)
        score_k4 = ndcg_at_k(ranked, query, k=4)
        # At k=4 we find c, but at k=2 we don't → different scores
        assert score_k4 >= score_k2


# ---------------------------------------------------------------------------
# MRR
# ---------------------------------------------------------------------------


class TestReciprocalRank:
    """Reciprocal Rank: 1/position of first relevant result."""

    def test_first_result_relevant(self) -> None:
        query = _binary_query({"a"})
        assert reciprocal_rank(["a", "b", "c"], query) == pytest.approx(1.0)

    def test_second_result_relevant(self) -> None:
        query = _binary_query({"b"})
        assert reciprocal_rank(["a", "b", "c"], query) == pytest.approx(0.5)

    def test_third_result_relevant(self) -> None:
        query = _binary_query({"c"})
        assert reciprocal_rank(["a", "b", "c"], query) == pytest.approx(1 / 3)

    def test_no_relevant(self) -> None:
        query = _binary_query({"x"})
        assert reciprocal_rank(["a", "b", "c"], query) == 0.0

    def test_multiple_relevant_uses_first(self) -> None:
        query = _binary_query({"b", "c"})
        # First relevant is "b" at position 2 → RR = 0.5
        assert reciprocal_rank(["a", "b", "c"], query) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Precision@k
# ---------------------------------------------------------------------------


class TestPrecisionAtK:
    def test_all_relevant(self) -> None:
        query = _binary_query({"a", "b", "c"})
        assert precision_at_k(["a", "b", "c"], query, k=3) == pytest.approx(1.0)

    def test_none_relevant(self) -> None:
        query = _binary_query({"x", "y"})
        assert precision_at_k(["a", "b", "c"], query, k=3) == pytest.approx(0.0)

    def test_half_relevant(self) -> None:
        query = _binary_query({"a", "c"})
        assert precision_at_k(["a", "b", "c", "d"], query, k=4) == pytest.approx(0.5)

    def test_k_zero(self) -> None:
        query = _binary_query({"a"})
        assert precision_at_k(["a"], query, k=0) == 0.0


# ---------------------------------------------------------------------------
# Recall@k
# ---------------------------------------------------------------------------


class TestRecallAtK:
    def test_all_found(self) -> None:
        query = _binary_query({"a", "b"})
        assert recall_at_k(["a", "b", "c"], query, k=3) == pytest.approx(1.0)

    def test_partial_found(self) -> None:
        query = _binary_query({"a", "b", "c"})
        assert recall_at_k(["a", "x", "y"], query, k=3) == pytest.approx(1 / 3)

    def test_none_found(self) -> None:
        query = _binary_query({"x", "y"})
        assert recall_at_k(["a", "b", "c"], query, k=3) == pytest.approx(0.0)

    def test_empty_relevant_set(self) -> None:
        query = _binary_query(set())
        assert recall_at_k(["a", "b"], query, k=2) == 0.0


# ---------------------------------------------------------------------------
# MAP (Mean Average Precision via single-query AP)
# ---------------------------------------------------------------------------


class TestAveragePrecision:
    def test_perfect_ranking(self) -> None:
        """All relevant at top → AP = 1.0."""
        query = _binary_query({"a", "b"})
        assert average_precision(["a", "b", "c"], query) == pytest.approx(1.0)

    def test_hand_computed(self) -> None:
        """Hand-computed AP example.

        Relevant: {a, c, e}
        Ranking:  [a, b, c, d, e]

        Precision at relevant positions:
          Position 1 (a): 1/1 = 1.0
          Position 3 (c): 2/3 = 0.667
          Position 5 (e): 3/5 = 0.6

        AP = (1.0 + 0.667 + 0.6) / 3 = 0.756
        """
        query = _binary_query({"a", "c", "e"})
        ranked = ["a", "b", "c", "d", "e"]
        ap = average_precision(ranked, query)
        expected = (1.0 + 2 / 3 + 3 / 5) / 3
        assert ap == pytest.approx(expected, abs=1e-10)

    def test_no_relevant_found(self) -> None:
        query = _binary_query({"x", "y"})
        assert average_precision(["a", "b", "c"], query) == 0.0

    def test_empty_relevant_set(self) -> None:
        query = _binary_query(set())
        assert average_precision(["a", "b"], query) == 0.0


# ---------------------------------------------------------------------------
# SearchEvaluator integration
# ---------------------------------------------------------------------------


class TestSearchEvaluator:
    """End-to-end evaluation with mock search functions."""

    @pytest.mark.asyncio
    async def test_perfect_search(self) -> None:
        """A search function that returns perfect results gets 1.0 everywhere."""
        dataset = EvalDataset(
            queries=[
                _binary_query({"a", "b"}),
                _binary_query({"c", "d"}),
            ],
        )

        async def perfect_search(query: str, top_k: int) -> list[str]:
            if query == "test":
                return ["a", "b"] if dataset.queries[0].relevant_ids == frozenset({"a", "b"}) else ["c", "d"]
            return []

        # Patch: each query has query="test", so we need a different approach
        call_count = 0

        async def tracking_search(query: str, top_k: int) -> list[str]:
            nonlocal call_count
            q = dataset.queries[call_count]
            call_count += 1
            return sorted(q.relevant_ids)[:top_k]

        evaluator = SearchEvaluator(dataset)
        report = await evaluator.evaluate(tracking_search, top_k=10)

        ndcg = report.metric_by_name("nDCG@10")
        assert ndcg is not None
        assert ndcg.mean == pytest.approx(1.0)

        mrr = report.metric_by_name("MRR")
        assert mrr is not None
        assert mrr.mean == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_empty_search(self) -> None:
        """A search function that returns nothing gets 0.0 everywhere."""
        dataset = EvalDataset(
            queries=[_binary_query({"a", "b"})],
        )

        async def empty_search(query: str, top_k: int) -> list[str]:
            return []

        evaluator = SearchEvaluator(dataset)
        report = await evaluator.evaluate(empty_search, top_k=10)

        for metric in report.metrics:
            assert metric.mean == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_report_summary(self) -> None:
        """Summary string contains metric names and values."""
        dataset = EvalDataset(queries=[_binary_query({"a"})])

        async def trivial_search(query: str, top_k: int) -> list[str]:
            return ["a"]

        evaluator = SearchEvaluator(dataset)
        report = await evaluator.evaluate(
            trivial_search, top_k=10, config_name="test-config"
        )

        summary = report.summary()
        assert "test-config" in summary
        assert "nDCG@10" in summary
        assert "MRR" in summary

    @pytest.mark.asyncio
    async def test_compare_multiple_configs(self) -> None:
        """Compare two search configs and verify both get reports."""
        dataset = EvalDataset(queries=[_binary_query({"a", "b"})])

        async def good_search(query: str, top_k: int) -> list[str]:
            return ["a", "b", "c"]

        async def bad_search(query: str, top_k: int) -> list[str]:
            return ["c", "d", "e"]

        evaluator = SearchEvaluator(dataset)
        reports = await evaluator.compare(
            {"good": good_search, "bad": bad_search},
            top_k=3,
        )

        assert len(reports) == 2
        assert reports[0].config_name == "good"
        assert reports[1].config_name == "bad"

        # Good search should have better nDCG than bad search
        good_ndcg = reports[0].metric_by_name("nDCG@3")
        bad_ndcg = reports[1].metric_by_name("nDCG@3")
        assert good_ndcg is not None and bad_ndcg is not None
        assert good_ndcg.mean > bad_ndcg.mean

    @pytest.mark.asyncio
    async def test_graded_relevance(self) -> None:
        """nDCG distinguishes between graded relevance levels."""
        query = _graded_query({"a": 3, "b": 2, "c": 1})
        dataset = EvalDataset(queries=[query])

        async def ideal_search(query: str, top_k: int) -> list[str]:
            return ["a", "b", "c"]

        async def suboptimal_search(query: str, top_k: int) -> list[str]:
            return ["c", "b", "a"]

        evaluator = SearchEvaluator(dataset)
        ideal = await evaluator.evaluate(ideal_search, top_k=3, config_name="ideal")
        subopt = await evaluator.evaluate(suboptimal_search, top_k=3, config_name="subopt")

        ideal_ndcg = ideal.metric_by_name("nDCG@3")
        subopt_ndcg = subopt.metric_by_name("nDCG@3")
        assert ideal_ndcg is not None and subopt_ndcg is not None

        assert ideal_ndcg.mean == pytest.approx(1.0)
        assert subopt_ndcg.mean < 1.0
