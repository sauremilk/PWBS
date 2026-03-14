"""Tests for pwbs.storage.weaviate – WeaviateChunkStore (TASK-059).

All tests mock the Weaviate client to avoid requiring a running instance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from pwbs.storage.weaviate import (
    COLLECTION_NAME,
    ChunkUpsertRequest,
    ChunkUpsertResult,
    WeaviateChunkStore,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=timezone.utc)
_USER_ID = uuid.uuid4()
_DOC_ID = uuid.uuid4()


def _make_request(
    chunk_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    chunk_index: int = 0,
) -> ChunkUpsertRequest:
    return ChunkUpsertRequest(
        chunk_id=chunk_id or uuid.uuid4(),
        user_id=user_id or _USER_ID,
        document_id=_DOC_ID,
        embedding=[0.1] * 1536,
        content="test content",
        title="Test Document",
        source_type="notion",
        language="de",
        created_at=_NOW,
        chunk_index=chunk_index,
    )


def _mock_client() -> MagicMock:
    """Build a mock Weaviate client with collection/tenant chain."""
    client = MagicMock()

    # collections.exists
    client.collections.exists.return_value = True

    # collection chain: client.collections.get(name)
    collection = MagicMock()
    client.collections.get.return_value = collection

    # tenant chain: collection.with_tenant(str)
    tenant_col = MagicMock()
    collection.with_tenant.return_value = tenant_col

    # batch context manager
    batch_ctx = MagicMock()
    tenant_col.batch.dynamic.return_value.__enter__ = MagicMock(return_value=batch_ctx)
    tenant_col.batch.dynamic.return_value.__exit__ = MagicMock(return_value=False)
    tenant_col.batch.failed_objects = []

    # tenants
    collection.tenants.get.return_value = {}

    return client


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------


class TestEnsureCollection:
    def test_skips_if_exists(self) -> None:
        client = _mock_client()
        client.collections.exists.return_value = True
        store = WeaviateChunkStore(client)
        store.ensure_collection()
        client.collections.create.assert_not_called()

    def test_creates_if_not_exists(self) -> None:
        client = _mock_client()
        client.collections.exists.return_value = False
        store = WeaviateChunkStore(client)
        store.ensure_collection()
        client.collections.create.assert_called_once()
        call_kwargs = client.collections.create.call_args.kwargs
        assert call_kwargs["name"] == COLLECTION_NAME


class TestEnsureTenant:
    def test_creates_new_tenant(self) -> None:
        client = _mock_client()
        collection = client.collections.get.return_value
        collection.tenants.get.return_value = {}

        store = WeaviateChunkStore(client)
        store.ensure_tenant(_USER_ID)

        collection.tenants.create.assert_called_once()

    def test_skips_existing_active_tenant(self) -> None:
        client = _mock_client()
        collection = client.collections.get.return_value
        from weaviate.classes.tenants import TenantActivityStatus

        existing_tenant = MagicMock()
        existing_tenant.activity_status = TenantActivityStatus.ACTIVE
        collection.tenants.get.return_value = {str(_USER_ID): existing_tenant}

        store = WeaviateChunkStore(client)
        store.ensure_tenant(_USER_ID)

        collection.tenants.create.assert_not_called()


# ---------------------------------------------------------------------------
# AC: Upsert idempotent
# ---------------------------------------------------------------------------


class TestUpsertChunks:
    def test_empty_input_returns_empty(self) -> None:
        client = _mock_client()
        store = WeaviateChunkStore(client)
        results = store.upsert_chunks([])
        assert results == []

    def test_single_chunk_upsert(self) -> None:
        client = _mock_client()
        store = WeaviateChunkStore(client)
        req = _make_request()
        results = store.upsert_chunks([req])

        assert len(results) == 1
        assert isinstance(results[0], ChunkUpsertResult)
        assert results[0].chunk_id == req.chunk_id
        assert results[0].success is True

    def test_multiple_chunks_same_user(self) -> None:
        client = _mock_client()
        store = WeaviateChunkStore(client)
        reqs = [_make_request(chunk_index=i) for i in range(5)]
        results = store.upsert_chunks(reqs)

        assert len(results) == 5
        assert all(r.success for r in results)

    def test_multiple_users_creates_tenants(self) -> None:
        client = _mock_client()
        user1 = uuid.uuid4()
        user2 = uuid.uuid4()
        store = WeaviateChunkStore(client)

        reqs = [
            _make_request(user_id=user1),
            _make_request(user_id=user2),
        ]
        results = store.upsert_chunks(reqs)

        assert len(results) == 2

    def test_deterministic_uuid(self) -> None:
        """Same chunk_id always produces the same weaviate_id."""
        chunk_id = uuid.uuid4()
        id1 = WeaviateChunkStore._deterministic_uuid(chunk_id)
        id2 = WeaviateChunkStore._deterministic_uuid(chunk_id)
        assert id1 == id2

    def test_different_chunks_different_uuids(self) -> None:
        id1 = WeaviateChunkStore._deterministic_uuid(uuid.uuid4())
        id2 = WeaviateChunkStore._deterministic_uuid(uuid.uuid4())
        assert id1 != id2

    def test_weaviate_id_returned(self) -> None:
        client = _mock_client()
        store = WeaviateChunkStore(client)
        req = _make_request()
        results = store.upsert_chunks([req])

        expected_weaviate_id = WeaviateChunkStore._deterministic_uuid(req.chunk_id)
        assert results[0].weaviate_id == expected_weaviate_id


# ---------------------------------------------------------------------------
# AC: Properties gesetzt
# ---------------------------------------------------------------------------


class TestProperties:
    def test_batch_add_called_with_properties(self) -> None:
        client = _mock_client()
        collection = client.collections.get.return_value
        tenant_col = collection.with_tenant.return_value
        batch_ctx = MagicMock()
        tenant_col.batch.dynamic.return_value.__enter__ = MagicMock(return_value=batch_ctx)
        tenant_col.batch.dynamic.return_value.__exit__ = MagicMock(return_value=False)
        tenant_col.batch.failed_objects = []

        store = WeaviateChunkStore(client)
        req = _make_request()
        store.upsert_chunks([req])

        batch_ctx.add_object.assert_called_once()
        call_kwargs = batch_ctx.add_object.call_args.kwargs
        props = call_kwargs["properties"]

        assert props["chunkId"] == str(req.chunk_id)
        assert props["documentId"] == str(req.document_id)
        assert props["userId"] == str(req.user_id)
        assert props["sourceType"] == "notion"
        assert props["content"] == "test content"
        assert props["title"] == "Test Document"
        assert props["language"] == "de"
        assert props["chunkIndex"] == 0
        assert "vector" in call_kwargs
        assert "uuid" in call_kwargs


# ---------------------------------------------------------------------------
# DSGVO: Delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_chunks(self) -> None:
        client = _mock_client()
        store = WeaviateChunkStore(client)
        chunk_ids = [uuid.uuid4(), uuid.uuid4()]

        store.delete_chunks(_USER_ID, chunk_ids)

        collection = client.collections.get.return_value
        tenant_col = collection.with_tenant.return_value
        assert tenant_col.data.delete_by_id.call_count == 2

    def test_delete_empty_list(self) -> None:
        client = _mock_client()
        store = WeaviateChunkStore(client)
        store.delete_chunks(_USER_ID, [])
        # Should not call any delete operations
        client.collections.get.assert_not_called()

    def test_delete_user_data(self) -> None:
        client = _mock_client()
        store = WeaviateChunkStore(client)
        store.delete_user_data(_USER_ID)

        collection = client.collections.get.return_value
        collection.tenants.remove.assert_called_once()
