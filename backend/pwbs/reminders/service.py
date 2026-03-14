"""Reminder service -- Follow-up detection and trigger engine (TASK-131).

Provides:
1. Follow-up detection: extract follow-up commitments from document content
   using pattern matching and keywords.
2. Trigger engine: daily check for overdue follow-ups, inactive topics
   (>30 days without mention), and open questions without answers.
3. CRUD operations for reminders.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select

from pwbs.models.reminder import Reminder
from pwbs.schemas.enums import ReminderStatus, ReminderType, Urgency

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Follow-up detection patterns
# ---------------------------------------------------------------------------

_FOLLOWUP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:ich|wir)\s+(?:schicke?|sende?|liefere?|mache?|erledige?|"
        r"bereite?\s+vor|klaere?|pruefe?)\s+.*?(?:bis|morgen|naechste\s+woche|"
        r"montag|dienstag|mittwoch|donnerstag|freitag|heute)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:bis|deadline|faellig|due)\s*:?\s*\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:action\s+item|todo|to-do|follow[- ]?up)\s*:?\s+.{5,}",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:i(?:'ll| will)|we(?:'ll| will))\s+(?:send|deliver|prepare|check|"
        r"review|follow up|get back)\s+.*?(?:by|tomorrow|next week|monday|"
        r"tuesday|wednesday|thursday|friday|today|end of)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:bitte|please)\s+(?:bis|by)\s+\w+\s+(?:erledigen|liefern|senden|"
        r"fertigstellen|submit|complete|deliver)",
        re.IGNORECASE,
    ),
]

_QUESTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:offene?\s+frage|open\s+question|ungeklaert|noch\s+zu\s+klaeren"
        r"|to\s+be\s+determined|tbd)\s*:?\s+.{5,}",
        re.IGNORECASE,
    ),
]


def extract_followups(content: str) -> list[dict[str, str]]:
    """Extract follow-up commitments from document content.

    Returns a list of dicts with keys: ``text``, ``type``.
    """
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for pattern in _FOLLOWUP_PATTERNS:
        for match in pattern.finditer(content):
            text = match.group(0).strip()[:200]
            if text.lower() not in seen:
                seen.add(text.lower())
                results.append({"text": text, "type": ReminderType.FOLLOW_UP.value})

    for pattern in _QUESTION_PATTERNS:
        for match in pattern.finditer(content):
            text = match.group(0).strip()[:200]
            if text.lower() not in seen:
                seen.add(text.lower())
                results.append({"text": text, "type": ReminderType.OPEN_QUESTION.value})

    return results


# ---------------------------------------------------------------------------
# Reminder CRUD
# ---------------------------------------------------------------------------


async def create_reminder(
    db: AsyncSession,
    *,
    user_id: UUID,
    reminder_type: ReminderType,
    title: str,
    description: str = "",
    urgency: Urgency = Urgency.MEDIUM,
    due_at: datetime | None = None,
    responsible_person: str | None = None,
    source_document_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> Reminder:
    """Create and persist a new reminder."""
    reminder = Reminder(
        user_id=user_id,
        reminder_type=reminder_type.value,
        title=title,
        description=description,
        status=ReminderStatus.PENDING.value,
        urgency=urgency.value,
        due_at=due_at,
        responsible_person=responsible_person,
        source_document_id=source_document_id,
        metadata=metadata or {},
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=90),
    )
    db.add(reminder)
    await db.flush()
    return reminder


async def get_pending_reminders(
    db: AsyncSession,
    *,
    user_id: UUID,
    limit: int = 50,
) -> list[Reminder]:
    """Return pending reminders for a user, sorted by urgency and due date."""
    urgency_order = func.array_position(
        func.cast(["high", "medium", "low"], type_=None),
        Reminder.urgency,
    )
    stmt = (
        select(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.status == ReminderStatus.PENDING.value,
        )
        .order_by(urgency_order, Reminder.due_at.asc().nulls_last())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_reminder_status(
    db: AsyncSession,
    *,
    reminder_id: UUID,
    user_id: UUID,
    new_status: ReminderStatus,
) -> Reminder | None:
    """Update a reminder status (acknowledge, dismiss, snooze).

    Returns the updated reminder or None if not found / not owned.
    """
    stmt = (
        select(Reminder)
        .where(
            Reminder.id == reminder_id,
            Reminder.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    reminder = result.scalar_one_or_none()
    if reminder is None:
        return None

    reminder.status = new_status.value
    if new_status in (ReminderStatus.ACKNOWLEDGED, ReminderStatus.DISMISSED):
        reminder.resolved_at = datetime.now(tz=timezone.utc)
    elif new_status == ReminderStatus.SNOOZED:
        reminder.due_at = datetime.now(tz=timezone.utc) + timedelta(days=3)
        reminder.resolved_at = None

    await db.flush()
    return reminder


# ---------------------------------------------------------------------------
# Trigger engine: daily check
# ---------------------------------------------------------------------------


async def run_trigger_engine(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> list[Reminder]:
    """Run the trigger engine for a user: check for overdue follow-ups,
    inactive topics, and generate reminders.

    Called by the daily scheduler job.
    """
    now = datetime.now(tz=timezone.utc)
    new_reminders: list[Reminder] = []

    # 1. Escalate overdue follow-ups to high urgency
    overdue_stmt = (
        select(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.status == ReminderStatus.PENDING.value,
            Reminder.reminder_type == ReminderType.FOLLOW_UP.value,
            Reminder.due_at < now,
        )
    )
    overdue_result = await db.execute(overdue_stmt)
    overdue_reminders = list(overdue_result.scalars().all())

    for reminder in overdue_reminders:
        if reminder.urgency != Urgency.HIGH.value:
            reminder.urgency = Urgency.HIGH.value
            logger.info("Escalated overdue reminder %s to HIGH", reminder.id)

    # 2. Detect inactive topics (entities not mentioned in >30 days)
    from pwbs.models.entity import Entity, EntityMention

    thirty_days_ago = now - timedelta(days=30)

    old_entities_stmt = (
        select(Entity.id, Entity.name, Entity.entity_type)
        .join(EntityMention, Entity.id == EntityMention.entity_id)
        .where(
            Entity.user_id == user_id,
            EntityMention.created_at < thirty_days_ago,
        )
        .group_by(Entity.id, Entity.name, Entity.entity_type)
    )
    old_result = await db.execute(old_entities_stmt)
    old_entities = {row.id: (row.name, row.entity_type) for row in old_result.all()}

    if old_entities:
        recent_entities_stmt = (
            select(EntityMention.entity_id)
            .where(
                EntityMention.entity_id.in_(list(old_entities.keys())),
                EntityMention.created_at >= thirty_days_ago,
            )
            .distinct()
        )
        recent_result = await db.execute(recent_entities_stmt)
        recent_ids = {row[0] for row in recent_result.all()}

        inactive_ids = set(old_entities.keys()) - recent_ids

        # Skip entities that already have a pending reminder
        existing_stmt = (
            select(Reminder.reminder_metadata["entity_id"].as_string())
            .where(
                Reminder.user_id == user_id,
                Reminder.reminder_type == ReminderType.INACTIVE_TOPIC.value,
                Reminder.status == ReminderStatus.PENDING.value,
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing_entity_ids = {row[0] for row in existing_result.all()}

        for entity_id in inactive_ids:
            if str(entity_id) in existing_entity_ids:
                continue
            name, etype = old_entities[entity_id]
            reminder = await create_reminder(
                db,
                user_id=user_id,
                reminder_type=ReminderType.INACTIVE_TOPIC,
                title=f"Inaktives Thema: {name}",
                description=(
                    f"{name} ({etype}) wurde seit ueber 30 Tagen nicht erwaehnt."
                ),
                urgency=Urgency.LOW,
                metadata={"entity_id": str(entity_id), "entity_name": name},
            )
            new_reminders.append(reminder)

    await db.flush()
    logger.info(
        "Trigger engine for user %s: %d overdue escalated, %d new reminders",
        user_id,
        len(overdue_reminders),
        len(new_reminders),
    )
    return new_reminders