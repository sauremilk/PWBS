"""Knowledge API endpoints (TASK-090, TASK-129).

GET    /api/v1/knowledge/entities              -- Paginated entity list (filterable by type)
GET    /api/v1/knowledge/entities/{id}         -- Entity detail with connections
GET    /api/v1/knowledge/entities/{id}/related -- Related entities up to depth 2
GET    /api/v1/knowledge/entities/{id}/documents -- Documents mentioning an entity
GET    /api/v1/knowledge/graph                 -- Subgraph for D3.js visualisation (max 50 nodes)
GET    /api/v1/knowledge/decisions             -- Paginated decisions list
POST   /api/v1/knowledge/decisions             -- Create a decision
PATCH  /api/v1/knowledge/decisions/{id}        -- Update a decision
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
from pwbs.models.decision import Decision as DecisionORM
from pwbs.models.document import Document as DocumentORM
from pwbs.models.entity import Entity as EntityORM
from pwbs.models.entity import EntityMention
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/knowledge",
    tags=["knowledge"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)

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


# ---------------------------------------------------------------------------
# Decision schemas (TASK-129)
# ---------------------------------------------------------------------------

_VALID_DECISION_STATUSES = {"pending", "made", "revised"}


class DecisionListItem(BaseModel):
    """Compact decision for list endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    summary: str
    status: str
    decided_by: str | None = None
    decided_at: datetime | None = None
    created_at: datetime


class DecisionListResponse(BaseModel):
    decisions: list[DecisionListItem]
    total: int


