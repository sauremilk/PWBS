"""Briefings API endpoints (TASK-089).

GET    /api/v1/briefings/                -- Paginated list (filterable by type)
GET    /api/v1/briefings/latest          -- Latest briefing per type
GET    /api/v1/briefings/{id}            -- Single briefing with resolved sources
POST   /api/v1/briefings/generate        -- Trigger async briefing generation
POST   /api/v1/briefings/{id}/feedback   -- Submit rating + optional comment
DELETE /api/v1/briefings/{id}            -- Delete a briefing (owner only)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    status,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.briefing import Briefing as BriefingORM
from pwbs.models.chunk import Chunk
from pwbs.models.document import Document
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.schemas.enums import BriefingType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/briefings",
    tags=["briefings"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)

# Maximum generation requests per user within the cooldown window
_GENERATE_COOLDOWN_SECONDS = 60


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class BriefingListItem(BaseModel):
    """Compact briefing representation for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    briefing_type: str
    title: str
    generated_at: datetime
    expires_at: datetime | None = None


class BriefingListResponse(BaseModel):
    briefings: list[BriefingListItem]
    total: int
    has_more: bool


class SourceRefResponse(BaseModel):
    """Resolved source reference for a briefing."""

    chunk_id: uuid.UUID
    doc_title: str
    source_type: str
    date: datetime
    relevance: float = Field(ge=0.0, le=1.0)


class BriefingDetailResponse(BaseModel):
    """Full briefing representation with resolved sources."""

    id: uuid.UUID
    briefing_type: str
    title: str
    content: str
    source_chunks: list[uuid.UUID]
    source_entities: list[uuid.UUID]
    trigger_context: dict[str, Any] | None = None
    generated_at: datetime
    expires_at: datetime | None = None
    sources: list[SourceRefResponse] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    """Request body for triggering briefing generation."""

    briefing_type: BriefingType
    trigger_context: dict[str, Any] | None = None


class GenerateResponse(BaseModel):
    briefing_id: uuid.UUID
    status: str = "generating"


