"""Briefing-Persistierung in PostgreSQL (TASK-080).

Service for persisting generated briefings to the `briefings` table.
Handles:
- Automatic `expires_at` calculation (Morning +24h, Meeting +48h)
- Upsert semantics for regeneration
- Tenant-isolated queries via `user_id` filter
- Full field persistence including `source_chunks`, `source_entities`,
  `trigger_context`

D1 Section 3.3.1, D4 F-022 (Briefing-Caching und Regenerierung).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.models.briefing import Briefing as BriefingORM
from pwbs.schemas.enums import BriefingType

logger = logging.getLogger(__name__)

__all__ = [
    "BriefingPersistenceService",
    "PersistedBriefing",
    "PersistenceConfig",
]

# Expiration durations per briefing type
_EXPIRY_DURATIONS: dict[BriefingType, timedelta] = {
    BriefingType.MORNING: timedelta(hours=24),
    BriefingType.MEETING_PREP: timedelta(hours=48),
}


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PersistenceConfig:
    """Configuration for briefing persistence."""

    morning_expiry_hours: int = 24
    meeting_expiry_hours: int = 48


@dataclass(frozen=True, slots=True)
class PersistedBriefing:
    """Result of a briefing persistence operation."""

    id: uuid.UUID
    user_id: uuid.UUID
    briefing_type: BriefingType
    title: str
    content: str
    source_chunks: list[uuid.UUID]
    source_entities: list[uuid.UUID]
    trigger_context: dict[str, Any] | None
    generated_at: datetime
    expires_at: datetime | None
    is_new: bool = True


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class BriefingPersistenceService:
    """Persists and retrieves briefings from PostgreSQL.

    Parameters
    ----------
    session:
        SQLAlchemy async session.
    config:
        Persistence configuration (expiry durations).
    """

    def __init__(
        self,
        session: AsyncSession,
        config: PersistenceConfig | None = None,
    ) -> None:
        self._session = session
        self._config = config or PersistenceConfig()

    # ------------------------------------------------------------------
    # Create / Upsert
    # ------------------------------------------------------------------

    async def save(
        self,
        user_id: uuid.UUID,
        briefing_type: BriefingType,
        title: str,
        content: str,
        source_chunks: list[uuid.UUID],
        source_entities: list[uuid.UUID] | None = None,
        trigger_context: dict[str, Any] | None = None,
        briefing_id: uuid.UUID | None = None,
    ) -> PersistedBriefing:
        """Persist a briefing to the database.

        Parameters
        ----------
        user_id:
            Owner of the briefing.
        briefing_type:
            Type of briefing (MORNING, MEETING_PREP).
        title:
            Briefing title.
        content:
            Briefing content (Markdown).
        source_chunks:
            UUIDs of chunks used as sources.
        source_entities:
            UUIDs of entities referenced (optional).
        trigger_context:
            JSON trigger context (calendar event ID, schedule, etc.).
        briefing_id:
            Optional ID for upsert (regeneration). If None, generates new UUID.

        Returns
        -------
        PersistedBriefing
            The persisted briefing with server-set fields.
        """
        now = datetime.now(timezone.utc)
        expires_at = self._calculate_expiry(briefing_type, now)
        bid = briefing_id or uuid.uuid4()
        entities = source_entities or []

        orm_obj = BriefingORM(
            id=bid,
            user_id=user_id,
            briefing_type=briefing_type.value,
            title=title,
            content=content,
            source_chunks=source_chunks,
            source_entities=entities if entities else None,
            trigger_context=trigger_context,
            generated_at=now,
            expires_at=expires_at,
        )

        self._session.add(orm_obj)
        await self._session.flush()

        logger.info(
            "Briefing persisted: id=%s type=%s user=%s chunks=%d",
            bid, briefing_type.value, user_id, len(source_chunks),
        )

        return PersistedBriefing(
            id=bid,
            user_id=user_id,
            briefing_type=briefing_type,
            title=title,
            content=content,
            source_chunks=source_chunks,
            source_entities=entities,
            trigger_context=trigger_context,
            generated_at=now,
            expires_at=expires_at,
            is_new=True,
        )

    async def regenerate(
        self,
        briefing_id: uuid.UUID,
        user_id: uuid.UUID,
        briefing_type: BriefingType,
        title: str,
        content: str,
        source_chunks: list[uuid.UUID],
        source_entities: list[uuid.UUID] | None = None,
        trigger_context: dict[str, Any] | None = None,
    ) -> PersistedBriefing:
        """Regenerate an existing briefing (delete + create with same ID).

        Parameters
        ----------
        briefing_id:
            ID of the briefing to regenerate.
        user_id:
            Owner (must match for tenant isolation).
        Other params:
            Same as `save()`.

        Returns
        -------
        PersistedBriefing
            The regenerated briefing.
        """
        # Delete existing with tenant isolation
        await self._session.execute(
            delete(BriefingORM).where(
                BriefingORM.id == briefing_id,
                BriefingORM.user_id == user_id,
            )
        )

        return await self.save(
            user_id=user_id,
            briefing_type=briefing_type,
            title=title,
            content=content,
            source_chunks=source_chunks,
            source_entities=source_entities,
            trigger_context=trigger_context,
            briefing_id=briefing_id,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        briefing_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PersistedBriefing | None:
        """Get a briefing by ID (tenant-isolated).

        Parameters
        ----------
        briefing_id:
            Briefing UUID.
        user_id:
            Owner UUID (mandatory filter).

        Returns
        -------
        PersistedBriefing or None
        """
        stmt = select(BriefingORM).where(
            BriefingORM.id == briefing_id,
            BriefingORM.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_persisted(row)

    async def get_latest(
        self,
        user_id: uuid.UUID,
        briefing_type: BriefingType | None = None,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[PersistedBriefing]:
        """Get latest briefings for a user.

        Parameters
        ----------
        user_id:
            Owner UUID.
        briefing_type:
            Optional filter by type.
        limit:
            Maximum results (default 10, max 50).
        include_expired:
            Whether to include expired briefings.

        Returns
        -------
        list[PersistedBriefing]
        """
        limit = min(limit, 50)
        stmt = select(BriefingORM).where(BriefingORM.user_id == user_id)

        if briefing_type is not None:
            stmt = stmt.where(BriefingORM.briefing_type == briefing_type.value)

        if not include_expired:
            now = datetime.now(timezone.utc)
            stmt = stmt.where(
                (BriefingORM.expires_at.is_(None))
                | (BriefingORM.expires_at > now)
            )

        stmt = stmt.order_by(BriefingORM.generated_at.desc()).limit(limit)

        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_persisted(r) for r in rows]

    async def delete_expired(self, user_id: uuid.UUID) -> int:
        """Delete expired briefings for a user.

        Returns the count of deleted briefings.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            delete(BriefingORM)
            .where(
                BriefingORM.user_id == user_id,
                BriefingORM.expires_at.isnot(None),
                BriefingORM.expires_at <= now,
            )
            .returning(BriefingORM.id)
        )
        result = await self._session.execute(stmt)
        count = len(result.all())
        logger.info("Deleted %d expired briefings for user %s", count, user_id)
        return count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calculate_expiry(
        self,
        briefing_type: BriefingType,
        now: datetime,
    ) -> datetime:
        """Calculate expiry timestamp based on briefing type."""
        if briefing_type == BriefingType.MORNING:
            return now + timedelta(hours=self._config.morning_expiry_hours)
        elif briefing_type == BriefingType.MEETING_PREP:
            return now + timedelta(hours=self._config.meeting_expiry_hours)
        # Fallback: 24h for unknown types
        return now + timedelta(hours=24)

    @staticmethod
    def _to_persisted(row: BriefingORM) -> PersistedBriefing:
        """Convert ORM model to dataclass."""
        # Parse briefing_type safely
        try:
            bt = BriefingType(row.briefing_type)
        except ValueError:
            bt = BriefingType.MORNING

        return PersistedBriefing(
            id=row.id,
            user_id=row.user_id,
            briefing_type=bt,
            title=row.title,
            content=row.content,
            source_chunks=row.source_chunks or [],
            source_entities=row.source_entities or [],
            trigger_context=row.trigger_context,
            generated_at=row.generated_at,
            expires_at=row.expires_at,
            is_new=False,
        )
