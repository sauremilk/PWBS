"""Briefing export API routes (TASK-164).

GET  /api/v1/briefings/{id}/export?format=pdf|markdown  -- Export single briefing
POST /api/v1/export/confluence                          -- Create Confluence page
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.export.schemas import ConfluenceExportRequest
from pwbs.export.strategies import build_metadata, get_strategy
from pwbs.models.briefing import Briefing
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["export"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


async def _get_briefing_for_user(
    db: AsyncSession,
    briefing_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Briefing:
    """Fetch briefing ensuring owner_id isolation."""
    briefing = await db.get(Briefing, briefing_id)
    if briefing is None or briefing.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BRIEFING_NOT_FOUND", "message": "Briefing nicht gefunden"},
        )
    return briefing


def _build_source_list(briefing: Briefing) -> list[str]:
    """Build human-readable source references from chunk + entity IDs."""
    sources: list[str] = []
    if briefing.source_chunks:
        for chunk_id in briefing.source_chunks:
            sources.append(f"Chunk: {chunk_id}")
    if briefing.source_entities:
        for entity_id in briefing.source_entities:
            sources.append(f"Entity: {entity_id}")
    return sources


@router.get(
    "/briefings/{briefing_id}/export",
    summary="Briefing exportieren (PDF, Markdown)",
    responses={
        200: {
            "description": "Export-Datei",
            "content": {
                "application/pdf": {},
                "text/markdown": {},
            },
        },
    },
)
async def export_briefing(
    briefing_id: uuid.UUID,
    format: str = Query(  # noqa: A002
        ...,
        description="Export format: 'pdf' or 'markdown'",
        pattern="^(pdf|markdown)$",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    briefing = await _get_briefing_for_user(db, briefing_id, user.id)

    try:
        strategy = get_strategy(format)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_FORMAT", "message": str(exc)},
        ) from exc

    metadata = build_metadata(
        briefing_id=briefing.id,
        briefing_type=briefing.briefing_type,
        title=briefing.title,
        generated_at=briefing.generated_at,
        source_count=len(briefing.source_chunks or []),
    )
    sources = _build_source_list(briefing)

    try:
        result = strategy.export(
            title=briefing.title,
            content=briefing.content,
            metadata=metadata,
            sources=sources,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"code": "DEPENDENCY_MISSING", "message": str(exc)},
        ) from exc

    return Response(
        content=result.data,
        media_type=result.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
        },
    )


@router.post(
    "/export/confluence",
    status_code=status.HTTP_201_CREATED,
    summary="Briefing als Confluence-Seite erstellen",
)
async def export_to_confluence(
    body: ConfluenceExportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    briefing = await _get_briefing_for_user(db, body.briefing_id, user.id)

    strategy = get_strategy("confluence")
    metadata = build_metadata(
        briefing_id=briefing.id,
        briefing_type=briefing.briefing_type,
        title=body.title or briefing.title,
        generated_at=briefing.generated_at,
        source_count=len(briefing.source_chunks or []),
    )
    sources = _build_source_list(briefing)

    result = strategy.export(
        title=body.title or briefing.title,
        content=briefing.content,
        metadata=metadata,
        sources=sources,
    )

    # In a real implementation, this would call the Confluence REST API.
    # For MVP, we return the storage-format body for manual integration.
    logger.info(
        "Confluence export prepared for briefing %s, space %s",
        body.briefing_id,
        body.space_key,
    )

    return {
        "status": "prepared",
        "space_key": body.space_key,
        "title": body.title or briefing.title,
        "body_storage_format": result.data.decode("utf-8"),
        "message": (
            "Confluence-Seite vorbereitet. Direkter API-Push wird in Phase 4 implementiert."
        ),
    }
