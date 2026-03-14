"""Tests for EdgeWeightService (TASK-065)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.graph.edge_weights import (
    CoOccurrence,
    EdgeWeightConfig,
    EdgeWeightService,
    WeightedEdge,
    _build_weight_query,
    _pair_key,
    compute_weight,
)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def _co(
    a_id: str = "p1",
    b_id: str = "p2",
    a_label: str = "Person",
    b_label: str = "Person",
    occurred_at: datetime | None = None,
    context_id: str = "ctx-1",
) -> CoOccurrence:
    return CoOccurrence(
        entity_a_id=a_id,
        entity_b_id=b_id,
        entity_a_label=a_label,
        entity_b_label=b_label,
        occurred_at=occurred_at or NOW,
        context_id=context_id,
    )


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.run = AsyncMock(return_value=MagicMock())
    return session


def _service(
    session: AsyncMock | None = None,
    config: EdgeWeightConfig | None = None,
) -> EdgeWeightService:
    return EdgeWeightService(
        neo4j_session=session or _mock_session(),
        config=config,
    )


# ===================================================================
# compute_weight (pure function)
# ===================================================================


class TestComputeWeight:
    def test_single_occurrence_no_decay(self) -> None:
        cfg = EdgeWeightConfig()
        w = compute_weight(1, 0.0, cfg)
        assert abs(w - cfg.base_weight) < 1e-9

    def test_multiple_occurrences(self) -> None:
        cfg = EdgeWeightConfig()
        w = compute_weight(3, 0.0, cfg)
        expected = cfg.base_weight + cfg.weight_increment * 2
        assert abs(w - expected) < 1e-9

    def test_decay_reduces_weight(self) -> None:
        cfg = EdgeWeightConfig()
        w_fresh = compute_weight(1, 0.0, cfg)
        w_old = compute_weight(1, 100.0, cfg)
        assert w_old < w_fresh

    def test_zero_occurrences(self) -> None:
        w = compute_weight(0, 0.0, EdgeWeightConfig())
        assert w == 0.0

    def test_clamped_to_max(self) -> None:
        cfg = EdgeWeightConfig(max_weight=1.0)
        w = compute_weight(100, 0.0, cfg)
        assert w == 1.0

    def test_negative_days_treated_as_zero(self) -> None:
        cfg = EdgeWeightConfig()
        w = compute_weight(1, -5.0, cfg)
        assert abs(w - cfg.base_weight) < 1e-9

    def test_large_decay_low_weight(self) -> None:
        cfg = EdgeWeightConfig(decay_rate=1.0)
        w = compute_weight(1, 100.0, cfg)
        assert w < 0.001


# ===================================================================
# _pair_key
# ===================================================================


class TestPairKey:
    def test_canonical_order(self) -> None:
        assert _pair_key("a", "b") == ("a", "b")
        assert _pair_key("b", "a") == ("a", "b")

    def test_same_ids(self) -> None:
        assert _pair_key("x", "x") == ("x", "x")


# ===================================================================
# _build_weight_query
# ===================================================================


class TestBuildWeightQuery:
    def test_contains_merge(self) -> None:
        edge = WeightedEdge(
            edge_type="KNOWS",
            source_id="s1",
            target_id="t1",
            source_label="Person",
            target_label="Person",
            user_id=USER_ID,
            weight=0.5,
            co_occurrence_count=2,
            last_occurrence=NOW,
        )
        query = _build_weight_query(edge)
        assert "MERGE" in query
        assert "$weight" in query
        assert "$userId" in query
        assert "KNOWS" in query

    def test_parametrized_no_concatenation(self) -> None:
        edge = WeightedEdge(
            edge_type="DISCUSSED",
            source_id="s1",
            target_id="t1",
            source_label="Meeting",
            target_label="Topic",
            user_id=USER_ID,
            weight=0.3,
            co_occurrence_count=1,
            last_occurrence=NOW,
        )
        query = _build_weight_query(edge)
        assert "$sourceId" in query
        assert "$targetId" in query


# ===================================================================
# Config
# ===================================================================


class TestEdgeWeightConfig:
    def test_defaults(self) -> None:
        cfg = EdgeWeightConfig()
        assert cfg.decay_rate == 0.01
        assert cfg.base_weight == 0.3
        assert cfg.knows_min_co_occurrences == 2
        assert cfg.related_to_min_co_occurrences == 3
        assert cfg.batch_size == 50

    def test_custom(self) -> None:
        cfg = EdgeWeightConfig(decay_rate=0.05, knows_min_co_occurrences=5)
        assert cfg.decay_rate == 0.05
        assert cfg.knows_min_co_occurrences == 5


# ===================================================================
# update_weights
# ===================================================================


class TestUpdateWeights:
    @pytest.mark.asyncio
    async def test_single_co_occurrence(self) -> None:
        session = _mock_session()
        svc = _service(session=session)
        cos = [_co(a_id="p1", b_id="m1", a_label="Person", b_label="Meeting")]
        result = await svc.update_weights(cos, USER_ID, reference_time=NOW)
        assert result.edges_updated == 1
        assert session.run.await_count == 1

    @pytest.mark.asyncio
    async def test_multiple_co_occurrences_same_pair(self) -> None:
        session = _mock_session()
        svc = _service(session=session)
        cos = [
            _co(a_id="p1", b_id="m1", a_label="Person", b_label="Meeting", context_id="c1"),
            _co(a_id="p1", b_id="m1", a_label="Person", b_label="Meeting", context_id="c2"),
        ]
        result = await svc.update_weights(cos, USER_ID, reference_time=NOW)
        # Aggregated to 1 pair → 1 edge written
        assert result.edges_updated == 1

    @pytest.mark.asyncio
    async def test_old_co_occurrence_decayed(self) -> None:
        session = _mock_session()
        cfg = EdgeWeightConfig(min_weight=0.2)
        svc = _service(session=session, config=cfg)
        old = NOW - timedelta(days=500)
        cos = [_co(a_id="p1", b_id="m1", a_label="Person", b_label="Meeting", occurred_at=old)]
        result = await svc.update_weights(cos, USER_ID, reference_time=NOW)
        # Weight decayed below min_weight → not written
        assert result.edges_updated == 0

    @pytest.mark.asyncio
    async def test_empty_input(self) -> None:
        session = _mock_session()
        svc = _service(session=session)
        result = await svc.update_weights([], USER_ID, reference_time=NOW)
        assert result.edges_updated == 0
        session.run.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_neo4j_failure_recorded(self) -> None:
        session = AsyncMock()
        session.run = AsyncMock(side_effect=RuntimeError("Neo4j down"))
        svc = _service(session=session)
        cos = [_co(a_id="p1", b_id="m1", a_label="Person", b_label="Meeting")]
        result = await svc.update_weights(cos, USER_ID, reference_time=NOW)
        assert result.edges_updated == 0
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_unknown_label_pair_skipped(self) -> None:
        session = _mock_session()
        svc = _service(session=session)
        # Unknown label pair has no mapping → skipped
        cos = [_co(a_id="x1", b_id="y1", a_label="Unknown", b_label="Other")]
        result = await svc.update_weights(cos, USER_ID, reference_time=NOW)
        assert result.edges_updated == 0

    @pytest.mark.asyncio
    async def test_user_id_in_params(self) -> None:
        session = _mock_session()
        svc = _service(session=session)
        cos = [_co(a_id="p1", b_id="m1", a_label="Person", b_label="Meeting")]
        await svc.update_weights(cos, USER_ID, reference_time=NOW)
        call_args = session.run.call_args
        params = (
            call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get("parameters", {})
        )
        assert params.get("userId") == USER_ID


# ===================================================================
# derive_implicit_edges: KNOWS
# ===================================================================


class TestDeriveKnows:
    @pytest.mark.asyncio
    async def test_knows_derived_at_threshold(self) -> None:
        session = _mock_session()
        cfg = EdgeWeightConfig(knows_min_co_occurrences=2)
        svc = _service(session=session, config=cfg)
        cos = [
            _co(a_id="p1", b_id="p2", a_label="Person", b_label="Person", context_id="c1"),
            _co(a_id="p1", b_id="p2", a_label="Person", b_label="Person", context_id="c2"),
        ]
        result = await svc.derive_implicit_edges(cos, USER_ID, reference_time=NOW)
        assert result.edges_derived == 1
        assert result.edges_updated == 0

    @pytest.mark.asyncio
    async def test_knows_not_derived_below_threshold(self) -> None:
        session = _mock_session()
        cfg = EdgeWeightConfig(knows_min_co_occurrences=3)
        svc = _service(session=session, config=cfg)
        cos = [
            _co(a_id="p1", b_id="p2", a_label="Person", b_label="Person", context_id="c1"),
            _co(a_id="p1", b_id="p2", a_label="Person", b_label="Person", context_id="c2"),
        ]
        result = await svc.derive_implicit_edges(cos, USER_ID, reference_time=NOW)
        assert result.edges_derived == 0


# ===================================================================
# derive_implicit_edges: RELATED_TO
# ===================================================================


class TestDeriveRelatedTo:
    @pytest.mark.asyncio
    async def test_related_to_derived_at_threshold(self) -> None:
        session = _mock_session()
        cfg = EdgeWeightConfig(related_to_min_co_occurrences=3)
        svc = _service(session=session, config=cfg)
        cos = [
            _co(a_id="t1", b_id="t2", a_label="Topic", b_label="Topic", context_id=f"ch{i}")
            for i in range(3)
        ]
        result = await svc.derive_implicit_edges(cos, USER_ID, reference_time=NOW)
        assert result.edges_derived == 1

    @pytest.mark.asyncio
    async def test_related_to_not_derived_below_threshold(self) -> None:
        session = _mock_session()
        cfg = EdgeWeightConfig(related_to_min_co_occurrences=3)
        svc = _service(session=session, config=cfg)
        cos = [
            _co(a_id="t1", b_id="t2", a_label="Topic", b_label="Topic", context_id=f"ch{i}")
            for i in range(2)
        ]
        result = await svc.derive_implicit_edges(cos, USER_ID, reference_time=NOW)
        assert result.edges_derived == 0


# ===================================================================
# process (combined)
# ===================================================================


class TestProcess:
    @pytest.mark.asyncio
    async def test_combined_update_and_derive(self) -> None:
        session = _mock_session()
        cfg = EdgeWeightConfig(knows_min_co_occurrences=2)
        svc = _service(session=session, config=cfg)
        cos = [
            _co(a_id="p1", b_id="p2", a_label="Person", b_label="Person", context_id="c1"),
            _co(a_id="p1", b_id="p2", a_label="Person", b_label="Person", context_id="c2"),
            _co(a_id="p1", b_id="m1", a_label="Person", b_label="Meeting", context_id="c3"),
        ]
        result = await svc.process(cos, USER_ID, reference_time=NOW)
        # update_weights: Person+Person has no explicit mapping → 0
        # but Person+Meeting maps to PARTICIPATED_IN → 1
        # derive: KNOWS for p1+p2 with count=2 → 1
        assert result.edges_updated == 1
        assert result.edges_derived == 1

    @pytest.mark.asyncio
    async def test_errors_combined(self) -> None:
        session = AsyncMock()
        call_count = 0

        async def _fail_some(q: str, p: dict | None = None) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("fail1")
            return MagicMock()

        session.run = AsyncMock(side_effect=_fail_some)
        cfg = EdgeWeightConfig(knows_min_co_occurrences=2)
        svc = _service(session=session, config=cfg)
        cos = [
            _co(a_id="p1", b_id="m1", a_label="Person", b_label="Meeting"),
            _co(a_id="p1", b_id="p2", a_label="Person", b_label="Person", context_id="c1"),
            _co(a_id="p1", b_id="p2", a_label="Person", b_label="Person", context_id="c2"),
        ]
        result = await svc.process(cos, USER_ID, reference_time=NOW)
        assert len(result.errors) >= 1


# ===================================================================
# Aggregation
# ===================================================================


class TestAggregation:
    def test_aggregates_same_pair(self) -> None:
        svc = _service()
        cos = [
            _co(a_id="a", b_id="b", context_id="c1"),
            _co(a_id="b", b_id="a", context_id="c2"),
            _co(a_id="a", b_id="b", context_id="c3"),
        ]
        agg = svc._aggregate(cos)
        assert len(agg) == 1
        key = ("a", "b")
        assert agg[key]["count"] == 3
        assert len(agg[key]["contexts"]) == 3

    def test_different_pairs_separate(self) -> None:
        svc = _service()
        cos = [
            _co(a_id="a", b_id="b"),
            _co(a_id="c", b_id="d"),
        ]
        agg = svc._aggregate(cos)
        assert len(agg) == 2

    def test_last_occurrence_is_latest(self) -> None:
        svc = _service()
        t1 = NOW - timedelta(days=10)
        t2 = NOW
        cos = [
            _co(a_id="a", b_id="b", occurred_at=t1),
            _co(a_id="a", b_id="b", occurred_at=t2),
        ]
        agg = svc._aggregate(cos)
        assert agg[("a", "b")]["last"] == t2


# ===================================================================
# Batch processing
# ===================================================================


class TestBatchProcessing:
    @pytest.mark.asyncio
    async def test_batch_size_respected(self) -> None:
        session = _mock_session()
        cfg = EdgeWeightConfig(batch_size=2)
        svc = _service(session=session, config=cfg)
        # 5 distinct Person+Meeting pairs
        cos = [
            _co(a_id=f"p{i}", b_id=f"m{i}", a_label="Person", b_label="Meeting") for i in range(5)
        ]
        result = await svc.update_weights(cos, USER_ID, reference_time=NOW)
        assert result.edges_updated == 5


# ===================================================================
# Weight property range
# ===================================================================


class TestWeightRange:
    def test_weight_between_zero_and_one(self) -> None:
        cfg = EdgeWeightConfig()
        for count in range(1, 20):
            for days in [0, 10, 50, 100, 365]:
                w = compute_weight(count, float(days), cfg)
                assert 0.0 <= w <= 1.0, f"count={count}, days={days}, w={w}"
