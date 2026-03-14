"""Knowledge API endpoints (TASK-090).

GET    /api/v1/knowledge/entities              -- Paginated entity list (filterable by type)
GET    /api/v1/knowledge/entities/{id}         -- Entity detail with connections
GET    /api/v1/knowledge/entities/{id}/related -- Related entities up to depth 2
GET    /api/v1/knowledge/entities/{id}/documents -- Documents mentioning an entity
GET    /api/v1/knowledge/graph                 -- Subgraph for D3.js visualisation (max 50 nodes)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.document import Document as DocumentORM
from pwbs.models.entity import Entity as EntityORM
from pwbs.models.entity import EntityMention
from pwbs.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

_MAX_GRAPH_NODES = 50
_MAX_RELATED_DEPTH = 3


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class EntityListItem(BaseModel):
    """Compact entity representation for list endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    name: str
    mention_count: int
    last_seen: datetime | None = None


class EntityListResponse(BaseModel):
    entities: list[EntityListItem]
    total: int


class RelatedEntityItem(BaseModel):
    """Entity connected to the primary entity."""

    id: uuid.UUID
    type: str
    name: str
    mention_count: int
    relation: str | None = None


class EntityDetailResponse(BaseModel):
    """Full entity detail with related entities."""

    id: uuid.UUID
    type: str
    name: str
    normalized_name: str
    mention_count: int
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    metadata: dict | None = None
    related_entities: list[RelatedEntityItem] = Field(default_factory=list)


class EntityDocumentItem(BaseModel):
    """Document referencing an entity."""

    id: uuid.UUID
    title: str | None = None
    source_type: str
    created_at: datetime


class EntityDocumentsResponse(BaseModel):
    documents: list[EntityDocumentItem]
    total: int


class GraphNode(BaseModel):
    id: str
    type: str
    name: str
    size: int = 1


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = 1.0


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_entity_or_404(
    entity_id: uuid.UUID,
    db: AsyncSession,
) -> EntityORM:
    """Fetch entity by ID or raise 404."""
    stmt = select(EntityORM).where(EntityORM.id == entity_id)
    result = await db.execute(stmt)
    entity = result.scalar_one_or_none()
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Entity not found"},
        )
    return entity


def _check_entity_ownership(entity: EntityORM, user_id: uuid.UUID) -> None:
    """Raise 403 if entity does not belong to user."""
    if entity.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Access denied"},
        )


async def _get_related_from_postgres(
    entity_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 20,
) -> list[RelatedEntityItem]:
    """Find related entities via shared chunk mentions (PostgreSQL fallback).

    Two entities are related if they appear in the same chunk.
    """
    # Subquery: chunk_ids mentioning the target entity
    entity_chunks_sq = (
        select(EntityMention.chunk_id).where(EntityMention.entity_id == entity_id).subquery()
    )

    # Entities that share at least one chunk with the target entity
    stmt = (
        select(
            EntityORM.id,
            EntityORM.entity_type,
            EntityORM.name,
            EntityORM.mention_count,
            func.count(EntityMention.chunk_id).label("shared_count"),
        )
        .join(EntityMention, EntityORM.id == EntityMention.entity_id)
        .where(
            EntityMention.chunk_id.in_(select(entity_chunks_sq.c.chunk_id)),
            EntityORM.id != entity_id,
            EntityORM.user_id == user_id,
        )
        .group_by(EntityORM.id, EntityORM.entity_type, EntityORM.name, EntityORM.mention_count)
        .order_by(func.count(EntityMention.chunk_id).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        RelatedEntityItem(
            id=r.id,
            type=r.entity_type,
            name=r.name,
            mention_count=r.mention_count,
            relation="co_mentioned",
        )
        for r in rows
    ]


async def _get_neo4j_related(
    entity_id: uuid.UUID,
    user_id: uuid.UUID,
    depth: int = 2,
    limit: int = 20,
) -> list[RelatedEntityItem]:
    """Get related entities from Neo4j knowledge graph."""
    depth = max(1, min(depth, _MAX_RELATED_DEPTH))

    try:
        from pwbs.db.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity {id: $entity_id, owner_id: $owner_id})"
                f"-[r*1..{depth}]-(related:Entity {{owner_id: $owner_id}}) "
                "WHERE related.id <> $entity_id "
                "RETURN DISTINCT related.id AS id, related.type AS type, "
                "related.name AS name, related.mention_count AS mention_count, "
                "type(r[0]) AS relation "
                "LIMIT $limit",
                entity_id=str(entity_id),
                owner_id=str(user_id),
                limit=limit,
            )
            records = await result.data()

        return [
            RelatedEntityItem(
                id=uuid.UUID(r["id"]),
                type=r.get("type", "unknown"),
                name=r.get("name", ""),
                mention_count=r.get("mention_count", 0),
                relation=r.get("relation"),
            )
            for r in records
        ]
    except Exception:
        logger.warning("Neo4j related query failed, falling back to PostgreSQL")
        return []


