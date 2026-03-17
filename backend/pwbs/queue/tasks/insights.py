"""Proactive Insight generation queue task (TASK-158).

Celery task for generating proactive insights for all users
with enabled insight preferences. Triggered by Celery Beat (daily).
"""

from __future__ import annotations

import asyncio
import logging
import time

from pwbs.queue.celery_app import app

logger = logging.getLogger(__name__)


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(
    name="pwbs.queue.tasks.insights.generate_proactive_insights",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,
    queue="briefing.generate",
    acks_late=True,
)
def generate_proactive_insights(self: object) -> dict[str, object]:
    """Generate proactive insights for all eligible users.

    Iterates all users with insight frequency != 'off' and generates
    personalized insights based on their Knowledge Graph patterns.
    """
    start = time.monotonic()
    try:
        result = _run_async(_generate_insights_async())
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "generate_proactive_insights completed: users=%d insights=%d duration=%.0fms",
            result["users_processed"],
            result["insights_generated"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("generate_proactive_insights failed: %s", exc)
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


async def _generate_insights_async() -> dict[str, object]:
    """Core async logic for insight generation across all users."""
    from sqlalchemy import select

    from pwbs.core.llm_gateway import LLMConfig, LLMGateway
    from pwbs.db.postgres import get_session_factory
    from pwbs.graph.pattern_recognition import (
        NullPatternGraphService,
        PatternRecognitionService,
    )
    from pwbs.insights.generator import (
        InsightGeneratorConfig,
        ProactiveInsightGenerator,
    )
    from pwbs.insights.persistence import (
        get_negative_entity_ids,
        get_preferences,
        persist_insights,
    )
    from pwbs.models.user import User

    factory = get_session_factory()
    users_processed = 0
    total_insights = 0

    # Build shared services
    llm_gateway = LLMGateway(LLMConfig())
    graph_session = NullPatternGraphService()
    pattern_service = PatternRecognitionService(graph_session)
    generator = ProactiveInsightGenerator(pattern_service, llm_gateway)

    # Fetch all users
    async with factory() as db:
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()

    for user in users:
        try:
            async with factory() as db:
                # Load preferences
                prefs = await get_preferences(db, user.id)

                # Skip users who opted out or have no prefs
                if prefs is None:
                    continue
                if prefs.frequency == "off":
                    continue

                # Get suppressed entities from negative feedback
                negatives = await get_negative_entity_ids(
                    db,
                    user.id,
                    within_days=InsightGeneratorConfig().exclude_recently_rated_days,
                )

                # Generate insights
                insights = await generator.generate(
                    owner_id=user.id,
                    enabled_categories=prefs.enabled_categories,
                    max_insights=prefs.max_insights_per_run,
                    negative_entity_ids=negatives,
                )

                if insights:
                    await persist_insights(db, user.id, insights)
                    await db.commit()
                    total_insights += len(insights)

                users_processed += 1
        except Exception:
            logger.exception("Failed to generate insights for user_id=%s", user.id)

    return {
        "users_processed": users_processed,
        "insights_generated": total_insights,
    }
