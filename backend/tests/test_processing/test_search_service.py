"""Tests for pwbs.search.service – SemanticSearchService (TASK-072)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.search.service import (
    SearchConfig,
    SemanticSearchResult,
    SemanticSearchService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_ID = uuid.uuid4()
_CHUNK_ID = uuid.uuid4()


def _mock_embedding_service() -> AsyncMock:
    svc = AsyncMock()
    svc.embed_text = AsyncMock(return_value=[0.1] * 1536)
    return svc


def _make_weaviate_object(
    chunk_id: uuid.UUID | None = None,
    content: str = "test",
    title: str = "Title",
    source_type: str = "notion",
    created_at: str = "2026-01-01T00:00:00Z",
    chunk_index: int = 0,
    certainty: float = 0.95,
) -> MagicMock:
    obj = MagicMock()
    obj.properties = {
        "chunkId": str(chunk_id or _CHUNK_ID),
        "content": content,
        "title": title,
        "sourceType": source_type,
        "createdAt": created_at,
        "chunkIndex": chunk_index,
    }
    obj.metadata = MagicMock()
    obj.metadata.certainty = certainty
    return obj


def _mock_weaviate_client(objects: list[MagicMock] | None = None) -> MagicMock:
    client = MagicMock()
    collection = MagicMock()
    client.collections.get.return_value = collection
    tenant_col = MagicMock()
    collection.with_tenant.return_value = tenant_col

    response = MagicMock()
    response.objects = objects or []
    tenant_col.query.near_vector.return_value = response

    return client


def _make_service(
    weaviate_objects: list[MagicMock] | None = None,
    config: SearchConfig | None = None,
) -> SemanticSearchService:
    return SemanticSearchService(
        weaviate_client=_mock_weaviate_client(weaviate_objects),
        embedding_service=_mock_embedding_service(),
        config=config,
    )


# ---------------------------------------------------------------------------
# AC: Query → Embedding → Weaviate nearVector
# ---------------------------------------------------------------------------


class TestSearch:
    @pytest.mark.asyncio
    async def test_returns_results(self) -> None:
        objs = [_make_weaviate_object()]
        svc = _make_service(weaviate_objects=objs)

        results = await svc.search("test query", _USER_ID)

        assert len(results) == 1
        assert isinstance(results[0], SemanticSearchResult)

    @pytest.mark.asyncio
    async def test_result_fields(self) -> None:
        cid = uuid.uuid4()
        objs = [
            _make_weaviate_object(
                chunk_id=cid,
                content="hello",
                title="Doc Title",
                source_type="notion",
                created_at="2026-01-15T10:00:00Z",
                certainty=0.88,
                chunk_index=3,
            )
        ]
        svc = _make_service(weaviate_objects=objs)

        results = await svc.search("test", _USER_ID)
        r = results[0]
        assert r.chunk_id == cid
        assert r.content == "hello"
        assert r.title == "Doc Title"
        assert r.source_type == "notion"
        assert r.score == pytest.approx(0.88)
        assert r.chunk_index == 3

    @pytest.mark.asyncio
    async def test_multiple_results(self) -> None:
        objs = [_make_weaviate_object(chunk_id=uuid.uuid4()) for _ in range(5)]
        svc = _make_service(weaviate_objects=objs)

        results = await svc.search("query", _USER_ID)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_embed_text_called(self) -> None:
        embed_svc = _mock_embedding_service()
        weaviate_client = _mock_weaviate_client([])
        svc = SemanticSearchService(weaviate_client, embed_svc)

        await svc.search("hello world", _USER_ID)

        embed_svc.embed_text.assert_called_once_with("hello world")


# ---------------------------------------------------------------------------
# AC: Isoliert auf Nutzer-Tenant
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_uses_user_tenant(self) -> None:
        weaviate_client = _mock_weaviate_client([])
        svc = SemanticSearchService(weaviate_client, _mock_embedding_service())

        await svc.search("test", _USER_ID)

        collection = weaviate_client.collections.get.return_value
        collection.with_tenant.assert_called_once_with(str(_USER_ID))


# ---------------------------------------------------------------------------
# AC: top_k konfigurierbar (Default: 10, Max: 50)
# ---------------------------------------------------------------------------


class TestTopK:
    @pytest.mark.asyncio
    async def test_default_top_k(self) -> None:
        weaviate_client = _mock_weaviate_client([])
        svc = SemanticSearchService(weaviate_client, _mock_embedding_service())

        await svc.search("test", _USER_ID)

        collection = weaviate_client.collections.get.return_value
        tenant_col = collection.with_tenant.return_value
        call_kwargs = tenant_col.query.near_vector.call_args.kwargs
        assert call_kwargs["limit"] == 10

    @pytest.mark.asyncio
    async def test_custom_top_k(self) -> None:
        weaviate_client = _mock_weaviate_client([])
        svc = SemanticSearchService(weaviate_client, _mock_embedding_service())

        await svc.search("test", _USER_ID, top_k=25)

        collection = weaviate_client.collections.get.return_value
        tenant_col = collection.with_tenant.return_value
        call_kwargs = tenant_col.query.near_vector.call_args.kwargs
        assert call_kwargs["limit"] == 25

    @pytest.mark.asyncio
    async def test_top_k_capped_at_max(self) -> None:
        weaviate_client = _mock_weaviate_client([])
        svc = SemanticSearchService(weaviate_client, _mock_embedding_service())

        await svc.search("test", _USER_ID, top_k=100)

        collection = weaviate_client.collections.get.return_value
        tenant_col = collection.with_tenant.return_value
        call_kwargs = tenant_col.query.near_vector.call_args.kwargs
        assert call_kwargs["limit"] == 50


# ---------------------------------------------------------------------------
# AC: Leerer Query gibt leere Liste zurück
# ---------------------------------------------------------------------------


class TestEmptyQuery:
    @pytest.mark.asyncio
    async def test_empty_string(self) -> None:
        svc = _make_service()
        results = await svc.search("", _USER_ID)
        assert results == []

    @pytest.mark.asyncio
    async def test_whitespace_only(self) -> None:
        svc = _make_service()
        results = await svc.search("   ", _USER_ID)
        assert results == []

    @pytest.mark.asyncio
    async def test_no_results(self) -> None:
        svc = _make_service(weaviate_objects=[])
        results = await svc.search("something", _USER_ID)
        assert results == []


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_default_config(self) -> None:
        svc = _make_service()
        assert svc.config.default_top_k == 10
        assert svc.config.max_top_k == 50
        assert svc.config.default_alpha == 0.75
