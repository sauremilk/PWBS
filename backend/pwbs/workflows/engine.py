"""Workflow engine: evaluates triggers and executes actions (TASK-160).

The engine is called when events occur (document ingested, schedule fires)
and evaluates all active rules for the affected user.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, update

from pwbs.workflows.models import WorkflowExecution, WorkflowRule

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Trigger evaluation ────────────────────────────────────────────


def evaluate_new_document_trigger(
    trigger_config: dict[str, object],
    event_data: dict[str, object],
) -> bool:
    """Check if a 'new_document' trigger matches the event."""
    source_types = trigger_config.get("source_types")
    if source_types is None:
        return True
    doc_source = event_data.get("source_type", "")
    return str(doc_source) in list(source_types)  # type: ignore[arg-type]


def evaluate_keyword_trigger(
    trigger_config: dict[str, object],
    event_data: dict[str, object],
) -> bool:
    """Check if a 'keyword_match' trigger matches the event content."""
    keywords: list[str] = list(trigger_config.get("keywords", []))  # type: ignore[arg-type]
    if not keywords:
        return False

    content = str(event_data.get("content", "")).lower()
    title = str(event_data.get("title", "")).lower()
    search_text = f"{title} {content}"

    match_all = bool(trigger_config.get("match_all", False))
    matches = [bool(re.search(re.escape(kw.lower()), search_text)) for kw in keywords]

    if match_all:
        return all(matches)
    return any(matches)


def evaluate_schedule_trigger(
    trigger_config: dict[str, object],
    event_data: dict[str, object],
) -> bool:
    """Schedule triggers always match when fired by the scheduler."""
    return event_data.get("event_type") == "schedule"


_TRIGGER_EVALUATORS = {
    "new_document": evaluate_new_document_trigger,
    "keyword_match": evaluate_keyword_trigger,
    "schedule": evaluate_schedule_trigger,
}


# ── Action execution ─────────────────────────────────────────────


async def execute_email_action(
    action_config: dict[str, object],
    event_data: dict[str, object],
    user_id: UUID,
    db: AsyncSession,
) -> dict[str, object]:
    """Execute an email action (logs intent; actual sending via email service)."""
    subject = str(action_config.get("subject_template", ""))
    body = str(action_config.get("body_template", ""))

    logger.info("Workflow email action: user=%s subject=%s", user_id, subject)
    return {
        "action": "email",
        "subject": subject,
        "body_preview": body[:100],
        "status": "queued",
    }


async def execute_create_reminder_action(
    action_config: dict[str, object],
    event_data: dict[str, object],
    user_id: UUID,
    db: AsyncSession,
) -> dict[str, object]:
    """Create a reminder as the action result."""
    from pwbs.models.reminder import Reminder

    title = str(action_config.get("title_template", "Workflow-Erinnerung"))
    urgency = str(action_config.get("urgency", "medium"))

    reminder = Reminder(
        user_id=user_id,
        reminder_type="workflow",
        title=title,
        description=(
            "Automatisch erstellt durch Workflow-Regel."
            f" Event: {event_data.get('event_type', 'unknown')}"
        ),
        urgency=urgency,
        status="pending",
        reminder_metadata={"workflow_event": event_data},
    )
    db.add(reminder)
    await db.flush()

    return {
        "action": "create_reminder",
        "reminder_id": str(reminder.id),
        "title": title,
        "status": "created",
    }


async def execute_generate_briefing_action(
    action_config: dict[str, object],
    event_data: dict[str, object],
    user_id: UUID,
    db: AsyncSession,
) -> dict[str, object]:
    """Queue a briefing generation (logs intent)."""
    briefing_type = str(action_config.get("briefing_type", "project"))

    logger.info("Workflow briefing action: user=%s type=%s", user_id, briefing_type)
    return {
        "action": "generate_briefing",
        "briefing_type": briefing_type,
        "status": "queued",
    }


_ACTION_EXECUTORS = {
    "email": execute_email_action,
    "create_reminder": execute_create_reminder_action,
    "generate_briefing": execute_generate_briefing_action,
}


# ── Main engine ──────────────────────────────────────────────────


async def evaluate_rules_for_event(
    db: AsyncSession,
    *,
    user_id: UUID,
    event_type: str,
    event_data: dict[str, object],
) -> list[WorkflowExecution]:
    """Evaluate all active rules for a user against an event.

    Parameters
    ----------
    db:
        Database session.
    user_id:
        The user whose rules to evaluate.
    event_type:
        Event type (e.g. 'new_document', 'keyword_match', 'schedule').
    event_data:
        Event payload for trigger evaluation.

    Returns
    -------
    list[WorkflowExecution]
        List of execution log entries created.
    """
    stmt = select(WorkflowRule).where(
        WorkflowRule.user_id == user_id,
        WorkflowRule.is_active.is_(True),
    )
    result = await db.execute(stmt)
    rules = result.scalars().all()

    executions: list[WorkflowExecution] = []

    enriched_event = {**event_data, "event_type": event_type}

    for rule in rules:
        trigger_type = rule.trigger_config.get("type", "")
        evaluator = _TRIGGER_EVALUATORS.get(trigger_type)
        if evaluator is None:
            continue

        if not evaluator(rule.trigger_config, enriched_event):
            continue

        # Trigger matched → execute action
        action_type = rule.action_config.get("type", "")
        executor = _ACTION_EXECUTORS.get(action_type)

        if executor is None:
            action_result = "failed"
            action_data: dict[str, object] = {"error": f"Unknown action type: {action_type}"}
        else:
            try:
                action_data = await executor(rule.action_config, enriched_event, user_id, db)
                action_result = "success"
            except Exception as exc:
                logger.exception(
                    "Workflow action failed: rule=%s action=%s",
                    rule.id,
                    action_type,
                )
                action_result = "failed"
                action_data = {"error": str(exc)}

        execution = WorkflowExecution(
            rule_id=rule.id,
            user_id=user_id,
            trigger_event=event_type,
            trigger_data=enriched_event,
            action_result=action_result,
            action_data=action_data,
        )
        db.add(execution)

        # Increment execution count
        await db.execute(
            update(WorkflowRule)
            .where(WorkflowRule.id == rule.id)
            .values(execution_count=WorkflowRule.execution_count + 1)
        )

        executions.append(execution)

    return executions
