# Changelog

Alle nennenswerten Änderungen am PWBS werden in diesem Dokument festgehalten.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/spec/v2.0.0.html).

## [Unreleased]

### 🏗️ Refactoring – MVP-Fokussierung

#### Schritt 1: Out-of-Scope Module nach `_deferred/` verschoben
- **Verschobene Module:** billing, teams, rbac, marketplace, developer, sso → `_deferred/`
- **Verschobene Routes:** billing.py, rbac.py, marketplace.py, developer.py, organizations.py, sso.py → `_deferred/routes/`
- **Verschobene Tests:** test_billing, test_teams, test_rbac, test_marketplace, test_developer, test_sso → `_deferred/tests/`
- **Deaktivierte Router in main.py:** 8 Router-Includes mit `# DEFERRED: Phase 3` kommentiert
- **api_key_auth.py:** Validierungslogik aus developer-Modul inlined (Public API bleibt funktional)
- **ORM-Models:** Bleiben in `models/__init__.py` für Alembic-Migrationsintegrität
- **Dokumentation:** `_deferred/README.md` mit Reaktivierungsanleitung erstellt

#### Schritt 2: Phase-3 Konnektoren deaktiviert (nur Kern-4 aktiv)
- **Aktive Konnektoren (Kern-4):** Google Calendar, Notion, Zoom, Obsidian
- **Deaktivierte Konnektoren:** Gmail, Slack, Outlook, Google Docs → `_deferred/connectors/`
- **Deaktivierte Integration:** `integrations/slack/` → `_deferred/integrations/slack/`
- **Verschobene Tests:** test_gmail, test_slack, test_outlook, test_google_docs → `_deferred/tests/`
- **Deaktivierter Router:** webhooks (Gmail Pub/Sub + Slack Events) in main.py kommentiert
- **connectors.py Route:** Phase-3 Einträge in `_CONNECTOR_META`, `_AUTH_URLS`, `_SCOPES`, Token-Maps kommentiert
- **Verifiziert:** 320 Connector-Tests bestehen, 18/18 aktive Module importieren fehlerfrei

#### Schritt 3: Feature Flags – beibehalten (bereits MVP-tauglich)
- **Analyse-Ergebnis:** Feature-Flags-Service ist nicht over-engineered – unterstützt bereits ENV-Overrides als höchste Priorität (`FEATURE_FLAGS_OVERRIDE`)
- **Aktueller Status:** Kein Business-Logik-Code nutzt Feature Flags; Service ist opt-in
- **Entscheidung:** Beibehalten. ENV-Override erfüllt MVP-Anforderungen; DB-Backend ist vorbereitet für Phase 3

#### Schritt 4: Vertikale Profile – beibehalten (bereits auf Default eingefroren)
- **Analyse-Ergebnis:** Standard-Profil "general" ist bereits Default; kein Supplement, keine Speziallogik
- **Einziger Nutzungsort:** `briefing/generator.py` (optionaler System-Prompt-Supplement)
- **entity_priorities/ner_focus:** Definiert, aber nirgends in Processing/Search implementiert → kein Overhead
- **Entscheidung:** Beibehalten. Dormante Konfiguration kostet nichts; entfernen würde Tests brechen

#### Schritt 5: Datenbank-Architektur vereinfacht – Neo4j optional
- **Analyse-Ergebnis:** Neo4j Knowledge Graph wird in der MVP-Pipeline nicht beschrieben (GraphBuilder nie aufgerufen)
- **Problem:** App crashte beim Startup wenn Neo4j nicht erreichbar → kritische einzelne Fehlerstelle
- **neo4j_client.py:** `get_neo4j_driver()` gibt `None` zurück bei Verbindungsfehlern; `_init_failed`-Flag verhindert wiederholte Timeouts
- **main.py lifespan:** Neo4j-Init mit None-Check + Warning-Log umschlossen
- **docker-compose.yml:** Neo4j-Service hinter `profiles: ["graph"]` verschoben (optional mit `--profile graph`)
- **Bestehende Fallbacks:** Briefing-Module nutzen bereits `NullGraphService`; Knowledge-API hat try/except mit PostgreSQL-Fallback
- **Verifiziert:** App startet ohne Neo4j; alle Health-Checks graceful degraded; 133+ Tests bestehen

### ✨ Features

