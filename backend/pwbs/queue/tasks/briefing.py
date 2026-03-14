"""Briefing queue tasks (TASK-121 stubs, TASK-122 will implement fully)."""

from __future__ import annotations

from pwbs.queue.celery_app import app


@app.task(
    name="pwbs.queue.tasks.briefing.generate_morning_briefings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=60,
    queue="briefing.generate",
)
def generate_morning_briefings(self: object) -> dict[str, str]:
    """Generate morning briefings for all users."""
    raise NotImplementedError("TASK-122: Queue-Worker-Migration ausstehend")


@app.task(
    name="pwbs.queue.tasks.briefing.generate_weekly_briefings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=60,
    queue="briefing.generate",
)
def generate_weekly_briefings(self: object) -> dict[str, str]:
    """Generate weekly briefings for all users."""
    raise NotImplementedError("TASK-122: Queue-Worker-Migration ausstehend")
