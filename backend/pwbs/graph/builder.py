"""Neo4j Graph Builder mit MERGE-basierter Idempotenz (TASK-064).

Writes extracted entities as nodes and their relationships as edges
into the Neo4j knowledge graph.  Uses `MERGE` instead of `CREATE`
for full idempotency.

Node labels: Person, Project, Topic, Decision, Meeting, Document
Edge types: PARTICIPATED_IN, WORKS_ON, MENTIONED_IN, KNOWS,
            HAS_TOPIC, HAS_DECISION, DECIDED_IN, AFFECTS,
            SUPERSEDES, DISCUSSED, RELATES_TO, PRODUCED,
            MENTIONS, COVERS, REFERENCES, RELATED_TO

All queries use parametrized Cypher (no string concatenation)
and include `userId` for tenant isolation.

D1 §3.3.3, D1 §3.2, AGENTS.md GraphAgent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

__all__ = [
    "GraphBuilder",
    "GraphBuilderConfig",
    "GraphBuildResult",
    "NodeLabel",
    "EdgeType",
    "NodeData",
    "EdgeData",
    "Neo4jSession",
]


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

_DEFAULT_BATCH_SIZE = 50


@dataclass(frozen=True, slots=True)
class GraphBuilderConfig:
    """Configuration for the Neo4j Graph Builder."""

    batch_size: int = _DEFAULT_BATCH_SIZE


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class NodeLabel(str, Enum):
    """Supported Neo4j node labels."""

    PERSON = "Person"
    PROJECT = "Project"
    TOPIC = "Topic"
    DECISION = "Decision"
    MEETING = "Meeting"
    DOCUMENT = "Document"
    GOAL = "Goal"
    RISK = "Risk"
    HYPOTHESIS = "Hypothesis"
    OPEN_QUESTION = "OpenQuestion"
    DATE_REF = "DateRef"


class EdgeType(str, Enum):
    """Supported Neo4j relationship types."""

    PARTICIPATED_IN = "PARTICIPATED_IN"
    WORKS_ON = "WORKS_ON"
    MENTIONED_IN = "MENTIONED_IN"
    KNOWS = "KNOWS"
    HAS_TOPIC = "HAS_TOPIC"
    HAS_DECISION = "HAS_DECISION"
    DECIDED_IN = "DECIDED_IN"
    AFFECTS = "AFFECTS"
    SUPERSEDES = "SUPERSEDES"
    DISCUSSED = "DISCUSSED"
    RELATES_TO = "RELATES_TO"
    PRODUCED = "PRODUCED"
    MENTIONS = "MENTIONS"
    COVERS = "COVERS"
    REFERENCES = "REFERENCES"
    RELATED_TO = "RELATED_TO"


# ------------------------------------------------------------------
# Data containers
# ------------------------------------------------------------------


@dataclass(slots=True)
class NodeData:
    """Data for a single node to create/update in Neo4j."""

    label: NodeLabel
    node_id: str
    user_id: str
    name: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EdgeData:
    """Data for a relationship between two nodes."""

    edge_type: EdgeType
    source_label: NodeLabel
    source_id: str
    target_label: NodeLabel
    target_id: str
    user_id: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphBuildResult:
    """Result of a graph build operation."""

    nodes_created: int = 0
    nodes_updated: int = 0
    edges_created: int = 0
    neo4j_node_ids: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Neo4j Session Protocol
# ------------------------------------------------------------------


@runtime_checkable
class Neo4jSession(Protocol):
    """Protocol for async Neo4j session/transaction."""

    async def run(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a Cypher query."""
        ...


# ------------------------------------------------------------------
# Cypher Templates (parametrized, no string concatenation)
# ------------------------------------------------------------------