class DecisionDetailResponse(BaseModel):
    """Full decision detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    summary: str
    pro_arguments: list[str]
    contra_arguments: list[str]
    assumptions: list[str]
    dependencies: list[str]
    status: str
    decided_by: str | None = None
    decided_at: datetime | None = None
    source_document_id: uuid.UUID | None = None
    neo4j_node_id: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DecisionCreateRequest(BaseModel):
    """Request body to create a decision."""

    summary: str = Field(min_length=1, max_length=2000)
    pro_arguments: list[str] = Field(default_factory=list)
    contra_arguments: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    status: str = "pending"
    decided_by: str | None = None
    decided_at: datetime | None = None
    source_document_id: uuid.UUID | None = None
    expires_at: datetime | None = None


class DecisionUpdateRequest(BaseModel):
    """Request body to update a decision (partial)."""

    summary: str | None = Field(default=None, min_length=1, max_length=2000)
    pro_arguments: list[str] | None = None
    contra_arguments: list[str] | None = None
    assumptions: list[str] | None = None
    dependencies: list[str] | None = None
    status: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    expires_at: datetime | None = None


# ---------------------------------------------------------------------------
# Decision helpers
# ---------------------------------------------------------------------------


async def _get_decision_or_404(
    decision_id: uuid.UUID,
    db: AsyncSession,
) -> DecisionORM:
    """Fetch decision by ID or raise 404."""
    stmt = select(DecisionORM).where(DecisionORM.id == decision_id)
    result = await db.execute(stmt)
    decision = result.scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DECISION_NOT_FOUND", "message": "Entscheidung nicht gefunden"},
        )
    return decision


def _check_decision_ownership(decision: DecisionORM, user_id: uuid.UUID) -> None:
    """Raise 403 if decision does not belong to user."""
    if decision.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Zugriff auf fremde Entscheidung nicht erlaubt",
            },
        )


async def _sync_decision_to_neo4j(decision: DecisionORM) -> str | None:
    """Sync decision node to Neo4j knowledge graph. Returns neo4j_node_id."""
    try:
        from pwbs.db.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(
                "MERGE (d:Decision {id: $id}) "
                "ON CREATE SET d.userId = $user_id, d.summary = $summary, "
                "d.status = $status, d.decidedBy = $decided_by, "
                "d.decidedAt = $decided_at "
                "ON MATCH SET d.summary = $summary, d.status = $status, "
                "d.decidedBy = $decided_by, d.decidedAt = $decided_at "
                "RETURN elementId(d) AS node_id",
                id=str(decision.id),
                user_id=str(decision.user_id),
                summary=decision.summary,
                status=decision.status,
                decided_by=decision.decided_by or "",
                decided_at=decision.decided_at.isoformat() if decision.decided_at else None,
            )
            record = await result.single()
            return record["node_id"] if record else None
    except Exception:
        logger.warning("Failed to sync decision %s to Neo4j", decision.id, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/decisions — paginated list (TASK-129)
# ---------------------------------------------------------------------------


@router.get("/decisions", response_model=DecisionListResponse)
async def list_decisions(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    decision_status: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> DecisionListResponse:
    """Return paginated decisions for the authenticated user."""
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    base = select(DecisionORM).where(DecisionORM.user_id == user.id)
    count_base = select(func.count()).select_from(DecisionORM).where(DecisionORM.user_id == user.id)

    if decision_status is not None and decision_status in _VALID_DECISION_STATUSES:
        base = base.where(DecisionORM.status == decision_status)
        count_base = count_base.where(DecisionORM.status == decision_status)

    total_result = await db.execute(count_base)
    total = total_result.scalar_one()

    stmt = base.order_by(DecisionORM.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = [
        DecisionListItem(
            id=r.id,
            summary=r.summary,
            status=r.status,
            decided_by=r.decided_by,
            decided_at=r.decided_at,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return DecisionListResponse(decisions=items, total=total)


# ---------------------------------------------------------------------------
# POST /api/v1/knowledge/decisions — create (TASK-129)
# ---------------------------------------------------------------------------


@router.post("/decisions", response_model=DecisionDetailResponse, status_code=201)
async def create_decision(
    body: DecisionCreateRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DecisionDetailResponse:
    """Create a new decision with pro/contra arguments."""
    if body.status not in _VALID_DECISION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_STATUS",
                "message": f"Status muss einer von {_VALID_DECISION_STATUSES} sein",
            },
        )

    decision = DecisionORM(
        user_id=user.id,
        summary=body.summary,
        pro_arguments=body.pro_arguments,
        contra_arguments=body.contra_arguments,
        assumptions=body.assumptions,
        dependencies=body.dependencies,
        status=body.status,
        decided_by=body.decided_by,
        decided_at=body.decided_at,
        source_document_id=body.source_document_id,
        expires_at=body.expires_at,
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)

    # Sync to Neo4j (best-effort)
    neo4j_id = await _sync_decision_to_neo4j(decision)
    if neo4j_id and decision.neo4j_node_id != neo4j_id:
        decision.neo4j_node_id = neo4j_id
        await db.commit()

    return DecisionDetailResponse(
        id=decision.id,
        summary=decision.summary,
        pro_arguments=decision.pro_arguments,
        contra_arguments=decision.contra_arguments,
        assumptions=decision.assumptions,
        dependencies=decision.dependencies,
        status=decision.status,
        decided_by=decision.decided_by,
        decided_at=decision.decided_at,
        source_document_id=decision.source_document_id,
        neo4j_node_id=decision.neo4j_node_id,
        expires_at=decision.expires_at,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/knowledge/decisions/{decision_id} — update (TASK-129)
# ---------------------------------------------------------------------------


@router.patch("/decisions/{decision_id}", response_model=DecisionDetailResponse)
async def update_decision(
    decision_id: uuid.UUID,
    body: DecisionUpdateRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DecisionDetailResponse:
    """Update an existing decision (partial update)."""
    decision = await _get_decision_or_404(decision_id, db)
    _check_decision_ownership(decision, user.id)

    update_data = body.model_dump(exclude_unset=True)

    if "status" in update_data and update_data["status"] not in _VALID_DECISION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_STATUS",
                "message": f"Status muss einer von {_VALID_DECISION_STATUSES} sein",
            },
        )

    for field_name, value in update_data.items():
        setattr(decision, field_name, value)

    await db.commit()
    await db.refresh(decision)

    # Sync to Neo4j (best-effort)
    neo4j_id = await _sync_decision_to_neo4j(decision)
    if neo4j_id and decision.neo4j_node_id != neo4j_id:
        decision.neo4j_node_id = neo4j_id
        await db.commit()

    return DecisionDetailResponse(
        id=decision.id,
        summary=decision.summary,
        pro_arguments=decision.pro_arguments,
        contra_arguments=decision.contra_arguments,
        assumptions=decision.assumptions,
        dependencies=decision.dependencies,
        status=decision.status,
        decided_by=decision.decided_by,
        decided_at=decision.decided_at,
        source_document_id=decision.source_document_id,
        neo4j_node_id=decision.neo4j_node_id,
        expires_at=decision.expires_at,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
    )
