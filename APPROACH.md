# Engineering Approach & AI-Assisted Development

This document explains the development methodology behind PWBS, including the role of AI tooling. Written for engineers who want to understand how the project was built.

---

## How This Project Was Built

PWBS is a solo project built by an autodidact developer using AI tooling (primarily GitHub Copilot / Claude Sonnet) as pair-programmer. This is deliberate and worth explaining clearly.

### What I designed

Every architectural decision in this codebase reflects my own judgment:

- The **7-layer middleware stack** (CORS → TrustedHost → SecurityHeaders → CorrelationId → RateLimit → Auth → Audit) and its ordering — Starlette applies middleware bottom-up, so the order matters and was thought through explicitly against OWASP threat models.
- The **compound cursor encoding** in `connectors/google_calendar.py` — the decision to JSON-encode `{syncToken, pageToken}` as a single opaque string so the caller never needs to differentiate between full-sync and incremental-sync cursors came from debugging the Google Calendar API's `410 Gone` behavior on expired syncTokens.
- The **RRF fusion weighting** (`sem_weight=0.75, kw_weight=0.25`) in `search/hybrid.py` — calibrated empirically against the Cormack et al. SIGIR 2009 paper after testing against the POC dataset in `poc/sample_data/`.
- The **NullGraphService fallback pattern** — Neo4j being optional wasn't a performance choice but a deployment-cost one. The decision meant every graph-touching code path needed explicit `driver is None` guards, which I traced through all callers.
- The **ADR discipline** — 20 architecture decision records written before or during implementation, not retroactively. ADR-016 (MVP focussing) actively removed code that was already written.
- The **security model** — `owner_id` on every query is enforced at the service layer, not the route layer. This was a conscious choice after reading about multi-tenant isolation failures in Weaviate and PostgreSQL RLS tradeoffs.

### Where AI helped

AI tooling accelerated several categories of work:

| Category            | AI contribution                                    | My contribution                                                      |
| ------------------- | -------------------------------------------------- | -------------------------------------------------------------------- |
| Boilerplate         | Generated initial CRUD route scaffolding           | Reviewed and adapted every generated route; cut ~40% as unnecessary  |
| Test fixtures       | Suggested mock structures for async DB sessions    | Wrote the actual test assertions and edge cases                      |
| SQL/Cypher queries  | First drafts of complex joins and graph traversals | Verified correctness, added `owner_id` filters that AI often omitted |
| Documentation       | Drafted ADR structure                              | Wrote the decision rationale and tradeoffs myself                    |
| Dependency research | Suggested library choices                          | Evaluated alternatives, checked security advisories, made final call |

AI did **not** make architectural decisions. Every tradeoff between approaches is documented in the relevant ADR.

### What this means in an interview

If you ask me about any component, I can explain:

- **Why** it exists (the problem it solves)
- **Why this specific design** (and what alternatives I considered)
- **What would break** if you changed it

I cannot write production Python from memory at LeetCode speed. I can reason about systems, debug production failures, and make defensible engineering decisions.

---

## Technical decisions worth knowing

### Why RRF and not a learned reranker?

Reciprocal Rank Fusion (Cormack et al. 2009) is parameter-free beyond `k=60`, which avoids overfitting to the limited POC dataset. A learned reranker (e.g. cross-encoder) would require labeled relevance judgments we don't have at MVP scale. See [ADR-010](docs/adr/010-hybrid-suche.md).

### Why Weaviate and not pgvector?

pgvector's HNSW index requires `lists` parameter tuning that scales with dataset size. At MVP scale (&lt;100k vectors per user) pgvector would be fine, but the Weaviate multi-tenancy model (one tenant per user, tenant-isolated HNSW graphs) gives us data isolation essentially for free. The tradeoff is operational complexity of a separate service, which we accept because the Docker Compose setup makes it transparent. See [ADR-003](docs/adr/003-weaviate-vector-db.md).

### Why async all the way down?

Three connectors (Google Calendar, Notion, Zoom) make external HTTP calls that can take 2–10 seconds. Under synchronous I/O, a 10-user concurrent ingestion cycle would need 10 threads just for waiting. With `asyncio` + `httpx.AsyncClient`, the same event loop handles 100+ concurrent waits with a single thread. The tradeoff: any CPU-bound operation (chunking, NER) blocks the event loop — those are `asyncio.to_thread()` wrapped.

### Why Celery for a solo MVP?

The morning briefing job runs at 06:30 for all users. If that's a synchronous HTTP call on a cron, a single slow LLM response blocks all subsequent users. Celery + Redis separates the scheduler (which enqueues) from the workers (which process), giving independent failure domains. The operational cost is one extra Redis connection and the Celery beat service — acceptable even for MVP.

---

## What I'd improve with more time

1. **Branch coverage enforcement** — Only added `fail_under=80` after initial development. There are modules (workflows engine, multimodal processing) with &lt;60% branch coverage.
2. **create_app() decomposition** — The app factory was a 213-line god function until recently refactored into `_init_observability`, `_register_exception_handlers`, `_register_middlewares`, `_register_routers`. That decomposition should have happened earlier.
3. **ADRs in English** — Written in German for speed. For a global audience these need translation; the architecture reasoning is sound, the language is not.
4. **No LeetCode profile** — My algorithmic thinking is visible in `chunking.py` (`_overlap_start`), `hybrid.py` (RRF), and `briefing/validation.py` (cosine similarity), but I don't have competitive programming credentials. That's a real gap for Big Tech screening.
