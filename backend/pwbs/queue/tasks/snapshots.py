"""Weekly Knowledge Snapshot queue task (TASK-162).

Celery task for creating automatic weekly snapshots for all users.
Triggered by Celery Beat (weekly, configurable per user).
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
    name="pwbs.queue.tasks.snapshots.create_weekly_snapshots",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=300,
    queue="briefing.generate",
    acks_late=True,
)
def create_weekly_snapshots(self: object) -> dict[str, object]:
    """Create weekly knowledge snapshots for all active users.

    This task iterates all users and creates an automatic weekly
    snapshot of their knowledge graph state.
    """
    start = time.monotonic()
    try:
        result = _run_async(_create_snapshots_async())
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "create_weekly_snapshots completed: users=%d snapshots=%d duration=%.0fms",
            result["users_processed"],
            result["snapshots_created"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("create_weekly_snapshots failed: %s", exc)
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


async def _create_snapshots_async() -> dict[str, object]:
    """Core async logic for weekly snapshot creation across all users."""
    from sqlalchemy import select

    from pwbs.db.postgres import get_session_factory
    from pwbs.models.user import User
    from pwbs.snapshots.service import capture_snapshot

    session_factory = get_session_factory()
    users_processed = 0
    snapshots_created = 0

    async with session_factory() as db:
        stmt = select(User.id)
        result = await db.execute(stmt)
        user_ids = [row[0] for row in result.all()]

    for user_id in user_ids:
        try:
            async with session_factory() as db:
                await capture_snapshot(
                    db,
                    user_id=user_id,
                    label="Automatischer Wochen-Snapshot",
                    trigger="weekly_auto",
                )
                await db.commit()
                snapshots_created += 1
        except Exception:
            logger.exception("Failed to create snapshot for user %s", user_id)
        users_processed += 1

    return {
        "users_processed": users_processed,
        "snapshots_created": snapshots_created,
    }
