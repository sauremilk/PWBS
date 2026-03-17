"""Search API endpoints (TASK-088, TASK-182).

POST  /api/v1/search/           -- Hybrid search with optional RAG answer
GET   /api/v1/search/autocomplete  -- Entity-based auto-complete
POST  /api/v1/search/saved      -- Save a named search
GET   /api/v1/search/saved      -- List saved searches
DELETE /api/v1/search/saved/{id} -- Delete a saved search
GET   /api/v1/search/history    -- Last 50 search queries
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.audit.audit_service import AuditAction, get_client_ip, log_event
from pwbs.core.config import get_settings
from pwbs.core.posthog import capture as posthog_capture
from pwbs.db.postgres import get_db_session
from pwbs.db.weaviate_client import get_weaviate_client
from pwbs.models.entity import Entity
from pwbs.models.saved_search import SavedSearch
from pwbs.models.search_history import SearchHistory
from pwbs.models.user import User
from pwbs.processing.embedding import EmbeddingService
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.schemas.search import (
    AutoCompleteItem,
    AutoCompleteResponse,
    SavedSearchCreate,
    SavedSearchOut,
    SearchFilters,
    SearchHistoryItem,
    SearchHistoryResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from pwbs.search.enrichment import EnrichedSearchResult, SearchResultEnricher
from pwbs.search.hybrid import HybridSearchConfig, HybridSearchService
from pwbs.search.keyword import KeywordSearchService
from pwbs.search.reranker import RerankerConfig, SearchReranker
from pwbs.search.service import SemanticSearchService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/search",
    tags=["search"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ---------------------------------------------------------------------------
# Helpers: build service chain from request-scoped deps
# ---------------------------------------------------------------------------


def _build_semantic_service() -> SemanticSearchService | None:
    """Create a SemanticSearchService from current singletons.

    Returns ``None`` when Weaviate is unavailable.
    """
    weaviate_client = get_weaviate_client()
    if weaviate_client is None:
        return None
    settings = get_settings()
    embedding_service = EmbeddingService(
        api_key=settings.openai_api_key.get_secret_value(),
    )
    return SemanticSearchService(
        weaviate_client=weaviate_client,
        embedding_service=embedding_service,
    )


def _build_hybrid_service(
    session: AsyncSession,
) -> HybridSearchService | None:
    """Create a HybridSearchService wiring semantic + keyword backends.

    Returns ``None`` when Weaviate is unavailable (semantic search
    is a required component of hybrid search).

    Reads ``SEARCH_SEMANTIC_WEIGHT`` and ``SEARCH_KEYWORD_WEIGHT`` from
    environment configuration (TASK-201).
    """
    semantic = _build_semantic_service()
    if semantic is None:
        return None
    settings = get_settings()
    config = HybridSearchConfig(
        semantic_weight=settings.search_semantic_weight,
        keyword_weight=settings.search_keyword_weight,
    )
    keyword = KeywordSearchService(session=session)
    return HybridSearchService(
        semantic_service=semantic,
        keyword_service=keyword,
        config=config,
    )


def _apply_filters(
    results: list[EnrichedSearchResult],
    filters: SearchFilters | None,
) -> list[EnrichedSearchResult]:
    """Post-filter enriched results by source_type, date range."""
    if filters is None:
        return results

    filtered = results

    if filters.source_types:
        allowed = {st.value for st in filters.source_types}
        filtered = [r for r in filtered if r.source_ref.source_type.value in allowed]

    if filters.date_from:
        filtered = [r for r in filtered if r.source_ref.date >= filters.date_from]

    if filters.date_to:
        filtered = [r for r in filtered if r.source_ref.date <= filters.date_to]

    return filtered


def _to_search_result(enriched: EnrichedSearchResult) -> SearchResult:
    """Map an enriched result to the API response schema."""
    return SearchResult(
        chunk_id=enriched.chunk_id,
        doc_title=enriched.source_ref.doc_title,
        source_type=enriched.source_ref.source_type,
        date=enriched.source_ref.date,
        content=enriched.content,
        score=enriched.source_ref.relevance,
        entities=[],
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid-Suche über alle Nutzerdaten",
    responses={
        400: {"description": "Leere Query"},
        401: {"description": "Kein gültiges JWT"},
        422: {"description": "Ungültige Filter"},
    },
)
async def search(
    body: SearchRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    """Execute a hybrid search (semantic + keyword) with RRF fusion.

    The ``owner_id`` is extracted from the JWT and used as mandatory
    tenant filter — no cross-user results are possible.
    """
    user_id: uuid.UUID = user.id

    # Build the service chain (request-scoped)
    settings = get_settings()
    hybrid = _build_hybrid_service(session)

    # When Weaviate is unavailable, return empty results instead of crashing
    if hybrid is None:
        logger.warning("Search unavailable – Weaviate not connected")
        return SearchResponse(results=[], answer=None, sources=[], confidence=None)

    reranker = SearchReranker(
        config=RerankerConfig(
            recency_boost_pct=settings.search_recency_boost_pct,
            recency_boost_days=settings.search_recency_boost_days,
        ),
    )
    enricher = SearchResultEnricher(session=session)

    # Step 1: Over-fetch candidates for reranking (TASK-201)
    rerank_candidates = min(50, max(body.limit, 10))
    hybrid_results = await hybrid.search(
        query=body.query,
        user_id=user_id,
        top_k=rerank_candidates,
    )

    # Step 2: Rerank and cut to requested limit
    reranked = reranker.rerank(hybrid_results, top_k=body.limit)

    # Enrich with SourceRef and original URL
    enriched = await enricher.enrich(results=reranked, user_id=user_id)

    # Apply optional filters (post-filtering)
    enriched = _apply_filters(enriched, body.filters)

    # Map to API schema
    results = [_to_search_result(e) for e in enriched]
    sources = [e.source_ref for e in enriched]

    # Record search in history (fire-and-forget, don't block response)
    history_entry = SearchHistory(
        user_id=user_id,
        query=body.query,
        result_count=len(results),
    )
    session.add(history_entry)

    await log_event(
        session,
        action=AuditAction.SEARCH_EXECUTED,
        user_id=user_id,
        ip_address=get_client_ip(request),
        metadata={"result_count": len(results)},
    )
    await session.commit()

    posthog_capture(
        str(user_id),
        "search_executed",
        {"result_count": len(results)},
    )

    return SearchResponse(
        results=results,
        answer=None,
        sources=sources,
        confidence=None,
    )


# ---------------------------------------------------------------------------
# Auto-Complete (TASK-182)
# ---------------------------------------------------------------------------


@router.get(
    "/autocomplete",
    response_model=AutoCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Entity-basierte Auto-Vervollständigung",
)
async def autocomplete(
    q: str = Query(min_length=2, description="Suchbegriff (mind. 2 Zeichen)"),
    limit: int = Query(default=10, ge=1, le=30),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AutoCompleteResponse:
    """Return entity names matching the prefix, filtered by owner_id."""
    user_id: uuid.UUID = user.id
    prefix = q.lower()

    stmt = (
        select(Entity)
        .where(
            Entity.user_id == user_id,
            Entity.normalized_name.startswith(prefix),
        )
        .order_by(Entity.mention_count.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    entities = result.scalars().all()

    suggestions = [
        AutoCompleteItem(
            entity_id=e.id,
            name=e.name,
            entity_type=e.entity_type,
        )
        for e in entities
    ]
    return AutoCompleteResponse(suggestions=suggestions)


# ---------------------------------------------------------------------------
# Saved Searches (TASK-182)
# ---------------------------------------------------------------------------


@router.post(
    "/saved",
    response_model=SavedSearchOut,
    status_code=status.HTTP_201_CREATED,
    summary="Suche speichern",
)
async def create_saved_search(
    body: SavedSearchCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SavedSearchOut:
    """Persist a named search for the current user."""
    saved = SavedSearch(
        user_id=user.id,
        name=body.name,
        query=body.query,
        filters_json=body.filters.model_dump(exclude_none=True) if body.filters else None,
    )
    session.add(saved)
    await session.commit()
    await session.refresh(saved)

    return SavedSearchOut(
        id=saved.id,
        name=saved.name,
        query=saved.query,
        filters_json=saved.filters_json,
        created_at=saved.created_at,
    )


@router.get(
    "/saved",
    response_model=list[SavedSearchOut],
    status_code=status.HTTP_200_OK,
    summary="Gespeicherte Suchen auflisten",
)
async def list_saved_searches(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SavedSearchOut]:
    """Return all saved searches for the current user."""
    stmt = (
        select(SavedSearch)
        .where(SavedSearch.user_id == user.id)
        .order_by(SavedSearch.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    return [
        SavedSearchOut(
            id=r.id,
            name=r.name,
            query=r.query,
            filters_json=r.filters_json,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete(
    "/saved/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Gespeicherte Suche löschen",
)
async def delete_saved_search(
    search_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a saved search owned by the current user."""
    from fastapi import HTTPException

    stmt = select(SavedSearch).where(
        SavedSearch.id == search_id,
        SavedSearch.user_id == user.id,
    )
    result = await session.execute(stmt)
    saved = result.scalar_one_or_none()
    if saved is None:
        raise HTTPException(status_code=404, detail="Gespeicherte Suche nicht gefunden")

    await session.delete(saved)
    await session.commit()


# ---------------------------------------------------------------------------
# Search History (TASK-182)
# ---------------------------------------------------------------------------


@router.get(
    "/history",
    response_model=SearchHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Suchverlauf der letzten 50 Anfragen",
)
async def get_search_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SearchHistoryResponse:
    """Return the last 50 search queries for the current user."""
    stmt = (
        select(SearchHistory)
        .where(SearchHistory.user_id == user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    items = [
        SearchHistoryItem(
            id=r.id,
            query=r.query,
            result_count=r.result_count,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return SearchHistoryResponse(items=items)
