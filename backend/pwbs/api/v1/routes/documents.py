"""Documents API endpoints (TASK-091).

GET    /api/v1/documents/           -- Paginated document list (filterable by source_type)
GET    /api/v1/documents/{id}       -- Document metadata + chunks with content-preview and entities
DELETE /api/v1/documents/{id}       -- Cascaded deletion (PostgreSQL, Weaviate vectors, Neo4j refs)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.chunk import Chunk as ChunkORM
from pwbs.models.document import Document as DocumentORM
from pwbs.models.entity import Entity, EntityMention
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DocumentListItem(BaseModel):
    """Compact document representation for list endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None = None
    source_type: str
    source_id: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


class ChunkEntityResponse(BaseModel):
    """Entity mention within a chunk."""

    entity_id: uuid.UUID
    name: str
    entity_type: str
    confidence: float


class ChunkDetailResponse(BaseModel):
    """Chunk with content preview and entities."""

    id: uuid.UUID
    index: int
    content_preview: str | None = None
    entities: list[ChunkEntityResponse] = Field(default_factory=list)


class DocumentDetailResponse(BaseModel):
    """Full document metadata with chunks."""

    id: uuid.UUID
    title: str | None = None
    source_type: str
    source_id: str
    chunk_count: int
    language: str
    processing_status: str
    created_at: datetime
    updated_at: datetime
    chunks: list[ChunkDetailResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_document_ownership(doc: DocumentORM, user_id: uuid.UUID) -> None:
    """Raise 403 if the document does not belong to the user."""
    if doc.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Access denied"},
        )


async def _get_document_or_404(
    document_id: uuid.UUID,
    db: AsyncSession,
) -> DocumentORM:
    """Fetch a document by ID or raise 404."""
    stmt = select(DocumentORM).where(DocumentORM.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Document not found"},
        )
    return doc


async def _build_chunk_details(
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> list[ChunkDetailResponse]:
    """Load chunks for a document with their entity mentions."""
    chunk_stmt = (
        select(ChunkORM)
        .where(
            ChunkORM.document_id == document_id,
            ChunkORM.user_id == user_id,
        )
        .order_by(ChunkORM.chunk_index)
    )
    chunk_result = await db.execute(chunk_stmt)
    chunks = chunk_result.scalars().all()

    if not chunks:
        return []

    chunk_ids = [c.id for c in chunks]

    # Fetch entity mentions for all chunks in one query
    mention_stmt = (
        select(
            EntityMention.chunk_id,
            Entity.id.label("entity_id"),
            Entity.name,
            Entity.entity_type,
            EntityMention.confidence,
        )
        .join(Entity, EntityMention.entity_id == Entity.id)
        .where(EntityMention.chunk_id.in_(chunk_ids))
    )
    mention_result = await db.execute(mention_stmt)
    mentions = mention_result.all()

    # Group mentions by chunk_id
    mentions_by_chunk: dict[uuid.UUID, list[ChunkEntityResponse]] = {}
    for m in mentions:
        mentions_by_chunk.setdefault(m.chunk_id, []).append(
            ChunkEntityResponse(
                entity_id=m.entity_id,
                name=m.name,
                entity_type=m.entity_type,
                confidence=m.confidence,
            )
        )

    return [
        ChunkDetailResponse(
            id=c.id,
            index=c.chunk_index,
            content_preview=c.content_preview,
            entities=mentions_by_chunk.get(c.id, []),
        )
        for c in chunks
    ]


async def _cascade_delete_weaviate(chunks: list[ChunkORM]) -> int:
    """Delete chunk vectors from Weaviate. Returns count of deleted vectors."""
    weaviate_ids = [c.weaviate_id for c in chunks if c.weaviate_id is not None]
    if not weaviate_ids:
        return 0

    deleted = 0
    try:
        from pwbs.db.weaviate_client import get_weaviate_client

        client = get_weaviate_client()
        if client is None:
            return 0
        collection = client.collections.get("DocumentChunk")
        for wid in weaviate_ids:
            try:
                collection.data.delete_by_id(str(wid))
                deleted += 1
            except Exception:
                logger.warning("Failed to delete Weaviate vector %s", wid)
    except Exception:
        logger.exception("Weaviate cascade delete failed")

    return deleted


async def _cascade_delete_neo4j(document_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Remove document references from Neo4j knowledge graph."""
    try:
        from pwbs.db.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        if driver is None:
            return
        async with driver.session() as session:
            await session.run(
                "MATCH (d:Document {id: $doc_id, owner_id: $owner_id}) DETACH DELETE d",
                doc_id=str(document_id),
                owner_id=str(user_id),
            )
    except Exception:
        logger.exception("Neo4j cascade delete failed for document %s", document_id)


# ---------------------------------------------------------------------------
# GET /api/v1/documents/ — paginated list
# ---------------------------------------------------------------------------


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    source_type: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> DocumentListResponse:
    """Return a paginated list of documents for the authenticated user."""
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    base = select(DocumentORM).where(DocumentORM.user_id == user.id)
    count_base = select(func.count()).select_from(DocumentORM).where(DocumentORM.user_id == user.id)

    if source_type is not None:
        base = base.where(DocumentORM.source_type == source_type)
        count_base = count_base.where(DocumentORM.source_type == source_type)

    total_result = await db.execute(count_base)
    total = total_result.scalar_one()

    stmt = base.order_by(DocumentORM.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = [
        DocumentListItem(
            id=r.id,
            title=r.title,
            source_type=r.source_type,
            source_id=r.source_id,
            chunk_count=r.chunk_count,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]

    return DocumentListResponse(documents=items, total=total)


# ---------------------------------------------------------------------------
# GET /api/v1/documents/{document_id} — detail with chunks
# ---------------------------------------------------------------------------


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentDetailResponse:
    """Return document metadata and chunks with content-preview and entities."""
    doc = await _get_document_or_404(document_id, db)
    _check_document_ownership(doc, user.id)

    chunks = await _build_chunk_details(document_id, user.id, db)

    return DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        source_type=doc.source_type,
        source_id=doc.source_id,
        chunk_count=doc.chunk_count,
        language=doc.language,
        processing_status=doc.processing_status,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        chunks=chunks,
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/documents/{document_id} — cascaded deletion
# ---------------------------------------------------------------------------


@router.delete("/{document_id}", status_code=204, response_class=Response)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a document with cascaded cleanup across all storage layers.

    1. PostgreSQL: Delete document + chunks (ON DELETE CASCADE)
    2. Weaviate: Remove vector embeddings for each chunk
    3. Neo4j: Remove document node and its relationships
    """
    doc = await _get_document_or_404(document_id, db)
    _check_document_ownership(doc, user.id)

    # Collect chunk Weaviate IDs before deleting from PostgreSQL
    chunk_stmt = select(ChunkORM).where(
        ChunkORM.document_id == document_id,
        ChunkORM.user_id == user.id,
    )
    chunk_result = await db.execute(chunk_stmt)
    chunks = list(chunk_result.scalars().all())

    # Cascade 1: Weaviate vectors
    deleted_vectors = await _cascade_delete_weaviate(chunks)
    logger.info("Deleted %d Weaviate vectors for document %s", deleted_vectors, document_id)

    # Cascade 2: Neo4j references
    await _cascade_delete_neo4j(document_id, user.id)

    # Cascade 3: PostgreSQL (chunks cascade via ON DELETE CASCADE)
    await db.execute(
        delete(DocumentORM).where(
            DocumentORM.id == document_id,
            DocumentORM.user_id == user.id,
        )
    )
    return Response(status_code=204)