# MERGE node by (userId, id) – the uniqueness constraint pair
_MERGE_NODE_TEMPLATE: dict[NodeLabel, str] = {
    NodeLabel.PERSON: (
        "MERGE (n:Person {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.name = $name, n.firstSeen = $now, n.lastSeen = $now, "
        "n.mentionCount = 1{extra_set} "
        "ON MATCH SET n.lastSeen = $now, n.mentionCount = n.mentionCount + 1{extra_set} "
        "RETURN n.id AS nodeId, n.mentionCount AS mc"
    ),
    NodeLabel.PROJECT: (
        "MERGE (n:Project {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.name = $name, n.firstSeen = $now, n.lastSeen = $now{extra_set} "
        "ON MATCH SET n.lastSeen = $now{extra_set} "
        "RETURN n.id AS nodeId"
    ),
    NodeLabel.TOPIC: (
        "MERGE (n:Topic {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.name = $name, n.mentionCount = 1{extra_set} "
        "ON MATCH SET n.mentionCount = n.mentionCount + 1{extra_set} "
        "RETURN n.id AS nodeId"
    ),
    NodeLabel.DECISION: (
        "MERGE (n:Decision {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.summary = $name{extra_set} "
        "ON MATCH SET n.summary = $name{extra_set} "
        "RETURN n.id AS nodeId"
    ),
    NodeLabel.MEETING: (
        "MERGE (n:Meeting {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.title = $name{extra_set} "
        "ON MATCH SET n.title = $name{extra_set} "
        "RETURN n.id AS nodeId"
    ),
    NodeLabel.DOCUMENT: (
        "MERGE (n:Document {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.title = $name, n.createdAt = $now{extra_set} "
        "ON MATCH SET n.title = $name{extra_set} "
        "RETURN n.id AS nodeId"
    ),
    NodeLabel.GOAL: (
        "MERGE (n:Goal {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.description = $name, n.firstSeen = $now{extra_set} "
        "ON MATCH SET n.lastSeen = $now{extra_set} "
        "RETURN n.id AS nodeId"
    ),
    NodeLabel.RISK: (
        "MERGE (n:Risk {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.description = $name, n.firstSeen = $now{extra_set} "
        "ON MATCH SET n.lastSeen = $now{extra_set} "
        "RETURN n.id AS nodeId"
    ),
    NodeLabel.HYPOTHESIS: (
        "MERGE (n:Hypothesis {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.statement = $name, n.firstSeen = $now{extra_set} "
        "ON MATCH SET n.lastSeen = $now{extra_set} "
        "RETURN n.id AS nodeId"
    ),
    NodeLabel.OPEN_QUESTION: (
        "MERGE (n:OpenQuestion {{id: $nodeId, userId: $userId}}) "
        "ON CREATE SET n.text = $name, n.firstSeen = $now{extra_set} "
        "ON MATCH SET n.lastSeen = $now{extra_set} "
        "RETURN n.id AS nodeId"
    ),
}


def _build_merge_query(label: NodeLabel, properties: dict[str, Any]) -> str:
    """Build a MERGE Cypher query with optional extra properties."""
    template = _MERGE_NODE_TEMPLATE[label]
    extra_parts: list[str] = []
    for key in properties:
        extra_parts.append(f", n.{key} = ${key}")
    extra_set = "".join(extra_parts)
    return template.replace("{extra_set}", extra_set)


# Edge MERGE template
_MERGE_EDGE_QUERY = (
    "MATCH (a:{source_label} {{id: $sourceId, userId: $userId}}) "
    "MATCH (b:{target_label} {{id: $targetId, userId: $userId}}) "
    "MERGE (a)-[r:{edge_type}]->(b) "
    "SET r.updatedAt = $now{extra_set} "
    "RETURN type(r) AS relType"
)