- Onboarding-Wizard mit 4-Schritt-Flow: Welcome → Connector → Sync → Briefing (LAUNCH-UX-009)
- Sync-Fortschrittsanzeige im Onboarding-Wizard mit Echtzeit-Status (LAUNCH-UX-004)
- Onboarding-Fortschritt persistent in localStorage gespeichert (LAUNCH-UX-005)
- Wizard Zurück-Navigation auf allen Schritten inkl. Briefing (LAUNCH-UX-006)
- Skip-Banner nach Wizard-Abbruch: persistent, dismissible, mit CTA (LAUNCH-UX-008)
- 10 spezifische Empty States mit motivierenden CTAs für alle Dashboard-Seiten (LAUNCH-UX-007)
- Nutzerfreundliche Error-Seiten mit MappedErrorCard auf allen Dashboard-Routen (LAUNCH-UX-001)
- Demo-Briefing Fallback für neue Nutzer ohne Datenquellen (LAUNCH-UX-003)
- Auto-generiertes Initial-Briefing nach erstem Connector-Sync (feat: pipeline)
- PostHog Self-Hosted Analytics mit pseudonymisierten User-IDs (LAUNCH-ANA-001)
- Server-Side Core Events: connector_oauth_started, briefing_generated etc. (LAUNCH-ANA-002)
- PostHog identify() mit User Properties (LAUNCH-ANA-003)

### 🔒 Security

- Security Audit CI-Job mit pip-audit + npm audit (LAUNCH-REL-001)
- RSA-Key-Guard: Produktionsstart blockiert ohne gültige JWT-Keys (LAUNCH-REL-002)
- Alembic-Head-Validierung im Release-Prozess (LAUNCH-REL-004)
- Content-Security-Policy Header implementiert (LAUNCH-REL-005)
- CORS auf explizite Methoden und Header eingeschränkt (LAUNCH-REL-006)
- Rate-Limit In-Memory Fallback statt Fail-Open bei Redis-Ausfall (fix: security)
- Audit-Trail für alle sicherheitsrelevanten Aktionen (LAUNCH-LEG-005)

### 📚 Docs

- ADR-016: MVP-Fokussierung – 5-Schritte-Refactoring dokumentiert (`docs/adr/016-mvp-fokussierung-refactoring.md`)
- AGB / Nutzungsbedingungen erstellt (LAUNCH-LEG-003)
- Impressum erstellt (LAUNCH-LEG-002)
- Datenschutzerklärung erstellt (LAUNCH-LEG-001)
- Deployment-Runbook (`docs/runbooks/deployment.md`) (LAUNCH-OPS-003)
- Database-Migration-Runbook mit Rollback-Verfahren (`docs/runbooks/database-migration.md`) (LAUNCH-OPS-006)
- DR-Testprotokoll erstellt (`docs/runbooks/disaster-recovery.md`) (LAUNCH-OPS-004)
- GTM-Storyboard für Produkt-Demo-Video (LAUNCH-GTM-002)

### 🔧 Ops

- Sentry-Integration verifiziert und SENTRY_DSN konfiguriert (LAUNCH-OPS-001)
- Grafana-Alerting für P0/P1-Alerts → Discord (LAUNCH-OPS-002)
- Dependabot aktiviert für pip und npm (LAUNCH-OPS-005)

#### Test-Suite Performance: von ∞ Timeout auf 72s
- **Root Cause 1:** DB-Singletons (Redis, Weaviate) wurden in Tests nicht gemockt → echte Verbindungsversuche → Timeout
  - `tests/conftest.py`: Autouse-Fixture `_isolate_db_singletons` patcht `_client`-Singletons mit Mocks
  - Betrifft alle Tests die `create_app()` mit `AsyncClient` aufrufen (lifespan triggert DB-Init)
- **Root Cause 2:** Locust/gevent-Import deadlockt mit pytest Event Loop auf Windows
  - `test_load_infra.py`: Locust-Import-Tests mit `skipif` markiert
- **Konfiguration:** `pytest-timeout>=2.3.0` als Dev-Dependency; `--timeout=30` als Default in `pyproject.toml`
- **Ergebnis:** 2183 Tests in 72s (vorher: einzelne Verzeichnisse hängten 300s+)

### 🔒 Security

### 📚 Docs

- ADR-016: MVP-Fokussierung – 5-Schritte-Refactoring dokumentiert (`docs/adr/016-mvp-fokussierung-refactoring.md`)

### 💥 Breaking Changes

---

## [0.1.0] - 2026-03-13

### ✨ Features

- Embedding PoC: 51 Dokumente aus 2 Quellen in Weaviate indexiert (TASK-001)
- Semantische Suche über PoC-Daten mit CLI (TASK-002)

### 📚 Docs

- DSGVO-Erstkonzept mit Mapping der Art. 5/6/15/17/20/25/32 (TASK-003)
- Verschlüsselungsstrategie: Envelope Encryption mit KEK/DEK (TASK-004)
- 12 Architecture Decision Records (ADR-001 bis ADR-012) (TASK-005)
- Interview-Leitfaden und Auswertungstemplate (TASK-006)
- Interview-Auswertungssystem mit Dashboard + CSV (TASK-007)
- PoC-Ergebnisse mit Go-Empfehlung für Phase 2 (TASK-008)
