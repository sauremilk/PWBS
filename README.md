# Personal Knowledge Operating System (PWBS)

[![CI](https://github.com/sauremilk/PWBS/actions/workflows/ci.yml/badge.svg)](https://github.com/sauremilk/PWBS/actions/workflows/ci.yml)

A cognitive infrastructure that continuously ingests data from heterogeneous personal sources, builds a semantic knowledge model, and delivers context-aware briefings at the right moment — so knowledge workers spend less time remembering and more time deciding.

---

## Features

- **Universal data ingestion** — connects to Google Calendar, Notion, Obsidian, and Zoom transcripts via OAuth2 or local file watchers; cursor-based incremental sync prevents data loss or duplication (Slack, Gmail, Outlook, Google Docs: Phase 3)
- **Unified Document Format (UDF)** — all sources are normalized into a single canonical data model before any downstream processing
- **Semantic processing pipeline** — chunks documents, generates embeddings, extracts named entities (people, projects, decisions, open questions), and writes to a multi-database knowledge store
- **Hybrid search** — combines vector similarity (Weaviate) with full-text BM25 using Reciprocal Rank Fusion; owner-isolated by design
- **Knowledge graph** — Neo4j graph connecting persons, projects, topics, decisions, and meetings with weighted, time-decaying edges
- **Context briefings** — LLM-generated briefings (morning briefing, meeting prep, project summary, weekly review) backed exclusively by retrieved context, never raw LLM world knowledge
- **Full explainability** — every briefing carries `sources: list[SourceRef]`; the knowledge graph is the audit layer between raw data and generated output
- **GDPR by design** — per-user encryption keys, `expires_at` on every document, `DELETE CASCADE` on all user-owned data, no LLM training on user data
- **Idempotent pipeline** — every ingestion and processing step is safe to re-run; watermarks are persisted after each successful batch

---

## Tech Stack

| Layer              | Technology                                                                                    |
| ------------------ | --------------------------------------------------------------------------------------------- |
| **Backend**        | Python 3.12+, FastAPI, Pydantic v2                                                            |
| **Relational DB**  | PostgreSQL (users, connectors, documents, audit log)                                          |
| **Vector DB**      | Weaviate (chunk embeddings, hybrid search)                                                    |
| **Graph DB**       | Neo4j (knowledge graph, entity relationships)                                                 |
| **LLM**            | Anthropic Claude (primary), OpenAI GPT-4 (fallback), Ollama (local/offline)                   |
| **Embeddings**     | OpenAI `text-embedding-3-small` (cloud), `all-MiniLM-L6-v2` via Sentence Transformers (local) |
| **Frontend**       | Next.js (App Router), React, TypeScript, Tailwind CSS                                         |
| **Infrastructure** | Docker Compose (local), Vercel (frontend), AWS ECS Fargate + RDS + ElastiCache (backend)      |
| **Task queue**     | Celery + Redis (active in MVP: ingestion, processing, briefing queues)                         |
| **Migrations**     | Alembic                                                                                       |
| **Testing**        | pytest, pytest-asyncio                                                                        |

---

## Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Node.js 20+
- API keys for at least one LLM provider (Anthropic or OpenAI) and one embedding provider
- OAuth2 application credentials for any connectors you want to enable (Google, Notion, Zoom)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sauremilk/PWBS.git
cd PWBS
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env — see Configuration section for required variables
```

### 3. Start backing services

```bash
docker compose up -d
# Starts PostgreSQL, Weaviate, and Redis
# Neo4j (Knowledge Graph) is optional — activate with:
#   docker compose --profile graph up -d
```

### 4. Set up the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the API server (hot-reload)
uvicorn pwbs.api.main:app --reload
```

### 5. Set up the frontend

```bash
cd frontend
npm install
npm run dev
```

The API is available at `http://localhost:8000` and the web app at `http://localhost:3000`.

---

## Quickstart

### Connect a data source

```bash
# Initiate OAuth2 flow for Google Calendar
curl http://localhost:8000/api/v1/connectors/google_calendar/auth-url \
  -H "Authorization: Bearer <access_token>"
# Returns a redirect URL — open in browser to complete OAuth consent

# Trigger a manual sync after connecting
curl -X POST http://localhost:8000/api/v1/connectors/<connection_id>/sync \
  -H "Authorization: Bearer <access_token>"
```

### Semantic search

```bash
curl "http://localhost:8000/api/v1/search?q=product+roadmap+Q2&mode=hybrid&top_k=10" \
  -H "Authorization: Bearer <access_token>"
```

### Generate a morning briefing

```bash
curl -X POST http://localhost:8000/api/v1/briefings/generate \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"type": "morning"}'
```

### Implementing a new connector

Every connector extends `BaseConnector` and must be idempotent:

```python
from pwbs.connectors.base import BaseConnector, ConnectorConfig, SyncResult
from pwbs.ingestion.models import UnifiedDocument

class MyConnector(BaseConnector):
    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Cursor-based fetch. Returns the new cursor for the next run."""
        ...

    async def normalize(self, raw: dict) -> UnifiedDocument:
        """Transform raw API response into the Unified Document Format."""
        ...
```

---

## Project Structure

```
PWBS/
├── backend/
│   ├── pwbs/                   # Python package (import: pwbs.*)
│   │   ├── api/                # FastAPI routers, middleware, dependency injection
│   │   │   ├── v1/             # Versioned API endpoints
│   │   │   └── middleware/     # Auth, rate limiting, request ID, audit
│   │   ├── connectors/         # BaseConnector + source-specific implementations
│   │   ├── ingestion/          # Ingestion pipeline, UDF normalization
│   │   ├── processing/         # Chunking, embedding generation, NER
│   │   ├── services/           # Business logic (briefing, search, LLM, encryption)
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── storage/            # Repository layer: PostgreSQL, Weaviate, Neo4j
│   │   ├── briefing/           # Briefing generation, prompt templates
│   │   ├── search/             # Semantic, keyword, and hybrid search
│   │   ├── graph/              # Knowledge graph operations (Neo4j)
│   │   ├── scheduler/          # Scheduled jobs (ingestion cycles, briefings)
│   │   ├── prompts/            # Versioned LLM prompt files
│   │   ├── scripts/            # DB init scripts (Weaviate, Neo4j)
│   │   └── core/               # Shared config, exceptions, base classes
│   ├── migrations/             # Alembic database migrations
│   ├── tests/                  # pytest test suites
│   └── pyproject.toml          # Python 3.12+ project configuration
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js App Router pages
│   │   ├── components/         # React components (briefing, search, layout, ...)
│   │   ├── lib/api/            # Typed API client (never raw fetch in components)
│   │   ├── hooks/              # Custom React hooks
│   │   ├── stores/             # Client state (Zustand)
│   │   └── types/              # TypeScript types from OpenAPI schema
│   ├── package.json            # Next.js, React, TypeScript, Tailwind CSS
│   └── tsconfig.json           # Strict TypeScript configuration
├── infra/
│   ├── terraform/              # Infrastructure as Code (AWS)
│   └── docker/                 # Production Docker Compose
├── docs/
│   ├── adr/                    # Architecture Decision Records
│   └── orchestration/          # Multi-agent task coordination
├── .github/
│   ├── copilot-instructions.md
│   ├── instructions/           # Scoped coding instructions (backend, frontend, security)
│   ├── prompts/                # Reusable development workflow prompts
│   └── workflows/              # GitHub Actions CI/CD
├── .env.example                # Environment variable template (never commit .env)
├── ARCHITECTURE.md             # Full architecture documentation
├── AGENTS.md                   # AI agent roles and orchestration design
├── ROADMAP.md                  # Phase-by-phase product roadmap
└── docker-compose.yml          # Local development services
```

---

## Configuration

All secrets and environment-specific settings are loaded from `.env`. Commit `.env.example` with placeholder values; never commit `.env`.

| Variable               | Required | Description                                                    |
| ---------------------- | -------- | -------------------------------------------------------------- |
| `PWBS_ENV`             | Yes      | `development` or `production` (disables `/docs` in production) |
| `DATABASE_URL`         | Yes      | PostgreSQL connection string                                   |
| `WEAVIATE_URL`         | Yes      | Weaviate instance URL                                          |
| `NEO4J_URI`            | No       | Neo4j bolt URI (optional – activate with `--profile graph`)    |
| `NEO4J_USER`           | No       | Neo4j username                                                 |
| `NEO4J_PASSWORD`       | No       | Neo4j password                                                 |
| `ANTHROPIC_API_KEY`    | Yes\*    | Claude API key (\*required unless using Ollama only)           |
| `OPENAI_API_KEY`       | No       | OpenAI API key (embeddings + GPT-4 fallback)                   |
| `JWT_PRIVATE_KEY`      | Yes      | RS256 private key for signing access tokens                    |
| `JWT_PUBLIC_KEY`       | Yes      | Corresponding RS256 public key                                 |
| `ENCRYPTION_KEK`       | Yes      | Key-encryption key for wrapping per-user data encryption keys  |
| `GOOGLE_CLIENT_ID`     | No       | OAuth2 client ID for Google connectors                         |
| `GOOGLE_CLIENT_SECRET` | No       | OAuth2 client secret for Google connectors                     |
| `NOTION_CLIENT_ID`     | No       | OAuth2 client ID for Notion connector                          |
| `NOTION_CLIENT_SECRET` | No       | OAuth2 client secret for Notion connector                      |
| `SLACK_CLIENT_ID`      | No       | OAuth2 client ID for Slack connector (Phase 3)                 |
| `SLACK_CLIENT_SECRET`  | No       | OAuth2 client secret for Slack connector (Phase 3)             |
| `ZOOM_CLIENT_ID`       | No       | OAuth2 client ID for Zoom connector                            |
| `ZOOM_CLIENT_SECRET`   | No       | OAuth2 client secret for Zoom connector                        |
| `REDIS_URL`            | Yes      | Redis connection string (required for Celery task queues)      |

Security defaults enforced in production (`PWBS_ENV=production`):

- `/docs` and `/redoc` endpoints disabled
- CORS restricted to explicit allowlist
- TLS 1.3 required; HTTP connections rejected
- Security headers (`HSTS`, `X-Content-Type-Options`, `X-Frame-Options`) active

---

## API Documentation

The FastAPI application exposes interactive API documentation at `http://localhost:8000/docs` (development only).

### Endpoint groups

| Prefix                                     | Description                            |
| ------------------------------------------ | -------------------------------------- |
| `POST /api/v1/auth/register`               | User registration                      |
| `POST /api/v1/auth/token`                  | JWT token issuance                     |
| `POST /api/v1/auth/refresh`                | Access token refresh                   |
| `GET /api/v1/connectors`                   | List configured connectors             |
| `GET /api/v1/connectors/{source}/auth-url` | Initiate OAuth2 flow                   |
| `POST /api/v1/connectors/{id}/sync`        | Trigger manual sync                    |
| `GET /api/v1/search`                       | Semantic / keyword / hybrid search     |
| `GET /api/v1/briefings`                    | List generated briefings               |
| `POST /api/v1/briefings/generate`          | Generate a new briefing on demand      |
| `GET /api/v1/knowledge/entities`           | Query extracted entities               |
| `GET /api/v1/knowledge/graph`              | Explore knowledge graph context        |
| `GET /api/v1/documents`                    | List ingested documents                |
| `DELETE /api/v1/documents/{id}`            | Delete a document and all derived data |

All endpoints require a valid JWT Bearer token. The `user_id` claim is always extracted from the token — never from the request body. Every query against user data includes `WHERE owner_id = :user_id`.

---

## Architecture Overview

PWBS follows a **modular monolith** pattern in the current MVP (Phase 2). All backend logic runs in a single FastAPI process; modules communicate via typed Python interfaces, not HTTP. This enables rapid iteration while keeping the service boundary clear enough for a future service split in Phase 3.

```
Data Sources → Ingestion Layer → Processing Pipeline → Knowledge Store
                                                              ↓
                                               API Layer (FastAPI)
                                                              ↓
                                               Next.js Web Frontend
```

The processing pipeline runs in three stages:

1. **Chunking** — semantic splitting at sentence boundaries, max 512 tokens, 64-token overlap
2. **Embedding** — batch embedding generation (OpenAI or local Sentence Transformers)
3. **NER + Graph** — two-stage entity extraction (rule-based → LLM-based) followed by idempotent `MERGE` writes to Neo4j

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design, database schemas, Weaviate collection configuration, and Neo4j graph model.

---

## Development

### Running tests

```bash
cd backend

# Unit tests (no network, no running databases required)
pytest tests/unit/ -v

# Integration tests (requires running Docker services)
pytest tests/integration/ -v --docker
```

### Creating a database migration

```bash
cd backend
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

### Adding a new briefing type

Derive from `BriefingTemplate`, place the LLM prompt in `pwbs/prompts/`, and register the new type in the scheduler if it should run on a schedule. Every briefing must return `sources: list[SourceRef]` — the system does not deliver briefings without source attribution.

### Architecture decisions

Significant architectural decisions are documented as Architecture Decision Records in [docs/adr/](docs/adr/). Use `docs/adr/000-template.md` as the starting point for new ADRs.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Follow the coding conventions in `.github/instructions/` (applied automatically by GitHub Copilot).
3. Ensure all unit tests pass before opening a pull request.
4. For significant changes, create an ADR in `docs/adr/` before writing code.
5. Do not commit `.env` or any file containing secrets.

Security issues should be reported privately rather than via public issues.

---

## License

License terms have not yet been specified for this project.
