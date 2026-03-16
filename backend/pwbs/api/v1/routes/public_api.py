"""Public API routes -- API-key-authenticated endpoints (TASK-150).

These endpoints are designed for external tool integrations and use
API-Key authentication (X-API-Key header) instead of JWT.

GET    /api/v1/public/search            -- Search the knowledge base
GET    /api/v1/public/entities          -- List entities
GET    /api/v1/public/entities/{id}     -- Entity detail
GET    /api/v1/public/briefings/latest  -- Latest briefing per type
POST   /api/v1/public/documents/ingest  -- Ingest a document
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.api_key_auth import get_api_key_user
from pwbs.db.postgres import get_db_session
from pwbs.models.briefing import Briefing
from pwbs.models.chunk import Chunk
from pwbs.models.document import Document
from pwbs.models.entity import Entity
from pwbs.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/public",
    tags=["public-api"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PublicSearchResult(BaseModel):
    doc_id: uuid.UUID
    title: str | None
    source_type: str
    content_preview: str
    score: float
    created_at: datetime | None


class PublicSearchResponse(BaseModel):
    results: list[PublicSearchResult]
    total: int
    query: str


class PublicEntityItem(BaseModel):
    id: uuid.UUID
    type: str
    name: str
    mention_count: int


class PublicEntityListResponse(BaseModel):
    entities: list[PublicEntityItem]
    total: int


class PublicEntityDetail(BaseModel):
    id: uuid.UUID
    type: str
    name: str
    mention_count: int
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class PublicBriefingItem(BaseModel):
    id: uuid.UUID
    briefing_type: str
    title: str
    content_preview: str
    created_at: datetime


class PublicBriefingsResponse(BaseModel):
    briefings: list[PublicBriefingItem]


class IngestDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=50_000)
    source_type: str = Field(default="api_upload")
    metadata: dict[str, str] | None = None


class IngestDocumentResponse(BaseModel):
    document_id: uuid.UUID
    title: str
    source_type: str
    status: str


class PublicErrorResponse(BaseModel):
    code: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/search",
    response_model=PublicSearchResponse,
    summary="Search the knowledge base",
    responses={401: {"model": PublicErrorResponse}},
)
async def public_search(
    query: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=10, ge=1, le=50),
    source_type: str | None = Query(default=None),
    current_user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db_session),
) -> PublicSearchResponse:
    """Search documents using keyword matching on titles (public API).

    Uses PostgreSQL ILIKE on document titles filtered by user_id.
    """
    pattern = f"%{query}%"

    stmt = select(Document).where(Document.user_id == current_user.id)

    if source_type is not None:
        stmt = stmt.where(Document.source_type == source_type)

    stmt = stmt.where(Document.title.ilike(pattern))
    stmt = stmt.order_by(Document.created_at.desc()).limit(limit)

    result = await db.execute(stmt)
    docs = list(result.scalars().all())

    # Count total matches
    count_stmt = (
        select(func.count())
        .select_from(Document)
        .where(Document.user_id == current_user.id)
        .where(Document.title.ilike(pattern))
    )
    if source_type is not None:
        count_stmt = count_stmt.where(Document.source_type == source_type)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    results: list[PublicSearchResult] = []
    for doc in docs:
        # Get first chunk content preview if available
        chunk_stmt = (
            select(Chunk)
            .where(Chunk.document_id == doc.id)
            .order_by(Chunk.chunk_index)
            .limit(1)
        )
        chunk_result = await db.execute(chunk_stmt)
        first_chunk = chunk_result.scalar_one_or_none()
        preview = (first_chunk.content_preview or "") if first_chunk else ""

        results.append(
            PublicSearchResult(
                doc_id=doc.id,
                title=doc.title,
                source_type=doc.source_type,
                content_preview=preview[:300],
                score=1.0,
                created_at=doc.created_at,
            )
        )

    return PublicSearchResponse(results=results, total=total, query=query)


@router.get(
    "/entities",
    response_model=PublicEntityListResponse,
    summary="List entities in the knowledge graph",
)
async def public_entities(
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db_session),
) -> PublicEntityListResponse:
    """List entities for the authenticated API-key owner."""
    stmt = select(Entity).where(Entity.user_id == current_user.id)

    if entity_type is not None:
        stmt = stmt.where(Entity.entity_type == entity_type)

    # Count
    count_stmt = (
        select(func.count())
        .select_from(Entity)
        .where(Entity.user_id == current_user.id)
    )
    if entity_type is not None:
        count_stmt = count_stmt.where(Entity.entity_type == entity_type)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    stmt = stmt.order_by(Entity.mention_count.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    entities = list(result.scalars().all())

    return PublicEntityListResponse(
        entities=[
            PublicEntityItem(
                id=e.id,
                type=e.entity_type,
                name=e.name,
                mention_count=e.mention_count,
            )
            for e in entities
        ],
        total=total,
    )


@router.get(
    "/entities/{entity_id}",
    response_model=PublicEntityDetail,
    summary="Entity detail",
)
async def public_entity_detail(
    entity_id: uuid.UUID,
    current_user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db_session),
) -> PublicEntityDetail:
    """Get details for a specific entity."""
    stmt = select(Entity).where(
        Entity.id == entity_id, Entity.user_id == current_user.id
    )
    result = await db.execute(stmt)
    entity = result.scalar_one_or_none()

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"},
        )

    return PublicEntityDetail(
        id=entity.id,
        type=entity.entity_type,
        name=entity.name,
        mention_count=entity.mention_count,
        first_seen=entity.first_seen,
        last_seen=entity.last_seen,
    )


@router.get(
    "/briefings/latest",
    response_model=PublicBriefingsResponse,
    summary="Latest briefings",
)
async def public_latest_briefings(
    current_user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db_session),
) -> PublicBriefingsResponse:
    """Return the latest briefings for the authenticated user."""
    stmt = (
        select(Briefing)
        .where(Briefing.user_id == current_user.id)
        .order_by(Briefing.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    briefings = list(result.scalars().all())

    return PublicBriefingsResponse(
        briefings=[
            PublicBriefingItem(
                id=b.id,
                briefing_type=b.briefing_type,
                title=b.title,
                content_preview=(b.content or "")[:500],
                created_at=b.created_at,
            )
            for b in briefings
        ],
    )


@router.post(
    "/documents/ingest",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a document",
)
async def public_ingest_document(
    body: IngestDocumentRequest,
    current_user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db_session),
) -> IngestDocumentResponse:
    """Ingest a new document via the public API.

    Creates a document record with initial processing_status=pending.
    Chunking and embedding will be triggered asynchronously.
    """
    content_hash = hashlib.sha256(body.content.encode("utf-8")).hexdigest()

    doc = Document(
        user_id=current_user.id,
        source_type=body.source_type,
        source_id=f"api:{uuid.uuid4().hex[:12]}",
        title=body.title,
        content_hash=content_hash,
        processing_status="pending",
    )
    db.add(doc)
    await db.flush()
    await db.commit()

    return IngestDocumentResponse(
        document_id=doc.id,
        title=body.title,
        source_type=doc.source_type,
        status="ingested",
    )
