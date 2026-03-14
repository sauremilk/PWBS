"""Tests for Search API endpoint (TASK-088)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.api.v1.routes.search import (
    _apply_filters,
    _build_hybrid_service,
    _build_semantic_service,
    _to_search_result,
    router,
)
from pwbs.models.user import User
from pwbs.schemas.briefing import SourceRef
from pwbs.schemas.enums import SourceType
from pwbs.schemas.search import SearchFilters, SearchRequest, SearchResponse
from pwbs.search.enrichment import EnrichedSearchResult
from pwbs.search.hybrid import HybridSearchResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(user_id: uuid.UUID | None = None) -> User:
    """Create a fake User ORM object."""
    u = MagicMock(spec=User)
    u.id = user_id or uuid.uuid4()
    u.email = "test@example.com"
    u.display_name = "Test User"
    u.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return u


def _make_hybrid_result(
    chunk_id: uuid.UUID | None = None,
    content: str = "Test content",
    title: str = "Test doc",
    source_type: str = "notion",
    score: float = 0.85,
) -> HybridSearchResult:
    return HybridSearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        content=content,
        title=title,
        source_type=source_type,
        score=score,
        semantic_score=0.9,
        keyword_score=0.7,
        semantic_rank=1,
        keyword_rank=2,
    )


def _make_enriched_result(
    chunk_id: uuid.UUID | None = None,
    content: str = "Test content",
    score: float = 0.85,
    source_type: SourceType = SourceType.NOTION,
    doc_title: str = "Test doc",
    date: datetime | None = None,
) -> EnrichedSearchResult:
    cid = chunk_id or uuid.uuid4()
    return EnrichedSearchResult(
        chunk_id=cid,
        content=content,
        score=score,
        source_ref=SourceRef(
            chunk_id=cid,
            doc_title=doc_title,
            source_type=source_type,
            date=date or datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
            relevance=min(score, 1.0),
        ),
        original_url="https://notion.so/abc123",
        semantic_rank=1,
        keyword_rank=2,
    )


# ---------------------------------------------------------------------------
# _apply_filters
# ---------------------------------------------------------------------------


class TestApplyFilters:
    def test_no_filters_returns_all(self) -> None:
        results = [_make_enriched_result() for _ in range(3)]
        assert _apply_filters(results, None) == results

    def test_filter_by_source_type(self) -> None:
        r1 = _make_enriched_result(source_type=SourceType.NOTION)
        r2 = _make_enriched_result(source_type=SourceType.GOOGLE_CALENDAR)
        r3 = _make_enriched_result(source_type=SourceType.ZOOM)

        filters = SearchFilters(source_types=[SourceType.NOTION, SourceType.ZOOM])
        filtered = _apply_filters([r1, r2, r3], filters)
        assert len(filtered) == 2
        types = {r.source_ref.source_type for r in filtered}
        assert SourceType.NOTION in types
        assert SourceType.ZOOM in types
        assert SourceType.GOOGLE_CALENDAR not in types

    def test_filter_by_date_from(self) -> None:
        old = _make_enriched_result(date=datetime(2025, 1, 1, tzinfo=timezone.utc))
        new = _make_enriched_result(date=datetime(2026, 6, 1, tzinfo=timezone.utc))

        filters = SearchFilters(date_from=datetime(2026, 1, 1, tzinfo=timezone.utc))
        filtered = _apply_filters([old, new], filters)
        assert len(filtered) == 1
        assert filtered[0].source_ref.date.year == 2026

    def test_filter_by_date_to(self) -> None:
        old = _make_enriched_result(date=datetime(2025, 1, 1, tzinfo=timezone.utc))
        new = _make_enriched_result(date=datetime(2026, 6, 1, tzinfo=timezone.utc))

        filters = SearchFilters(date_to=datetime(2025, 6, 1, tzinfo=timezone.utc))
        filtered = _apply_filters([old, new], filters)
        assert len(filtered) == 1
        assert filtered[0].source_ref.date.year == 2025

    def test_combined_filters(self) -> None:
        r1 = _make_enriched_result(
            source_type=SourceType.NOTION,
            date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        r2 = _make_enriched_result(
            source_type=SourceType.GOOGLE_CALENDAR,
            date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        r3 = _make_enriched_result(
            source_type=SourceType.NOTION,
            date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )

        filters = SearchFilters(
            source_types=[SourceType.NOTION],
            date_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        filtered = _apply_filters([r1, r2, r3], filters)
        assert len(filtered) == 1
        assert filtered[0] is r1

    def test_empty_results_with_filters(self) -> None:
        filters = SearchFilters(source_types=[SourceType.NOTION])
        assert _apply_filters([], filters) == []


# ---------------------------------------------------------------------------
# _to_search_result
# ---------------------------------------------------------------------------


class TestToSearchResult:
    def test_maps_enriched_to_search_result(self) -> None:
        enriched = _make_enriched_result(
            content="Hello world",
            doc_title="My doc",
            source_type=SourceType.ZOOM,
            score=0.75,
        )
        result = _to_search_result(enriched)
        assert result.chunk_id == enriched.chunk_id
        assert result.doc_title == "My doc"
        assert result.source_type == SourceType.ZOOM
        assert result.content == "Hello world"
        assert result.score == 0.75
        assert result.entities == []


# ---------------------------------------------------------------------------
# _build_semantic_service
# ---------------------------------------------------------------------------


class TestBuildSemanticService:
    def test_creates_service(self) -> None:
        with (
            patch("pwbs.api.v1.routes.search.get_settings") as mock_settings,
            patch("pwbs.api.v1.routes.search.get_weaviate_client") as mock_wc,
            patch("pwbs.api.v1.routes.search.EmbeddingService") as mock_emb,
        ):
            s = MagicMock()
            s.openai_api_key.get_secret_value.return_value = "test-key"
            mock_settings.return_value = s
            mock_wc.return_value = MagicMock()
            mock_emb.return_value = MagicMock()

            svc = _build_semantic_service()
            assert svc is not None
            mock_emb.assert_called_once_with(api_key="test-key")


# ---------------------------------------------------------------------------
# _build_hybrid_service
# ---------------------------------------------------------------------------


class TestBuildHybridService:
    def test_creates_hybrid_service(self) -> None:
        with (
            patch("pwbs.api.v1.routes.search.get_settings") as mock_settings,
            patch("pwbs.api.v1.routes.search.get_weaviate_client") as mock_wc,
            patch("pwbs.api.v1.routes.search.EmbeddingService") as mock_emb,
        ):
            s = MagicMock()
            s.openai_api_key.get_secret_value.return_value = "test-key"
            mock_settings.return_value = s
            mock_wc.return_value = MagicMock()
            mock_emb.return_value = MagicMock()

            session = AsyncMock()
            svc = _build_hybrid_service(session)
            assert svc is not None


# ---------------------------------------------------------------------------
# POST /search/
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    @pytest.mark.asyncio
    async def test_successful_search(self) -> None:
        from pwbs.api.v1.routes.search import search

        user = _make_user()
        session = AsyncMock()
        chunk_id = uuid.uuid4()

        hybrid_results = [
            _make_hybrid_result(chunk_id=chunk_id, content="Found it", title="Doc 1"),
        ]
        enriched_results = [
            _make_enriched_result(
                chunk_id=chunk_id,
                content="Found it",
                doc_title="Doc 1",
            ),
        ]

        with (
            patch("pwbs.api.v1.routes.search._build_hybrid_service") as mock_build,
            patch("pwbs.api.v1.routes.search.SearchResultEnricher") as mock_enricher_cls,
        ):
            mock_hybrid = AsyncMock()
            mock_hybrid.search.return_value = hybrid_results
            mock_build.return_value = mock_hybrid

            mock_enricher = AsyncMock()
            mock_enricher.enrich.return_value = enriched_results
            mock_enricher_cls.return_value = mock_enricher

            body = SearchRequest(query="test query", limit=10)
            response = MagicMock()
            result = await search(body=body, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), response=response, user=user, session=session)

        assert isinstance(result, SearchResponse)
        assert len(result.results) == 1
        assert result.results[0].chunk_id == chunk_id
        assert result.results[0].doc_title == "Doc 1"
        assert result.results[0].content == "Found it"
        assert result.answer is None
        assert len(result.sources) == 1

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        from pwbs.api.v1.routes.search import search

        user = _make_user()
        session = AsyncMock()

        with (
            patch("pwbs.api.v1.routes.search._build_hybrid_service") as mock_build,
            patch("pwbs.api.v1.routes.search.SearchResultEnricher") as mock_enricher_cls,
        ):
            mock_hybrid = AsyncMock()
            mock_hybrid.search.return_value = []
            mock_build.return_value = mock_hybrid

            mock_enricher = AsyncMock()
            mock_enricher.enrich.return_value = []
            mock_enricher_cls.return_value = mock_enricher

            body = SearchRequest(query="nothing", limit=10)
            response = MagicMock()
            result = await search(body=body, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), response=response, user=user, session=session)

        assert isinstance(result, SearchResponse)
        assert len(result.results) == 0
        assert result.sources == []

    @pytest.mark.asyncio
    async def test_passes_user_id_to_services(self) -> None:
        from pwbs.api.v1.routes.search import search

        user_id = uuid.uuid4()
        user = _make_user(user_id=user_id)
        session = AsyncMock()

        with (
            patch("pwbs.api.v1.routes.search._build_hybrid_service") as mock_build,
            patch("pwbs.api.v1.routes.search.SearchResultEnricher") as mock_enricher_cls,
        ):
            mock_hybrid = AsyncMock()
            mock_hybrid.search.return_value = []
            mock_build.return_value = mock_hybrid

            mock_enricher = AsyncMock()
            mock_enricher.enrich.return_value = []
            mock_enricher_cls.return_value = mock_enricher

            body = SearchRequest(query="test", limit=5)
            response = MagicMock()
            await search(body=body, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), response=response, user=user, session=session)

        mock_hybrid.search.assert_called_once_with(
            query="test",
            user_id=user_id,
            top_k=5,
        )
        mock_enricher.enrich.assert_called_once()
        _, kwargs = mock_enricher.enrich.call_args
        assert kwargs["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_applies_filters(self) -> None:
        from pwbs.api.v1.routes.search import search

        user = _make_user()
        session = AsyncMock()

        notion_enriched = _make_enriched_result(source_type=SourceType.NOTION)
        gcal_enriched = _make_enriched_result(source_type=SourceType.GOOGLE_CALENDAR)

        with (
            patch("pwbs.api.v1.routes.search._build_hybrid_service") as mock_build,
            patch("pwbs.api.v1.routes.search.SearchResultEnricher") as mock_enricher_cls,
        ):
            mock_hybrid = AsyncMock()
            mock_hybrid.search.return_value = [
                _make_hybrid_result(),
                _make_hybrid_result(),
            ]
            mock_build.return_value = mock_hybrid

            mock_enricher = AsyncMock()
            mock_enricher.enrich.return_value = [notion_enriched, gcal_enriched]
            mock_enricher_cls.return_value = mock_enricher

            body = SearchRequest(
                query="test",
                filters=SearchFilters(source_types=[SourceType.NOTION]),
            )
            response = MagicMock()
            result = await search(body=body, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), response=response, user=user, session=session)

        assert len(result.results) == 1
        assert result.results[0].source_type == SourceType.NOTION

    @pytest.mark.asyncio
    async def test_respects_limit(self) -> None:
        from pwbs.api.v1.routes.search import search

        user = _make_user()
        session = AsyncMock()

        with (
            patch("pwbs.api.v1.routes.search._build_hybrid_service") as mock_build,
            patch("pwbs.api.v1.routes.search.SearchResultEnricher") as mock_enricher_cls,
        ):
            mock_hybrid = AsyncMock()
            mock_hybrid.search.return_value = []
            mock_build.return_value = mock_hybrid

            mock_enricher = AsyncMock()
            mock_enricher.enrich.return_value = []
            mock_enricher_cls.return_value = mock_enricher

            body = SearchRequest(query="test", limit=25)
            response = MagicMock()
            await search(body=body, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), response=response, user=user, session=session)

        mock_hybrid.search.assert_called_once_with(
            query="test",
            user_id=user.id,
            top_k=25,
        )

    @pytest.mark.asyncio
    async def test_sources_included_in_response(self) -> None:
        from pwbs.api.v1.routes.search import search

        user = _make_user()
        session = AsyncMock()
        cid = uuid.uuid4()

        enriched = _make_enriched_result(chunk_id=cid, doc_title="Source Doc")

        with (
            patch("pwbs.api.v1.routes.search._build_hybrid_service") as mock_build,
            patch("pwbs.api.v1.routes.search.SearchResultEnricher") as mock_enricher_cls,
        ):
            mock_hybrid = AsyncMock()
            mock_hybrid.search.return_value = [_make_hybrid_result(chunk_id=cid)]
            mock_build.return_value = mock_hybrid

            mock_enricher = AsyncMock()
            mock_enricher.enrich.return_value = [enriched]
            mock_enricher_cls.return_value = mock_enricher

            body = SearchRequest(query="test")
            response = MagicMock()
            result = await search(body=body, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), response=response, user=user, session=session)

        assert len(result.sources) == 1
        assert result.sources[0].chunk_id == cid
        assert result.sources[0].doc_title == "Source Doc"


# ---------------------------------------------------------------------------
# SearchRequest validation
# ---------------------------------------------------------------------------


class TestSearchRequestValidation:
    def test_empty_query_rejected(self) -> None:
        """Pydantic min_length=1 rejects empty queries."""
        with pytest.raises(Exception):
            SearchRequest(query="", limit=10)

    def test_limit_max_50(self) -> None:
        """Pydantic le=50 rejects limit > 50."""
        with pytest.raises(Exception):
            SearchRequest(query="test", limit=100)

    def test_limit_min_1(self) -> None:
        """Pydantic ge=1 rejects limit < 1."""
        with pytest.raises(Exception):
            SearchRequest(query="test", limit=0)

    def test_valid_request(self) -> None:
        req = SearchRequest(query="hello", limit=10)
        assert req.query == "hello"
        assert req.limit == 10
        assert req.filters is None

    def test_valid_request_with_filters(self) -> None:
        req = SearchRequest(
            query="hello",
            filters=SearchFilters(source_types=[SourceType.NOTION]),
        )
        assert req.filters is not None
        assert req.filters.source_types == [SourceType.NOTION]


# ---------------------------------------------------------------------------
# Router metadata
# ---------------------------------------------------------------------------


class TestRouterMetadata:
    def test_router_prefix(self) -> None:
        assert router.prefix == "/api/v1/search"

    def test_router_has_search_route(self) -> None:
        paths = [r.path for r in router.routes]
        assert "/api/v1/search/" in paths