class FeedbackRequest(BaseModel):
    """Feedback on a generated briefing."""

    rating: str = Field(pattern=r"^(positive|negative)$")
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    briefing_id: uuid.UUID
    rating: str
    message: str = "Feedback recorded"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _resolve_sources(
    source_chunk_ids: list[uuid.UUID],
    user_id: uuid.UUID,
    db: AsyncSession,
) -> list[SourceRefResponse]:
    """Resolve chunk UUIDs to SourceRefResponse objects.

    Joins chunks → documents to get doc_title and source_type.
    Only returns chunks owned by the given user.
    """
    if not source_chunk_ids:
        return []

    stmt = (
        select(
            Chunk.id,
            Document.title,
            Document.source_type,
            Document.created_at,
        )
        .join(Document, Chunk.document_id == Document.id)
        .where(
            Chunk.id.in_(source_chunk_ids),
            Chunk.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    rows = result.all()

    chunk_order = {cid: idx for idx, cid in enumerate(source_chunk_ids)}
    sources = []
    for row in rows:
        rank = chunk_order.get(row.id, len(source_chunk_ids))
        relevance = max(0.0, min(1.0, 1.0 - (rank * 0.05)))
        sources.append(
            SourceRefResponse(
                chunk_id=row.id,
                doc_title=row.title or "Untitled",
                source_type=row.source_type,
                date=row.created_at,
                relevance=round(relevance, 2),
            )
        )
    return sources


def _orm_to_detail(
    row: BriefingORM,
    sources: list[SourceRefResponse],
) -> BriefingDetailResponse:
    """Map ORM model to detail response."""
    return BriefingDetailResponse(
        id=row.id,
        briefing_type=row.briefing_type,
        title=row.title,
        content=row.content,
        source_chunks=row.source_chunks or [],
        source_entities=row.source_entities or [],
        trigger_context=row.trigger_context,
        generated_at=row.generated_at,
        expires_at=row.expires_at,
        sources=sources,
    )


def _check_ownership(row: BriefingORM, user_id: uuid.UUID) -> None:
    """Raise 403 if the briefing does not belong to the user."""
    if row.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Access denied"},
        )


# ---------------------------------------------------------------------------
# GET /api/v1/briefings/  — paginated list
# ---------------------------------------------------------------------------


@router.get("/", response_model=BriefingListResponse)
async def list_briefings(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    briefing_type: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> BriefingListResponse:
    """Return a paginated list of briefings for the authenticated user."""
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    base = select(BriefingORM).where(BriefingORM.user_id == user.id)
    count_base = select(func.count()).select_from(BriefingORM).where(BriefingORM.user_id == user.id)

    if briefing_type is not None:
        base = base.where(BriefingORM.briefing_type == briefing_type)
        count_base = count_base.where(BriefingORM.briefing_type == briefing_type)

    total_result = await db.execute(count_base)
    total = total_result.scalar_one()

    stmt = base.order_by(BriefingORM.generated_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = [
        BriefingListItem(
            id=r.id,
            briefing_type=r.briefing_type,
            title=r.title,
            generated_at=r.generated_at,
            expires_at=r.expires_at,
        )
        for r in rows
    ]

    return BriefingListResponse(
        briefings=items,
        total=total,
        has_more=(offset + limit) < total,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/briefings/latest — latest briefing per type
# ---------------------------------------------------------------------------


@router.get("/latest", response_model=list[BriefingDetailResponse])
async def latest_briefings(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[BriefingDetailResponse]:
    """Return the most recent briefing for each briefing type."""
    results: list[BriefingDetailResponse] = []

    for bt in BriefingType:
        stmt = (
            select(BriefingORM)
            .where(
                BriefingORM.user_id == user.id,
                BriefingORM.briefing_type == bt.value,
            )
            .order_by(BriefingORM.generated_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            sources = await _resolve_sources(row.source_chunks or [], user.id, db)
            results.append(_orm_to_detail(row, sources))

    return results


# ---------------------------------------------------------------------------
# GET /api/v1/briefings/{briefing_id} — single briefing with sources
# ---------------------------------------------------------------------------


@router.get("/{briefing_id}", response_model=BriefingDetailResponse)
async def get_briefing(
    briefing_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BriefingDetailResponse:
    """Return a single briefing with resolved source references."""
    stmt = select(BriefingORM).where(BriefingORM.id == briefing_id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Briefing not found"},
        )

    _check_ownership(row, user.id)

    sources = await _resolve_sources(row.source_chunks or [], user.id, db)
    return _orm_to_detail(row, sources)


# ---------------------------------------------------------------------------
# POST /api/v1/briefings/generate — trigger async generation
# ---------------------------------------------------------------------------


async def _run_briefing_generation(
    briefing_id: uuid.UUID,
    briefing_type: BriefingType,
    user_id: uuid.UUID,
    trigger_context: dict[str, Any] | None,
) -> None:
    """Background task: generate and persist a briefing.

    Imports the briefing engine lazily to avoid circular imports at
    module level. Errors are logged but do not propagate to the caller
    (the HTTP response has already been sent).
    """
    try:
        from pwbs.briefing.context import MorningContextAssembler
        from pwbs.briefing.generator import BriefingGenerator
        from pwbs.briefing.persistence import BriefingPersistenceService
        from pwbs.core.llm_gateway import LLMGateway
        from pwbs.db.postgres import async_session_factory
        from pwbs.prompts.registry import PromptRegistry

        async with async_session_factory()() as session:
            # Build services
            llm = LLMGateway()
            registry = PromptRegistry()
            generator = BriefingGenerator(llm, registry)

            # For morning briefings, assemble context
            if briefing_type == BriefingType.MORNING:
                context: dict[str, Any] = trigger_context or {}
            elif briefing_type == BriefingType.PROJECT:
                from pwbs.briefing.project_context import (
                    NullProjectGraphService,
                    ProjectContextAssembler,
                )
                from pwbs.search.service import SemanticSearchService as _ProjSearchSvc

                project_name = (trigger_context or {}).get("project_name", "")
                project_entity_id = (trigger_context or {}).get(
                    "project_entity_id", None,
                )
                if not project_name:
                    logger.warning(
                        "Project briefing requested without project_name: id=%s",
                        briefing_id,
                    )
                    return

                proj_search_svc = _ProjSearchSvc(session)
                proj_assembler = ProjectContextAssembler(
                    session=session,
                    search_service=proj_search_svc,
                    graph_service=NullProjectGraphService(),
                )
                proj_ctx = await proj_assembler.assemble(
                    user_id=user_id,
                    project_name=project_name,
                    project_id=project_entity_id,
                )
                context = {
                    "project_name": proj_ctx.project_name,
                    "project_id": proj_ctx.project_id,
                    "timeline": proj_ctx.timeline,
                    "decisions": proj_ctx.decisions,
                    "participants": proj_ctx.participants,
                    "open_items": proj_ctx.open_items,
                    "recent_documents": proj_ctx.recent_documents,
                    "summary_stats": proj_ctx.summary_stats,
                }
            elif briefing_type == BriefingType.WEEKLY:
                from pwbs.briefing.weekly_context import (
                    NullWeeklyGraphService,
                    WeeklyContextAssembler,
                )
                from pwbs.search.service import SemanticSearchService

                search_svc = SemanticSearchService(session)
                assembler = WeeklyContextAssembler(
                    session=session,
                    search_service=search_svc,
                    graph_service=NullWeeklyGraphService(),
                )
                weekly_ctx = await assembler.assemble(user_id=user_id)
                context = {
                    "week_start": weekly_ctx.week_start,
                    "week_end": weekly_ctx.week_end,
                    "top_topics": weekly_ctx.top_topics,
                    "decisions": weekly_ctx.decisions,
                    "project_progress": weekly_ctx.project_progress,
                    "open_items": weekly_ctx.open_items,
                    "recent_documents": weekly_ctx.recent_documents,
                }
            else:
                context = trigger_context or {}

            llm_result = await generator.generate(
                briefing_type=briefing_type,
                context=context,
                user_id=user_id,
            )

            persistence = BriefingPersistenceService(session)
            await persistence.save(
                user_id=user_id,
                briefing_type=briefing_type,
                title=f"{briefing_type.value.replace('_', ' ').title()} Briefing",
                content=llm_result.content,
                source_chunks=[],
                trigger_context=trigger_context,
                briefing_id=briefing_id,
            )
            await session.commit()

        logger.info(
            "Briefing generation completed: id=%s type=%s user=%s",
            briefing_id,
            briefing_type.value,
            user_id,
        )
    except Exception:
        logger.exception(
            "Briefing generation failed: id=%s type=%s user=%s",
            briefing_id,
            briefing_type.value,
            user_id,
        )


@router.post("/generate", response_model=GenerateResponse, status_code=202)
async def generate_briefing(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> GenerateResponse:
    """Trigger asynchronous briefing generation.

    Returns immediately with a briefing_id. The actual generation runs
    as a FastAPI background task. Rate-limited to one request per user
    per cooldown window.
    """
    # Rate-limit check: ensure no briefing was generated in the last N seconds
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=_GENERATE_COOLDOWN_SECONDS)
    recent_stmt = (
        select(func.count())
        .select_from(BriefingORM)
        .where(
            BriefingORM.user_id == user.id,
            BriefingORM.briefing_type == body.briefing_type.value,
            BriefingORM.generated_at > cutoff,
        )
    )
    recent_result = await db.execute(recent_stmt)
    recent_count = recent_result.scalar_one()

    if recent_count > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "A briefing was recently generated. Please wait before retrying.",
            },
        )

    briefing_id = uuid.uuid4()

    background_tasks.add_task(
        _run_briefing_generation,
        briefing_id=briefing_id,
        briefing_type=body.briefing_type,
        user_id=user.id,
        trigger_context=body.trigger_context,
    )

    return GenerateResponse(briefing_id=briefing_id, status="generating")


# ---------------------------------------------------------------------------
# POST /api/v1/briefings/{briefing_id}/feedback — rate a briefing
# ---------------------------------------------------------------------------


@router.post("/{briefing_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    briefing_id: uuid.UUID,
    body: FeedbackRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FeedbackResponse:
    """Submit feedback (positive/negative + optional comment) for a briefing."""
    stmt = select(BriefingORM).where(BriefingORM.id == briefing_id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Briefing not found"},
        )

    _check_ownership(row, user.id)

    # Store feedback in trigger_context JSONB (MVP approach)
    ctx = dict(row.trigger_context) if row.trigger_context else {}
    ctx["feedback"] = {
        "rating": body.rating,
        "comment": body.comment,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    row.trigger_context = ctx
    await db.flush()

    return FeedbackResponse(
        briefing_id=briefing_id,
        rating=body.rating,
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/briefings/{briefing_id} — delete a briefing
# ---------------------------------------------------------------------------


@router.delete("/{briefing_id}", status_code=204)
async def delete_briefing(
    briefing_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a briefing (owner only)."""
    stmt = select(BriefingORM).where(BriefingORM.id == briefing_id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Briefing not found"},
        )

    _check_ownership(row, user.id)

    await db.execute(
        delete(BriefingORM).where(
            BriefingORM.id == briefing_id,
            BriefingORM.user_id == user.id,
        )
    )
