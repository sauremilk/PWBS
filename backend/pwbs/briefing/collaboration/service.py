"""Service layer for collaborative briefings (TASK-163).

Functions:
  - share_briefing: Share a briefing with recipients (owner-only).
  - list_shares: List shares for a briefing (owner or recipient).
  - mark_read: Mark a shared briefing as read by the recipient.
  - add_comment: Add an inline comment (owner or recipient).
  - list_comments: Paginated comments for a briefing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.briefing.collaboration.models import BriefingComment, BriefingShare
from pwbs.models.briefing import Briefing

logger = logging.getLogger(__name__)


async def _get_briefing_or_404(
    db: AsyncSession,
    briefing_id: uuid.UUID,
) -> Briefing:
    """Return Briefing row or raise ValueError."""
    row = await db.get(Briefing, briefing_id)
    if row is None:
        raise ValueError("BRIEFING_NOT_FOUND")
    return row


async def _assert_access(
    db: AsyncSession,
    briefing_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Briefing:
    """Return Briefing if user is owner OR recipient of a share.

    Raises ValueError with descriptive code on failure.
    """
    briefing = await _get_briefing_or_404(db, briefing_id)

    # Owner always has access
    if briefing.user_id == user_id:
        return briefing

    # Check share
    share_q = select(BriefingShare.id).where(
        BriefingShare.briefing_id == briefing_id,
        BriefingShare.recipient_id == user_id,
    )
    result = await db.execute(share_q)
    if result.scalar_one_or_none() is None:
        raise ValueError("ACCESS_DENIED")

    return briefing


# ── Sharing ───────────────────────────────────────────────────────────────────


async def share_briefing(
    db: AsyncSession,
    briefing_id: uuid.UUID,
    sharer_id: uuid.UUID,
    recipient_ids: list[uuid.UUID],
) -> list[BriefingShare]:
    """Share a briefing with one or more recipients.

    Only the briefing **owner** may share. Duplicate shares are silently
    ignored (upsert ON CONFLICT DO NOTHING).

    Returns the list of *newly created* share rows.
    """
    briefing = await _get_briefing_or_404(db, briefing_id)

    if briefing.user_id != sharer_id:
        raise ValueError("NOT_OWNER")

    # Filter out self-sharing
    valid_recipients = [rid for rid in recipient_ids if rid != sharer_id]
    if not valid_recipients:
        return []

    now = datetime.now(timezone.utc)
    values = [
        {
            "id": uuid.uuid4(),
            "briefing_id": briefing_id,
            "shared_by": sharer_id,
            "recipient_id": rid,
            "shared_at": now,
        }
        for rid in valid_recipients
    ]

    stmt = (
        pg_insert(BriefingShare)
        .values(values)
        .on_conflict_do_nothing(
            index_elements=["briefing_id", "recipient_id"],
        )
        .returning(BriefingShare)
    )
    result = await db.execute(stmt)
    rows: list[BriefingShare] = list(result.scalars().all())
    await db.flush()

    logger.info(
        "Shared briefing %s with %d recipients (%d new)",
        briefing_id,
        len(valid_recipients),
        len(rows),
    )
    return rows


async def list_shares(
    db: AsyncSession,
    briefing_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[BriefingShare]:
    """List all shares for a briefing. Accessible to owner or any recipient."""
    await _assert_access(db, briefing_id, user_id)

    q = (
        select(BriefingShare)
        .where(BriefingShare.briefing_id == briefing_id)
        .order_by(BriefingShare.shared_at)
    )
    result = await db.execute(q)
    return list(result.scalars().all())


# ── Read Receipts ─────────────────────────────────────────────────────────────


async def mark_read(
    db: AsyncSession,
    briefing_id: uuid.UUID,
    user_id: uuid.UUID,
) -> BriefingShare:
    """Mark a shared briefing as read by the recipient.

    Raises ValueError if the user has no share record for this briefing.
    """
    q = select(BriefingShare).where(
        BriefingShare.briefing_id == briefing_id,
        BriefingShare.recipient_id == user_id,
    )
    result = await db.execute(q)
    share = result.scalar_one_or_none()
    if share is None:
        raise ValueError("SHARE_NOT_FOUND")

    if share.read_at is None:
        share.read_at = datetime.now(timezone.utc)
        await db.flush()

    return share


# ── Comments ──────────────────────────────────────────────────────────────────


async def add_comment(
    db: AsyncSession,
    briefing_id: uuid.UUID,
    author_id: uuid.UUID,
    section_ref: str,
    content: str,
) -> BriefingComment:
    """Add an inline comment. Author must be owner or share recipient."""
    await _assert_access(db, briefing_id, author_id)

    comment = BriefingComment(
        id=uuid.uuid4(),
        briefing_id=briefing_id,
        author_id=author_id,
        section_ref=section_ref,
        content=content,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    return comment


async def list_comments(
    db: AsyncSession,
    briefing_id: uuid.UUID,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[BriefingComment], int]:
    """Paginated comments for a briefing. Accessible to owner or recipient."""
    await _assert_access(db, briefing_id, user_id)

    count_q = select(func.count()).select_from(BriefingComment).where(
        BriefingComment.briefing_id == briefing_id,
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    data_q = (
        select(BriefingComment)
        .where(BriefingComment.briefing_id == briefing_id)
        .order_by(BriefingComment.created_at)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(data_q)
    return list(result.scalars().all()), total
