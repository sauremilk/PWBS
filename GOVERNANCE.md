# PWBS – Governance & Entwicklungsstandards

**Version:** 1.0.0 | **Stand:** 13. März 2026 | **Status:** Verbindlich
**Geltungsbereich:** Alle Entwickler, KI-Agenten und Orchestratoren im PWBS-Workspace

---

## Inhaltsverzeichnis

1. [Zweck und Geltungsbereich](#1-zweck-und-geltungsbereich)
2. [Workspace- und Projektstruktur](#2-workspace--und-projektstruktur)
3. [Versionskontrolle und Code-Management](#3-versionskontrolle-und-code-management)
4. [Entscheidungsdokumentation (ADR-Framework)](#4-entscheidungsdokumentation-adr-framework)
5. [Task- und Wissensmanagement](#5-task--und-wissensmanagement)
6. [Code-Qualität und Enforcement](#6-code-qualität-und-enforcement)
7. [Release- und Changelog-Management](#7-release--und-changelog-management)
8. [Sicherheits- und DSGVO-Gates](#8-sicherheits--und-dsgvo-gates)
9. [Onboarding-Checkliste](#9-onboarding-checkliste)
10. [Governance-Änderungen](#10-governance-änderungen)

---

## 1. Zweck und Geltungsbereich

Dieses Dokument ist das **zentrale, verbindliche Regelwerk** für den gesamten PWBS-Entwicklungsprozess. Es verfolgt drei Hauptziele:

| Ziel                               | Maßnahmen                                                            |
| ---------------------------------- | -------------------------------------------------------------------- |
| **Lückenlose Nachvollziehbarkeit** | Conventional Commits, ADRs, Task-State-Tracking, Audit-Trail in Git  |
| **Fehlerreduktion**                | Pre-Commit-Hooks, Typ-Sicherheit, Code-Reviews, automatisierte Tests |
| **Skalierbarkeit**                 | Modulare Struktur, maschinenlesbare Protokolle, Orchestrator-Slots   |

### Hierarchie der Regelwerke

```
GOVERNANCE.md                          ← Dieses Dokument (Prozesse & Workflows)
├── .github/copilot-instructions.md    ← KI-Assistenten-Konfiguration (Code-Stil, Stack)
├── .github/instructions/*.md          ← Kontextspezifische Code-Regeln (Backend, Frontend, Security, Agents)
├── AGENTS.md                          ← Agenten-Architektur & Kommunikation
├── ORCHESTRATION.md                   ← Parallele Orchestrator-Koordination
├── ARCHITECTURE.md                    ← Technische Architektur & Schicht-Modell
├── docs/adr/*.md                      ← Architekturentscheidungen (einzeln)
└── tasks.md + task-state.json         ← Aufgaben-Definitionen & Koordinationszustand
```

**Konflikt-Resolution:** Bei Widersprüchen gilt: `GOVERNANCE.md` > `ARCHITECTURE.md` > `.github/instructions/*.md` > Inline-Kommentare.

---

## 2. Workspace- und Projektstruktur

### 2.1 Kanonische Verzeichnisstruktur

```
PWBS/                                  # Monorepo-Root
│
│── GOVERNANCE.md                      # ← Dieses Dokument
│── ARCHITECTURE.md                    # Technische Architektur
│── AGENTS.md                          # Agenten-Definitionen & Orchestrierung
│── ORCHESTRATION.md                   # Parallele Work-Stream-Koordination
│── PRD-SPEC.md                        # Product Requirements (Personas, User Stories)
│── ROADMAP.md                         # Strategische Phasen-Planung
│── CHANGELOG.md                       # Versionierte Änderungshistorie
│── tasks.md                           # Menschenlesbare Task-Definitionen
│── Makefile                           # Entwickler-Shortcuts (make dev, make test, make lint)
│── docker-compose.yml                 # Lokale Entwicklungsumgebung
│── .editorconfig                      # Cross-Editor Formatierungsstandards
│── .pre-commit-config.yaml            # Git-Hook-Konfiguration
│── .gitignore                         # Exclusion-Patterns
│
├── .github/
│   ├── copilot-instructions.md        # Globale KI-Assistenten-Konfiguration
│   ├── instructions/                  # Kontextspezifische .instructions.md (per applyTo)
│   │   ├── agents.instructions.md
│   │   ├── backend.instructions.md
│   │   ├── frontend.instructions.md
│   │   └── security.instructions.md
│   ├── prompts/                       # Wiederverwendbare KI-Workflows (.prompt.md)
│   │   ├── new-connector.prompt.md
│   │   ├── briefing-feature.prompt.md
│   │   ├── architecture-review.prompt.md
│   │   ├── db-migration.prompt.md
│   │   ├── debug-agent.prompt.md
│   │   ├── extended-thinking.prompt.md
│   │   ├── orchestrator-init.prompt.md
│   │   └── task-executor.prompt.md
│   ├── pull_request_template.md       # PR-Template (Pflicht für alle PRs)
│   └── workflows/                     # CI/CD-Pipelines (GitHub Actions)
│       ├── ci.yml                     # Lint → Type-Check → Test → Build
│       └── security-audit.yml         # DSGVO- & Dependency-Audit
│
├── backend/
│   ├── pyproject.toml                 # Python-Paketdefinition & Tool-Konfiguration
│   ├── Dockerfile / Dockerfile.dev
│   ├── migrations/                    # Alembic-Migrationen
│   │   └── versions/                  # Einzelne Migrationsdateien
│   ├── pwbs/                          # Haupt-Package
│   │   ├── __init__.py
│   │   ├── core/                      # Config, Exceptions, Shared Utilities
│   │   │   ├── config.py              # Settings via Pydantic BaseSettings
│   │   │   └── exceptions.py          # PWBSError-Hierarchie
│   │   ├── models/                    # SQLAlchemy ORM-Modelle
│   │   ├── schemas/                   # Pydantic v2 API-Schemas (Request/Response)
│   │   ├── api/                       # FastAPI-Routen
│   │   │   ├── middleware/            # Auth, Rate-Limiting, CORS, Logging
│   │   │   └── v1/                    # Versionierte Endpunkte
│   │   ├── services/                  # Business-Logik (Service-Layer)
│   │   ├── connectors/                # Datenquellen-Konnektoren
│   │   ├── ingestion/                 # Ingestion-Pipeline
│   │   ├── processing/                # Chunking, Embedding, NER
│   │   ├── storage/                   # DB-Clients (Postgres, Weaviate, Neo4j)
│   │   ├── search/                    # Such-Services
│   │   ├── briefing/                  # Briefing-Generierung
│   │   ├── graph/                     # Knowledge-Graph-Operationen
│   │   ├── scheduler/                 # Zeitgesteuerte Jobs
│   │   ├── prompts/                   # LLM-Prompt-Templates (versioniert)
│   │   └── scripts/                   # CLI-Skripte (Seed, Migrate, etc.)
│   └── tests/
│       ├── conftest.py                # Shared Fixtures (DB-Mocks, Auth-Fixtures)
│       ├── unit/                      # Isolierte Unit-Tests (kein I/O)
│       ├── integration/               # Tests mit DB/Services (Docker erforderlich)
│       ├── e2e/                       # End-to-End API-Tests
│       ├── test_api/                  # Route-spezifische Tests
│       ├── test_connectors/           # Konnektor-spezifische Tests
│       ├── test_processing/           # Processing-Pipeline-Tests
│       └── test_services/             # Service-Layer-Tests
│
├── frontend/
│   ├── package.json / tsconfig.json
│   ├── next.config.ts / tailwind.config.ts
│   ├── Dockerfile / Dockerfile.dev
│   ├── public/                        # Statische Assets
│   └── src/
│       ├── app/                       # Next.js App Router (Seiten & Layouts)
│       ├── components/                # UI-Komponenten
│       ├── hooks/                     # Custom React Hooks
│       ├── lib/                       # Shared Utilities
│       │   └── api/                   # API-Client-Abstraktion (einziger Fetch-Ort)
│       ├── stores/                    # Client-State (minimal)
│       └── types/                     # TypeScript-Typendefinitionen
│
├── docs/
│   ├── adr/                           # Architecture Decision Records
│   │   ├── 000-template.md            # Pflicht-Vorlage für neue ADRs
│   │   └── 001-*.md ... 012-*.md      # Bestehende Entscheidungen
│   ├── backlog/                       # Phasenweise Backlog-Definitionen
│   ├── orchestration/                 # Maschinenlesbare Koordination
│   │   ├── task-state.json            # Aktueller Koordinationszustand
│   │   └── task-state.schema.json     # JSON-Schema für Validierung
│   └── interviews/                    # User-Research
│
├── infra/
│   ├── docker/                        # Zusätzliche Docker-Konfigurationen
│   └── terraform/                     # IaC (AWS-Infrastruktur)
│       ├── main.tf / variables.tf / outputs.tf
│       ├── environments/              # Umgebungsspezifische Variablen
│       └── modules/                   # Terraform-Module (RDS, ECS, etc.)
│
├── legal/
│   └── avv/                           # Auftragsverarbeitungs-Vereinbarungen
│
└── poc/                               # Proof-of-Concept (Phase 1, archiviert)
    ├── docker-compose.yml
    ├── embedding_poc.py
    ├── search_poc.py
    └── sample_data/
```

### 2.2 Regeln für neue Dateien und Verzeichnisse

| Regel           | Beschreibung                                                                                         |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| **R-STRUCT-01** | Neue Module im Backend werden unter `pwbs/` als Package (mit `__init__.py`) angelegt                 |
| **R-STRUCT-02** | Jedes neue Modul bekommt ein korrespondierendes Test-Verzeichnis unter `tests/`                      |
| **R-STRUCT-03** | Konfigurationsdateien liegen im Repo-Root oder im jeweiligen Stack-Root (`backend/`, `frontend/`)    |
| **R-STRUCT-04** | Dokumentation geht nach `docs/`, **nicht** in Code-Verzeichnisse (Ausnahme: Inline-Docstrings)       |
| **R-STRUCT-05** | Keine verschachtelten Packages tiefer als 3 Ebenen (`pwbs.connectors.google_calendar` = Maximum)     |
| **R-STRUCT-06** | Temporäre Dateien, Build-Artefakte und Secrets sind in `.gitignore` aufgeführt — niemals committen   |
| **R-STRUCT-07** | Neue Prompt-Files gehen nach `.github/prompts/`, neue Instruction-Files nach `.github/instructions/` |

---

## 3. Versionskontrolle und Code-Management

### 3.1 Branching-Modell: Trunk-Based Development (vereinfacht)

Das PWBS nutzt **Trunk-Based Development** mit kurzlebigen Feature-Branches:

```
master (= Trunk, immer deploybar)
│
├── feat/TASK-041-base-connector       ← Feature-Branch (max. 3 Tage Lebensdauer)
├── fix/TASK-087-token-refresh-bug     ← Bugfix-Branch
├── docs/adr-013-caching-strategy      ← Dokumentations-Branch
└── infra/TASK-012-ci-pipeline         ← Infrastruktur-Branch
```

#### Branch-Namenskonvention

```
<typ>/<task-id>-<kurzbeschreibung>
```

| Typ         | Bedeutung                  | Beispiel                              |
| ----------- | -------------------------- | ------------------------------------- |
| `feat/`     | Neues Feature              | `feat/TASK-041-base-connector`        |
| `fix/`      | Bugfix                     | `fix/TASK-087-token-refresh`          |
| `refactor/` | Code-Umstrukturierung      | `refactor/TASK-060-chunking-pipeline` |
| `docs/`     | Dokumentation              | `docs/adr-013-caching-strategy`       |
| `infra/`    | Infrastruktur / DevOps     | `infra/TASK-012-ci-pipeline`          |
| `test/`     | Test-Ergänzungen           | `test/TASK-108-integration-tests`     |
| `hotfix/`   | Kritischer Produktions-Fix | `hotfix/auth-token-expiry`            |

#### Branch-Regeln

| Regel           | Beschreibung                                                                                                                                                                                      |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **R-BRANCH-01** | `master` ist geschützt — kein direkter Push (Ausnahme: Orchestrator-Commits auf `task-state.json`)                                                                                                |
| **R-BRANCH-02** | Feature-Branches leben maximal **3 Arbeitstage** — danach Merge oder Split in kleinere Branches                                                                                                   |
| **R-BRANCH-03** | Jeder Branch referenziert eine **TASK-ID** aus `tasks.md` (Ausnahme: `docs/` und `hotfix/`)                                                                                                       |
| **R-BRANCH-04** | Vor dem Merge: Rebase auf aktuellen `master` (kein Merge-Commit, linearer Verlauf)                                                                                                                |
| **R-BRANCH-05** | Nach dem Merge: Branch wird gelöscht (kein Stale-Branch-Clutter)                                                                                                                                  |
| **R-BRANCH-06** | Orchestrator-Slots (ORCH-A bis ORCH-L) dürfen direkt auf `master` committen, **ausschließlich** für: `task-state.json`-Updates und vollständig implementierte Tasks nach ihrem Claiming-Protokoll |

### 3.2 Commit-Message-Konvention: Conventional Commits

Alle Commits folgen der **Conventional Commits v1.0.0**-Spezifikation:

```
<type>(<scope>): <kurzbeschreibung> (<TASK-ID>)

[optionaler Body: Was und Warum, nicht Wie]

[optionaler Footer: Breaking Changes, Referenzen]
```

#### Typen

| Typ        | Bedeutung                                      | Changelog-Sektion | Beispiel                                                        |
| ---------- | ---------------------------------------------- | ----------------- | --------------------------------------------------------------- |
| `feat`     | Neues Feature                                  | ✨ Features       | `feat(connectors): Google Calendar Konnektor (TASK-049)`        |
| `fix`      | Bugfix                                         | 🐛 Fixes          | `fix(auth): Token-Rotation bei abgelaufenem Refresh (TASK-087)` |
| `refactor` | Code-Umstrukturierung (kein Feature, kein Fix) | –                 | `refactor(processing): Chunking-Pipeline vereinfacht`           |
| `perf`     | Performance-Verbesserung                       | ⚡ Performance    | `perf(search): Weaviate-Batch-Query optimiert`                  |
| `test`     | Tests hinzufügen/ändern                        | –                 | `test(api): Briefing-Endpunkt-Tests ergänzt (TASK-108)`         |
| `docs`     | Dokumentation                                  | 📚 Docs           | `docs: ADR-013 Caching-Strategie erstellt`                      |
| `chore`    | Wartung, Tooling, Dependencies                 | –                 | `chore: Pre-Commit-Hooks konfiguriert`                          |
| `ci`       | CI/CD-Änderungen                               | –                 | `ci: GitHub Actions Pipeline hinzugefügt`                       |
| `build`    | Build-System oder Dependencies                 | –                 | `build: Weaviate-Client auf 4.11.0 aktualisiert`                |
| `security` | Sicherheits-Fix                                | 🔒 Security       | `security(auth): SQL-Injection in User-Suche gefixt`            |
| `claim`    | Orchestrator-Task-Claiming                     | –                 | `claim: ORCH-E nimmt TASK-041 in Bearbeitung`                   |

#### Scopes (erlaubt)

```
connectors, ingestion, processing, storage, search, briefing, graph, scheduler,
api, auth, models, schemas, core, config, db, frontend, infra, ci, docs, deps
```

#### Regeln

| Regel           | Beschreibung                                                                               |
| --------------- | ------------------------------------------------------------------------------------------ |
| **R-COMMIT-01** | Jeder Commit hat einen Typ und eine Kurzbeschreibung — kein leerer oder generischer Text   |
| **R-COMMIT-02** | Feature- und Fix-Commits **müssen** eine TASK-ID im Subject oder Body enthalten            |
| **R-COMMIT-03** | Breaking Changes werden mit `!` markiert: `feat(api)!: Endpunkt-Schema geändert`           |
| **R-COMMIT-04** | Breaking Changes enthalten einen `BREAKING CHANGE:`-Footer mit Migrations-Anleitung        |
| **R-COMMIT-05** | Ein Commit = eine logische Änderung. Kein Mischen von Feature + Refactoring + Formatierung |
| **R-COMMIT-06** | Commit-Beschreibung in der **Imperativ-Form**: „füge hinzu", nicht „hinzugefügt"           |
| **R-COMMIT-07** | Maximale Länge der Subject-Zeile: **72 Zeichen**                                           |
| **R-COMMIT-08** | Body erklärt **Warum**, nicht **Was** (das zeigt der Diff)                                 |

#### Beispiele

```bash
# Feature mit TASK-ID
feat(connectors): BaseConnector ABC mit cursor-basierter Pagination (TASK-041)

Implementiert die abstrakte Basisklasse für alle Datenquellen-Konnektoren.
Cursor-Persistierung über ConnectorState in PostgreSQL.

Refs: ADR-006, ARCHITECTURE.md §3.2

# Bugfix
fix(auth): Token-Rotation schlägt bei abgelaufenem Refresh fehl (TASK-087)

Der Refresh-Flow prüfte das Ablaufdatum des Access-Tokens statt des
Refresh-Tokens. Korrigiert auf refresh_token.expires_at.

# Breaking Change
feat(api)!: Briefing-Response-Schema um sources-Array erweitert (TASK-072)

BREAKING CHANGE: BriefingResponse enthält jetzt ein Pflichtfeld `sources: list[SourceRef]`.
Clients müssen das Feld verarbeiten oder ignorieren.

# Orchestrator-Claiming
claim: ORCH-E nimmt TASK-041 in Bearbeitung

# Dokumentation
docs: ADR-013 Caching-Strategie mit Redis erstellt
```

### 3.3 Code-Review-Standards

#### Wann ist ein Review Pflicht?

| Änderung                                          | Review erforderlich?  | Reviewer                                      |
| ------------------------------------------------- | --------------------- | --------------------------------------------- |
| Feature-Code (`feat/`)                            | ✅ Ja                 | Mind. 1 Entwickler oder KI-Architektur-Review |
| Bugfix (`fix/`)                                   | ✅ Ja                 | 1 Reviewer                                    |
| Sicherheitsrelevant (`security/`, Auth, Crypto)   | ✅ Ja, **2 Reviewer** | 1 Security-kompetent                          |
| DSGVO-relevant (Nutzer-Daten, Löschung, Export)   | ✅ Ja, **2 Reviewer** | 1 DSGVO-kompetent                             |
| Dokumentation (`docs/`)                           | ⚠️ Optional           | Empfohlen für ADRs                            |
| Tooling/CI (`chore/`, `ci/`)                      | ⚠️ Optional           | Bei Pipeline-Änderungen empfohlen             |
| Orchestrator-Commits (`claim`, `task-state.json`) | ❌ Nein               | Automatisiert via Protokoll                   |

#### Review-Checkliste (im PR-Template integriert)

Jeder Reviewer prüft:

- [ ] **Korrektheit:** Logik stimmt, Randfälle behandelt, keine offensichtlichen Bugs
- [ ] **Typisierung:** Vollständige Type Annotations (Python: kein `Any`, TypeScript: kein implizites `any`)
- [ ] **DSGVO:** `owner_id`-Filter in allen DB-Queries, `expires_at` bei neuen Datenstrukturen, keine PII in Logs
- [ ] **Idempotenz:** Schreiboperationen als Upsert, Konnektoren mit Cursor/Watermark
- [ ] **Sicherheit:** Input-Validierung, keine SQL-Injection, keine Secrets im Code, OWASP-Check
- [ ] **Tests:** Neue Funktionalität hat Tests, bestehende Tests nicht gebrochen
- [ ] **Erklärbarkeit:** LLM-Ausgaben haben Quellenreferenzen (`sources: list[SourceRef]`)
- [ ] **Commit-Hygiene:** Conventional Commits, TASK-ID vorhanden, ein Commit = eine Änderung

#### Merge-Regeln

| Regel           | Beschreibung                                                          |
| --------------- | --------------------------------------------------------------------- |
| **R-REVIEW-01** | Kein Merge ohne mindestens 1 Approval (Sicherheit/DSGVO: 2 Approvals) |
| **R-REVIEW-02** | CI-Pipeline muss grün sein (Lint + Type-Check + Tests)                |
| **R-REVIEW-03** | Keine offenen Review-Kommentare mit `[blocking]`-Prefix               |
| **R-REVIEW-04** | Squash-Merge für Feature-Branches (ein sauberer Commit im Trunk)      |
| **R-REVIEW-05** | Merge-Commit-Message folgt Conventional Commits mit TASK-ID           |

### 3.4 Orchestrator-spezifische Git-Regeln

Für parallele KI-Orchestratoren (ORCH-A bis ORCH-L) gelten Sonderregeln:

| Regel         | Beschreibung                                                                                               |
| ------------- | ---------------------------------------------------------------------------------------------------------- |
| **R-ORCH-01** | Orchestratoren committen direkt auf `master` — kein Branch/PR (Geschwindigkeit)                            |
| **R-ORCH-02** | `task-state.json`-Änderungen sind **immer** atomare Einzelcommits                                          |
| **R-ORCH-03** | Implementation-Commits enthalten TASK-ID und Orchestrator-Slot: `feat(connectors): ... (TASK-041, ORCH-E)` |
| **R-ORCH-04** | Vor jedem `git push`: `git pull --rebase` um Konflikte zu vermeiden                                        |
| **R-ORCH-05** | Bei Merge-Konflikten in `task-state.json`: Manuell resolven (eigene Felder bearbeiten, fremde behalten)    |
| **R-ORCH-06** | Code-Qualität wird durch Pre-Commit-Hooks sichergestellt (Lint, Type-Check)                                |

---

## 4. Entscheidungsdokumentation (ADR-Framework)

### 4.1 Wann wird ein ADR erstellt?

Ein Architecture Decision Record ist **Pflicht** bei:

| Trigger                         | Beispiel                                             |
| ------------------------------- | ---------------------------------------------------- |
| Technologiewahl                 | Neue Datenbank, neues Framework, neuer Service       |
| Architekturmuster               | Caching-Strategie, Event-Sourcing, Service-Split     |
| Sicherheitsarchitektur          | Verschlüsselungsansatz, Auth-Mechanismus             |
| DSGVO-relevante Architektur     | Datenflüsse zu externen Diensten, Retention-Policies |
| Signifikante Trade-offs         | Performance vs. Konsistenz, Self-Host vs. Cloud      |
| Abweichung von bestehenden ADRs | Revision oder Ablösung einer früheren Entscheidung   |

Ein ADR ist **nicht nötig** bei:

- Bugfixes, Code-Formatierung, Dependency-Updates (minor)
- Implementierungsdetails innerhalb eines bereits entschiedenen Rahmens

### 4.2 ADR-Prozess

```
1. Bedarf erkennen     → Trigger aus obiger Liste
2. Nummer vergeben     → Nächste freie Nummer (aktuell: 013+)
3. Template kopieren   → docs/adr/000-template.md als Basis
4. Entwurf schreiben   → Alle Pflichtfelder ausfüllen (siehe 4.3)
5. Review              → Mind. 1 Reviewer (Sicherheit/DSGVO: 2)
6. Status setzen       → "Vorgeschlagen" → "Akzeptiert" | "Abgelehnt"
7. Committen           → docs: ADR-013 <Titel> erstellt
8. Verlinken           → In ARCHITECTURE.md und relevanten tasks.md-Einträgen referenzieren
```

### 4.3 Pflichtfelder im ADR

Jedes ADR **muss** folgende Sektionen enthalten (Vorlage: `docs/adr/000-template.md`):

| Sektion                      | Pflicht | Beschreibung                                                           |
| ---------------------------- | ------- | ---------------------------------------------------------------------- |
| **Status**                   | ✅      | `Vorgeschlagen` / `Akzeptiert` / `Abgelehnt` / `Ersetzt durch ADR-XXX` |
| **Datum**                    | ✅      | Erstellungsdatum                                                       |
| **Entscheider**              | ✅      | Wer hat die Entscheidung getroffen?                                    |
| **Kontext**                  | ✅      | Problem/Anforderung in 2–5 Sätzen                                      |
| **Entscheidung**             | ✅      | Klare Aussage: „Wir werden X tun, weil Y."                             |
| **Optionen bewertet**        | ✅      | Tabellenformat: ≥ 3 Alternativen mit Vor-/Nachteilen                   |
| **Konsequenzen**             | ✅      | Positive + Negative + Offene Fragen                                    |
| **DSGVO-Implikationen**      | ✅      | Welche personenbezogene Daten betroffen? Löschbarkeit?                 |
| **Sicherheitsimplikationen** | ✅      | Welche Risiken? Wie mitigiert?                                         |
| **Revisionsdatum**           | ✅      | Wann wird die Entscheidung erneut geprüft? (Standard: 12 Monate)       |

### 4.4 ADR-Status-Lifecycle

```
Vorgeschlagen ──→ Akzeptiert ──→ [Ersetzt durch ADR-XXX]
        │                            ↑
        └──→ Abgelehnt               │
                                     └── Neues ADR mit Verweis auf altes
```

### 4.5 ADR-Querverweise

- Jedes ADR wird in `ARCHITECTURE.md` im passenden Abschnitt referenziert
- Tasks, die auf einer ADR basieren, verlinken diese in ihrem `Quelle`-Feld
- Wenn ein ADR ersetzt wird: Altes ADR bekommt `Status: Ersetzt durch ADR-XXX`, neues ADR referenziert das alte im Kontext

---

## 5. Task- und Wissensmanagement

### 5.1 Task-Lifecycle

Jede Aufgabe im PWBS durchläuft einen definierten Lifecycle:

```
┌──────────┐     ┌─────────────┐     ┌──────────┐     ┌──────────┐
│  Backlog  │ ──→ │   Claimed   │ ──→ │  In Work  │ ──→ │   Done   │
│  (open)   │     │(in_progress)│     │           │     │  (done)  │
└──────────┘     └─────────────┘     └──────────┘     └──────────┘
      │                                    │
      ↓                                    ↓
┌──────────┐                        ┌──────────┐
│ Blocked  │                        │ Skipped  │
│(blocked) │                        │(skipped) │
└──────────┘                        └──────────┘
```

### 5.2 Task-Definition (Pflichtfelder in tasks.md)

Jede Task-Definition in `tasks.md` **muss** enthalten:

| Feld                    | Format                                             | Pflicht | Beschreibung                         |
| ----------------------- | -------------------------------------------------- | ------- | ------------------------------------ |
| **TASK-ID**             | `TASK-XXX` (3-stellig, fortlaufend)                | ✅      | Eindeutige Kennung                   |
| **Titel**               | Imperativ, max. 80 Zeichen                         | ✅      | Was wird getan?                      |
| **Priorität**           | P0 / P1 / P2 / P3                                  | ✅      | Kritikalität                         |
| **Bereich**             | Backend / Frontend / Infra / etc.                  | ✅      | Technischer Bereich                  |
| **Aufwand**             | XS / S / M / L / XL                                | ✅      | Geschätzter Aufwand                  |
| **Status**              | 🔴 Offen / 🟡 In Arbeit / 🟢 Fertig / ⛔ Blockiert | ✅      | Aktueller Zustand                    |
| **Quelle**              | Referenz auf PRD, ADR, Architektur-Dokument        | ✅      | Warum gibt es diese Aufgabe?         |
| **Abhängig von**        | TASK-IDs oder `–`                                  | ✅      | Blocker                              |
| **Blockiert**           | TASK-IDs oder `–`                                  | ✅      | Was wird durch diese Task entblockt? |
| **Beschreibung**        | Prosatext, 3–8 Sätze                               | ✅      | Was genau ist zu tun?                |
| **Acceptance Criteria** | Checkbox-Liste, testbar                            | ✅      | Wann ist die Task fertig?            |
| **Technische Hinweise** | Implementierungshinweise                           | ✅      | Wie soll es umgesetzt werden?        |

### 5.3 Duale Datenhaltung: Mensch + Maschine

Das PWBS verwendet ein **Zweiteiliges System** für Task-Management:

```
tasks.md                          docs/orchestration/task-state.json
├── Menschenlesbar                ├── Maschinenlesbar
├── Vollständige Beschreibungen   ├── Nur Status + Koordination
├── Acceptance Criteria           ├── Blocking-Graph
├── Technische Hinweise           ├── Claiming-Informationen
└── Wird manuell gepflegt         └── Wird atomar via Git aktualisiert
```

| Datei                    | Wer schreibt?                      | Wann?                                 |
| ------------------------ | ---------------------------------- | ------------------------------------- |
| `tasks.md`               | Mensch (Projektmanager, Architekt) | Bei Planung neuer Phasen/Tasks        |
| `task-state.json`        | Orchestrator (KI-Agent)            | Bei Claim, Start, Completion          |
| `task-state.schema.json` | Mensch                             | Bei Änderung des Koordinationsmodells |

### 5.4 Wissenskopplung: Task ↔ Dokumente ↔ Code

Jede Aufgabe ist durch explizite Referenzen an das Projektwissen gekoppelt:

```
TASK-041 (BaseConnector ABC)
│
├── Quelle:    PRD-SPEC.md §FR-002, ARCHITECTURE.md §3.2
├── ADR:       ADR-006 (Modularer Monolith)
├── Prompt:    .github/prompts/new-connector.prompt.md
├── Instruktionen: .github/instructions/agents.instructions.md
├── Code:      pwbs/connectors/base.py
├── Tests:     tests/test_connectors/test_base_connector.py
├── Commit:    feat(connectors): BaseConnector ABC (TASK-041, ORCH-E)
└── Entblockt: TASK-042, TASK-049, TASK-050, TASK-051, TASK-052
```

Diese Traceability-Kette ermöglicht:

- **Rückwärts:** Von Code → Commit → Task → Anforderung → Persona
- **Vorwärts:** Von Anforderung → Task → Code → Test → Deployment

### 5.5 Task-Koordination für parallele Orchestratoren

Die Koordination zwischen parallelen KI-Agenten ist in `ORCHESTRATION.md` vollständig definiert. Kernregeln:

| Regel         | Beschreibung                                                                    |
| ------------- | ------------------------------------------------------------------------------- |
| **R-TASK-01** | Jeder Orchestrator bearbeitet **nur Tasks seines Streams**                      |
| **R-TASK-02** | Ein Task wird erst gestartet, wenn **alle `blocked_by`-Tasks `done` sind**      |
| **R-TASK-03** | Claiming ist atomar: JSON-Änderung + `git commit` + `git push` in einem Schritt |
| **R-TASK-04** | Reihenfolge innerhalb eines Streams: **P0 → P1 → P2 → P3**                      |
| **R-TASK-05** | Wenn alle Tasks eines Streams `done` sind: Orchestrator meldet Completion       |
| **R-TASK-06** | Bei Fehlern: Task auf `blocked` setzen mit `notes`-Feld, nächste Task beginnen  |

### 5.6 Wissensmanagement-Schichten

```
Schicht 1: Strategisch       → PRD-SPEC.md, ROADMAP.md, vision-wissens-os.md
Schicht 2: Architektur        → ARCHITECTURE.md, docs/adr/*.md, AGENTS.md
Schicht 3: Prozess            → GOVERNANCE.md (dieses Dokument), ORCHESTRATION.md
Schicht 4: Operativ           → tasks.md, task-state.json, docs/backlog/*.md
Schicht 5: Implementierung    → Code, Tests, Inline-Kommentare
Schicht 6: Kontext (KI)       → .github/instructions/*.md, .github/prompts/*.md
```

---

## 6. Code-Qualität und Enforcement

### 6.1 Pre-Commit-Hooks

Automatische Qualitätsprüfungen vor jedem Commit (definiert in `.pre-commit-config.yaml`):

| Hook                      | Prüfung                                                  | Blockiert Commit?   |
| ------------------------- | -------------------------------------------------------- | ------------------- |
| `ruff check`              | Python-Linting (Ruff)                                    | ✅ Ja               |
| `ruff format --check`     | Python-Formatierung                                      | ✅ Ja               |
| `mypy`                    | Python-Typenprüfung                                      | ✅ Ja               |
| `prettier --check`        | Frontend-Formatierung (TS, CSS, JSON, MD)                | ✅ Ja               |
| `eslint`                  | TypeScript-Linting                                       | ✅ Ja               |
| `check-added-large-files` | Keine Dateien > 1 MB                                     | ✅ Ja               |
| `detect-private-key`      | Keine Private Keys im Repo                               | ✅ Ja               |
| `no-commit-to-branch`     | Kein direkter Commit auf `master` (außer Orchestratoren) | ⚠️ Nur für Menschen |
| `trailing-whitespace`     | Kein Trailing Whitespace                                 | ✅ Ja               |
| `end-of-file-fixer`       | Dateiende-Newline                                        | ✅ Ja               |
| `check-json`              | JSON-Syntax valid                                        | ✅ Ja               |
| `check-yaml`              | YAML-Syntax valid                                        | ✅ Ja               |

### 6.2 CI/CD-Pipeline (GitHub Actions)

```
Push/PR → Lint → Type-Check → Unit-Tests → Integration-Tests → Build → (Deploy)
```

| Stage                 | Tools                                                  | Fehlschlag =                 |
| --------------------- | ------------------------------------------------------ | ---------------------------- |
| **Lint**              | Ruff (Python), ESLint (TypeScript)                     | ❌ PR nicht mergebar         |
| **Type-Check**        | Mypy (Python), `tsc --noEmit` (TypeScript)             | ❌ PR nicht mergebar         |
| **Unit-Tests**        | pytest (Backend), Jest falls eingerichtet (Frontend)   | ❌ PR nicht mergebar         |
| **Integration-Tests** | pytest + Docker-Services (PostgreSQL, Weaviate, Neo4j) | ❌ PR nicht mergebar         |
| **Build**             | Docker Build (Backend), `next build` (Frontend)        | ❌ PR nicht mergebar         |
| **Security-Audit**    | `pip-audit`, `npm audit`, DSGVO-Checkliste             | ⚠️ Warning (blockiert nicht) |

### 6.3 Test-Standards

| Regel         | Beschreibung                                                                |
| ------------- | --------------------------------------------------------------------------- |
| **R-TEST-01** | Jedes neue Feature hat **mindestens Unit-Tests** (pytest / Jest)            |
| **R-TEST-02** | DB-Operationen haben **Integration-Tests** mit echten DB-Instanzen (Docker) |
| **R-TEST-03** | Kein Netzwerkzugriff in Unit-Tests — alle externen Abhängigkeiten gemockt   |
| **R-TEST-04** | Fixtures in `conftest.py` für DB-Sessions, Auth-Tokens, Mock-LLM-Clients    |
| **R-TEST-05** | Test-Namenskonvention: `test_<was>_<szenario>_<erwartung>()`                |
| **R-TEST-06** | Mindest-Coverage-Ziel: 80% Line-Coverage für `pwbs/` Package                |
| **R-TEST-07** | E2E-Tests prüfen vollständige API-Flows (Auth → CRUD → Suche → Briefing)    |

---

## 7. Release- und Changelog-Management

### 7.1 Versionierung: Semantic Versioning 2.0

```
MAJOR.MINOR.PATCH
  │      │     └── Bugfixes, keine API-Änderung
  │      └──────── Neue Features, abwärtskompatibel
  └─────────────── Breaking Changes
```

| Phase                  | Versionierungsmodell                                             |
| ---------------------- | ---------------------------------------------------------------- |
| MVP (Phase 2)          | `0.x.y` — Breaking Changes erlaubt, MINOR = Feature, PATCH = Fix |
| Private Beta (Phase 3) | `0.x.y` — API stabilisiert sich, Breaking Changes dokumentiert   |
| Launch (Phase 4+)      | `1.0.0+` — Volle SemVer-Garantie                                 |

### 7.2 Changelog-Pflege

Die Datei `CHANGELOG.md` wird bei jedem Release aktualisiert:

```markdown
# Changelog

Alle nennenswerten Änderungen am PWBS werden in diesem Dokument festgehalten.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/spec/v2.0.0.html).

## [Unreleased]

### ✨ Features

- feat(connectors): BaseConnector ABC mit cursor-basierter Pagination (TASK-041)

### 🐛 Fixes

### ⚡ Performance

### 🔒 Security

### 📚 Docs

### 💥 Breaking Changes
```

| Regel              | Beschreibung                                                                       |
| ------------------ | ---------------------------------------------------------------------------------- |
| **R-CHANGELOG-01** | Jeder `feat`- und `fix`-Commit bekommt einen Eintrag in `[Unreleased]`             |
| **R-CHANGELOG-02** | Breaking Changes werden in einer eigenen Sektion gelistet mit Migrations-Anleitung |
| **R-CHANGELOG-03** | Bei Release: `[Unreleased]` wird zu `[x.y.z] - YYYY-MM-DD` umbenannt               |
| **R-CHANGELOG-04** | Einträge enthalten die TASK-ID für Traceability                                    |

---

## 8. Sicherheits- und DSGVO-Gates

### 8.1 Security-Gate bei Pull Requests

Jeder PR, der einen der folgenden Bereiche berührt, durchläuft ein **Security-Gate**:

| Bereich                           | Gate-Anforderung                                      |
| --------------------------------- | ----------------------------------------------------- |
| Authentifizierung / Autorisierung | 2 Reviewer, OWASP-Checkliste                          |
| Verschlüsselung / Key-Management  | 2 Reviewer, Crypto-Review                             |
| Neue externe API-Aufrufe          | DSGVO-Impact-Assessment im PR                         |
| Nutzer-Daten-Verarbeitung         | `owner_id`-Filter verifiziert, `expires_at` vorhanden |
| LLM-Aufrufe                       | Keine PII im Prompt, Structured Output erzwungen      |
| Datenbank-Migrationen             | Rollback-Fähigkeit geprüft, keine Datenverluste       |

### 8.2 DSGVO-Checkliste für neue Features

Vor dem Merge von Features, die Nutzer-Daten verarbeiten:

- [ ] `owner_id` in allen DB-Queries als Filter (keine Cross-User-Leaks)
- [ ] `expires_at` bei neuen Datenstrukturen gesetzt (Speicherbegrenzung)
- [ ] Lösch-Kaskade implementiert (Art. 17 — Recht auf Löschung)
- [ ] Export-Fähigkeit gewährleistet (Art. 20 — Datenportabilität)
- [ ] Keine PII in Logs, Fehlermeldungen oder Metriken
- [ ] LLM-Prompts enthalten keine unnötigen personenbezogenen Daten
- [ ] Datenverarbeitungszweck im Code-Kommentar oder ADR dokumentiert

---

## 9. Onboarding-Checkliste

### Für neue Entwickler (Mensch)

- [ ] Repository klonen und `.env`-Datei aus Vorlage erstellen
- [ ] `make setup` ausführen (Python-Env + Node-Deps + Pre-Commit-Hooks)
- [ ] Docker Compose starten: `docker compose up -d`
- [ ] Backend-Tests ausführen: `make test-backend`
- [ ] Frontend-Dev-Server starten: `make dev-frontend`
- [ ] Dieses Dokument (GOVERNANCE.md) vollständig lesen
- [ ] ARCHITECTURE.md und AGENTS.md lesen
- [ ] Zugewiesenen Stream und Tasks in `ORCHESTRATION.md` identifizieren

### Für neue KI-Agenten (Orchestratoren)

1. `.github/copilot-instructions.md` als Kontext laden
2. `AGENTS.md` lesen — eigene Rolle und Modul-Boundaries verstehen
3. `ORCHESTRATION.md` lesen — zugewiesenen Slot und Stream identifizieren
4. `docs/orchestration/task-state.json` lesen — nächste offene Task finden
5. `tasks.md` lesen — vollständige Task-Definition mit Acceptance Criteria laden
6. Relevante `.github/instructions/*.md` laden (kontextabhängig)
7. Claiming-Protokoll ausführen (Abschnitt 3 in ORCHESTRATION.md)

---

## 10. Governance-Änderungen

### Änderungsprozess für dieses Dokument

| Schritt | Beschreibung                                                               |
| ------- | -------------------------------------------------------------------------- |
| 1       | Bedarf identifizieren (neue Regel, Regeländerung, Regelstreichung)         |
| 2       | Änderung als PR mit `docs/`-Branch einreichen                              |
| 3       | Begründung im PR-Body dokumentieren                                        |
| 4       | Review durch mindestens 1 Person mit Architektur-Verantwortung             |
| 5       | Versionsnummer in diesem Dokument hochzählen (SemVer)                      |
| 6       | Commit: `docs: GOVERNANCE.md auf v1.1.0 aktualisiert — <Kurzbeschreibung>` |

### Regel-Nummerierung

Alle Regeln in diesem Dokument folgen dem Schema `R-<BEREICH>-XX`:

```
R-STRUCT-XX    → Projektstruktur
R-BRANCH-XX    → Branching
R-COMMIT-XX    → Commit-Konventionen
R-REVIEW-XX    → Code-Review
R-ORCH-XX      → Orchestrator-Regeln
R-TEST-XX      → Test-Standards
R-CHANGELOG-XX → Changelog
```

Neue Regeln werden fortlaufend nummeriert. Bestehende Regeln werden **nie** umnummeriert (Referenzstabilität).

---

**Dieses Dokument ist verbindlich für alle Contributor (Mensch und KI) am PWBS-Projekt.**
**Nächstes Review: September 2026**
