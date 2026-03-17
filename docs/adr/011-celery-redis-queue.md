# ADR-011: Celery + Redis Instead of AWS SQS (Phase 3)

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

Starting in Phase 3, the PWBS requires a task queue for asynchronous processing: ingestion cycles, embedding generation, briefing generation, reprocessing jobs, and GDPR deletion cascades. In the MVP (Phase 2), processing occurs directly (synchronous/async within the monolith). The queue solution must be Python-native, easy to operate, and integrate into the existing infrastructure.

---

## Decision

We use **Celery with Redis as Message Broker** for the task queue starting in Phase 3, because Celery is Python-native, well-documented, and Redis is already used for caching and session management.

---

## Options Evaluated

| Option                      | Advantages                                                                                                                                                                                                     | Disadvantages                                                                                                                                  | Exclusion Reasons                   |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| **Celery + Redis** (chosen) | Python-native, excellently documented, large ecosystem (Flower for monitoring, django-celery-beat for scheduling). Redis is already used for caching – no additional infrastructure. Simple local development. | Redis as broker less resilient than SQS (messages lost on Redis crash).                                                                        | –                                   |
| AWS SQS + Lambda            | Fully managed, no operational complexity. SQS guarantees at-least-once delivery. Serverless workers scale automatically.                                                                                       | Vendor lock-in (AWS-specific). Lambda cold starts problematic for long-running processing jobs. More difficult local development.              | Cold starts and vendor lock-in      |
| RabbitMQ                    | Robust, AMQP standard, guaranteed message delivery, flexible routing patterns.                                                                                                                                 | Separate service with its own operational overhead. Redundant when Redis is already running. More complex configuration than Redis as broker.  | Redundant to already existing Redis |
| Kafka                       | Excellent for event streaming, high throughput, persistent messages, replay capability.                                                                                                                        | Massive operational overhead (ZooKeeper/KRaft, topic management). Overkill for the expected message rate in MVP/Phase 3. Steep learning curve. | Overkill for expected scale         |

---

## Consequences

### Positive Consequences

- No additional infrastructure: Redis is already running for caching and sessions
- Python-native API: Tasks are normal Python functions with `@celery.task` decorator
- Flower dashboard for task monitoring and debugging
- Celery Beat for cron-based scheduling (morning briefings, ingestion cycles)
- Simple transition: Modular monolith → Celery workers is an interface swap (`await agent.run()` → `agent.run.delay()`)

### Negative Consequences / Trade-offs

- Redis as broker: Unprocessed messages are lost on Redis crash (mitigated: Redis persistence with AOF, critical jobs are additionally logged in PostgreSQL as fallback – `scheduled_job_runs` table)
- Celery workers are single-threaded by default – CPU-bound tasks (embedding generation) require separate worker pools (mitigated: Celery supports prefork pool and gevent pool)
- Migration to SQS in Phase 5 requires broker switch (mitigated: Celery natively supports SQS as broker)

### Open Questions

- Define Redis persistence configuration (AOF vs. RDB) for broker reliability
- Worker pool strategy: Separate workers for I/O-bound (ingestion) vs. CPU-bound (embeddings)?
- Standardize retry strategy: Max 3 retries with exponential backoff (1min → 5min → 25min)

---

## GDPR Implications

- **Data in transit in queue:** Messages in Redis contain references (IDs), not plaintext user data. OAuth tokens or document contents are not passed as task parameters – workers load these from the DB.
- **Deletion cascades:** GDPR deletion jobs (`cleanup_expired`, account deletion) run as Celery tasks with highest priority.
- **Audit logging:** Every task execution is logged in `scheduled_job_runs` (task ID, status, duration, errors).
- **Data residency:** Redis runs on AWS ElastiCache (eu-central-1) with encryption at rest.

---

## Security Implications

- Redis access: Only from private subnet, password-authenticated (AUTH), TLS-encrypted
- No secrets in task parameters – workers load credentials from the DB or environment
- Flower dashboard only accessible via internal port (not publicly exposed)
- Rate limiting on task submission for LLM-based tasks (cost control)
- Dead letter queue pattern: Failed tasks after 3 retries are persisted to error table (not retried endlessly)

---

## Revision Date

2027-09-13 – Assessment after Phase 3 rollout. Evaluation of Redis reliability vs. SQS migration based on actual outage rates.
