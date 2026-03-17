"""Insight persistence layer (TASK-158).

CRUD operations for ProactiveInsight and InsightPreferences.
All queries filter by owner_id for tenant isolation.
Writes use upsert pattern for idempotency.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.insights.generator import InsightResult
from pwbs.models.proactive_insight import InsightPreferences, ProactiveInsight

logger = logging.getLogger(__name__)

__all__ = [
    "get_negative_entity_ids",
    "get_preferences",
    "get_recent_insights",
    "persist_insights",
    "submit_feedback",
    "upsert_preferences",
]

# DSGVO: default expiry for insights
_DEFAULT_EXPIRY_DAYS = 90


async def get_preferences(
    db: AsyncSession,
    owner_id: UUID,
) -> InsightPreferences | None:
    """Load insight preferences for a user. Returns None if not configured."""
    stmt = select(InsightPreferences).where(InsightPreferences.owner_id == owner_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_preferences(
    db: AsyncSession,
    owner_id: UUID,
    frequency: str,
    enabled_categories: list[str],
    max_insights_per_run: int = 3,
) -> InsightPreferences:
    """Create or update insight preferences (idempotent upsert)."""
    stmt = (
        pg_insert(InsightPreferences)
        .values(
            owner_id=owner_id,
            frequency=frequency,
            enabled_categories=enabled_categories,
            max_insights_per_run=max_insights_per_run,
        )
        .on_conflict_on_constraint("uq_insight_prefs_owner")  # type: ignore[union-attr]
        .do_update(
            set_={
                "frequency": frequency,
                "enabled_categories": enabled_categories,
                "max_insights_per_run": max_insights_per_run,
                "updated_at": datetime.now(UTC),
            }
        )
        .returning(InsightPreferences)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def persist_insights(
    db: AsyncSession,
    owner_id: UUID,
    insights: list[InsightResult],
) -> list[ProactiveInsight]:
    """Persist generated insights to the database."""
    expires_at = datetime.now(UTC) + timedelta(days=_DEFAULT_EXPIRY_DAYS)
    rows: list[ProactiveInsight] = []

    for insight in insights:
        sources_json = [asdict(s) for s in insight.sources]
        row = ProactiveInsight(
            owner_id=owner_id,
            category=insight.category,
            title=insight.title,
            content=insight.content,
            sources=sources_json,
            pattern_data=insight.pattern_data,
            expires_at=expires_at,
        )
        db.add(row)
        rows.append(row)

    await db.flush()
    return rows


async def get_recent_insights(
    db: AsyncSession,
    owner_id: UUID,
    limit: int = 10,
) -> list[ProactiveInsight]:
    """Fetch recent insights for a user, newest first."""
    stmt = (
        select(ProactiveInsight)
        .where(ProactiveInsight.owner_id == owner_id)
        .order_by(ProactiveInsight.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def submit_feedback(
    db: AsyncSession,
    owner_id: UUID,
    insight_id: UUID,
    rating: str,
) -> bool:
    """Submit feedback for an insight. Returns True if updated."""
    stmt = (
        update(ProactiveInsight)
        .where(
            ProactiveInsight.id == insight_id,
            ProactiveInsight.owner_id == owner_id,
        )
        .values(
            feedback_rating=rating,
            feedback_at=datetime.now(UTC),
        )
    )
    result = await db.execute(stmt)
    return result.rowcount > 0  # type: ignore[union-attr]


async def get_negative_entity_ids(
    db: AsyncSession,
    owner_id: UUID,
    within_days: int = 30,
) -> frozenset[str]:
    """Get entity IDs the user rated 'not_helpful' within N days.

    Used to suppress patterns in future insight generation.
    """
    cutoff = datetime.now(UTC) - timedelta(days=within_days)
    stmt = select(ProactiveInsight.pattern_data).where(
        ProactiveInsight.owner_id == owner_id,
        ProactiveInsight.feedback_rating == "not_helpful",
        ProactiveInsight.feedback_at >= cutoff,
        ProactiveInsight.pattern_data.isnot(None),
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    entity_ids: set[str] = set()
    for data in rows:
        if isinstance(data, dict) and data.get("entity_id"):
            entity_ids.add(data["entity_id"])

    return frozenset(entity_ids)
