"""Collaborative Briefings API routes (TASK-163).

POST   /api/v1/briefings/{id}/share      -- Share briefing with recipients
GET    /api/v1/briefings/{id}/shares      -- List shares (with read status)
POST   /api/v1/briefings/{id}/read        -- Mark shared briefing as read
POST   /api/v1/briefings/{id}/comments    -- Add inline comment
GET    /api/v1/briefings/{id}/comments    -- List comments (paginated)
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.briefing.collaboration import schemas, service
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/briefings",
    tags=["briefing-collaboration"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


def _map_value_error(err: ValueError) -> HTTPException:
    """Map service-layer ValueError codes to HTTP exceptions."""
    code = str(err)
    mapping: dict[str, tuple[int, str]] = {
        "BRIEFING_NOT_FOUND": (404, "Briefing nicht gefunden"),
        "NOT_OWNER": (403, "Nur der Ersteller darf Briefings teilen"),
        "ACCESS_DENIED": (403, "Kein Zugriff auf dieses Briefing"),
        "SHARE_NOT_FOUND": (404, "Kein Share-Eintrag gefunden"),
    }
    status_code, message = mapping.get(code, (400, code))
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


# ── Share Endpoints ───────────────────────────────────────────────────────────


@router.post(
    "/{briefing_id}/share",
    response_model=schemas.ShareListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Briefing mit Nutzern teilen",
)
async def share_briefing(
    briefing_id: uuid.UUID,
    body: schemas.ShareBriefingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> schemas.ShareListResponse:
    try:
        shares = await service.share_briefing(db, briefing_id, user.id, body.recipient_ids)
    except ValueError as exc:
        raise _map_value_error(exc) from exc

    items = [
        schemas.ShareResponse(
            id=s.id,
            briefing_id=s.briefing_id,
            shared_by=s.shared_by,
            recipient_id=s.recipient_id,
            shared_at=s.shared_at,
            read_at=s.read_at,
        )
        for s in shares
    ]
    return schemas.ShareListResponse(shares=items, total=len(items))


@router.get(
    "/{briefing_id}/shares",
    response_model=schemas.ShareListResponse,
    summary="Shares eines Briefings auflisten",
)
async def get_shares(
    briefing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> schemas.ShareListResponse:
    try:
        shares = await service.list_shares(db, briefing_id, user.id)
    except ValueError as exc:
        raise _map_value_error(exc) from exc

    items = [
        schemas.ShareResponse(
            id=s.id,
            briefing_id=s.briefing_id,
            shared_by=s.shared_by,
            recipient_id=s.recipient_id,
            shared_at=s.shared_at,
            read_at=s.read_at,
        )
        for s in shares
    ]
    return schemas.ShareListResponse(shares=items, total=len(items))


@router.post(
    "/{briefing_id}/read",
    response_model=schemas.ReadReceiptResponse,
    summary="Geteiltes Briefing als gelesen markieren",
)
async def mark_as_read(
    briefing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> schemas.ReadReceiptResponse:
    try:
        share = await service.mark_read(db, briefing_id, user.id)
    except ValueError as exc:
        raise _map_value_error(exc) from exc

    return schemas.ReadReceiptResponse(
        briefing_id=share.briefing_id,
        recipient_id=share.recipient_id,
        read_at=share.read_at,  # type: ignore[arg-type]
    )


# ── Comment Endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/{briefing_id}/comments",
    response_model=schemas.CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add inline comment",
)
async def create_comment(
    briefing_id: uuid.UUID,
    body: schemas.CreateCommentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> schemas.CommentResponse:
    try:
        comment = await service.add_comment(
            db, briefing_id, user.id, body.section_ref, body.content
        )
    except ValueError as exc:
        raise _map_value_error(exc) from exc

    return schemas.CommentResponse(
        id=comment.id,
        briefing_id=comment.briefing_id,
        author_id=comment.author_id,
        section_ref=comment.section_ref,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.get(
    "/{briefing_id}/comments",
    response_model=schemas.CommentListResponse,
    summary="Kommentare eines Briefings (paginiert)",
)
async def get_comments(
    briefing_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> schemas.CommentListResponse:
    try:
        comments, total = await service.list_comments(db, briefing_id, user.id, offset, limit)
    except ValueError as exc:
        raise _map_value_error(exc) from exc

    items = [
        schemas.CommentResponse(
            id=c.id,
            briefing_id=c.briefing_id,
            author_id=c.author_id,
            section_ref=c.section_ref,
            content=c.content,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in comments
    ]
    return schemas.CommentListResponse(comments=items, total=total)
