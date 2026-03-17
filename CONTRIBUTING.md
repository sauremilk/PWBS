# Contributing to PWBS

Thank you for your interest in contributing to the Personal Knowledge Operating System (PWBS). This document outlines the conventions and development workflow for this project.

---

## Project Structure

```
backend/          Python · FastAPI backend (MVP active)
  pwbs/           Core application code
  migrations/     Alembic database migrations
  tests/          Unit, integration, and e2e test suites
  _deferred/      Phase 3+ modules (not active in MVP)
frontend/         Next.js · TypeScript frontend
docs/             Architecture decisions (ADR), API docs, audit reports
infra/            Docker, Terraform, Prometheus/Grafana
obsidian-plugin/  Obsidian vault sync plugin
browser-extension Chrome/Edge extension (Manifest V3)
desktop-app/      Tauri desktop wrapper (Phase 4)
mobile-app/       React Native · Expo (Phase 4)
```

---

## Development Setup

```bash
# Start all services (PostgreSQL, Weaviate, Redis)
docker compose up -d

# Optional: include Neo4j knowledge graph
docker compose --profile graph up -d

# Backend (hot-reload)
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e ".[dev,llm,vector]"
uvicorn pwbs.api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Run backend test suite
cd backend
pytest tests/unit/ -v
pytest tests/integration/ -v   # requires running Docker services
```

---

## Code Conventions

### Python

- **Python 3.12+**, type annotations on every function and class.
- **Pydantic v2** for all data models and config.
- **Async by default** — use `async def` for I/O-bound operations; wrap blocking code in `asyncio.to_thread()`.
- **Idempotent writes** — always `UPSERT` / `MERGE`, never blind `INSERT`.
- **`owner_id` on every DB query** — no cross-user data leakage.
- Exceptions extend `PWBSError`; HTTP errors use `HTTPException` with a structured `detail` dict.
- New connector? Implement `BaseConnector` with cursor-based pagination (`fetch_since(cursor)`).

### TypeScript / Frontend

- `tsconfig.json` strict mode — no implicit `any`.
- Functional components with explicit props interfaces.
- All API calls go through `src/lib/api/`; no raw `fetch()` in components.

### Git

- Branch naming: `feat/<scope>`, `fix/<scope>`, `chore/<scope>`
- Commit message format: `<type>(<scope>): <short description>` (Conventional Commits)
- All public-facing changes should include or reference an ADR in `docs/adr/` if they affect architecture.

---

## Architecture Principles

1. **GDPR by design** — every new data structure needs `owner_id`, `expires_at`, and must support deletion.
2. **Explainability** — every LLM output must carry `sources: list[SourceRef]`.
3. **Idempotency** — ingestion and processing pipelines must be safely re-runnable.
4. **Modularity** — in the MVP, modules communicate via Python interfaces, not HTTP.
5. **Neo4j is optional** — any code using `get_neo4j_driver()` must handle `None` gracefully.

---

## MVP Scope (ADR-016)

The following modules in `backend/_deferred/` are **not part of the MVP** and must not be imported or extended:

| Module | Phase |
|--------|-------|
| `billing/` | Phase 4 |
| `teams/` | Phase 4 |
| `rbac/` | Phase 4 |
| `marketplace/` | Phase 5 |
| `developer/` | Phase 5 |
| `sso/` | Phase 4 |

Active connectors (MVP): **Google Calendar, Notion, Zoom, Obsidian**

---

## Testing

- Unit tests: `backend/tests/unit/` — no real network, all external deps mocked.
- Integration tests: `backend/tests/integration/` — requires Docker services.
- Default timeout: 30 seconds per test (`pytest-timeout`).
- DB singletons auto-mocked via `_isolate_db_singletons` fixture.

```bash
pytest tests/unit/ -v --timeout=30
pytest tests/integration/ -v --docker
```

---

## Opening Issues

Please include:
- Expected vs. actual behavior
- Steps to reproduce
- Relevant log output (remove any personal data before posting)

---

## Licence

By contributing you agree that your contributions will be licensed under the same licence as this project. See [LICENSE](LICENSE) if present, or contact the maintainer.
