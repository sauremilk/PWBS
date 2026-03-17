# ADR-006: Modular Monolith Instead of Microservices (MVP)

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

The PWBS is being built in Phase 2 (MVP) by a small team (2\u20135 developers). The architecture must enable fast iteration cycles while also supporting a later split into services (Phase 3+). The choice between monolith and microservices affects development speed, deployment complexity, testing effort, and the ability to cleanly enforce module boundaries.

---

## Decision

We use a **modular monolith** in the MVP, where modules communicate via defined Python interfaces (not via HTTP). Service split occurs only in Phase 3 via Celery + Redis.

---

## Options Evaluated

| Option                            | Advantages                                                                                                                                                                                                                                                          | Disadvantages                                                                                                                                            | Exclusion Reasons                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| **Modular Monolith** (chosen)     | 2\u20135 developers can iterate on a monolith significantly faster. No overhead from service mesh, distributed tracing, API contracts. Module boundaries in code enforce separation of concerns through Python interfaces. Simple debugging (single process).              | Later service split requires refactoring. All modules share one process \u2013 a memory leak affects all.                                                     | \u2013                                          |
| Microservices from the start      | Independent deployment per service, technological flexibility, independent scaling.                                                                                                                                                                                  | Massive overhead for a small team: service mesh, distributed tracing, API contracts, inter-service auth. Significantly slower development in MVP.        | Too much overhead for MVP team             |
| Serverless Functions              | Pay-per-use, automatic scaling, no server management.                                                                                                                                                                                                                | Cold-start latency problematic for real-time search. Difficult local development. Vendor lock-in (AWS Lambda). State management is complex.              | Cold-start latency and state complexity    |

---

## Consequences

### Positive Consequences

- Fast iteration cycles: one deployment artifact, one Docker container, one log stream
- Simple debugging: breakpoints across module boundaries, no network overhead between modules
- Python interfaces as module boundaries: wait ingestion_agent.run(context) instead of httpx.post(\x22/api/internal/process\x22)
- Transactions across module boundaries: a single DB commit can atomically persist changes from ingestion + processing
- Testability: unit tests mock interfaces, no service stubs or containers needed

### Negative Consequences / Trade-offs

- Service split in Phase 3 requires refactoring of module communication (mitigated: modules communicate via defined interfaces, not via global state \u2013 the transition to message queues is an interface swap, not a rewrite)
- A faulty module can affect the entire process (mitigated: error isolation via try/except at the module level, health checks)
- No independent scaling of individual modules (mitigated: MVP scale does not require independent scaling)

### Open Questions

- Define which modules will be the first to become standalone services in Phase 3 (candidates: IngestionAgent, ProcessingAgent)
- Monitoring strategy for module-level metrics within the monolith

---

## GDPR Implications

No direct GDPR implications from the monolith decision. All GDPR measures (owner_id filters, encryption, delete cascades) are implemented at the module level, independent of the deployment topology. The monolith actually simplifies GDPR compliance, as data flows within a single process are easier to audit than across service boundaries.

---

## Security Implications

- One process = one attack surface (instead of N services each with their own endpoints)
- All modules share the same authentication middleware \u2013 no forgotten auth checks on internal endpoints
- Disadvantage: compromise of one module endangers all modules in the same process (mitigated: modules have no direct DB access to other modules \u2013 only via interfaces)
- Secrets management is simpler (one .env instead of N)

---

## Revision Date

2027-06-13 \u2013 Assessment of service split needs after MVP launch. Trigger: when independent scaling or independent deployment cycles for individual modules become necessary.
