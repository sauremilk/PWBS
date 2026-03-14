"""Tests for Neo4j Graph Builder (TASK-064)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.graph.builder import (
    EdgeData,
    EdgeType,
    GraphBuilder,
    GraphBuilderConfig,
    GraphBuildResult,
    NodeData,
    NodeLabel,
    _build_edge_query,
    _build_merge_query,
)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
NODE_ID_1 = str(uuid.uuid4())
NODE_ID_2 = str(uuid.uuid4())


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _node(
    label: NodeLabel = NodeLabel.PERSON,
    node_id: str | None = None,
    name: str = "Alice",
    properties: dict[str, Any] | None = None,
) -> NodeData:
    return NodeData(
        label=label,
        node_id=node_id or str(uuid.uuid4()),
        user_id=USER_ID,
        name=name,
        properties=properties or {},
    )


def _edge(
    edge_type: EdgeType = EdgeType.MENTIONED_IN,
    source_label: NodeLabel = NodeLabel.PERSON,
    source_id: str | None = None,
    target_label: NodeLabel = NodeLabel.DOCUMENT,
    target_id: str | None = None,
    properties: dict[str, Any] | None = None,
) -> EdgeData:
    return EdgeData(
        edge_type=edge_type,
        source_label=source_label,
        source_id=source_id or NODE_ID_1,
        target_label=target_label,
        target_id=target_id or NODE_ID_2,
        user_id=USER_ID,
        properties=properties or {},
    )


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.run = AsyncMock(return_value=MagicMock())
    return session


def _builder(
    session: AsyncMock | None = None,
    config: GraphBuilderConfig | None = None,
) -> GraphBuilder:
    return GraphBuilder(
        neo4j_session=session or _mock_session(),
        config=config,
    )


# ===================================================================
# Config
# ===================================================================


class TestGraphBuilderConfig:
    def test_defaults(self) -> None:
        cfg = GraphBuilderConfig()
        assert cfg.batch_size == 50

    def test_custom(self) -> None:
        cfg = GraphBuilderConfig(batch_size=10)
        assert cfg.batch_size == 10


# ===================================================================
# Node Labels
# ===================================================================


class TestNodeLabels:
    def test_all_six_labels(self) -> None:
        labels = {nl.value for nl in NodeLabel}
        assert labels == {"Person", "Project", "Topic", "Decision", "Meeting", "Document"}


# ===================================================================
# Edge Types
# ===================================================================


class TestEdgeTypes:
    def test_all_edge_types_defined(self) -> None:
        expected = {
            "PARTICIPATED_IN", "WORKS_ON", "MENTIONED_IN", "KNOWS",
            "HAS_TOPIC", "HAS_DECISION", "DECIDED_IN", "AFFECTS",
            "SUPERSEDES", "DISCUSSED", "RELATES_TO", "PRODUCED",
            "MENTIONS", "COVERS", "REFERENCES", "RELATED_TO",
        }
        actual = {et.value for et in EdgeType}
        assert actual == expected


# ===================================================================
# Cypher Query Building
# ===================================================================


class TestCypherQueryBuilding:
    def test_merge_person_query(self) -> None:
        query = _build_merge_query(NodeLabel.PERSON, {})
        assert "MERGE (n:Person" in query
        assert "" in query
        assert "" in query
        assert "n.mentionCount" in query

    def test_merge_project_query(self) -> None:
        query = _build_merge_query(NodeLabel.PROJECT, {})
        assert "MERGE (n:Project" in query
        assert "n.firstSeen" in query

    def test_merge_with_extra_properties(self) -> None:
        query = _build_merge_query(NodeLabel.PERSON, {"email": "test@ex.com"})
        assert "n.email = " in query

    def test_merge_topic_query(self) -> None:
        query = _build_merge_query(NodeLabel.TOPIC, {})
        assert "MERGE (n:Topic" in query

    def test_merge_decision_query(self) -> None:
        query = _build_merge_query(NodeLabel.DECISION, {})
        assert "MERGE (n:Decision" in query
        assert "n.summary" in query

    def test_merge_meeting_query(self) -> None:
        query = _build_merge_query(NodeLabel.MEETING, {})
        assert "MERGE (n:Meeting" in query
        assert "n.title" in query

    def test_merge_document_query(self) -> None:
        query = _build_merge_query(NodeLabel.DOCUMENT, {})
        assert "MERGE (n:Document" in query

    def test_edge_query_parametrized(self) -> None:
        edge = _edge()
        query = _build_edge_query(edge)
        assert "" in query
        assert "" in query
        assert "" in query
        assert "MERGE" in query
        assert "MENTIONED_IN" in query

    def test_edge_query_extra_properties(self) -> None:
        edge = _edge(properties={"weight": 0.8})
        query = _build_edge_query(edge)
        assert "r.weight = " in query

    def test_no_string_concatenation_in_node_queries(self) -> None:
        """All node queries use parametrized values, not concatenation."""
        for label in NodeLabel:
            query = _build_merge_query(label, {})
            # All variable values use $ parameters
            assert "" in query
            assert "" in query

    def test_userid_in_all_node_queries(self) -> None:
        """Tenant isolation: userId in every query."""
        for label in NodeLabel:
            query = _build_merge_query(label, {})
            assert "userId: " in query

    def test_userid_in_edge_query(self) -> None:
        edge = _edge()
        query = _build_edge_query(edge)
        assert "userId: " in query


# ===================================================================
# merge_nodes
# ===================================================================


class TestMergeNodes:
    @pytest.mark.asyncio
    async def test_single_node(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        result = await builder.merge_nodes([_node()])
        assert result.nodes_created == 1
        assert session.run.await_count == 1

    @pytest.mark.asyncio
    async def test_multiple_nodes(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        nodes = [_node(name=f"Person {i}") for i in range(3)]
        result = await builder.merge_nodes(nodes)
        assert result.nodes_created == 3
        assert session.run.await_count == 3

    @pytest.mark.asyncio
    async def test_batch_processing(self) -> None:
        session = _mock_session()
        builder = _builder(session=session, config=GraphBuilderConfig(batch_size=2))
        nodes = [_node(name=f"P{i}") for i in range(5)]
        result = await builder.merge_nodes(nodes)
        assert result.nodes_created == 5

    @pytest.mark.asyncio
    async def test_node_failure_logged(self) -> None:
        session = AsyncMock()
        session.run = AsyncMock(side_effect=RuntimeError("Neo4j down"))
        builder = _builder(session=session)
        result = await builder.merge_nodes([_node()])
        assert result.nodes_created == 0
        assert len(result.errors) == 1
        assert "Neo4j down" in result.errors[0]

    @pytest.mark.asyncio
    async def test_partial_failure(self) -> None:
        session = AsyncMock()
        call_count = 0

        async def _alternate_run(q: str, p: dict | None = None) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("fail")
            return MagicMock()

        session.run = AsyncMock(side_effect=_alternate_run)
        builder = _builder(session=session)
        nodes = [_node(name=f"P{i}") for i in range(3)]
        result = await builder.merge_nodes(nodes)
        assert result.nodes_created == 2
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_empty_nodes(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        result = await builder.merge_nodes([])
        assert result.nodes_created == 0
        session.run.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_neo4j_node_ids_returned(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        nid = str(uuid.uuid4())
        result = await builder.merge_nodes([_node(node_id=nid)])
        assert nid in result.neo4j_node_ids

    @pytest.mark.asyncio
    async def test_all_labels_supported(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        nodes = [_node(label=label, name=f"Test {label.value}") for label in NodeLabel]
        result = await builder.merge_nodes(nodes)
        assert result.nodes_created == 6

    @pytest.mark.asyncio
    async def test_extra_properties_passed(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        node = _node(properties={"email": "alice@example.com", "role": "CTO"})
        await builder.merge_nodes([node])
        call_args = session.run.call_args
        params = call_args[1].get("parameters") or call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get("parameters", {})
        assert params.get("email") == "alice@example.com"
        assert params.get("role") == "CTO"


# ===================================================================
# merge_edges
# ===================================================================


class TestMergeEdges:
    @pytest.mark.asyncio
    async def test_single_edge(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        result = await builder.merge_edges([_edge()])
        assert result.edges_created == 1

    @pytest.mark.asyncio
    async def test_multiple_edges(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        edges = [_edge(edge_type=et) for et in [EdgeType.MENTIONED_IN, EdgeType.WORKS_ON]]
        result = await builder.merge_edges(edges)
        assert result.edges_created == 2

    @pytest.mark.asyncio
    async def test_edge_failure(self) -> None:
        session = AsyncMock()
        session.run = AsyncMock(side_effect=RuntimeError("Edge fail"))
        builder = _builder(session=session)
        result = await builder.merge_edges([_edge()])
        assert result.edges_created == 0
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_empty_edges(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        result = await builder.merge_edges([])
        assert result.edges_created == 0


# ===================================================================
# build (combined)
# ===================================================================


class TestBuild:
    @pytest.mark.asyncio
    async def test_build_nodes_and_edges(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        nodes = [_node()]
        edges = [_edge()]
        result = await builder.build(nodes, edges)
        assert result.nodes_created == 1
        assert result.edges_created == 1

    @pytest.mark.asyncio
    async def test_build_errors_combined(self) -> None:
        session = AsyncMock()
        call_count = 0

        async def _fail_second(q: str, p: dict | None = None) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("edge fail")
            return MagicMock()

        session.run = AsyncMock(side_effect=_fail_second)
        builder = _builder(session=session)
        result = await builder.build([_node()], [_edge()])
        assert len(result.errors) == 1


# ===================================================================
# Tenant Isolation
# ===================================================================


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_user_id_in_node_params(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        await builder.merge_nodes([_node()])
        call_args = session.run.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get("parameters", {})
        assert params.get("userId") == USER_ID

    @pytest.mark.asyncio
    async def test_user_id_in_edge_params(self) -> None:
        session = _mock_session()
        builder = _builder(session=session)
        await builder.merge_edges([_edge()])
        call_args = session.run.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get("parameters", {})
        assert params.get("userId") == USER_ID


# ===================================================================
# Config property
# ===================================================================


class TestConfigProperty:
    def test_config_accessible(self) -> None:
        cfg = GraphBuilderConfig(batch_size=25)
        builder = _builder(config=cfg)
        assert builder.config.batch_size == 25
