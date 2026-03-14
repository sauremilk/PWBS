"""Search API endpoint (TASK-088).

POST  /api/v1/search/   -- Hybrid search with optional RAG answer
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.audit.audit_service import AuditAction, get_client_ip, log_event
from pwbs.core.config import get_settings
from pwbs.db.postgres import get_db_session
from pwbs.db.weaviate_client import get_weaviate_client
from pwbs.models.user import User
from pwbs.processing.embedding import EmbeddingService
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.schemas.search import SearchFilters, SearchRequest, SearchResponse, SearchResult
from pwbs.search.enrichment import EnrichedSearchResult, SearchResultEnricher
from pwbs.search.hybrid import HybridSearchService
from pwbs.search.keyword import KeywordSearchService
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


def _build_semantic_service() -> SemanticSearchService:
    """Create a SemanticSearchService from current singletons."""
    settings = get_settings()
    weaviate_client = get_weaviate_client()
    embedding_service = EmbeddingService(
        api_key=settings.openai_api_key.get_secret_value(),
    )
    return SemanticSearchService(
        weaviate_client=weaviate_client,
        embedding_service=embedding_service,
    )


def _build_hybrid_service(
    session: AsyncSession,
) -> HybridSearchService:
    """Create a HybridSearchService wiring semantic + keyword backends."""
    semantic = _build_semantic_service()
    keyword = KeywordSearchService(session=session)
    return HybridSearchService(
        semantic_service=semantic,
        keyword_service=keyword,
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
    hybrid = _build_hybrid_service(session)
    enricher = SearchResultEnricher(session=session)

    # Execute hybrid search — candidate_k is handled internally
    hybrid_results = await hybrid.search(
        query=body.query,
        user_id=user_id,
        top_k=body.limit,
    )

    # Enrich with SourceRef and original URL
    enriched = await enricher.enrich(results=hybrid_results, user_id=user_id)

    # Apply optional filters (post-filtering)
    enriched = _apply_filters(enriched, body.filters)

    # Map to API schema
    results = [_to_search_result(e) for e in enriched]
    sources = [e.source_ref for e in enriched]

    await log_event(
        session,
        action=AuditAction.SEARCH_EXECUTED,
        user_id=user_id,
        ip_address=get_client_ip(request),
        metadata={"result_count": len(results)},
    )
    await session.commit()

    return SearchResponse(
        results=results,
        answer=None,
        sources=sources,
        confidence=None,
    )
