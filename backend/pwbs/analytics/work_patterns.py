"""Work pattern analysis service (TASK-134).

Analyses user activity over the last N days to extract work patterns:
1. Top themes (from entity mentions)
2. Average meeting load per week
3. Preferred work hours (document creation times)
4. Decision speed (avg days from creation to status=made)

Results are persisted in the user_profiles table with versioning.
D3 Alleinstellungsmerkmal: Persoenliches Lernmodell.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.models.decision import Decision
from pwbs.models.document import Document
from pwbs.models.entity import Entity, EntityMention
from pwbs.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

__all__ = [
    "ThemeInfo",
    "WorkPatternProfile",
    "WorkPatternAnalyzer",
    "WorkPatternConfig",
]


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WorkPatternConfig:
    """Configuration for work pattern analysis.

    Attributes
    ----------
    lookback_days:
        Number of days to look back for analysis.
    top_themes_count:
        Number of top themes to extract.
    min_theme_mentions:
        Minimum mention count for a theme to be included.
    profile_expiry_days:
        DSGVO: days until profile expires.
    """

    lookback_days: int = 30
    top_themes_count: int = 5
    min_theme_mentions: int = 2
    profile_expiry_days: int = 90


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ThemeInfo:
    """A frequently encountered theme."""

    name: str
    mention_count: int
    entity_type: str


@dataclass(slots=True)
class WorkPatternProfile:
    """Extracted work patterns for a user."""

    top_themes: list[ThemeInfo] = field(default_factory=list)
    avg_meetings_per_week: float = 0.0
    preferred_hours: dict[str, Any] = field(default_factory=dict)
    decision_speed_avg_days: float | None = None
    analysis_date: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class WorkPatternAnalyzer:
    """Analyses user activity and extracts work patterns.

    All queries filter by user_id for tenant isolation.

    Parameters
    ----------
    session:
        SQLAlchemy async session.
    config:
        Analysis configuration.
    """

    def __init__(
        self,
        session: AsyncSession,
        config: WorkPatternConfig | None = None,
    ) -> None:
        self._session = session
        self._config = config or WorkPatternConfig()

    @property
    def config(self) -> WorkPatternConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(self, user_id: UUID) -> WorkPatternProfile:
        """Run full analysis and return a WorkPatternProfile."""
        themes = await self.extract_top_themes(user_id)
        meeting_load = await self.extract_meeting_load(user_id)
        hours = await self.extract_preferred_hours(user_id)
        speed = await self.extract_decision_speed(user_id)

        return WorkPatternProfile(
            top_themes=themes,
            avg_meetings_per_week=meeting_load,
            preferred_hours=hours,
            decision_speed_avg_days=speed,
        )

    async def analyze_and_persist(self, user_id: UUID) -> UserProfile:
        """Run analysis, persist as new versioned profile, and return it."""
        profile = await self.analyze(user_id)

        # Get next version number
        version_stmt = (
            select(func.coalesce(func.max(UserProfile.version), 0))
            .where(UserProfile.user_id == user_id)
        )
        result = await self._session.execute(version_stmt)
        current_max = result.scalar_one()
        next_version = current_max + 1

        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=self._config.profile_expiry_days
        )

        db_profile = UserProfile(
            user_id=user_id,
            version=next_version,
            analysis_date=profile.analysis_date,
            top_themes=[
                {"name": t.name, "mention_count": t.mention_count, "type": t.entity_type}
                for t in profile.top_themes
            ],
            avg_meetings_per_week=profile.avg_meetings_per_week,
            preferred_hours=profile.preferred_hours,
            decision_speed_avg_days=profile.decision_speed_avg_days,
            expires_at=expires_at,
        )
        self._session.add(db_profile)
        await self._session.flush()
        return db_profile

    # ------------------------------------------------------------------
    # Theme extraction
    # ------------------------------------------------------------------

    async def extract_top_themes(self, user_id: UUID) -> list[ThemeInfo]:
        """Extract most frequently mentioned entities in the lookback period."""
        since = datetime.now(tz=timezone.utc) - timedelta(
            days=self._config.lookback_days
        )

        stmt = (
            select(
                Entity.name,
                Entity.entity_type,
                func.count(EntityMention.entity_id).label("mention_count"),
            )
            .join(EntityMention, Entity.id == EntityMention.entity_id)
            .where(
                Entity.user_id == user_id,
                Entity.last_seen >= since,
            )
            .group_by(Entity.name, Entity.entity_type)
            .having(func.count(EntityMention.entity_id) >= self._config.min_theme_mentions)
            .order_by(func.count(EntityMention.entity_id).desc())
            .limit(self._config.top_themes_count)
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            ThemeInfo(
                name=row.name,
                mention_count=row.mention_count,
                entity_type=row.entity_type,
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Meeting load
    # ------------------------------------------------------------------

    async def extract_meeting_load(self, user_id: UUID) -> float:
        """Calculate average meetings per week in the lookback period."""
        since = datetime.now(tz=timezone.utc) - timedelta(
            days=self._config.lookback_days
        )

        stmt = (
            select(func.count(Document.id))
            .where(
                Document.user_id == user_id,
                Document.source_type.in_(["google_calendar", "zoom_transcript"]),
                Document.created_at >= since,
            )
        )

        result = await self._session.execute(stmt)
        total_meetings = result.scalar_one()

        weeks = max(1.0, self._config.lookback_days / 7.0)
        return round(total_meetings / weeks, 1)

    # ------------------------------------------------------------------
    # Preferred hours
    # ------------------------------------------------------------------

    async def extract_preferred_hours(self, user_id: UUID) -> dict[str, Any]:
        """Analyse document creation times to find preferred work hours."""
        since = datetime.now(tz=timezone.utc) - timedelta(
            days=self._config.lookback_days
        )

        stmt = (
            select(
                func.extract("hour", Document.created_at).label("hour"),
                func.count(Document.id).label("doc_count"),
            )
            .where(
                Document.user_id == user_id,
                Document.created_at >= since,
            )
            .group_by(func.extract("hour", Document.created_at))
            .order_by(func.extract("hour", Document.created_at))
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        hour_counts: dict[int, int] = {}
        for row in rows:
            hour_counts[int(row.hour)] = row.doc_count

        if not hour_counts:
            return {"hours": {}, "peak_start": None, "peak_end": None}

        # Find peak window (3-hour window with most activity)
        best_start = 0
        best_count = 0
        for start_hour in range(24):
            window_count = sum(
                hour_counts.get((start_hour + h) % 24, 0) for h in range(3)
            )
            if window_count > best_count:
                best_count = window_count
                best_start = start_hour

        return {
            "hours": {str(k): v for k, v in sorted(hour_counts.items())},
            "peak_start": best_start,
            "peak_end": (best_start + 3) % 24,
        }

    # ------------------------------------------------------------------
    # Decision speed
    # ------------------------------------------------------------------

    async def extract_decision_speed(self, user_id: UUID) -> float | None:
        """Calculate average days from decision creation to resolution."""
        since = datetime.now(tz=timezone.utc) - timedelta(
            days=self._config.lookback_days
        )

        stmt = (
            select(
                Decision.created_at,
                Decision.decided_at,
            )
            .where(
                Decision.user_id == user_id,
                Decision.status == "made",
                Decision.decided_at.is_not(None),
                Decision.created_at >= since,
            )
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        if not rows:
            return None

        total_days = 0.0
        count = 0
        for row in rows:
            if row.decided_at and row.created_at:
                delta = row.decided_at - row.created_at
                total_days += delta.total_seconds() / 86400.0
                count += 1

        if count == 0:
            return None

        return round(total_days / count, 1)
