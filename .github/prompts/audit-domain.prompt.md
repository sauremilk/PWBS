---
agent: agent
description: "Domänenspezifisches Audit: Führt Tiefenanalyse für einen einzelnen Qualitätsbereich durch. Parametrisiert für 10 Domänen."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Domänen-Audit: ${input:domain}

Du führst ein fokussiertes Tiefenaudit für den Bereich **${input:domain}** durch.

**Domain:** ${input:domain:security / architecture / code-quality / testing / documentation / infrastructure / performance / dependencies / monitoring / prompts}
**Scope:** ${input:scope:Spezifischer Pfad oder "all" für gesamten Bereich}

---

## Verfügbare Domänen

| Domain           | Prüfschwerpunkte                                                 |
| ---------------- | ---------------------------------------------------------------- |
| `security`       | OWASP Top 10, DSGVO, owner_id-Audit, OAuth, PII-Scanning         |
| `architecture`   | Modul-Grenzen, Datenflüsse, Schichtentrennung, Soll-Ist-Abgleich |
| `code-quality`   | Typing, Patterns, Konsistenz, Komplexität, Idiomatik             |
| `testing`        | Coverage, Test-Patterns, Edge Cases, Fixtures, CI-Readiness      |
| `documentation`  | ADRs, README, API-Docs, Inline-Doku, Cross-Doc-Konsistenz        |
| `infrastructure` | Docker, Terraform, CI/CD, Dev-Environment, Deployment            |
| `performance`    | DB-Queries, API-Latenz, Caching, Embeddings, Frontend-Bundles    |
| `dependencies`   | CVEs, Versionen, Tech Debt, Deprecated Packages, Upgrades        |
| `monitoring`     | Logging, Health-Checks, Metriken, Alerting, Tracing              |
| `prompts`        | Prompt-Konsistenz, Instructions-Alignment, Opus-4.6-Optimierung  |

---

## Phase 0: Inventar

Erfasse den aktuellen Zustand des Bereichs **${input:domain}**:

1. **Was existiert?** Relevante Dateien und Konfigurationen identifizieren
2. **Implementierungsgrad?** Vollständig / Partial / Stub / Nicht vorhanden
3. **Letzte Änderungen?** `git log` für relevante Dateien
4. **Bekannte Probleme?** `problems`-Tool für Compiler-/Lint-Fehler

---

## Phase 1: Domänenspezifische Analyse

### Bei `security`:

**DSGVO-Audit:**

- [ ] Jede DB-Query mit User-Bezug: `WHERE owner_id = ...` vorhanden
- [ ] Alle nutzerbezogenen Modelle haben `owner_id` und `expires_at`
- [ ] Keine PII in Logs (suche nach `logger.*` mit Content/Email/Token)
- [ ] DELETE CASCADE für User-Löschung implementiert
- [ ] Keine Nutzerdaten für externes LLM-Training

**OWASP Top 10:**

- [ ] A01 Broken Access Control: user_id aus JWT, nie aus Request-Body
- [ ] A02 Cryptographic Failures: argon2/bcrypt, Token verschlüsselt
- [ ] A03 Injection: Parametrisierte Queries (SQL, Cypher)
- [ ] A05 Security Misconfiguration: CORS, Debug-Mode, Headers
- [ ] A07 Auth Failures: JWT RS256, kurze Token-TTL, Rate Limiting
- [ ] A10 SSRF: URL-Validierung, private IP-Blocking

**OAuth-Sicherheit:**

- [ ] PKCE implementiert
- [ ] State-Parameter validiert
- [ ] Refresh-Token verschlüsselt gespeichert
- [ ] Token-Rotation bei Refresh

---

### Bei `architecture`:

**Modul-Grenzen:**

```
pwbs/api/         → darf: core, schemas, services
pwbs/connectors/  → darf: core, models, storage
pwbs/processing/  → darf: core, models, storage
pwbs/briefing/    → darf: core, search, graph, prompts
pwbs/search/      → darf: core, storage, models
pwbs/graph/       → darf: core, storage, models
pwbs/core/        → darf: NICHTS aus pwbs/
```