def _build_edge_query(edge: EdgeData) -> str:
    """Build a MERGE Cypher query for an edge."""
    extra_parts: list[str] = []
    for key in edge.properties:
        extra_parts.append(f", r.{key} = ${key}")
    extra_set = "".join(extra_parts)
    return _MERGE_EDGE_QUERY.format(
        source_label=edge.source_label.value,
        target_label=edge.target_label.value,
        edge_type=edge.edge_type.value,
        extra_set=extra_set,
    )


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class GraphBuilder:
    """Builds the Neo4j knowledge graph from extracted entities.

    All writes use MERGE for idempotency.  All queries include
    `userId` for tenant isolation.  Parametrized Cypher only.

    Parameters
    ----------
    neo4j_session:
        An async Neo4j session or transaction object.
    config:
        Builder configuration.
    """

    def __init__(
        self,
        neo4j_session: Neo4jSession,
        config: GraphBuilderConfig | None = None,
    ) -> None:
        self._session = neo4j_session
        self._config = config or GraphBuilderConfig()

    @property
    def config(self) -> GraphBuilderConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API: merge nodes
    # ------------------------------------------------------------------

    async def merge_nodes(
        self,
        nodes: list[NodeData],
    ) -> GraphBuildResult:
        """MERGE a list of nodes into Neo4j.

        Processes in batches of `config.batch_size`.

        Returns
        -------
        GraphBuildResult
        """
        result = GraphBuildResult()

        for i in range(0, len(nodes), self._config.batch_size):
            batch = nodes[i : i + self._config.batch_size]
            for node in batch:
                try:
                    neo4j_id = await self._merge_single_node(node)
                    if neo4j_id is not None:
                        result.neo4j_node_ids[node.node_id] = neo4j_id
                        result.nodes_created += 1
                except Exception as exc:
                    msg = f"Failed to merge node {node.label.value}:{node.node_id}: {exc}"
                    logger.error(msg)
                    result.errors.append(msg)

        return result

    # ------------------------------------------------------------------
    # Public API: merge edges
    # ------------------------------------------------------------------

    async def merge_edges(
        self,
        edges: list[EdgeData],
    ) -> GraphBuildResult:
        """MERGE a list of relationships into Neo4j.

        Returns
        -------
        GraphBuildResult
        """
        result = GraphBuildResult()

        for i in range(0, len(edges), self._config.batch_size):
            batch = edges[i : i + self._config.batch_size]
            for edge in batch:
                try:
                    created = await self._merge_single_edge(edge)
                    if created:
                        result.edges_created += 1
                except Exception as exc:
                    msg = (
                        f"Failed to merge edge {edge.edge_type.value} "
                        f"({edge.source_id}{edge.target_id}): {exc}"
                    )
                    logger.error(msg)
                    result.errors.append(msg)

        return result

    # ------------------------------------------------------------------
    # Public API: build (nodes + edges in one call)
    # ------------------------------------------------------------------

    async def build(
        self,
        nodes: list[NodeData],
        edges: list[EdgeData],
    ) -> GraphBuildResult:
        """MERGE all nodes and then all edges.

        Returns combined result.
        """
        node_result = await self.merge_nodes(nodes)
        edge_result = await self.merge_edges(edges)

        return GraphBuildResult(
            nodes_created=node_result.nodes_created,
            nodes_updated=node_result.nodes_updated,
            edges_created=edge_result.edges_created,
            neo4j_node_ids=node_result.neo4j_node_ids,
            errors=node_result.errors + edge_result.errors,
        )

    # ------------------------------------------------------------------
    # Internal: single MERGE operations
    # ------------------------------------------------------------------

    async def _merge_single_node(self, node: NodeData) -> str | None:
        """MERGE a single node and return its Neo4j internal id string."""
        now = datetime.now(tz=timezone.utc).isoformat()
        query = _build_merge_query(node.label, node.properties)

        params: dict[str, Any] = {
            "nodeId": node.node_id,
            "userId": node.user_id,
            "name": node.name,
            "now": now,
        }
        params.update(node.properties)

        result = await self._session.run(query, params)
        return node.node_id

    async def _merge_single_edge(self, edge: EdgeData) -> bool:
        """MERGE a single edge. Returns True on success."""
        now = datetime.now(tz=timezone.utc).isoformat()
        query = _build_edge_query(edge)

        params: dict[str, Any] = {
            "sourceId": edge.source_id,
            "targetId": edge.target_id,
            "userId": edge.user_id,
            "now": now,
        }
        params.update(edge.properties)

        await self._session.run(query, params)
        return True
