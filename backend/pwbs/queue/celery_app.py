"""Celery application instance and configuration (TASK-121).

Central Celery app that all workers and task modules import from.
Configured with Redis broker, five dedicated queues, retry policies
and structured logging.

Usage:
    # Start worker for specific queues:
    celery -A pwbs.queue.celery_app worker -Q ingestion.high,ingestion.bulk -c 4

    # Start beat scheduler:
    celery -A pwbs.queue.celery_app beat
"""

from __future__ import annotations

import os

from celery import Celery
from kombu import Exchange, Queue

from pwbs.queue.config import ALL_QUEUE_NAMES, PRIORITY_MAP, QUEUE_TOPOLOGY

# Broker URL: prefer CELERY_BROKER_URL, fall back to REDIS_URL
_broker_url = os.environ.get(
    "CELERY_BROKER_URL",
    os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)
# Result backend: use a separate Redis DB to avoid key collisions
_result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND",
    _broker_url.rsplit("/", 1)[0] + "/1",
)

app = Celery("pwbs")

# -- Broker & Result Backend --
app.conf.broker_url = _broker_url
app.conf.result_backend = _result_backend
app.conf.broker_connection_retry_on_startup = True

# -- Serialization (JSON only, no pickle for security) --
app.conf.accept_content = ["json"]
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"

# -- Queue definitions --
_default_exchange = Exchange("default", type="direct")

app.conf.task_queues = tuple(
    Queue(
        name=qcfg.name,
        exchange=_default_exchange,
        routing_key=qcfg.name,
    )
    for qcfg in QUEUE_TOPOLOGY.values()
)

app.conf.task_default_queue = "ingestion.high"
app.conf.task_default_exchange = "default"
app.conf.task_default_routing_key = "ingestion.high"

# -- Task routes (auto-route based on task name prefix) --
app.conf.task_routes = {
    "pwbs.queue.tasks.ingestion.*": {"queue": "ingestion.high"},
    "pwbs.queue.tasks.ingestion_bulk.*": {"queue": "ingestion.bulk"},
    "pwbs.queue.tasks.embedding.*": {"queue": "processing.embed"},
    "pwbs.queue.tasks.extraction.*": {"queue": "processing.extract"},
    "pwbs.queue.tasks.briefing.*": {"queue": "briefing.generate"},
}

# -- Retry defaults (Exponential Backoff: 60s -> 300s -> 1500s) --
app.conf.task_default_retry_delay = 60
app.conf.task_max_retries = 3

# -- Soft time limits per queue (applied via task decorator, not global) --
# Global hard limit as safety net (1 hour + 60s grace)
app.conf.task_time_limit = 3660
app.conf.task_soft_time_limit = 3600

# -- Worker settings --
app.conf.worker_prefetch_multiplier = 1  # fair scheduling
app.conf.worker_max_tasks_per_child = 1000  # prevent memory leaks

# -- Priority support --
app.conf.broker_transport_options = {
    "priority_steps": list(range(10)),
    "sep": ":",
    "queue_order_strategy": "priority",
}

# -- Task result expiry (24h) --
app.conf.result_expires = 86400

# -- Beat schedule (Celery Beat for cron-based scheduling) --
app.conf.beat_schedule = {
    "morning-briefing": {
        "task": "pwbs.queue.tasks.briefing.generate_morning_briefings",
        "schedule": {
            "__type__": "crontab",
            "minute": "30",
            "hour": "6",
        },
        "options": {"queue": "briefing.generate"},
    },
    "ingestion-cycle": {
        "task": "pwbs.queue.tasks.ingestion.run_all_connectors",
        "schedule": {
            "__type__": "crontab",
            "minute": "*/15",
        },
        "options": {"queue": "ingestion.high"},
    },
    "cleanup-expired": {
        "task": "pwbs.queue.tasks.ingestion.cleanup_expired_documents",
        "schedule": {
            "__type__": "crontab",
            "minute": "0",
            "hour": "3",
        },
        "options": {"queue": "ingestion.bulk"},
    },
    "weekly-briefing": {
        "task": "pwbs.queue.tasks.briefing.generate_weekly_briefings",
        "schedule": {
            "__type__": "crontab",
            "minute": "0",
            "hour": "17",
            "day_of_week": "5",
        },
        "options": {"queue": "briefing.generate"},
    },
    "daily-reminder-triggers": {
        "task": "pwbs.queue.tasks.briefing.run_daily_reminder_triggers",
        "schedule": {
            "__type__": "crontab",
            "minute": "0",
            "hour": "7",
        },
        "options": {"queue": "briefing.generate"},
    },
}

# -- Auto-discover tasks in pwbs.queue.tasks --
app.autodiscover_tasks(["pwbs.queue.tasks"], force=True)
