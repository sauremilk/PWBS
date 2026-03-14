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
    """Generate briefings for all active users.

    Wires through to BriefingGenerator + BriefingPersistenceService for
    actual LLM-based generation with source references.
    """
    from sqlalchemy import select

    from pwbs.briefing.generator import BriefingGenerator
    from pwbs.briefing.generator import BriefingType as GenBriefingType
    from pwbs.briefing.persistence import BriefingPersistenceService
    from pwbs.core.llm_gateway import LLMGateway
    from pwbs.db.postgres import get_session_factory
    from pwbs.models.user import User
    from pwbs.prompts.registry import PromptRegistry
    from pwbs.schemas.enums import BriefingType

    factory = get_session_factory()
    processed = 0
    failed = 0

    # Map string type to enum
    bt_map: dict[str, BriefingType] = {
        "morning": BriefingType.MORNING,
        "weekly": BriefingType.WEEKLY,
    }
    gen_bt_map: dict[str, GenBriefingType] = {
        "morning": GenBriefingType.MORNING,
        "weekly": GenBriefingType.WEEKLY,
    }

    schema_bt = bt_map.get(briefing_type)
    gen_bt = gen_bt_map.get(briefing_type)
    if schema_bt is None or gen_bt is None:
        logger.error("Unknown briefing_type: %s", briefing_type)
        return {"users_processed": 0, "briefing_type": briefing_type}

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

            async with factory() as db:
                # Build context depending on briefing type
                context: dict[str, object] = {}

                if briefing_type == "weekly":
                    from pwbs.briefing.weekly_context import (
                        NullWeeklyGraphService,
                        WeeklyContextAssembler,
                    )
                    from pwbs.search.service import SemanticSearchService

                    search_svc = SemanticSearchService(db)
                    assembler = WeeklyContextAssembler(
                        session=db,
                        search_service=search_svc,
                        graph_service=NullWeeklyGraphService(),
                    )
                    weekly_ctx = await assembler.assemble(user_id=user.id)
                    context = {
                        "week_start": weekly_ctx.week_start,
                        "week_end": weekly_ctx.week_end,
                        "top_topics": weekly_ctx.top_topics,
                        "decisions": weekly_ctx.decisions,
                        "project_progress": weekly_ctx.project_progress,
                        "open_items": weekly_ctx.open_items,
                        "recent_documents": weekly_ctx.recent_documents,
                    }

                # Generate via LLM
                llm = LLMGateway()
                registry = PromptRegistry()
                generator = BriefingGenerator(llm, registry)

                llm_result = await generator.generate(
                    briefing_type=gen_bt,
                    context=context,
                    user_id=user.id,
                )

                # Persist
                persistence = BriefingPersistenceService(db)
                await persistence.save(
                    user_id=user.id,
                    briefing_type=schema_bt,
                    title=f"{briefing_type.replace('_', ' ').title()} Briefing",
                    content=llm_result.content,
                    source_chunks=[],
                    trigger_context={"scheduled": True, "type": briefing_type},
                )
                await db.commit()

            processed += 1
        except Exception:
            failed += 1
            logger.exception(
                "Failed to generate %s briefing for user_id=%s",
                briefing_type,
                user.id,
            )

    return {
        "users_processed": processed,
        "failed": failed,
        "briefing_type": briefing_type,
    }


@app.task(
    name="pwbs.queue.tasks.briefing.run_daily_reminder_triggers",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,
    queue="briefing.generate",
    acks_late=True,
)
def run_daily_reminder_triggers(self: object) -> dict[str, object]:
    """Run the reminder trigger engine for all users (daily)."""
    start = time.monotonic()
    try:
        result = _run_async(_run_triggers_async())
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "run_daily_reminder_triggers completed: users=%d new_reminders=%d duration=%.0fms",
            result["users_processed"],
            result["total_new_reminders"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("run_daily_reminder_triggers failed: %s", exc)
        raise self.retry(exc=exc)  # type: ignore[attr-defined]


async def _run_triggers_async() -> dict[str, object]:
    """Run reminder trigger engine for all active users."""
    from sqlalchemy import select

    from pwbs.db.postgres import get_session_factory
    from pwbs.models.user import User
    from pwbs.reminders.service import run_trigger_engine

    factory = get_session_factory()
    processed = 0
    total_new = 0

    async with factory() as db:
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()

    for user in users:
        try:
            async with factory() as db:
                new_reminders = await run_trigger_engine(db, user_id=user.id)
                await db.commit()
                total_new += len(new_reminders)
            processed += 1
        except Exception:
            logger.exception("Failed to run trigger engine for user_id=%s", user.id)

    return {"users_processed": processed, "total_new_reminders": total_new}