- [ ] Keine Imports gegen erlaubte Richtung
- [ ] Keine zirkulären Abhängigkeiten
- [ ] Module kommunizieren über Interfaces, nicht HTTP (MVP)

**Datenfluss:**

- [ ] Ingestion → Processing → Storage klar definiert
- [ ] Search → Briefing → API Response klar definiert
- [ ] Fehlerbehandlung an jeder Transition

**Soll-Ist-Abgleich:**

- [ ] ARCHITECTURE.md vs. tatsächlicher Code
- [ ] AGENTS.md vs. implementierte Agenten

---

### Bei `code-quality`:

**Python Backend:**

- [ ] Vollständige Type Annotations (kein implizites `Any`)
- [ ] `list[X]`, `dict[K,V]` statt `List`, `Dict` (Python 3.12+)
- [ ] Pydantic v2: `model_config`, `model_dump()`, `@model_validator`
- [ ] FastAPI: Response vor Default-Dependencies, Status-Codes explizit
- [ ] Async: `async def` für alle I/O, kein Blocking im Event-Loop
- [ ] Exceptions: PWBSError-Hierarchie, strukturierte HTTPException
- [ ] Imports: Absolut, keine zirkulären, keine Wildcards

**TypeScript Frontend:**

- [ ] Strict Mode, kein `any`
- [ ] Explizite Props-Interfaces
- [ ] Server Components als Default, `"use client"` nur wenn nötig
- [ ] API-Aufrufe nur über `lib/api/`

---

### Bei `testing`:

**Coverage-Map:**
| Source-Modul | Test-Dateien | Geschätzte Coverage | Lücken |
|--------------|-------------|--------------------|---------|

**Test-Qualität:**

- [ ] Benennung: `test_<was>_<szenario>_<ergebnis>`
- [ ] Arrange-Act-Assert Struktur
- [ ] Isolation: Keine Abhängigkeit von Reihenfolge
- [ ] Async: `pytest-asyncio` korrekt konfiguriert

**Fixtures:**

- [ ] Alle externen Abhängigkeiten gemockt
- [ ] Kein echter Netzwerkzugriff in Unit-Tests
- [ ] Factory-Fixtures für flexible Test-Daten

**Edge Cases:**

- [ ] Leere Listen, None-Werte
- [ ] Abgelaufene Tokens, DB-Fehler
- [ ] Duplikat-Ingestion, Rate-Limits

---

### Bei `documentation`:

**Hauptdokumente:**
| Dokument | Existiert? | Aktuell? | Konsistent? |
|----------|-----------|----------|-------------|
| README.md | | | |
| ARCHITECTURE.md | | | |
| ROADMAP.md | | | |
| CHANGELOG.md | | | |
| AGENTS.md | | | |

**ADRs:**

- [ ] Jede Architekturentscheidung dokumentiert
- [ ] Status aktuell (Accepted/Deprecated/Superseded)
- [ ] Alternativen mit Begründung

**Code-Dokumentation:**

- [ ] Module-Level-Docstrings
- [ ] Public-API-Docstrings (Args, Returns, Raises)
- [ ] OpenAPI-Schema vollständig

---

### Bei `infrastructure`:

**Docker:**

- [ ] docker-compose.yml: Health Checks, Volumes, Resource Limits
- [ ] Dockerfile: Multi-Stage, Non-Root, Layer-Caching
- [ ] .dockerignore vollständig

**CI/CD:**

- [ ] GitHub Actions: lint, type-check, test, build, security
- [ ] Makefile: setup, test, lint, build, up, down, migrate

**Dev Environment:**

- [ ] Onboarding funktioniert (clone → up → test)
- [ ] Hot-Reload konfiguriert

---

### Bei `performance`:

**Datenbank:**

