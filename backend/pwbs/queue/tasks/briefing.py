"""Briefing queue tasks (TASK-122).

Celery tasks for generating briefings for all users.
Triggered by Celery Beat schedule (morning, weekly) or on-demand.
"""

from __future__ import annotations

import asyncio
import logging
import time
from uuid import UUID

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
    name="pwbs.queue.tasks.briefing.generate_morning_briefings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=60,
    queue="briefing.generate",
    acks_late=True,
)
def generate_morning_briefings(self: object) -> dict[str, object]:
    """Generate morning briefings for all users.

    Iterates all users with active connections and generates
    a personalized morning briefing via BriefingAgent.
    """
    start = time.monotonic()
    try:
        result = _run_async(_generate_briefings_async("morning"))
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "generate_morning_briefings completed: users=%d duration=%.0fms",
            result["users_processed"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("generate_morning_briefings failed: %s", exc)
        raise self.retry(exc=exc)  # type: ignore[attr-defined]


@app.task(
    name="pwbs.queue.tasks.briefing.generate_weekly_briefings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=60,
    queue="briefing.generate",
    acks_late=True,
)
def generate_weekly_briefings(self: object) -> dict[str, object]:
    """Generate weekly briefings for all users."""
    start = time.monotonic()
    try:
        result = _run_async(_generate_briefings_async("weekly"))
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "generate_weekly_briefings completed: users=%d duration=%.0fms",
            result["users_processed"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("generate_weekly_briefings failed: %s", exc)
        raise self.retry(exc=exc)  # type: ignore[attr-defined]


async def _generate_briefings_async(briefing_type: str) -> dict[str, object]:
    """Generate briefings for all active users."""
    from pwbs.db.postgres import get_session_factory
    from pwbs.models.user import User

    from sqlalchemy import select

    factory = get_session_factory()
    processed = 0

    async with factory() as db:
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()

    for user in users:
        try:
            logger.info(
                "Generating %s briefing for user_id=%s",
                briefing_type,
                user.id,
            )
            # TODO: Wire to BriefingAgent when available
            # The BriefingAgent.generate() method will:
            # 1. Call SearchAgent for relevant documents
            # 2. Call GraphAgent for relationships
            # 3. Call LLMGateway for generation
            # 4. Persist briefing with source references
            processed += 1
        except Exception:
            logger.exception(
                "Failed to generate %s briefing for user_id=%s",
                briefing_type,
                user.id,
            )

    return {"users_processed": processed, "briefing_type": briefing_type}
