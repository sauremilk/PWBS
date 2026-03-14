"""Tests for Knowledge API endpoints (TASK-090)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

# ── Shared fixtures ──────────────────────────────────────────────────────────

USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()
ENTITY_ID = uuid.uuid4()


def _make_entity(
    *,
    entity_id: uuid.UUID = ENTITY_ID,
    user_id: uuid.UUID = USER_ID,
    entity_type: str = "PERSON",
    name: str = "Alice",
    normalized_name: str = "alice",
    mention_count: int = 5,
    first_seen: datetime | None = None,
    last_seen: datetime | None = None,
    metadata_: dict | None = None,
) -> MagicMock:
    e = MagicMock()
    e.id = entity_id
    e.user_id = user_id
    e.entity_type = entity_type
    e.name = name
    e.normalized_name = normalized_name
    e.mention_count = mention_count
    e.first_seen = first_seen or datetime(2024, 1, 1, tzinfo=timezone.utc)
    e.last_seen = last_seen or datetime(2024, 6, 1, tzinfo=timezone.utc)
    e.metadata_ = metadata_ or {}
    return e


def _make_user(user_id: uuid.UUID = USER_ID) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    return u


# ── Schema tests ─────────────────────────────────────────────────────────────


class TestSchemaValidation:
    """Validate Pydantic response schemas."""

    def test_entity_list_item(self) -> None:
        from pwbs.api.v1.routes.knowledge import EntityListItem

        item = EntityListItem(
            id=ENTITY_ID,
            type="PERSON",
            name="Alice",
            mention_count=5,
            last_seen=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        assert item.id == ENTITY_ID
        assert item.type == "PERSON"

    def test_entity_list_response(self) -> None:
        from pwbs.api.v1.routes.knowledge import EntityListItem, EntityListResponse

        resp = EntityListResponse(
            entities=[
                EntityListItem(id=ENTITY_ID, type="PERSON", name="Alice", mention_count=5),
            ],
            total=1,
        )
        assert resp.total == 1
        assert len(resp.entities) == 1

    def test_graph_node(self) -> None:
        from pwbs.api.v1.routes.knowledge import GraphNode

        node = GraphNode(id=str(ENTITY_ID), type="PERSON", name="Alice", size=3)
        assert node.size == 3

    def test_graph_edge(self) -> None:
        from pwbs.api.v1.routes.knowledge import GraphEdge

        edge = GraphEdge(source="a", target="b", relation="RELATED_TO")
        assert edge.weight == 1.0

    def test_graph_response(self) -> None:
        from pwbs.api.v1.routes.knowledge import GraphEdge, GraphNode, GraphResponse

        resp = GraphResponse(
            nodes=[GraphNode(id="a", type="PERSON", name="Alice")],
            edges=[GraphEdge(source="a", target="b", relation="RELATED_TO")],
        )
        assert len(resp.nodes) == 1
        assert len(resp.edges) == 1

    def test_related_entity_item(self) -> None:
        from pwbs.api.v1.routes.knowledge import RelatedEntityItem

        item = RelatedEntityItem(
            id=ENTITY_ID,
            type="TOPIC",
            name="ML",
            mention_count=3,
            relation="co_mentioned",
        )
        assert item.relation == "co_mentioned"

    def test_entity_document_item(self) -> None:
        from pwbs.api.v1.routes.knowledge import EntityDocumentItem

        item = EntityDocumentItem(
            id=uuid.uuid4(),
            title="Meeting Notes",
            source_type="notion",
            created_at=datetime(2024, 3, 1, tzinfo=timezone.utc),
        )
        assert item.source_type == "notion"

    def test_entity_detail_response(self) -> None:
        from pwbs.api.v1.routes.knowledge import EntityDetailResponse

        resp = EntityDetailResponse(
            id=ENTITY_ID,
            type="PERSON",
            name="Alice",
            normalized_name="alice",
            mention_count=5,
            related_entities=[],
        )
        assert resp.metadata is None


# ── Helper tests ─────────────────────────────────────────────────────────────


class TestCheckEntityOwnership:
    """Test _check_entity_ownership helper."""

    def test_same_user_passes(self) -> None:
        from pwbs.api.v1.routes.knowledge import _check_entity_ownership

        entity = _make_entity(user_id=USER_ID)
        _check_entity_ownership(entity, USER_ID)  # should not raise

    def test_different_user_raises_403(self) -> None:
        from pwbs.api.v1.routes.knowledge import _check_entity_ownership

        entity = _make_entity(user_id=USER_ID)
        with pytest.raises(Exception) as exc_info:
            _check_entity_ownership(entity, OTHER_USER_ID)
        assert exc_info.value.status_code == 403


class TestGetEntityOr404:
    """Test _get_entity_or_404 helper."""

    @pytest.mark.asyncio
    async def test_found(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_entity_or_404

        entity = _make_entity()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entity
        db.execute.return_value = result_mock

        found = await _get_entity_or_404(ENTITY_ID, db)
        assert found.id == ENTITY_ID

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_entity_or_404

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(Exception) as exc_info:
            await _get_entity_or_404(ENTITY_ID, db)
        assert exc_info.value.status_code == 404


# ── Related entities (PostgreSQL fallback) ───────────────────────────────────


class TestGetRelatedFromPostgres:
    """Test _get_related_from_postgres helper."""

    @pytest.mark.asyncio
    async def test_returns_related_entities(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_related_from_postgres

        related_id = uuid.uuid4()
        row = MagicMock()
        row.id = related_id
        row.entity_type = "PROJECT"
        row.name = "PWBS"
        row.mention_count = 3

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.all.return_value = [row]
        db.execute.return_value = result_mock

        results = await _get_related_from_postgres(ENTITY_ID, USER_ID, db)
        assert len(results) == 1
        assert results[0].id == related_id
        assert results[0].relation == "co_mentioned"

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_related_from_postgres

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.all.return_value = []
        db.execute.return_value = result_mock

        results = await _get_related_from_postgres(ENTITY_ID, USER_ID, db)
        assert results == []


# ── Neo4j related entities ───────────────────────────────────────────────────


class TestGetNeo4jRelated:
    """Test _get_neo4j_related helper."""

    @pytest.mark.asyncio
    async def test_returns_neo4j_related(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_neo4j_related

        related_id = uuid.uuid4()

        mock_result = AsyncMock()
        mock_result.data.return_value = [
            {
                "id": str(related_id),
                "type": "TOPIC",
                "name": "AI",
                "mention_count": 7,
                "relation": "RELATED_TO",
            }
        ]

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.run = AsyncMock(return_value=mock_result)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_ctx

        with patch("pwbs.db.neo4j_client.get_neo4j_driver", return_value=mock_driver):
            results = await _get_neo4j_related(ENTITY_ID, USER_ID)

        assert len(results) == 1
        assert results[0].id == related_id
        assert results[0].relation == "RELATED_TO"

    @pytest.mark.asyncio
    async def test_neo4j_failure_returns_empty(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_neo4j_related

        with patch(
            "pwbs.db.neo4j_client.get_neo4j_driver",
            side_effect=RuntimeError("connection failed"),
        ):
            results = await _get_neo4j_related(ENTITY_ID, USER_ID)

        assert results == []

    @pytest.mark.asyncio
    async def test_depth_clamped(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_neo4j_related

        mock_result = AsyncMock()
        mock_result.data.return_value = []

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.run = AsyncMock(return_value=mock_result)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_ctx

        with patch("pwbs.db.neo4j_client.get_neo4j_driver", return_value=mock_driver):
            # depth=10 should be clamped to max 3
            await _get_neo4j_related(ENTITY_ID, USER_ID, depth=10)

        # Verify the Cypher query used *1..3 not *1..10
        call_args = mock_ctx.run.call_args
        assert "*1..3" in call_args[0][0]


# ── Neo4j graph ──────────────────────────────────────────────────────────────


class TestGetNeo4jGraph:
    """Test _get_neo4j_graph helper."""

    @pytest.mark.asyncio
    async def test_returns_graph(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_neo4j_graph

        node_id_a = str(uuid.uuid4())
        node_id_b = str(uuid.uuid4())

        node_result = AsyncMock()
        node_result.data.return_value = [
            {"id": node_id_a, "type": "PERSON", "name": "Alice", "mention_count": 5},
            {"id": node_id_b, "type": "TOPIC", "name": "AI", "mention_count": 3},
        ]

        edge_result = AsyncMock()
        edge_result.data.return_value = [
            {"source": node_id_a, "target": node_id_b, "relation": "DISCUSSED_IN", "weight": 2.0},
        ]

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.run = AsyncMock(side_effect=[node_result, edge_result])

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_ctx

        with patch("pwbs.db.neo4j_client.get_neo4j_driver", return_value=mock_driver):
            graph = await _get_neo4j_graph(USER_ID, limit=10)

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.edges[0].relation == "DISCUSSED_IN"

    @pytest.mark.asyncio
    async def test_empty_graph(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_neo4j_graph

        node_result = AsyncMock()
        node_result.data.return_value = []

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.run = AsyncMock(return_value=node_result)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_ctx

        with patch("pwbs.db.neo4j_client.get_neo4j_driver", return_value=mock_driver):
            graph = await _get_neo4j_graph(USER_ID)

        assert graph.nodes == []
        assert graph.edges == []

    @pytest.mark.asyncio
    async def test_neo4j_failure_returns_empty_graph(self) -> None:
        from pwbs.api.v1.routes.knowledge import _get_neo4j_graph

        with patch(
            "pwbs.db.neo4j_client.get_neo4j_driver",
            side_effect=RuntimeError("unavailable"),
        ):
            graph = await _get_neo4j_graph(USER_ID)

        assert graph.nodes == []
        assert graph.edges == []


# ── Endpoint tests ───────────────────────────────────────────────────────────


class TestListEntities:
    """Test GET /api/v1/knowledge/entities."""

    @pytest.mark.asyncio
    async def test_list_empty(self) -> None:
        from pwbs.api.v1.routes.knowledge import list_entities

        user = _make_user()
        db = AsyncMock()

        # Count returns 0
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        # Entity query returns empty
        entity_result = MagicMock()
        entity_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[count_result, entity_result])

        resp = await list_entities(
            response=MagicMock(),
            user=user,
            db=db,
            entity_type=None,
            offset=0,
            limit=20,
        )
        assert resp.total == 0
        assert resp.entities == []

    @pytest.mark.asyncio
    async def test_list_with_entities(self) -> None:
        from pwbs.api.v1.routes.knowledge import list_entities

        user = _make_user()
        db = AsyncMock()

        entity = _make_entity()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        entity_result = MagicMock()
        entity_result.scalars.return_value.all.return_value = [entity]

        db.execute = AsyncMock(side_effect=[count_result, entity_result])

        resp = await list_entities(
            response=MagicMock(),
            user=user,
            db=db,
            entity_type=None,
            offset=0,
            limit=20,
        )
        assert resp.total == 1
        assert resp.entities[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_limit_clamped(self) -> None:
        from pwbs.api.v1.routes.knowledge import list_entities

        user = _make_user()
        db = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        entity_result = MagicMock()
        entity_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[count_result, entity_result])

        # limit=200 should be clamped to 50
        resp = await list_entities(
            response=MagicMock(),
            user=user,
            db=db,
            entity_type=None,
            offset=0,
            limit=200,
        )
        assert resp.total == 0


# ── GET entity detail ────────────────────────────────────────────────────────


class TestGetEntity:
    """Test GET /api/v1/knowledge/entities/{entity_id}."""

    @pytest.mark.asyncio
    async def test_get_entity_success(self) -> None:
        from pwbs.api.v1.routes.knowledge import get_entity

        entity = _make_entity()
        user = _make_user()
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entity
        db.execute.return_value = result_mock

        with patch(
            "pwbs.api.v1.routes.knowledge._get_neo4j_related",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "pwbs.api.v1.routes.knowledge._get_related_from_postgres",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await get_entity(
                entity_id=ENTITY_ID,
                response=MagicMock(),
                user=user,
                db=db,
            )

        assert resp.id == ENTITY_ID
        assert resp.name == "Alice"

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self) -> None:
        from pwbs.api.v1.routes.knowledge import get_entity

        user = _make_user()
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(Exception) as exc_info:
            await get_entity(
                entity_id=ENTITY_ID,
                response=MagicMock(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_entity_forbidden(self) -> None:
        from pwbs.api.v1.routes.knowledge import get_entity

        entity = _make_entity(user_id=OTHER_USER_ID)
        user = _make_user(USER_ID)
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entity
        db.execute.return_value = result_mock

        with pytest.raises(Exception) as exc_info:
            await get_entity(
                entity_id=ENTITY_ID,
                response=MagicMock(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 403


# ── GET related entities ─────────────────────────────────────────────────────


class TestGetRelatedEntities:
    """Test GET /api/v1/knowledge/entities/{entity_id}/related."""

    @pytest.mark.asyncio
    async def test_related_success(self) -> None:
        from pwbs.api.v1.routes.knowledge import RelatedEntityItem, get_related_entities

        entity = _make_entity()
        user = _make_user()
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entity
        db.execute.return_value = result_mock

        related_item = RelatedEntityItem(
            id=uuid.uuid4(),
            type="TOPIC",
            name="ML",
            mention_count=2,
            relation="RELATED_TO",
        )

        with patch(
            "pwbs.api.v1.routes.knowledge._get_neo4j_related",
            new_callable=AsyncMock,
            return_value=[related_item],
        ):
            results = await get_related_entities(
                entity_id=ENTITY_ID,
                response=MagicMock(),
                user=user,
                db=db,
                depth=2,
                limit=20,
            )

        assert len(results) == 1
        assert results[0].name == "ML"

    @pytest.mark.asyncio
    async def test_related_not_found(self) -> None:
        from pwbs.api.v1.routes.knowledge import get_related_entities

        user = _make_user()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(Exception) as exc_info:
            await get_related_entities(
                entity_id=ENTITY_ID,
                response=MagicMock(),
                user=user,
                db=db,
                depth=2,
                limit=20,
            )
        assert exc_info.value.status_code == 404


# ── GET entity documents ─────────────────────────────────────────────────────


class TestGetEntityDocuments:
    """Test GET /api/v1/knowledge/entities/{entity_id}/documents."""

    @pytest.mark.asyncio
    async def test_documents_success(self) -> None:
        from pwbs.api.v1.routes.knowledge import get_entity_documents

        entity = _make_entity()
        user = _make_user()
        db = AsyncMock()

        # First call: _get_entity_or_404
        entity_result = MagicMock()
        entity_result.scalar_one_or_none.return_value = entity

        # Second call: count
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        # Third call: documents
        doc_id = uuid.uuid4()
        doc_row = MagicMock()
        doc_row.id = doc_id
        doc_row.title = "Meeting Notes"
        doc_row.source_type = "notion"
        doc_row.created_at = datetime(2024, 3, 1, tzinfo=timezone.utc)

        doc_result = MagicMock()
        doc_result.all.return_value = [doc_row]

        db.execute = AsyncMock(side_effect=[entity_result, count_result, doc_result])

        resp = await get_entity_documents(
            entity_id=ENTITY_ID,
            response=MagicMock(),
            user=user,
            db=db,
            offset=0,
            limit=20,
        )
        assert resp.total == 1
        assert resp.documents[0].title == "Meeting Notes"

    @pytest.mark.asyncio
    async def test_documents_entity_not_found(self) -> None:
        from pwbs.api.v1.routes.knowledge import get_entity_documents

        user = _make_user()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(Exception) as exc_info:
            await get_entity_documents(
                entity_id=ENTITY_ID,
                response=MagicMock(),
                user=user,
                db=db,
                offset=0,
                limit=20,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_documents_forbidden(self) -> None:
        from pwbs.api.v1.routes.knowledge import get_entity_documents

        entity = _make_entity(user_id=OTHER_USER_ID)
        user = _make_user(USER_ID)
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entity
        db.execute.return_value = result_mock

        with pytest.raises(Exception) as exc_info:
            await get_entity_documents(
                entity_id=ENTITY_ID,
                response=MagicMock(),
                user=user,
                db=db,
                offset=0,
                limit=20,
            )
        assert exc_info.value.status_code == 403


# ── GET graph ────────────────────────────────────────────────────────────────


class TestGetGraph:
    """Test GET /api/v1/knowledge/graph."""

    @pytest.mark.asyncio
    async def test_graph_success(self) -> None:
        from pwbs.api.v1.routes.knowledge import GraphResponse, get_graph

        user = _make_user()

        expected = GraphResponse(nodes=[], edges=[])
        with patch(
            "pwbs.api.v1.routes.knowledge._get_neo4j_graph",
            new_callable=AsyncMock,
            return_value=expected,
        ):
            resp = await get_graph(
                response=MagicMock(),
                user=user,
                limit=50,
            )

        assert resp.nodes == []
        assert resp.edges == []

    @pytest.mark.asyncio
    async def test_graph_limit_clamped(self) -> None:
        from pwbs.api.v1.routes.knowledge import get_graph

        user = _make_user()

        with patch(
            "pwbs.api.v1.routes.knowledge._get_neo4j_graph",
            new_callable=AsyncMock,
        ) as mock_graph:
            mock_graph.return_value = MagicMock(nodes=[], edges=[])
            await get_graph(
                response=MagicMock(),
                user=user,
                limit=200,
            )
            # Should be clamped to 50
            mock_graph.assert_called_once_with(user.id, limit=50)


# ── Router metadata ──────────────────────────────────────────────────────────


class TestRouterMetadata:
    """Verify router configuration."""

    def test_prefix(self) -> None:
        from pwbs.api.v1.routes.knowledge import router

        assert router.prefix == "/api/v1/knowledge"

    def test_tags(self) -> None:
        from pwbs.api.v1.routes.knowledge import router

        assert "knowledge" in router.tags

    def test_route_count(self) -> None:
        from pwbs.api.v1.routes.knowledge import router

        paths = [r.path for r in router.routes]
        assert "/api/v1/knowledge/entities" in paths
        assert "/api/v1/knowledge/entities/{entity_id}" in paths
        assert "/api/v1/knowledge/entities/{entity_id}/related" in paths
        assert "/api/v1/knowledge/entities/{entity_id}/documents" in paths
        assert "/api/v1/knowledge/graph" in paths