async def _get_neo4j_graph(
    user_id: uuid.UUID,
    limit: int = _MAX_GRAPH_NODES,
) -> GraphResponse:
    """Fetch graph subgraph from Neo4j for D3.js visualisation."""
    limit = min(limit, _MAX_GRAPH_NODES)

    try:
        from pwbs.db.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        async with driver.session() as session:
            # Get top nodes by mention count
            node_result = await session.run(
                "MATCH (e:Entity {owner_id: $owner_id}) "
                "RETURN e.id AS id, e.type AS type, e.name AS name, "
                "e.mention_count AS mention_count "
                "ORDER BY e.mention_count DESC "
                "LIMIT $limit",
                owner_id=str(user_id),
                limit=limit,
            )
            node_records = await node_result.data()

            node_ids = [r["id"] for r in node_records]
            if not node_ids:
                return GraphResponse(nodes=[], edges=[])

            # Get edges between these nodes
            edge_result = await session.run(
                "MATCH (a:Entity {owner_id: $owner_id})"
                "-[r]-(b:Entity {owner_id: $owner_id}) "
                "WHERE a.id IN $node_ids AND b.id IN $node_ids "
                "AND a.id < b.id "
                "RETURN a.id AS source, b.id AS target, "
                "type(r) AS relation, r.weight AS weight",
                owner_id=str(user_id),
                node_ids=node_ids,
            )
            edge_records = await edge_result.data()

        nodes = [
            GraphNode(
                id=r["id"],
                type=r.get("type", "unknown"),
                name=r.get("name", ""),
                size=r.get("mention_count", 1),
            )
            for r in node_records
        ]

        edges = [
            GraphEdge(
                source=r["source"],
                target=r["target"],
                relation=r.get("relation", "RELATED_TO"),
                weight=r.get("weight", 1.0) or 1.0,
            )
            for r in edge_records
        ]

        return GraphResponse(nodes=nodes, edges=edges)

    except Exception:
        logger.exception("Neo4j graph query failed")
        return GraphResponse(nodes=[], edges=[])


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/entities — paginated list
# ---------------------------------------------------------------------------


@router.get("/entities", response_model=EntityListResponse)
async def list_entities(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    entity_type: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> EntityListResponse:
    """Return paginated entity list for the authenticated user."""
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    base = select(EntityORM).where(EntityORM.user_id == user.id)
    count_base = select(func.count()).select_from(EntityORM).where(EntityORM.user_id == user.id)

    if entity_type is not None:
        base = base.where(EntityORM.entity_type == entity_type)
        count_base = count_base.where(EntityORM.entity_type == entity_type)

    total_result = await db.execute(count_base)
    total = total_result.scalar_one()

    stmt = base.order_by(EntityORM.mention_count.desc(), EntityORM.name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = [
        EntityListItem(
            id=r.id,
            type=r.entity_type,
            name=r.name,
            mention_count=r.mention_count,
            last_seen=r.last_seen,
        )
        for r in rows
    ]

    return EntityListResponse(entities=items, total=total)


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/entities/{entity_id} — detail with connections
# ---------------------------------------------------------------------------


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity(
    entity_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> EntityDetailResponse:
    """Return entity detail with related entities."""
    entity = await _get_entity_or_404(entity_id, db)
    _check_entity_ownership(entity, user.id)

    # Try Neo4j first, fallback to PostgreSQL
    related = await _get_neo4j_related(entity_id, user.id)
    if not related:
        related = await _get_related_from_postgres(entity_id, user.id, db)

    return EntityDetailResponse(
        id=entity.id,
        type=entity.entity_type,
        name=entity.name,
        normalized_name=entity.normalized_name,
        mention_count=entity.mention_count,
        first_seen=entity.first_seen,
        last_seen=entity.last_seen,
        metadata=entity.metadata_,
        related_entities=related,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/entities/{entity_id}/related — related entities
# ---------------------------------------------------------------------------


@router.get("/entities/{entity_id}/related", response_model=list[RelatedEntityItem])
async def get_related_entities(
    entity_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    depth: int = 2,
    limit: int = 20,
) -> list[RelatedEntityItem]:
    """Return entities related to the given entity (up to depth 2)."""
    entity = await _get_entity_or_404(entity_id, db)
    _check_entity_ownership(entity, user.id)

    depth = max(1, min(depth, _MAX_RELATED_DEPTH))
    limit = max(1, min(limit, 50))

    related = await _get_neo4j_related(entity_id, user.id, depth=depth, limit=limit)
    if not related:
        related = await _get_related_from_postgres(entity_id, user.id, db, limit=limit)

    return related


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/entities/{entity_id}/documents
# ---------------------------------------------------------------------------


@router.get("/entities/{entity_id}/documents", response_model=EntityDocumentsResponse)
async def get_entity_documents(
    entity_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    offset: int = 0,
    limit: int = 20,
) -> EntityDocumentsResponse:
    """Return documents that mention the given entity."""
    entity = await _get_entity_or_404(entity_id, db)
    _check_entity_ownership(entity, user.id)

    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    from pwbs.models.chunk import Chunk as ChunkORM

    # Find documents via entity_mentions → chunks → documents
    doc_stmt = (
        select(
            DocumentORM.id,
            DocumentORM.title,
            DocumentORM.source_type,
            DocumentORM.created_at,
        )
        .join(ChunkORM, DocumentORM.id == ChunkORM.document_id)
        .join(EntityMention, ChunkORM.id == EntityMention.chunk_id)
        .where(
            EntityMention.entity_id == entity_id,
            DocumentORM.user_id == user.id,
        )
        .distinct()
        .order_by(DocumentORM.created_at.desc())
    )

    # Count total
    count_stmt = select(func.count()).select_from(doc_stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Paginate
    stmt = doc_stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    items = [
        EntityDocumentItem(
            id=r.id,
            title=r.title,
            source_type=r.source_type,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return EntityDocumentsResponse(documents=items, total=total)


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/graph — D3.js subgraph
# ---------------------------------------------------------------------------


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    response: Response,
    user: User = Depends(get_current_user),
    limit: int = _MAX_GRAPH_NODES,
) -> GraphResponse:
    """Return subgraph for D3.js visualisation (max 50 nodes)."""
    limit = max(1, min(limit, _MAX_GRAPH_NODES))
    return await _get_neo4j_graph(user.id, limit=limit)
