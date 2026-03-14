"""Tests for Documents API endpoints (TASK-091)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.api.v1.routes.documents import (
    ChunkDetailResponse,
    ChunkEntityResponse,
    DocumentDetailResponse,
    DocumentListItem,
    DocumentListResponse,
    _build_chunk_details,
    _cascade_delete_neo4j,
    _cascade_delete_weaviate,
    _check_document_ownership,
    _get_document_or_404,
    router,
)
from pwbs.models.chunk import Chunk as ChunkORM
from pwbs.models.document import Document as DocumentORM
from pwbs.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID | None = None) -> User:
    u = MagicMock(spec=User)
    u.id = user_id or USER_ID
    u.email = "test@example.com"
    return u


def _make_document_orm(
    doc_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    title: str | None = "Test Document",
    source_type: str = "notion",
    source_id: str = "notion-page-123",
    chunk_count: int = 3,
    language: str = "de",
    processing_status: str = "completed",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> DocumentORM:
    row = MagicMock(spec=DocumentORM)
    row.id = doc_id or uuid.uuid4()
    row.user_id = user_id or USER_ID
    row.title = title
    row.source_type = source_type
    row.source_id = source_id
    row.chunk_count = chunk_count
    row.language = language
    row.processing_status = processing_status
    row.created_at = created_at or datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc)
    row.updated_at = updated_at or datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc)
    return row


def _make_chunk_orm(
    chunk_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    chunk_index: int = 0,
    content_preview: str | None = "Preview text...",
    weaviate_id: uuid.UUID | None = None,
) -> ChunkORM:
    c = MagicMock(spec=ChunkORM)
    c.id = chunk_id or uuid.uuid4()
    c.document_id = document_id or uuid.uuid4()
    c.user_id = user_id or USER_ID
    c.chunk_index = chunk_index
    c.content_preview = content_preview
    c.weaviate_id = weaviate_id
    return c


# ---------------------------------------------------------------------------
# Test: _check_document_ownership
# ---------------------------------------------------------------------------


class TestCheckDocumentOwnership:
    def test_passes_for_owner(self) -> None:
        doc = _make_document_orm(user_id=USER_ID)
        _check_document_ownership(doc, USER_ID)  # no exception

    def test_raises_403_for_other_user(self) -> None:
        from fastapi import HTTPException

        doc = _make_document_orm(user_id=USER_ID)
        with pytest.raises(HTTPException) as exc_info:
            _check_document_ownership(doc, OTHER_USER_ID)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test: _get_document_or_404
# ---------------------------------------------------------------------------


class TestGetDocumentOr404:
    @pytest.mark.asyncio
    async def test_returns_document(self) -> None:
        doc = _make_document_orm()
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = doc
        db.execute.return_value = result

        found = await _get_document_or_404(doc.id, db)
        assert found.id == doc.id

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self) -> None:
        from fastapi import HTTPException

        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        with pytest.raises(HTTPException) as exc_info:
            await _get_document_or_404(uuid.uuid4(), db)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test: _build_chunk_details
# ---------------------------------------------------------------------------


class TestBuildChunkDetails:
    @pytest.mark.asyncio
    async def test_returns_chunks_with_entities(self) -> None:
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        chunk = _make_chunk_orm(chunk_id=chunk_id, document_id=doc_id, chunk_index=0)

        db = AsyncMock()

        # First call: chunk query
        chunk_result = MagicMock()
        chunk_scalars = MagicMock()
        chunk_scalars.all.return_value = [chunk]
        chunk_result.scalars.return_value = chunk_scalars

        # Second call: entity mention query
        mention_row = MagicMock()
        mention_row.chunk_id = chunk_id
        mention_row.entity_id = entity_id
        mention_row.name = "Alice"
        mention_row.entity_type = "person"
        mention_row.confidence = 0.95

        mention_result = MagicMock()
        mention_result.all.return_value = [mention_row]

        db.execute.side_effect = [chunk_result, mention_result]

        result = await _build_chunk_details(doc_id, USER_ID, db)

        assert len(result) == 1
        assert result[0].id == chunk_id
        assert result[0].index == 0
        assert len(result[0].entities) == 1
        assert result[0].entities[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_chunks(self) -> None:
        db = AsyncMock()
        chunk_result = MagicMock()
        chunk_scalars = MagicMock()
        chunk_scalars.all.return_value = []
        chunk_result.scalars.return_value = chunk_scalars
        db.execute.return_value = chunk_result

        result = await _build_chunk_details(uuid.uuid4(), USER_ID, db)
        assert result == []


# ---------------------------------------------------------------------------
# Test: _cascade_delete_weaviate
# ---------------------------------------------------------------------------


class TestCascadeDeleteWeaviate:
    @pytest.mark.asyncio
    async def test_no_weaviate_ids_returns_zero(self) -> None:
        chunks = [_make_chunk_orm(weaviate_id=None)]
        result = await _cascade_delete_weaviate(chunks)
        assert result == 0

    @pytest.mark.asyncio
    async def test_deletes_weaviate_vectors(self) -> None:
        wid = uuid.uuid4()
        chunks = [_make_chunk_orm(weaviate_id=wid)]

        mock_collection = MagicMock()
        mock_collection.data.delete_by_id = MagicMock()

        mock_client = MagicMock()
        mock_client.collections.get.return_value = mock_collection

        with patch(
            "pwbs.db.weaviate_client.get_weaviate_client",
            return_value=mock_client,
        ):
            result = await _cascade_delete_weaviate(chunks)

        assert result == 1
        mock_collection.data.delete_by_id.assert_called_once_with(str(wid))

    @pytest.mark.asyncio
    async def test_handles_weaviate_failure_gracefully(self) -> None:
        wid = uuid.uuid4()
        chunks = [_make_chunk_orm(weaviate_id=wid)]

        with patch(
            "pwbs.db.weaviate_client.get_weaviate_client",
            side_effect=Exception("Connection failed"),
        ):
            result = await _cascade_delete_weaviate(chunks)
        assert result == 0


# ---------------------------------------------------------------------------
# Test: _cascade_delete_neo4j
# ---------------------------------------------------------------------------


class TestCascadeDeleteNeo4j:
    @pytest.mark.asyncio
    async def test_runs_cypher_delete(self) -> None:
        doc_id = uuid.uuid4()
        mock_session = AsyncMock()

        # Create a proper async context manager for driver.session()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_ctx

        with patch(
            "pwbs.db.neo4j_client.get_neo4j_driver",
            return_value=mock_driver,
        ):
            await _cascade_delete_neo4j(doc_id, USER_ID)

        mock_session.run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handles_neo4j_failure_gracefully(self) -> None:
        with patch(
            "pwbs.db.neo4j_client.get_neo4j_driver",
            side_effect=Exception("Neo4j down"),
        ):
            # Should not raise
            await _cascade_delete_neo4j(uuid.uuid4(), USER_ID)


# ---------------------------------------------------------------------------
# Test: GET /api/v1/documents/ (list)
# ---------------------------------------------------------------------------


class TestListDocuments:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self) -> None:
        from fastapi import Response

        user = _make_user()
        db = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        list_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        list_result.scalars.return_value = scalars_mock

        db.execute.side_effect = [count_result, list_result]

        from pwbs.api.v1.routes.documents import list_documents

        result = await list_documents(
            response=Response(),
            user=user,
            db=db,
        )

        assert result.total == 0
        assert result.documents == []

    @pytest.mark.asyncio
    async def test_returns_paginated_documents(self) -> None:
        from fastapi import Response

        user = _make_user()
        db = AsyncMock()
        doc = _make_document_orm()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 5
        list_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [doc]
        list_result.scalars.return_value = scalars_mock

        db.execute.side_effect = [count_result, list_result]

        from pwbs.api.v1.routes.documents import list_documents

        result = await list_documents(
            response=Response(),
            user=user,
            db=db,
            limit=20,
        )

        assert result.total == 5
        assert len(result.documents) == 1
        assert result.documents[0].source_type == "notion"

    @pytest.mark.asyncio
    async def test_filters_by_source_type(self) -> None:
        from fastapi import Response

        user = _make_user()
        db = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        list_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        list_result.scalars.return_value = scalars_mock
        db.execute.side_effect = [count_result, list_result]

        from pwbs.api.v1.routes.documents import list_documents

        result = await list_documents(
            response=Response(),
            user=user,
            db=db,
            source_type="google_calendar",
        )

        assert result.total == 0


# ---------------------------------------------------------------------------
# Test: GET /api/v1/documents/{id} (detail)
# ---------------------------------------------------------------------------


class TestGetDocument:
    @pytest.mark.asyncio
    async def test_returns_document_with_chunks(self) -> None:
        from fastapi import Response

        doc_id = uuid.uuid4()
        user = _make_user()
        doc = _make_document_orm(doc_id=doc_id, user_id=USER_ID)

        db = AsyncMock()

        # First call: document query
        doc_result = MagicMock()
        doc_result.scalar_one_or_none.return_value = doc

        # Second call: chunks query (no chunks)
        chunk_result = MagicMock()
        chunk_scalars = MagicMock()
        chunk_scalars.all.return_value = []
        chunk_result.scalars.return_value = chunk_scalars

        db.execute.side_effect = [doc_result, chunk_result]

        from pwbs.api.v1.routes.documents import get_document

        result = await get_document(
            document_id=doc_id,
            response=Response(),
            user=user,
            db=db,
        )

        assert result.id == doc_id
        assert result.source_type == "notion"
        assert result.chunks == []

    @pytest.mark.asyncio
    async def test_raises_404_for_missing_document(self) -> None:
        from fastapi import HTTPException, Response

        user = _make_user()
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        from pwbs.api.v1.routes.documents import get_document

        with pytest.raises(HTTPException) as exc_info:
            await get_document(
                document_id=uuid.uuid4(),
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_for_other_users_document(self) -> None:
        from fastapi import HTTPException, Response

        doc_id = uuid.uuid4()
        user = _make_user(user_id=OTHER_USER_ID)
        doc = _make_document_orm(doc_id=doc_id, user_id=USER_ID)

        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = doc
        db.execute.return_value = result

        from pwbs.api.v1.routes.documents import get_document

        with pytest.raises(HTTPException) as exc_info:
            await get_document(
                document_id=doc_id,
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test: DELETE /api/v1/documents/{id}
# ---------------------------------------------------------------------------


class TestDeleteDocument:
    @pytest.mark.asyncio
    async def test_deletes_document_with_cascades(self) -> None:
        from fastapi import Response

        doc_id = uuid.uuid4()
        user = _make_user()
        doc = _make_document_orm(doc_id=doc_id, user_id=USER_ID)

        db = AsyncMock()

        # First call: document lookup
        doc_result = MagicMock()
        doc_result.scalar_one_or_none.return_value = doc

        # Second call: chunks query
        chunk_result = MagicMock()
        chunk_scalars = MagicMock()
        chunk_scalars.all.return_value = []
        chunk_result.scalars.return_value = chunk_scalars

        # Third call: PostgreSQL delete
        delete_result = MagicMock()

        db.execute.side_effect = [doc_result, chunk_result, delete_result]

        from pwbs.api.v1.routes.documents import delete_document

        with patch(
            "pwbs.api.v1.routes.documents._cascade_delete_neo4j",
            new_callable=AsyncMock,
        ), patch(
            "pwbs.api.v1.routes.documents._cascade_delete_weaviate",
            new_callable=AsyncMock,
            return_value=0,
        ):
            result = await delete_document(
                document_id=doc_id,
                response=Response(),
                user=user,
                db=db,
            )

        assert result is None
        assert db.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_404_for_missing_document(self) -> None:
        from fastapi import HTTPException, Response

        user = _make_user()
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        from pwbs.api.v1.routes.documents import delete_document

        with pytest.raises(HTTPException) as exc_info:
            await delete_document(
                document_id=uuid.uuid4(),
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_for_other_users_document(self) -> None:
        from fastapi import HTTPException, Response

        doc_id = uuid.uuid4()
        user = _make_user(user_id=OTHER_USER_ID)
        doc = _make_document_orm(doc_id=doc_id, user_id=USER_ID)

        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = doc
        db.execute.return_value = result

        from pwbs.api.v1.routes.documents import delete_document

        with pytest.raises(HTTPException) as exc_info:
            await delete_document(
                document_id=doc_id,
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test: Schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_document_list_item(self) -> None:
        item = DocumentListItem(
            id=uuid.uuid4(),
            title="Test",
            source_type="notion",
            source_id="pg-1",
            chunk_count=5,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert item.chunk_count == 5

    def test_document_list_item_no_title(self) -> None:
        item = DocumentListItem(
            id=uuid.uuid4(),
            source_type="obsidian",
            source_id="file.md",
            chunk_count=1,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert item.title is None

    def test_chunk_entity_response(self) -> None:
        ent = ChunkEntityResponse(
            entity_id=uuid.uuid4(),
            name="Project Alpha",
            entity_type="project",
            confidence=0.88,
        )
        assert ent.entity_type == "project"

    def test_chunk_detail_response_defaults(self) -> None:
        c = ChunkDetailResponse(id=uuid.uuid4(), index=0)
        assert c.content_preview is None
        assert c.entities == []


# ---------------------------------------------------------------------------
# Test: Router metadata
# ---------------------------------------------------------------------------


class TestRouterMetadata:
    def test_prefix(self) -> None:
        assert router.prefix == "/api/v1/documents"

    def test_tags(self) -> None:
        assert "documents" in router.tags

    def test_route_paths(self) -> None:
        paths = [r.path for r in router.routes]
        assert "/api/v1/documents/" in paths
        assert "/api/v1/documents/{document_id}" in paths
