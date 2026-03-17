# ADR-001: Python/FastAPI as Backend

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

PWBS requires a backend framework that efficiently supports both classical REST API endpoints and data-intensive ML/NLP pipelines (embedding generation, NER, LLM orchestration). The choice of backend stack affects overall development velocity, the available ecosystem for ML libraries, and long-term maintainability. The team has primary Python expertise in the ML/Data Science domain.

---

## Decision

We use **Python 3.12+ with FastAPI** as the backend framework because the Python ecosystem for ML/NLP workloads is unmatched and FastAPI offers the best combination of performance, type safety, and developer experience.

---

## Options Evaluated

| Option                      | Advantages                                                                                                                                                                         | Disadvantages                                                                                                                               | Exclusion Reasons                         |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| **Python/FastAPI** (chosen) | Python ecosystem for ML/NLP is unmatched (Sentence Transformers, LangChain, spaCy). Async support, automatic OpenAPI docs, native Pydantic v2 validation. Existing team expertise. | Higher latency than Go/Rust for pure I/O operations. GIL limits CPU-bound parallelism.                                                      | –                                         |
| Node.js/Express             | Excellent I/O performance, large npm ecosystem, unified language with frontend (TypeScript).                                                                                       | ML/NLP ecosystem significantly weaker. No native support for Sentence Transformers, spaCy, etc. Python bridges (child_process) are fragile. | ML ecosystem gap too large                |
| Go/Gin                      | Outstanding performance and concurrency. Small binaries, simple deployment.                                                                                                        | Minimal ML/NLP ecosystem. Team would need to learn Go. No Pydantic equivalent for automatic validation.                                     | Missing ML libraries                      |
| Rust/Actix                  | Best performance of all options. Memory safety without GC.                                                                                                                         | Steep learning curve, slow compile times. ML ecosystem still immature. Development velocity significantly lower.                            | Development velocity unacceptable for MVP |

---

## Consequences

### Positive Consequences

- Direct access to the entire Python ML ecosystem (Sentence Transformers, spaCy, LangChain, OpenAI SDK)
- Pydantic v2 as data validation layer for all API requests and internal models
- Automatic OpenAPI/Swagger documentation via FastAPI
- Async support for all I/O-bound operations (DB queries, LLM calls, external APIs)
- Fast iteration cycles in MVP thanks to Python flexibility

### Negative Consequences / Trade-offs

- Higher latency than Go/Rust on pure I/O-bound paths (mitigated by async and horizontal scaling in Phase 4+)
- GIL limits CPU-bound parallelism for embedding generation (mitigated by `asyncio.to_thread()` and separate worker processes via Celery in Phase 3)
- Type enforcement only at runtime (mitigated by mypy in CI/CD)

### Open Questions

- Evaluate PyPy or mypyc for performance-critical paths in Phase 4

---

## GDPR Implications

No direct GDPR implications from the framework choice. FastAPI enables implementation of audit logging, rate limiting, and encryption middleware through its middleware support. Pydantic v2 ensures all incoming data is validated before processing.

---

## Security Implications

- FastAPI provides built-in protection against many OWASP Top 10 attacks (automatic input validation via Pydantic, CORS configuration, security header middleware)
- Dependency scanning via `pip-audit` and Dependabot for Python packages required
- Async code requires careful handling of shared state (no global variables for user data)

---

## Revision Date

2027-03-13 – Re-evaluation after 12 months of MVP operation, particularly performance metrics under load.