- [ ] N+1 Queries identifiziert (Eager Loading nutzen)
- [ ] Indexes auf owner_id, frequently filtered columns
- [ ] Connection Pooling konfiguriert
- [ ] Batch Operations statt Zeile-für-Zeile

**Caching:**

- [ ] Redis für Session/Cache implementiert
- [ ] Cache-Keys mit owner_id (Tenant-Isolation)
- [ ] Cache-Invalidierung bei Datenänderung

**API:**

- [ ] Response-Modelle nur nötige Felder
- [ ] BackgroundTasks für nicht-kritische Operationen
- [ ] Rate Limiting auf allen öffentlichen Endpunkten

---

### Bei `dependencies`:

**Security Audit:**

```bash
cd backend && pip-audit
cd frontend && npm audit
```

**Version-Check:**
| Package | Pinned | Latest | Gap | Breaking Changes? |
|---------|--------|--------|-----|-------------------|

**Tech Debt:**

- [ ] TODO/FIXME/HACK Kommentare inventarisieren
- [ ] `type: ignore` / `noqa` Kommentare prüfen
- [ ] Veraltete Patterns (Pydantic v1, alte SQLAlchemy)

---

### Bei `monitoring`:

**Logging:**

- [ ] Strukturiertes JSON-Format
- [ ] Correlation-ID durchgereicht
- [ ] Keine PII in Logs
- [ ] Log-Levels konsistent

**Health-Checks:**

- [ ] `/health` oder `/healthz` existiert
- [ ] `/ready` prüft DB, Weaviate, Neo4j
- [ ] Timeout < 1s

**Metriken:**

- [ ] Prometheus-Endpunkt `/metrics`
- [ ] Business-Metriken (ingestion, search, briefing)
- [ ] Infrastruktur-Metriken (latency, error-rate)

---

### Bei `prompts`:

**Konsistenz:**

- [ ] YAML-Frontmatter einheitlich (agent, description, tools)
- [ ] Keine widersprüchlichen Anweisungen
- [ ] Terminologie konsistent

**Instructions-Alignment:**

- [ ] Prompts fordern nichts, was Instructions widersprechen
- [ ] Neue Module durch Instructions abgedeckt

**Opus 4.6:**

- [ ] Extended Thinking wo sinnvoll
- [ ] Selbst-Validierung als expliziter Schritt
- [ ] Trade-off-Analysen bei Entscheidungen

---

## Phase 2: Priorisierung

| Prio | Finding | Betroffene Datei | Aufwand | Empfehlung |
| ---- | ------- | ---------------- | ------- | ---------- |
| 🔴   |         |                  |         |            |
| 🟡   |         |                  |         |            |
| 🟢   |         |                  |         |            |
| 🔵   |         |                  |         |            |

---

## Phase 3: Implementierung

**Für 🔴-Findings:** Sofort beheben innerhalb dieses Audits.

**Für 🟡-Findings:** Die Top 5 nach Impact/Aufwand implementieren.

**Für 🟢/🔵-Findings:** Dokumentieren für Follow-up.

Nach jedem Fix:

- [ ] Linting prüfen
- [ ] Tests prüfen
- [ ] Keine Regression eingeführt

---

## Phase 4: Bericht

```markdown
# ${input:domain}-Audit – [Datum]

## Zustandsbild

[Inventar-Zusammenfassung]

## Findings

[Priorisierte Tabelle]

## Durchgeführte Fixes

1. ...

## Offene Empfehlungen

1. ...
```

---

## Opus 4.6 – Kognitive Verstärker

Nutze Extended Thinking für:

1. **Root Cause:** Sind Findings Symptome eines tieferen Problems?
2. **Querverbindungen:** Beeinflusst dieses Finding andere Domänen?
3. **Kontra-Check:** Gibt es gute Gründe, das Finding zu akzeptieren?
4. **Zukunftsprojektion:** Was passiert, wenn das Finding nicht behoben wird?
