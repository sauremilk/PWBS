"""Kantengewichtung und Co-Occurrence-basierte Kantenableitung (TASK-065).

Computes edge weights based on co-occurrence frequency and temporal
decay, and derives implicit edges (KNOWS between persons, RELATED_TO
between topics) from co-occurrence patterns.

Decay formula: weight = base_weight * exp(-decay_rate * days_since_last)

D1 §3.3.3, D2 TASK-065.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

__all__ = [
    "CoOccurrence",
    "EdgeWeightConfig",
    "EdgeWeightService",
    "WeightResult",
    "WeightedEdge",
]


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EdgeWeightConfig:
    """Configuration for edge weight computation.

    Attributes
    ----------
    decay_rate:
        Exponential decay rate per day.  Higher = faster decay.
        Default 0.01 ≈ half-life ~69 days.
    base_weight:
        Starting weight for first co-occurrence.
    weight_increment:
        Added per additional co-occurrence (before decay).
    max_weight:
        Upper clamp.
    min_weight:
        Below this the edge is considered dead (will not be written).
    knows_min_co_occurrences:
        Minimum co-occurrences to derive a KNOWS edge between persons.
    related_to_min_co_occurrences:
        Minimum co-occurrences to derive a RELATED_TO edge between topics.
    batch_size:
        Max edges per Neo4j transaction batch.
    """

    decay_rate: float = 0.01
    base_weight: float = 0.3
    weight_increment: float = 0.1
    max_weight: float = 1.0
    min_weight: float = 0.05
    knows_min_co_occurrences: int = 2
    related_to_min_co_occurrences: int = 3
    batch_size: int = 50


# ------------------------------------------------------------------
# Data containers
# ------------------------------------------------------------------


@dataclass(slots=True)
class CoOccurrence:
    """Records a co-occurrence between two entities.

    Attributes
    ----------
    entity_a_id:
        Neo4j node id (or internal UUID string) of first entity.
    entity_b_id:
        Neo4j node id (or internal UUID string) of second entity.
    entity_a_label:
        Node label (e.g. "Person", "Topic").
    entity_b_label:
        Node label.
    occurred_at:
        When the co-occurrence was observed.
    context_id:
        ID of the chunk / document / meeting where co-occurrence happened.
    """

    entity_a_id: str
    entity_b_id: str
    entity_a_label: str
    entity_b_label: str
    occurred_at: datetime
    context_id: str


@dataclass(slots=True)
class WeightedEdge:
    """An edge to be written to Neo4j with its weight."""

    edge_type: str
    source_id: str
    target_id: str
    source_label: str
    target_label: str
    user_id: str
    weight: float
    co_occurrence_count: int
    last_occurrence: datetime
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WeightResult:
    """Result of a weight computation / derivation run."""

    edges_updated: int = 0
    edges_derived: int = 0
    errors: list[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Neo4j Session Protocol
# ------------------------------------------------------------------


@runtime_checkable
class Neo4jSession(Protocol):
    """Protocol for async Neo4j session / transaction."""

    async def run(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        ...


# ------------------------------------------------------------------
# Weight computation (pure functions)
# ------------------------------------------------------------------


def compute_weight(
    co_occurrence_count: int,
    days_since_last: float,
    config: EdgeWeightConfig,
) -> float:
    """Compute edge weight from co-occurrence count and recency.

    Formula: weight = base * exp(-decay_rate * days) + increment * (count - 1)
    Clamped to [0, max_weight].
    """
    if co_occurrence_count <= 0:
        return 0.0

    raw = config.base_weight * math.exp(-config.decay_rate * max(days_since_last, 0.0))
    raw += config.weight_increment * (co_occurrence_count - 1)
    return min(max(raw, 0.0), config.max_weight)


def _pair_key(id_a: str, id_b: str) -> tuple[str, str]:
    """Canonical ordering for an undirected pair."""
    return (id_a, id_b) if id_a <= id_b else (id_b, id_a)


# ------------------------------------------------------------------
# Cypher queries (parametrized)
# ------------------------------------------------------------------

_UPDATE_EDGE_WEIGHT = (
    "MATCH (a:{source_label} {{id: $sourceId, userId: $userId}}) "
    "MATCH (b:{target_label} {{id: $targetId, userId: $userId}}) "
    "MERGE (a)-[r:{edge_type}]->(b) "
    "SET r.weight = $weight, r.coOccurrenceCount = $coOccurrenceCount, "
    "r.lastOccurrence = $lastOccurrence, r.updatedAt = $now "
    "RETURN type(r) AS relType"
)


def _build_weight_query(edge: WeightedEdge) -> str:
    """Build a parametrized Cypher query for updating edge weight."""
    return _UPDATE_EDGE_WEIGHT.format(
        source_label=edge.source_label,
        target_label=edge.target_label,
        edge_type=edge.edge_type,
    )


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class EdgeWeightService:
    """Computes and persists edge weights in Neo4j.

    Workflow (post-processing step after GraphBuilder):
    1.  Receive co-occurrence data from the processing pipeline.
    2.  Aggregate co-occurrences per entity pair.
    3.  Compute weight with decay.
    4.  Derive implicit edges (KNOWS, RELATED_TO).
    5.  MERGE edges with weight into Neo4j.
    """

    def __init__(
        self,
        neo4j_session: Neo4jSession,
        config: EdgeWeightConfig | None = None,
    ) -> None:
        self._session = neo4j_session
        self._config = config or EdgeWeightConfig()

    @property
    def config(self) -> EdgeWeightConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public: compute and persist weights for explicit edges
    # ------------------------------------------------------------------

    async def update_weights(
        self,
        co_occurrences: list[CoOccurrence],
        user_id: str,
        reference_time: datetime | None = None,
    ) -> WeightResult:
        """Aggregate co-occurrences, compute weights, write to Neo4j.

        Parameters
        ----------
        co_occurrences:
            Raw co-occurrence events from the processing pipeline.
        user_id:
            Tenant user ID.
        reference_time:
            Time to compute decay against (default: now UTC).

        Returns
        -------
        WeightResult
        """
        ref = reference_time or datetime.now(tz=UTC)
        aggregated = self._aggregate(co_occurrences)
        edges = self._compute_edges(aggregated, user_id, ref)
        return await self._persist_edges(edges)

    # ------------------------------------------------------------------
    # Public: derive implicit edges
    # ------------------------------------------------------------------

    async def derive_implicit_edges(
        self,
        co_occurrences: list[CoOccurrence],
        user_id: str,
        reference_time: datetime | None = None,
    ) -> WeightResult:
        """Derive KNOWS (person↔person) and RELATED_TO (topic↔topic) edges.

        KNOWS: persons co-occurring in ≥ ``knows_min_co_occurrences`` contexts.
        RELATED_TO: topics co-occurring in ≥ ``related_to_min_co_occurrences`` chunks.
        """
        ref = reference_time or datetime.now(tz=UTC)
        aggregated = self._aggregate(co_occurrences)
        derived: list[WeightedEdge] = []

        for (id_a, id_b), info in aggregated.items():
            label_a = info["label_a"]
            label_b = info["label_b"]
            count = info["count"]
            last = info["last"]

            days = max((ref - last).total_seconds() / 86400.0, 0.0)
            weight = compute_weight(count, days, self._config)

            if weight < self._config.min_weight:
                continue

            # KNOWS: Person ↔ Person, ≥ N co-occurrences
            if (
                label_a == "Person"
                and label_b == "Person"
                and count >= self._config.knows_min_co_occurrences
            ):
                derived.append(
                    WeightedEdge(
                        edge_type="KNOWS",
                        source_id=id_a,
                        target_id=id_b,
                        source_label="Person",
                        target_label="Person",
                        user_id=user_id,
                        weight=weight,
                        co_occurrence_count=count,
                        last_occurrence=last,
                    )
                )

            # RELATED_TO: Topic ↔ Topic, ≥ M co-occurrences
            if (
                label_a == "Topic"
                and label_b == "Topic"
                and count >= self._config.related_to_min_co_occurrences
            ):
                derived.append(
                    WeightedEdge(
                        edge_type="RELATED_TO",
                        source_id=id_a,
                        target_id=id_b,
                        source_label="Topic",
                        target_label="Topic",
                        user_id=user_id,
                        weight=weight,
                        co_occurrence_count=count,
                        last_occurrence=last,
                    )
                )

        result = await self._persist_edges(derived)
        result.edges_derived = result.edges_updated
        result.edges_updated = 0
        return result

    # ------------------------------------------------------------------
    # Public: full pipeline (update + derive)
    # ------------------------------------------------------------------

    async def process(
        self,
        co_occurrences: list[CoOccurrence],
        user_id: str,
        reference_time: datetime | None = None,
    ) -> WeightResult:
        """Run full weight update + implicit edge derivation."""
        ref = reference_time or datetime.now(tz=UTC)
        w_result = await self.update_weights(co_occurrences, user_id, ref)
        d_result = await self.derive_implicit_edges(co_occurrences, user_id, ref)
        return WeightResult(
            edges_updated=w_result.edges_updated,
            edges_derived=d_result.edges_derived,
            errors=w_result.errors + d_result.errors,
        )

    # ------------------------------------------------------------------
    # Internal: aggregation
    # ------------------------------------------------------------------

    def _aggregate(
        self,
        co_occurrences: list[CoOccurrence],
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """Aggregate co-occurrences by canonical entity pair.

        Returns dict keyed by (id_a, id_b) with count, last, labels, contexts.
        """
        agg: dict[tuple[str, str], dict[str, Any]] = {}

        for co in co_occurrences:
            key = _pair_key(co.entity_a_id, co.entity_b_id)
            if key not in agg:
                # Ensure labels match canonical ordering
                if key == (co.entity_a_id, co.entity_b_id):
                    la, lb = co.entity_a_label, co.entity_b_label
                else:
                    la, lb = co.entity_b_label, co.entity_a_label
                agg[key] = {
                    "count": 0,
                    "last": co.occurred_at,
                    "label_a": la,
                    "label_b": lb,
                    "contexts": set(),
                }

            entry = agg[key]
            entry["count"] += 1
            if co.occurred_at > entry["last"]:
                entry["last"] = co.occurred_at
            entry["contexts"].add(co.context_id)

        return agg

    # ------------------------------------------------------------------
    # Internal: compute WeightedEdge list from aggregated data
    # ------------------------------------------------------------------

    def _compute_edges(
        self,
        aggregated: dict[tuple[str, str], dict[str, Any]],
        user_id: str,
        reference_time: datetime,
    ) -> list[WeightedEdge]:
        """Turn aggregated data into WeightedEdge list with computed weights."""
        edges: list[WeightedEdge] = []

        for (id_a, id_b), info in aggregated.items():
            days = max(
                (reference_time - info["last"]).total_seconds() / 86400.0,
                0.0,
            )
            weight = compute_weight(info["count"], days, self._config)

            if weight < self._config.min_weight:
                continue

            # Determine edge type from labels
            edge_type = self._infer_edge_type(info["label_a"], info["label_b"])
            if edge_type is None:
                continue

            edges.append(
                WeightedEdge(
                    edge_type=edge_type,
                    source_id=id_a,
                    target_id=id_b,
                    source_label=info["label_a"],
                    target_label=info["label_b"],
                    user_id=user_id,
                    weight=weight,
                    co_occurrence_count=info["count"],
                    last_occurrence=info["last"],
                )
            )

        return edges

    # ------------------------------------------------------------------
    # Internal: infer edge type from label pair
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_edge_type(label_a: str, label_b: str) -> str | None:
        """Infer the most appropriate edge type for a label pair.

        Returns an explicit edge type for common pairs, None for unknown.
        """
        pair = frozenset({label_a, label_b})
        return _LABEL_PAIR_EDGE_MAP.get(pair)

    # ------------------------------------------------------------------
    # Internal: persist edges in Neo4j
    # ------------------------------------------------------------------

    async def _persist_edges(self, edges: list[WeightedEdge]) -> WeightResult:
        """MERGE edges with weights into Neo4j in batches."""
        result = WeightResult()
        now = datetime.now(tz=UTC).isoformat()

        for i in range(0, len(edges), self._config.batch_size):
            batch = edges[i : i + self._config.batch_size]
            for edge in batch:
                try:
                    query = _build_weight_query(edge)
                    params: dict[str, Any] = {
                        "sourceId": edge.source_id,
                        "targetId": edge.target_id,
                        "userId": edge.user_id,
                        "weight": edge.weight,
                        "coOccurrenceCount": edge.co_occurrence_count,
                        "lastOccurrence": edge.last_occurrence.isoformat(),
                        "now": now,
                    }
                    params.update(edge.properties)
                    await self._session.run(query, params)
                    result.edges_updated += 1
                except Exception as exc:
                    msg = (
                        f"Failed to update edge {edge.edge_type} "
                        f"({edge.source_id}→{edge.target_id}): {exc}"
                    )
                    logger.error(msg)
                    result.errors.append(msg)

        return result


# ------------------------------------------------------------------
# Label-pair → edge-type mapping for explicit co-occurrence edges
# ------------------------------------------------------------------

_LABEL_PAIR_EDGE_MAP: dict[frozenset[str], str] = {
    frozenset({"Person", "Meeting"}): "PARTICIPATED_IN",
    frozenset({"Person", "Project"}): "WORKS_ON",
    frozenset({"Person", "Document"}): "MENTIONED_IN",
    frozenset({"Project", "Topic"}): "HAS_TOPIC",
    frozenset({"Project", "Decision"}): "HAS_DECISION",
    frozenset({"Decision", "Meeting"}): "DECIDED_IN",
    frozenset({"Decision", "Project"}): "AFFECTS",
    frozenset({"Meeting", "Topic"}): "DISCUSSED",
    frozenset({"Meeting", "Project"}): "RELATES_TO",
    frozenset({"Meeting", "Decision"}): "PRODUCED",
    frozenset({"Document", "Person"}): "MENTIONS",
    frozenset({"Document", "Topic"}): "COVERS",
    frozenset({"Document", "Project"}): "REFERENCES",
}
