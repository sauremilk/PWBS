"""Briefing queue tasks (TASK-122, TASK-177).

Celery tasks for generating briefings for all users.
Triggered by Celery Beat schedule (morning, weekly) or on-demand.
Includes email delivery for users with email_briefing_enabled=True.
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
        # Chain email delivery (TASK-177)
        send_briefing_emails.delay("morning")
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
        # Chain email delivery (TASK-177)
        send_briefing_emails.delay("weekly")
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


# ---------------------------------------------------------------------------
# Email delivery task (TASK-177)
# ---------------------------------------------------------------------------


@app.task(
    name="pwbs.queue.tasks.briefing.send_briefing_emails",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,
    queue="briefing.generate",
    acks_late=True,
)
def send_briefing_emails(self: object, briefing_type: str = "morning") -> dict[str, object]:
    """Send briefing emails to users that have email delivery enabled.

    Called automatically after generate_morning_briefings / generate_weekly_briefings.
    Only sends to users where email_briefing_enabled=True.
    """
    start = time.monotonic()
    try:
        result = _run_async(_send_briefing_emails_async(briefing_type))
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "send_briefing_emails completed: sent=%d failed=%d duration=%.0fms",
            result["emails_sent"],
            result["emails_failed"],
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("send_briefing_emails failed: %s", exc)
        raise self.retry(exc=exc)  # type: ignore[attr-defined]


async def _send_briefing_emails_async(briefing_type: str) -> dict[str, object]:
    """Send briefing emails to users with email_briefing_enabled=True.

    Loads the most recent briefing of the given type for each user and
    dispatches it via EmailService.send_briefing_email().
    Idempotency: skips briefings where email_sent_at is already set.
    """
    from datetime import datetime, timezone

    from sqlalchemy import select, update

    from pwbs.db.postgres import get_session_factory
    from pwbs.models.briefing import Briefing
    from pwbs.models.document import Document
    from pwbs.models.user import User
    from pwbs.schemas.enums import BriefingType
    from pwbs.services.email import create_email_service

    bt_map: dict[str, BriefingType] = {
        "morning": BriefingType.MORNING,
        "meeting_prep": BriefingType.MEETING_PREP,
        "weekly": BriefingType.WEEKLY,
    }
    schema_bt = bt_map.get(briefing_type)
    if schema_bt is None:
        logger.error("Unknown briefing_type for email: %s", briefing_type)
        return {"emails_sent": 0, "emails_failed": 0, "briefing_type": briefing_type}

    factory = get_session_factory()
    sent = 0
    failed = 0

    # Fetch users who opted in to email briefings
    async with factory() as db:
        stmt = select(User).where(User.email_briefing_enabled.is_(True))
        result = await db.execute(stmt)
        users = result.scalars().all()

    if not users:
        logger.info("No users with email_briefing_enabled for %s", briefing_type)
        return {"emails_sent": 0, "emails_failed": 0, "briefing_type": briefing_type}

    email_service = create_email_service()

    for user in users:
        try:
            # Fetch latest briefing of this type for the user
            async with factory() as db:
                stmt = (
                    select(Briefing)
                    .where(
                        Briefing.user_id == user.id,
                        Briefing.briefing_type == schema_bt,
                        Briefing.email_sent_at.is_(None),
                    )
                    .order_by(Briefing.generated_at.desc())
                    .limit(1)
                )
                res = await db.execute(stmt)
                briefing = res.scalar_one_or_none()

            if briefing is None:
                logger.info(
                    "No unsent %s briefing for user_id=%s – skipping",
                    briefing_type,
                    user.id,
                )
                continue

            # Load source references from source_chunks
            sources: list[dict[str, str]] = []
            if briefing.source_chunks:
                async with factory() as db:
                    from pwbs.models.chunk import Chunk

                    chunk_stmt = (
                        select(
                            Document.title,
                            Document.source_type,
                        )
                        .join(Chunk, Chunk.document_id == Document.id)
                        .where(Chunk.id.in_(briefing.source_chunks))
                        .distinct()
                    )
                    src_result = await db.execute(chunk_stmt)
                    for row in src_result.all():
                        sources.append(
                            {
                                "title": row.title or "Unbekannt",
                                "source_type": row.source_type or "",
                            }
                        )

            briefing_url = f"/briefings/{briefing.id}"
            email_result = await email_service.send_briefing_email(
                to=user.email,
                briefing_type=briefing_type.replace("_", " ").title(),
                briefing_title=briefing.title,
                briefing_content=briefing.content,
                briefing_url=briefing_url,
                sources=sources,
            )

            if email_result.success:
                sent += 1
                # Mark as sent (idempotency guard)
                async with factory() as db:
                    await db.execute(
                        update(Briefing)
                        .where(Briefing.id == briefing.id)
                        .values(email_sent_at=datetime.now(timezone.utc))
                    )
                    await db.commit()
                logger.info(
                    "Briefing email sent: user_id=%s type=%s",
                    user.id,
                    briefing_type,
                )
            else:
                failed += 1
                logger.error(
                    "Briefing email failed: user_id=%s error=%s",
                    user.id,
                    email_result.error,
                )
        except Exception:
            failed += 1
            logger.exception(
                "Failed to send %s briefing email for user_id=%s",
                briefing_type,
                user.id,
            )

    return {
        "emails_sent": sent,
        "emails_failed": failed,
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
