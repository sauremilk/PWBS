"""Knowledge Snapshot API endpoints (TASK-162).

POST   /api/v1/snapshots              -- Create a manual snapshot
GET    /api/v1/snapshots              -- List snapshots
GET    /api/v1/snapshots/{id}         -- Get snapshot detail
GET    /api/v1/snapshots/{id1}/diff/{id2} -- Diff between two snapshots
DELETE /api/v1/snapshots/{id}         -- Delete a snapshot
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.snapshots.models import KnowledgeSnapshot
from pwbs.snapshots.schemas import (
    SnapshotCreateRequest,
    SnapshotDetailResponse,
    SnapshotDiffResponse,
    SnapshotEntity,
    SnapshotListResponse,
    SnapshotRelationship,
    SnapshotResponse,
    SnapshotTheme,
)
from pwbs.snapshots.service import capture_snapshot, compute_diff

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/snapshots",
    tags=["snapshots"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ── Helpers ────────────────────────────────────────────────────


async def _get_snapshot_or_404(snapshot_id: uuid.UUID, db: AsyncSession) -> KnowledgeSnapshot:
    stmt = select(KnowledgeSnapshot).where(KnowledgeSnapshot.id == snapshot_id)
    result = await db.execute(stmt)
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Snapshot {snapshot_id} not found"},
        )
    return snapshot


def _check_snapshot_ownership(snapshot: KnowledgeSnapshot, user_id: uuid.UUID) -> None:
    if snapshot.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Snapshot does not belong to this user"},
        )


def _snapshot_to_response(s: KnowledgeSnapshot) -> SnapshotResponse:
    return SnapshotResponse(
        id=s.id,
        label=s.label,
        trigger=s.trigger,
        entity_count=s.entity_count,
        relationship_count=s.relationship_count,
        captured_at=s.captured_at,
        created_at=s.created_at,
    )


def _snapshot_to_detail(s: KnowledgeSnapshot) -> SnapshotDetailResponse:
    data = s.snapshot_data or {}
    return SnapshotDetailResponse(
        id=s.id,
        label=s.label,
        trigger=s.trigger,
        entity_count=s.entity_count,
        relationship_count=s.relationship_count,
        captured_at=s.captured_at,
        created_at=s.created_at,
        entities=[SnapshotEntity(**e) for e in data.get("entities", [])],
        relationships=[SnapshotRelationship(**r) for r in data.get("relationships", [])],
        top_themes=[SnapshotTheme(**t) for t in data.get("top_themes", [])],
    )


# ── Endpoints ─────────────────────────────────────────────────


@router.post(
    "/",
    response_model=SnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a knowledge snapshot",
)
async def create_snapshot(
    body: SnapshotCreateRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SnapshotResponse:
    """Create a manual point-in-time snapshot of the knowledge graph."""
    snapshot = await capture_snapshot(
        db,
        user_id=user.id,
        label=body.label,
        trigger="manual",
    )
    await db.commit()
    await db.refresh(snapshot)
    return _snapshot_to_response(snapshot)


@router.get(
    "/",
    response_model=SnapshotListResponse,
    summary="List knowledge snapshots",
)
async def list_snapshots(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 52,
    offset: int = 0,
) -> SnapshotListResponse:
    """List all snapshots for the authenticated user."""
    count_stmt = (
        select(func.count())
        .select_from(KnowledgeSnapshot)
        .where(KnowledgeSnapshot.user_id == user.id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(KnowledgeSnapshot)
        .where(KnowledgeSnapshot.user_id == user.id)
        .order_by(KnowledgeSnapshot.captured_at.desc())
        .offset(offset)
        .limit(min(limit, 100))
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return SnapshotListResponse(
        snapshots=[_snapshot_to_response(s) for s in snapshots],
        total=total,
    )


@router.get(
    "/{snapshot_id}",
    response_model=SnapshotDetailResponse,
    summary="Get snapshot detail",
)
async def get_snapshot(
    snapshot_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SnapshotDetailResponse:
    """Get full snapshot detail with entities and relationships."""
    snapshot = await _get_snapshot_or_404(snapshot_id, db)
    _check_snapshot_ownership(snapshot, user.id)
    return _snapshot_to_detail(snapshot)


@router.get(
    "/{snapshot_a_id}/diff/{snapshot_b_id}",
    response_model=SnapshotDiffResponse,
    summary="Diff between two snapshots",
)
async def get_snapshot_diff(
    snapshot_a_id: uuid.UUID,
    snapshot_b_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SnapshotDiffResponse:
    """Get a structured diff between two snapshots.

    snapshot_a is treated as the older snapshot, snapshot_b as the newer one.
    """
    snapshot_a = await _get_snapshot_or_404(snapshot_a_id, db)
    _check_snapshot_ownership(snapshot_a, user.id)

    snapshot_b = await _get_snapshot_or_404(snapshot_b_id, db)
    _check_snapshot_ownership(snapshot_b, user.id)

    return compute_diff(snapshot_a, snapshot_b)


@router.delete(
    "/{snapshot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a snapshot",
)
async def delete_snapshot(
    snapshot_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a snapshot."""
    snapshot = await _get_snapshot_or_404(snapshot_id, db)
    _check_snapshot_ownership(snapshot, user.id)
    await db.delete(snapshot)
    await db.commit()
