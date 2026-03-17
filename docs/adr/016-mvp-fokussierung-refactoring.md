# ADR-016: MVP Focus – 5-Step Refactoring

**Status:** Accepted
**Date:** 2026-03-15
**Authors:** Copilot-assisted Refactoring

## Context

The PWBS backend contained 36+ modules, many of which are not needed for the MVP (Phase 2, 10–20 Early Adopters). The complexity costs of Teams/RBAC/Billing/Marketplace/SSO/Developer modules plus 8 connectors significantly outweigh the benefit for the Phase 2 target audience.

**Goal:** Maximum reduction of the active codebase without data loss or breaking changes.

## Decision

5-step strategy with a conservative approach (comment out instead of delete):

### Step 1: Deactivate Out-of-Scope Modules

**Affected Modules:** billing, teams, rbac, marketplace, developer, sso

**Measures:**

- Module files copied to `_deferred/` (originals remain for Alembic import integrity)
- 9 router imports + `include_router` calls in `main.py` commented out with `# DEFERRED: Phase 3`
- Webhooks router deactivated (Gmail Pub/Sub + Slack Events)
- `_deferred/README.md` created with complete reactivation guide

**Deliberate Decision:** `models/__init__.py` retains ALL 32 ORM imports (Alembic Discovery). `schemas/enums.py` remains complete (no breaking changes in serialization).

### Step 2: Deactivate Phase 3 Connectors

**Active Core 4:** Google Calendar, Notion, Zoom, Obsidian
**Deactivated:** Gmail, Slack, Outlook, Google Docs

**Measures:**

- Connector files moved to `_deferred/connectors/`
- `integrations/slack/` moved to `_deferred/integrations/slack/`
- Test files moved to `_deferred/tests/`
- In `connectors.py` route: Phase 3 entries in 6+ dictionaries commented out (`_CONNECTOR_META`, `_AUTH_URLS`, `_SCOPES`, `redirect_uri_map`, `client_id_map`, `client_secret_map`, `token_endpoints`)

### Step 3: Feature Flags – Retained

**Analysis Result:** Feature flags service is already MVP-ready:

- ENV override (`FEATURE_FLAGS_OVERRIDE`) implemented as highest priority
- No business logic code uses feature flags
- Service is opt-in, no overhead

**Decision:** No changes needed.

### Step 4: Vertical Profiles – Retained

**Analysis Result:** Default profile "general" is active:

- No supplement, no special logic
- `entity_priorities`/`ner_focus` defined but not implemented anywhere
- Dormant configuration costs nothing

**Decision:** No changes needed.

### Step 5: Database Architecture – Neo4j Optional

**Problem:** App crashed when Neo4j was unreachable (SinglePointOfFailure).
**Analysis:** GraphBuilder is NEVER called in the pipeline – no user data writes to Neo4j.

**Measures:**

- `neo4j_client.py`: `get_neo4j_driver()` returns `AsyncDriver | None`; `_init_failed` flag for short-circuit
- `main.py` lifespan: Neo4j init with None check + warning log
- `docker-compose.yml`: Neo4j behind `profiles: ["graph"]` (activatable with `--profile graph`)
- Existing fallbacks confirmed: `NullGraphService` in Briefing, try/except in Knowledge API

## Changed Files

| File                               | Change                                           |
| ---------------------------------- | ------------------------------------------------ |
| `pwbs/api/main.py`                 | 9 routers deactivated, Neo4j startup optional    |
| `pwbs/api/v1/routes/connectors.py` | Phase 3 entries in 6+ dictionaries commented out |
| `pwbs/db/neo4j_client.py`          | Returns None on error, \_init_failed flag        |
| `docker-compose.yml`               | Neo4j behind `profiles: ["graph"]`               |
| `_deferred/README.md`              | Documentation with reactivation guide            |
| `CHANGELOG.md`                     | All 5 steps documented                           |

## Unchanged Files (intentional)

| File                 | Reason                                                            |
| -------------------- | ----------------------------------------------------------------- |
| `models/__init__.py` | All 32 ORM imports remain for Alembic                             |
| `schemas/enums.py`   | SourceType/EntityType complete for serialization compatibility    |
| `api_key_auth.py`    | Imports from developer module (still exists at original location) |

## Consequences

**Positive:**

- Reduced active codebase: ~6 modules + 4 connectors fewer active
- App starts without Neo4j (no more SPOF)
- Lighter Docker setup (only PG + Weaviate + Redis required)
- All tests continue to pass

**Negative:**

- Modules exist in duplicate (`pwbs/` + `_deferred/`) for Alembic compatibility
- Commented-out code blocks in `connectors.py` and `main.py`

**Risks:**

- For schema changes in deferred models: Alembic still sees the original model files
- `api_key_auth.py` depends on the developer module (must be inlined if deleted)

## Reactivation

Complete guide in `_deferred/README.md`. Summary:

1. Move files back
2. Uncomment router imports in `main.py`
3. Uncomment connector entries in `connectors.py`
4. Move tests back and run them
