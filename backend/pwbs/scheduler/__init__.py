"""Scheduler facade.

Scheduled jobs are managed by Celery Beat and implemented in::

    pwbs.queue.tasks.briefing   – timed briefing generation
    pwbs.queue.tasks.ingestion  – periodic connector sync cycles
    pwbs.queue.tasks.pipeline   – processing chain tasks

Import from those modules directly; this package is a namespace stub.
"""