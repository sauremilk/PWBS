# PWBS  Entwicklungs-Backlog

**Generiert:** 13. März 2026
**Basis-Dokumente:** ARCHITECTURE.md v0.1.0 | ROADMAP.md | PRD-SPEC.md v0.1.0 | vision-wissens-os.md

---

## Legende

| Feld | Mögliche Werte |
|------|---------------|
| **Priorität** | P0 (kritisch) / P1 (Must-Have MVP) / P2 (Should-Have) / P3 (Could-Have) |
| **Aufwand** | XS (<2h) / S (0.51 Tag) / M (23 Tage) / L (1 Woche) / XL (>1 Woche) |
| **Bereich** | Backend / Frontend / Infra / Auth / DB / LLM / Testing / Docs / DevOps / Mobile |
| **Status** |  Offen /  In Arbeit /  Fertig /  Blockiert |

---


---


---

## Phase 1: Discovery & Proof-of-Concept (Monate 1–3)

---

#### TASK-001: Technischen PoC für Embedding-Generierung implementieren

| Feld             | Wert                                                                   |
| ---------------- | ---------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                         |
| **Bereich**      | Backend                                                                |
| **Aufwand**      | M (2–3 Tage)                                                           |
| **Status**       | 🔴 Offen                                                               |
| **Quelle**       | D2 Phase 1 Kern-Deliverables, D1 Abschnitt 3.2 (Embedding-Generierung) |
| **Abhängig von** | –                                                                      |
| **Blockiert**    | TASK-002                                                               |

**Beschreibung:** Ein eigenständiges Python-Skript erstellen, das Kalendereinträge (Google Calendar) und Obsidian-/Notion-Markdown-Notizen einliest, mittels `text-embedding-3-small` (OpenAI) Embeddings generiert und diese in einer lokalen Weaviate-Instanz speichert. Ziel ist der Nachweis, dass Embedding-Generierung über heterogene Quellen technisch funktioniert.

**Acceptance Criteria:**

- [ ] Mindestens 50 Dokumente aus 2 verschiedenen Quellen (Kalender + Notizen) werden erfolgreich eingelesen und normalisiert
- [ ] Embedding-Vektoren (1536 Dimensionen) werden für alle Dokumente generiert und in Weaviate persistiert
- [ ] Skript ist reproduzierbar ausführbar mit Anleitung in einer README

**Technische Hinweise:** Embedding-Modell `text-embedding-3-small` gemäß D1 Abschnitt 3.2. Lokale Weaviate-Instanz per Docker starten. Chunking vorerst als einfaches Paragraph-Splitting (semantisches Splitting erst im MVP).

---

#### TASK-002: Semantische Suche über PoC-Daten demonstrieren

| Feld             | Wert                                                         |
| ---------------- | ------------------------------------------------------------ |
| **Priorität**    | P0 (kritisch, blockiert alles)                               |
| **Bereich**      | Backend                                                      |
| **Aufwand**      | S (0.5–1 Tag)                                                |
| **Status**       | 🔴 Offen                                                     |
| **Quelle**       | D2 Phase 1 Kern-Deliverables, D2 Messbare Erfolgsindikatoren |
| **Abhängig von** | TASK-001                                                     |
| **Blockiert**    | –                                                            |

**Beschreibung:** Auf Basis der in TASK-001 erzeugten Embeddings eine einfache semantische Suchfunktion implementieren, die natürlichsprachliche Queries entgegennimmt und relevante Ergebnisse aus mindestens 2 Datenquellen zurückliefert. Der PoC soll als CLI oder Jupyter-Notebook bereitgestellt werden.

**Acceptance Criteria:**

- [ ] Natürlichsprachliche Suchanfragen liefern semantisch relevante Ergebnisse (manuell verifiziert an mindestens 10 Testqueries)
- [ ] Ergebnisse enthalten Quellinformationen (Quelle, Titel, Datum)
- [ ] Suche läuft über Dokumente aus ≥ 2 verschiedenen Datenquellen hinweg

**Technische Hinweise:** Weaviate Nearest-Neighbor-Suche verwenden. Query wird ebenfalls mit `text-embedding-3-small` embedded. Ergebnisse nach Cosine-Similarity sortieren.

---

#### TASK-003: DSGVO-Erstkonzept erstellen und rechtliche Erstberatung einholen

| Feld             | Wert                                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------ |
| **Priorität**    | P0 (kritisch, blockiert alles)                                                                         |
| **Bereich**      | Docs                                                                                                   |
| **Aufwand**      | L (1 Woche)                                                                                            |
| **Status**       | 🔴 Offen                                                                                               |
| **Quelle**       | D2 Phase 1 Kern-Deliverables, D1 Abschnitt 5 (Datenschutz & Sicherheit), D3 Datenschutz und Sicherheit |
| **Abhängig von** | –                                                                                                      |
| **Blockiert**    | TASK-004                                                                                               |

**Beschreibung:** Ein initiales DSGVO-Konzept als Dokument erstellen, das die relevanten DSGVO-Artikel (Art. 5, 6, 15, 17, 20, 25, 32) auf das PWBS abbildet. Ergebnis einer rechtlichen Erstberatung dokumentieren: Rechtsgrundlagen für Datenverarbeitung, Anforderungen an AVVs mit LLM-Providern (OpenAI, Anthropic), und EU-Datenresidenz-Anforderungen.

**Acceptance Criteria:**

- [ ] Dokument `docs/dsgvo-erstkonzept.md` existiert mit Mapping aller relevanten DSGVO-Artikel auf PWBS-Funktionen
- [ ] Rechtsgrundlage für jede Datenverarbeitungskategorie (Kalender, Notizen, Transkripte, Embeddings, LLM-Calls) ist identifiziert
- [ ] Anforderungen an AVVs mit AWS, OpenAI, Anthropic, Vercel sind dokumentiert
- [ ] Offene rechtliche Fragen sind als Liste erfasst

**Technische Hinweise:** Gemäß D1 Abschnitt 5.2 DSGVO-Maßnahmen und D4 NF-017 bis NF-021. Ergebnisdokument wird Input für die Verschlüsselungsstrategie (TASK-004).

---

#### TASK-004: Verschlüsselungsstrategie definieren

| Feld             | Wert                                                                       |
| ---------------- | -------------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                             |
| **Bereich**      | Docs                                                                       |
| **Aufwand**      | M (2–3 Tage)                                                               |
| **Status**       | 🔴 Offen                                                                   |
| **Quelle**       | D2 Phase 1 Kern-Deliverables, D1 Abschnitt 5.1 (Verschlüsselungsstrategie) |
| **Abhängig von** | TASK-003                                                                   |
| **Blockiert**    | TASK-022                                                                   |

**Beschreibung:** Auf Basis des DSGVO-Erstkonzepts ein technisches Verschlüsselungskonzept erstellen, das die Envelope-Encryption-Architektur (KEK/DEK) dokumentiert. Festlegen, welche Daten at-rest und in-transit wie verschlüsselt werden. Entscheidung dokumentieren, wie Weaviate-Vektoren und Neo4j-Graphdaten behandelt werden (Trade-off: Suchfunktionalität vs. Verschlüsselung).

**Acceptance Criteria:**

- [ ] Dokument `docs/encryption-strategy.md` beschreibt die Key-Hierarchie (KEK via AWS KMS, DEK pro Nutzer) gemäß D1 Abschnitt 5.1
- [ ] At-Rest-Verschlüsselung ist pro Speicherschicht spezifiziert (PostgreSQL, Weaviate, Neo4j, Redis)
- [ ] In-Transit-Verschlüsselung ist pro Verbindungstyp spezifiziert (TLS-Versionen)
- [ ] Trade-offs für Weaviate (unverschlüsselte Vektoren für Suche) und Neo4j (unverschlüsselte Graphdaten für Query-Performance) sind explizit begründet

**Technische Hinweise:** Envelope-Encryption-Schema aus D1 Abschnitt 5.1: AES-256 für PostgreSQL, Volume Encryption für Weaviate/Neo4j, Fernet für OAuth-Tokens mit User-DEK.

---

#### TASK-005: ADR-Vorlage finalisieren und initiale ADRs erstellen

| Feld             | Wert                                                                                |
| ---------------- | ----------------------------------------------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                                                                  |
| **Bereich**      | Docs                                                                                |
| **Aufwand**      | M (2–3 Tage)                                                                        |
| **Status**       | 🔴 Offen                                                                            |
| **Quelle**       | D1 Abschnitt 7 (Entscheidungsprotokoll / ADR-Tabelle), D2 Phase 1 Kern-Deliverables |
| **Abhängig von** | –                                                                                   |
| **Blockiert**    | –                                                                                   |

**Beschreibung:** Die bestehende ADR-Vorlage (`docs/adr/000-template.md`) als Basis verwenden und für die 12 in D1 Abschnitt 7 dokumentierten Architekturentscheidungen (ADR-001 bis ADR-012) jeweils ein vollständiges ADR-Dokument erstellen. Jedes ADR enthält Kontext, Entscheidung, bewertete Optionen, Konsequenzen und DSGVO-Implikationen.

**Acceptance Criteria:**

- [ ] 12 ADR-Dateien existieren unter `docs/adr/` (ADR-001 bis ADR-012) im Format der Vorlage `000-template.md`
- [ ] Jedes ADR enthält: Kontext, Entscheidung, bewertete Optionen (inkl. Vorteile/Nachteile), Konsequenzen und DSGVO-Implikationen
- [ ] ADRs decken ab: Python/FastAPI (001), PostgreSQL (002), Weaviate (003), Neo4j (004), Claude API (005), Modularer Monolith (006), Next.js/Vercel (007), Tauri (008), Envelope Encryption (009), Hybrid-Suche (010), Celery+Redis (011), React Query (012)

**Technische Hinweise:** Entscheidungsdaten aus D1 Abschnitt 7 ADR-Tabelle übernehmen. DSGVO-Implikationen-Abschnitt gemäß ADR-Vorlage ausfüllen. Status der ADRs auf „Akzeptiert" setzen.

---

#### TASK-006: Tooling und Template für strukturierte Probleminterviews erstellen

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                                        |
| **Bereich**      | Docs                                                      |
| **Aufwand**      | S (0.5–1 Tag)                                             |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D2 Phase 1 Kern-Deliverables, D3 Nächste Schritte Punkt 1 |
| **Abhängig von** | –                                                         |
| **Blockiert**    | TASK-007                                                  |

**Beschreibung:** Ein Interview-Leitfaden und Auswertungstemplate für die 15–20 strukturierten Probleminterviews mit Wissensarbeitern (Gründer, PMs, Entwickler, Berater) erstellen. Der Leitfaden soll die fünf Problemdimensionen aus D3 (Fragmentierung, Kontextverlust, fehlende Verdichtung, Entscheidungsunsicherheit, fehlendes Langzeitgedächtnis) systematisch abfragen.

**Acceptance Criteria:**

- [ ] Interview-Leitfaden unter `docs/interviews/interview-guide.md` mit strukturierten Fragen zu allen 5 Problemdimensionen
- [ ] Auswertungstemplate unter `docs/interviews/evaluation-template.md` mit Bewertungsskalen für Problemintensität und Zahlungsbereitschaft
- [ ] Datenfelder für: Rolle, Unternehmensgröße, genutzte Tools, Top-3-Schmerzpunkte, bestehende Workarounds, Zahlungsbereitschaft

**Technische Hinweise:** Orientierung an den drei User Personas aus D4 Abschnitt 3 (Jana, Markus, Lena). Fragen ableiten aus D3 Problemstellung und D2 Phase 1 Erfolgsindikatoren (≥ 10 Interviews bestätigen Kontextverlust als Top-3-Problem).

---

#### TASK-007: Interview-Auswertungssystem einrichten

| Feld             | Wert                                                         |
| ---------------- | ------------------------------------------------------------ |
| **Priorität**    | P2 (Should-Have)                                             |
| **Bereich**      | Docs                                                         |
| **Aufwand**      | S (0.5–1 Tag)                                                |
| **Status**       | 🔴 Offen                                                     |
| **Quelle**       | D2 Phase 1 Kern-Deliverables, D2 Messbare Erfolgsindikatoren |
| **Abhängig von** | TASK-006                                                     |
| **Blockiert**    | –                                                            |

**Beschreibung:** Ein System zur strukturierten Auswertung der Interviews aufsetzen (Spreadsheet oder Notion-DB). Das System soll die Interviewergebnisse aggregieren und die messbaren Erfolgsindikatoren der Phase 1 abbilden: bestätigte Schmerzpunkte, Zahlungsbereitschaft und Bereitschaft zum Prototyp-Test.

**Acceptance Criteria:**

- [ ] Auswertungssystem ist eingerichtet (Spreadsheet oder Notion-DB) mit Feldern für alle Datenpunkte aus dem Auswertungstemplate
- [ ] Aggregationsansicht zeigt: Häufigkeit der Schmerzpunkte, Top-3-Probleme, Anzahl Tester-Bereitschaft, Zahlungsbereitschaft-Verteilung
- [ ] Erfolgsindikatoren aus D2 sind als Dashboard-Felder abgebildet (≥ 10 bestätigte Interviews, ≥ 5 Testerbereitschaften)

**Technische Hinweise:** Einfaches Tooling verwenden (Google Sheets, Notion). Kein Overengineering – die Auswertung soll schnell einsetzbar sein. Ergebnisse fließen in die Phase-2-Priorisierung ein.

---

#### TASK-008: PoC-Ergebnisse dokumentieren und Entscheidungsvorlage erstellen

| Feld             | Wert                                                              |
| ---------------- | ----------------------------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                                                |
| **Bereich**      | Docs                                                              |
| **Aufwand**      | S (0.5–1 Tag)                                                     |
| **Status**       | 🔴 Offen                                                          |
| **Quelle**       | D2 Phase 1 Kern-Deliverables, D1 Abschnitt 1.3 (Evolutionsstufen) |
| **Abhängig von** | TASK-001, TASK-002                                                |
| **Blockiert**    | –                                                                 |

**Beschreibung:** Die Ergebnisse des technischen PoC (TASK-001, TASK-002) in einem Dokument zusammenfassen. Embedding-Qualität, Suchrelevanz, Latenz und Kosten dokumentieren. Entscheidungsvorlage für Cloud vs. On-Premise, LLM-Provider-Auswahl und Vector-DB-Bestätigung erstellen.

**Acceptance Criteria:**

- [ ] Dokument `docs/poc-results.md` mit quantitativen Ergebnissen: Embedding-Latenz, Suchrelevanz (manuelle Bewertung), Kosten pro 1000 Embeddings
- [ ] Entscheidungsvorlage enthält Vergleich: text-embedding-3-small vs. text-embedding-3-large vs. all-MiniLM-L6-v2 (lokal)
- [ ] Go/No-Go-Empfehlung für Phase 2 ist formuliert mit Begründung

**Technische Hinweise:** Messwerte aus dem PoC-Lauf extrahieren. Embedding-Modellvergleich gemäß D1 Abschnitt 3.2 (Tabelle: Cloud Standard, Cloud High Quality, Lokal). Erfolgsindikatoren aus D2 Phase 1 als Bewertungsmaßstab.

---

## Phase 2: Projekt-Setup, Infrastruktur & Datenbank-Schema

---

#### TASK-009: Monorepo-Struktur mit Backend- und Frontend-Modulen erstellen

| Feld             | Wert                                             |
| ---------------- | ------------------------------------------------ |
| **Priorität**    | P0 (kritisch, blockiert alles)                   |
| **Bereich**      | Infra                                            |
| **Aufwand**      | S (0.5–1 Tag)                                    |
| **Status**       | 🔴 Offen                                         |
| **Quelle**       | D1 Abschnitt 8.2 (Projektstruktur)               |
| **Abhängig von** | –                                                |
| **Blockiert**    | TASK-010, TASK-011, TASK-012, TASK-013, TASK-014 |

**Beschreibung:** Die in D1 Abschnitt 8.2 definierte Projektstruktur als Monorepo aufsetzen. Backend unter `backend/` mit `app/`-Unterstruktur (api, connectors, processing, services, models, schemas, db, prompts, scripts). Frontend unter `frontend/` mit Next.js App Router-Struktur. Infrastruktur unter `infra/terraform/` und `docs/`.

**Acceptance Criteria:**

- [ ] Repository-Verzeichnisstruktur entspricht D1 Abschnitt 8.2 mit allen Unterverzeichnissen für Backend (`app/api/v1/`, `app/connectors/`, `app/processing/`, `app/services/`, `app/models/`, `app/schemas/`, `app/db/`, `app/prompts/`, `app/scripts/`) und Frontend (`src/app/`, `src/components/`, `src/lib/`, `src/hooks/`, `src/stores/`, `src/types/`)
- [ ] `backend/pyproject.toml` mit Python 3.12+ Konfiguration und initialen Dependencies (fastapi, pydantic, sqlalchemy, alembic) existiert
- [ ] `frontend/package.json` mit Next.js, React, TypeScript, Tailwind CSS existiert
- [ ] `.gitignore` für Python, Node.js und Docker konfiguriert
- [ ] Root-`README.md` mit Projektübersicht und Quick-Start-Anleitung

**Technische Hinweise:** Struktur exakt gemäß D1 Abschnitt 8.2. Python-Packages verwenden absolute Imports (`app.connectors`, `app.processing`). Frontend nutzt App Router (Next.js 14+).

---

#### TASK-010: Docker Compose für lokale Entwicklungsumgebung erstellen

| Feld             | Wert                                                       |
| ---------------- | ---------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                             |
| **Bereich**      | Infra                                                      |
| **Aufwand**      | M (2–3 Tage)                                               |
| **Status**       | 🔴 Offen                                                   |
| **Quelle**       | D1 Abschnitt 8.1 (Docker Compose)                          |
| **Abhängig von** | TASK-009                                                   |
| **Blockiert**    | TASK-015, TASK-016, TASK-017, TASK-025, TASK-026, TASK-027 |

**Beschreibung:** Die in D1 Abschnitt 8.1 spezifizierte `docker-compose.yml` implementieren mit allen Services: PostgreSQL 16, Weaviate 1.28, Neo4j 5.26 Community, Redis 7 und den Backend/Frontend-Dev-Containern. Alle Services mit Health-Checks, persistenten Volumes und korrekten Dependency-Chains konfigurieren.

**Acceptance Criteria:**

- [ ] `docker-compose.yml` im Repository-Root mit Services: postgres, weaviate, neo4j, redis, api, frontend
- [ ] PostgreSQL 16-Alpine mit Health-Check (`pg_isready`), persistentem Volume und Init-SQL-Mount
- [ ] Weaviate 1.28.2 mit Health-Check, `DEFAULT_VECTORIZER_MODULE: none`, Multi-Tenancy aktivierbar
- [ ] Neo4j 5.26-Community mit Health-Check, APOC-Plugin, Browser-Port (7474) und Bolt-Port (7687)
- [ ] Redis 7-Alpine mit Health-Check und persistentem Volume
- [ ] `docker compose up -d` startet alle Services erfolgreich und alle Health-Checks sind grün

**Technische Hinweise:** Konfiguration exakt gemäß D1 Abschnitt 8.1. Environment-Variablen aus `.env`-Datei lesen. Backend-Service nutzt `--reload` für Hot-Reload. Frontend-Service nutzt `npm run dev`.

---

#### TASK-011: .env-Vorlagen und Secrets-Handling einrichten

| Feld             | Wert                                                             |
| ---------------- | ---------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                   |
| **Bereich**      | Infra                                                            |
| **Aufwand**      | S (0.5–1 Tag)                                                    |
| **Status**       | 🔴 Offen                                                         |
| **Quelle**       | D1 Abschnitt 8.1 (Lokaler Startup), D1 Abschnitt 5 (Datenschutz) |
| **Abhängig von** | TASK-009                                                         |
| **Blockiert**    | TASK-010, TASK-012                                               |

**Beschreibung:** Eine `.env.example`-Datei mit allen benötigten Umgebungsvariablen erstellen (ohne echte Secrets). Dokumentieren, welche Variablen für die lokale Entwicklung benötigt werden und wie sie zu befüllen sind. Sicherstellen, dass `.env` in `.gitignore` aufgeführt ist.

**Acceptance Criteria:**

- [ ] `.env.example` im Repository-Root mit allen Variablen aus D1 Abschnitt 8.1: DATABASE_URL, WEAVIATE_URL, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, REDIS_URL, CLAUDE_API_KEY, OPENAI_API_KEY, ENCRYPTION_MASTER_KEY, JWT_SECRET_KEY, ENVIRONMENT
- [ ] Jede Variable mit Kommentar (Zweck, Format, ob optional/pflicht)
- [ ] `.env` in `.gitignore` eingetragen
- [ ] Anleitung in README zum Befüllen der `.env`-Datei

**Technische Hinweise:** Keine echten Secrets committen. Für lokale Entwicklung Default-Werte für DB-Credentials angeben (z. B. `pwbs_dev`). API-Keys müssen individuell eingetragen werden.

---

#### TASK-012: Pydantic Settings-Konfigurationsklasse implementieren

| Feld             | Wert                                                                   |
| ---------------- | ---------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                         |
| **Bereich**      | Backend                                                                |
| **Aufwand**      | S (0.5–1 Tag)                                                          |
| **Status**       | 🔴 Offen                                                               |
| **Quelle**       | D1 Abschnitt 8.2 (config.py), D1 Abschnitt 8.1 (Environment Variables) |
| **Abhängig von** | TASK-009, TASK-011                                                     |
| **Blockiert**    | TASK-025, TASK-026, TASK-027                                           |

**Beschreibung:** Eine `app/config.py` mit Pydantic Settings (v2) erstellen, die alle Konfigurationswerte aus Umgebungsvariablen typisiert, validiert und zentral bereitstellt. Unterstützung für verschiedene Environments (development, staging, production) mittels `model_config` und Prefix-Konfiguration.

**Acceptance Criteria:**

- [ ] `app/config.py` mit Pydantic `BaseSettings`-Klasse, die alle Variablen aus `.env.example` als typisierte Felder enthält
- [ ] Validierung: Pflichtfelder ohne Default lösen beim Start einen Fehler mit klarer Fehlermeldung aus
- [ ] Environment-spezifische Defaults (z. B. `debug=True` in development, `debug=False` in production)
- [ ] Singleton-Pattern: `get_settings()` gibt gecachte Instanz zurück (via `@lru_cache`)

**Technische Hinweise:** Pydantic v2 Settings-Syntax verwenden (`model_config = SettingsConfigDict(env_file=".env")`). Sensitive Felder mit `SecretStr` typisieren (z. B. `jwt_secret_key: SecretStr`). Strikte Typisierung, kein `Any`.

---

#### TASK-013: CI/CD-Pipeline mit GitHub Actions einrichten

| Feld             | Wert                               |
| ---------------- | ---------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)     |
| **Bereich**      | Infra                              |
| **Aufwand**      | M (2–3 Tage)                       |
| **Status**       | 🔴 Offen                           |
| **Quelle**       | D1 Abschnitt 8.3 (CI/CD-Strategie) |
| **Abhängig von** | TASK-009                           |
| **Blockiert**    | –                                  |

**Beschreibung:** GitHub Actions Workflows erstellen für die in D1 Abschnitt 8.3 definierte Pipeline: Lint (ruff + mypy für Backend, eslint + tsc für Frontend), Unit Tests (pytest, vitest) und Integration Tests (Testcontainers für PostgreSQL, Weaviate, Neo4j) bei Merge auf main.

**Acceptance Criteria:**

- [ ] `.github/workflows/ci.yml` mit Lint-Job (ruff, mypy, eslint, tsc) der bei jedem Push läuft
- [ ] Unit-Test-Job (pytest ohne DB, vitest) der bei jedem Push läuft, Ziel: < 2 min Backend, < 1 min Frontend
- [ ] Integration-Test-Job mit Testcontainers (PostgreSQL, Weaviate, Neo4j) der bei Merge auf main läuft
- [ ] Pipeline-Status als Badge in README

**Technische Hinweise:** Gemäß D1 Abschnitt 8.3. Ruff als Linter und Formatter verwenden. Mypy im strict-Modus. Testcontainers für Integration-Tests (gleiche Images wie Docker Compose). Caching von pip/npm Dependencies für Geschwindigkeit.

---

#### TASK-014: Backend-Dockerfile (Dev und Prod) erstellen

| Feld             | Wert                                                           |
| ---------------- | -------------------------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                                             |
| **Bereich**      | Infra                                                          |
| **Aufwand**      | S (0.5–1 Tag)                                                  |
| **Status**       | 🔴 Offen                                                       |
| **Quelle**       | D1 Abschnitt 8.2 (Projektstruktur: Dockerfile, Dockerfile.dev) |
| **Abhängig von** | TASK-009                                                       |
| **Blockiert**    | –                                                              |

**Beschreibung:** Zwei Dockerfiles für das Backend erstellen: `Dockerfile.dev` mit Hot-Reload (uvicorn --reload) und Volume-Mount für lokale Entwicklung, sowie `Dockerfile` als Multi-Stage-Build für Production (minimales Image, keine Dev-Dependencies).

**Acceptance Criteria:**

- [ ] `backend/Dockerfile.dev` mit Python 3.12, allen Dependencies und uvicorn im Reload-Modus
- [ ] `backend/Dockerfile` als Multi-Stage-Build: Builder-Stage für Dependencies, Runtime-Stage mit minimal Python-Image
- [ ] Production-Image < 300 MB, enthält keine Dev-Tools oder Testdependencies
- [ ] Beide Dockerfiles bauen fehlerfrei (`docker build .`)

**Technische Hinweise:** Gemäß D1 Abschnitt 8.2 und 8.3 (Docker Buildx multi-stage). Python 3.12+ verwenden. Non-root User im Production-Image.

---

#### TASK-015: PostgreSQL-Schema für users-Tabelle erstellen

| Feld             | Wert                                                       |
| ---------------- | ---------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                             |
| **Bereich**      | DB                                                         |
| **Aufwand**      | S (0.5–1 Tag)                                              |
| **Status**       | 🔴 Offen                                                   |
| **Quelle**       | D1 Abschnitt 3.3.1 (users-Tabelle), D4 Datenmodell: User   |
| **Abhängig von** | TASK-010, TASK-018                                         |
| **Blockiert**    | TASK-016, TASK-017, TASK-019, TASK-020, TASK-021, TASK-023 |

**Beschreibung:** Die `users`-Tabelle gemäß D1 Abschnitt 3.3.1 erstellen mit allen Feldern: id (UUID, PK), email (UNIQUE), display_name, password_hash, encryption_key_enc, created_at, updated_at. Inklusive generierten Defaults und Constraints.

**Acceptance Criteria:**

- [ ] `users`-Tabelle mit exakt den Feldern aus D1 Abschnitt 3.3.1: id (UUID, PK, DEFAULT gen_random_uuid()), email (TEXT UNIQUE NOT NULL), display_name (TEXT NOT NULL), password_hash (TEXT NOT NULL), encryption_key_enc (TEXT NOT NULL), created_at (TIMESTAMPTZ DEFAULT now()), updated_at (TIMESTAMPTZ DEFAULT now())
- [ ] Migration erstellt und anwendbar via `alembic upgrade head`
- [ ] Rollback-Migration vorhanden via `alembic downgrade`

**Technische Hinweise:** Passwort-Hash wird mit Argon2 erzeugt (D4 F-001). encryption_key_enc speichert den nutzer-spezifischen DEK verschlüsselt mit dem Master KEK (D1 Abschnitt 5.1).

---

#### TASK-016: PostgreSQL-Schema für connections-Tabelle erstellen

| Feld             | Wert                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                       |
| **Bereich**      | DB                                                                   |
| **Aufwand**      | XS (<2h)                                                             |
| **Status**       | 🔴 Offen                                                             |
| **Quelle**       | D1 Abschnitt 3.3.1 (connections-Tabelle), D4 Datenmodell: Connection |
| **Abhängig von** | TASK-015                                                             |
| **Blockiert**    | –                                                                    |

**Beschreibung:** Die `connections`-Tabelle gemäß D1 Abschnitt 3.3.1 erstellen. Speichert verbundene Datenquellen pro Nutzer mit verschlüsselten OAuth-Tokens, Watermark für inkrementellen Sync und quellenspezifischer Konfiguration.

**Acceptance Criteria:**

- [ ] `connections`-Tabelle mit Feldern: id (UUID, PK), user_id (FK → users, ON DELETE CASCADE), source_type (TEXT NOT NULL), status (TEXT NOT NULL DEFAULT 'active'), credentials_enc (TEXT NOT NULL), watermark (TIMESTAMPTZ), config (JSONB DEFAULT '{}'), created_at, updated_at
- [ ] UNIQUE-Constraint auf (user_id, source_type)
- [ ] Migration erstellt und anwendbar

**Technische Hinweise:** credentials_enc speichert verschlüsselte OAuth-Tokens mit User-DEK via Fernet (D1 Abschnitt 5.1, D4 NF-016). Status-Werte: active, paused, error, revoked (D4 Datenmodell: Connection).

---

#### TASK-017: PostgreSQL-Schema für documents-Tabelle erstellen

| Feld             | Wert                                                             |
| ---------------- | ---------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                   |
| **Bereich**      | DB                                                               |
| **Aufwand**      | XS (<2h)                                                         |
| **Status**       | 🔴 Offen                                                         |
| **Quelle**       | D1 Abschnitt 3.3.1 (documents-Tabelle), D4 Datenmodell: Document |
| **Abhängig von** | TASK-015                                                         |
| **Blockiert**    | TASK-019                                                         |

**Beschreibung:** Die `documents`-Tabelle gemäß D1 Abschnitt 3.3.1 erstellen. Speichert Dokument-Metadaten (Inhalt liegt in Weaviate) mit Content-Hash für idempotente Deduplizierung und Processing-Status-Tracking.

**Acceptance Criteria:**

- [ ] `documents`-Tabelle mit Feldern: id (UUID, PK), user_id (FK → users, CASCADE), source_type (TEXT NOT NULL), source_id (TEXT NOT NULL), title (TEXT), content_hash (TEXT NOT NULL), language (TEXT DEFAULT 'de'), chunk_count (INT DEFAULT 0), processing_status (TEXT DEFAULT 'pending'), created_at, updated_at
- [ ] UNIQUE-Constraint auf (user_id, source_type, source_id)
- [ ] Index `idx_documents_user_status` auf (user_id, processing_status)
- [ ] Migration erstellt und anwendbar

**Technische Hinweise:** content_hash ist SHA-256 des Rohinhalts für Deduplizierung (D4 Datenmodell: Document). processing_status-Werte: pending, processing, done, error.

---

#### TASK-018: Alembic-Migrations-Infrastruktur einrichten

| Feld             | Wert                                                                           |
| ---------------- | ------------------------------------------------------------------------------ |
| **Priorität**    | P0 (kritisch, blockiert alles)                                                 |
| **Bereich**      | DB                                                                             |
| **Aufwand**      | S (0.5–1 Tag)                                                                  |
| **Status**       | 🔴 Offen                                                                       |
| **Quelle**       | D1 Abschnitt 8.1 (Lokaler Startup Schritt 4), D1 Abschnitt 8.2 (migrations/)   |
| **Abhängig von** | TASK-009, TASK-010                                                             |
| **Blockiert**    | TASK-015, TASK-016, TASK-017, TASK-019, TASK-020, TASK-021, TASK-022, TASK-023 |

**Beschreibung:** Alembic als Datenbank-Migrationstool einrichten. `alembic.ini` und `env.py` konfigurieren, sodass Migrationen gegen die PostgreSQL-Instanz aus Docker Compose laufen. Async-Engine-Support konfigurieren (asyncpg). Initiale Migration erstellen, die eine leere Datenbank vorbereitet.

**Acceptance Criteria:**

- [ ] `backend/migrations/alembic.ini` konfiguriert mit Verweis auf `env.py`
- [ ] `backend/migrations/env.py` konfiguriert für async SQLAlchemy mit asyncpg
- [ ] `alembic revision --autogenerate` generiert korrekt Migrationen aus SQLAlchemy-Modellen
- [ ] `alembic upgrade head` und `alembic downgrade` funktionieren gegen die Docker-PostgreSQL-Instanz

**Technische Hinweise:** Alembic nutzt die DATABASE_URL aus der Pydantic Settings-Konfiguration (TASK-012). Async-Engine via asyncpg. Migration-Files unter `backend/migrations/versions/`.

---

#### TASK-019: PostgreSQL-Schema für chunks-Tabelle erstellen

| Feld             | Wert                                                       |
| ---------------- | ---------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                             |
| **Bereich**      | DB                                                         |
| **Aufwand**      | XS (<2h)                                                   |
| **Status**       | 🔴 Offen                                                   |
| **Quelle**       | D1 Abschnitt 3.3.1 (chunks-Tabelle), D4 Datenmodell: Chunk |
| **Abhängig von** | TASK-017, TASK-018                                         |
| **Blockiert**    | TASK-020                                                   |

**Beschreibung:** Die `chunks`-Tabelle gemäß D1 Abschnitt 3.3.1 erstellen. Speichert Referenzen zu Weaviate-Vektoren und Chunk-Metadaten. Denormalisierte user_id für schnelle Queries.

**Acceptance Criteria:**

- [ ] `chunks`-Tabelle mit Feldern: id (UUID, PK), document_id (FK → documents, CASCADE), user_id (FK → users, CASCADE), chunk_index (INT NOT NULL), token_count (INT NOT NULL), weaviate_id (UUID), content_preview (TEXT), created_at (TIMESTAMPTZ DEFAULT now())
- [ ] Index `idx_chunks_document` auf (document_id)
- [ ] Migration erstellt und anwendbar

**Technische Hinweise:** weaviate_id verknüpft den Chunk mit dem Vektor in Weaviate (D4 Datenmodell: Chunk). content_preview enthält die ersten 200 Zeichen für Debug/Admin-Zwecke.

---

#### TASK-020: PostgreSQL-Schema für entities- und entity_mentions-Tabellen erstellen

| Feld             | Wert                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                                          |
| **Bereich**      | DB                                                                                      |
| **Aufwand**      | S (0.5–1 Tag)                                                                           |
| **Status**       | 🔴 Offen                                                                                |
| **Quelle**       | D1 Abschnitt 3.3.1 (entities + entity_mentions), D4 Datenmodell: Entity + EntityMention |
| **Abhängig von** | TASK-015, TASK-019                                                                      |
| **Blockiert**    | –                                                                                       |

**Beschreibung:** Die `entities`-Tabelle (extrahierte Entitäten) und die `entity_mentions`-Tabelle (M:N-Zuordnung zwischen Entitäten und Chunks) gemäß D1 Abschnitt 3.3.1 erstellen. Entitäten werden per (user_id, entity_type, normalized_name) dedupliziert.

**Acceptance Criteria:**

- [ ] `entities`-Tabelle mit Feldern: id (UUID, PK), user_id (FK → users, CASCADE), entity_type (TEXT NOT NULL), name (TEXT NOT NULL), normalized_name (TEXT NOT NULL), metadata (JSONB DEFAULT '{}'), first_seen (TIMESTAMPTZ), last_seen (TIMESTAMPTZ), mention_count (INT DEFAULT 1), neo4j_node_id (TEXT)
- [ ] UNIQUE-Constraint auf (user_id, entity_type, normalized_name)
- [ ] Index `idx_entities_user_type` auf (user_id, entity_type)
- [ ] `entity_mentions`-Tabelle mit: entity_id (FK → entities, CASCADE), chunk_id (FK → chunks, CASCADE), confidence (FLOAT DEFAULT 1.0), extraction_method (TEXT DEFAULT 'rule'), PRIMARY KEY (entity_id, chunk_id)
- [ ] Migrationen erstellt und anwendbar

**Technische Hinweise:** entity_type-Werte: PERSON, PROJECT, TOPIC, DECISION (D4 Datenmodell: Entity). extraction_method: 'rule' oder 'llm' (D1 Abschnitt 3.2 NER). confidence 1.0 für regelbasiert, variabel für LLM-basiert.

---

#### TASK-021: PostgreSQL-Schema für briefings-Tabelle erstellen

| Feld             | Wert                                                             |
| ---------------- | ---------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                   |
| **Bereich**      | DB                                                               |
| **Aufwand**      | XS (<2h)                                                         |
| **Status**       | 🔴 Offen                                                         |
| **Quelle**       | D1 Abschnitt 3.3.1 (briefings-Tabelle), D4 Datenmodell: Briefing |
| **Abhängig von** | TASK-015, TASK-018                                               |
| **Blockiert**    | –                                                                |

**Beschreibung:** Die `briefings`-Tabelle gemäß D1 Abschnitt 3.3.1 erstellen. Speichert generierte Kontextbriefings mit Quellenreferenzen (source_chunks, source_entities) und Ablaufdatum.

**Acceptance Criteria:**

- [ ] `briefings`-Tabelle mit Feldern: id (UUID, PK), user_id (FK → users, CASCADE), briefing_type (TEXT NOT NULL), title (TEXT NOT NULL), content (TEXT NOT NULL), source_chunks (UUID[] NOT NULL), source_entities (UUID[]), trigger_context (JSONB), generated_at (TIMESTAMPTZ DEFAULT now()), expires_at (TIMESTAMPTZ)
- [ ] Index `idx_briefings_user_type` auf (user_id, briefing_type, generated_at DESC)
- [ ] Migration erstellt und anwendbar

**Technische Hinweise:** briefing_type-Werte: MORNING, MEETING_PREP (im MVP). source_chunks referenziert Chunk-UUIDs für Nachvollziehbarkeit (D4 Datenmodell: Briefing). expires_at: 24h für Morgenbriefings, 48h für Meeting-Briefings (D4 F-022).

---

#### TASK-022: PostgreSQL-Schema für audit_log-Tabelle erstellen

| Feld             | Wert                                                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                                                          |
| **Bereich**      | DB                                                                                                      |
| **Aufwand**      | XS (<2h)                                                                                                |
| **Status**       | 🔴 Offen                                                                                                |
| **Quelle**       | D1 Abschnitt 3.3.1 (audit_log-Tabelle), D1 Abschnitt 5.5 (Audit-Logging), D4 Datenmodell: AuditLogEntry |
| **Abhängig von** | TASK-015, TASK-018                                                                                      |
| **Blockiert**    | –                                                                                                       |

**Beschreibung:** Die `audit_log`-Tabelle gemäß D1 Abschnitt 3.3.1 erstellen. Unveränderliche Protokollierung aller datenschutzrelevanten Aktionen. ON DELETE SET NULL für user_id (Logs bleiben nach Account-Deletion aus Compliance-Gründen bestehen).

**Acceptance Criteria:**

- [ ] `audit_log`-Tabelle mit Feldern: id (BIGSERIAL, PK), user_id (FK → users, ON DELETE SET NULL), action (TEXT NOT NULL), resource_type (TEXT), resource_id (UUID), metadata (JSONB DEFAULT '{}'), ip_address (INET), created_at (TIMESTAMPTZ DEFAULT now())
- [ ] Index `idx_audit_user_time` auf (user_id, created_at DESC)
- [ ] Migration erstellt und anwendbar
- [ ] ON DELETE SET NULL (statt CASCADE) für user_id gemäß D4 Datenmodell: AuditLogEntry

**Technische Hinweise:** Append-only: Kein UPDATE/DELETE auf diese Tabelle im Anwendungscode (D1 Abschnitt 5.5). Aktionstypen gemäß AUDIT_EVENTS-Liste. metadata enthält keine PII, nur IDs und Zählwerte (D4 Datenmodell).

---

#### TASK-023: PostgreSQL-Schema für scheduled_job_runs-Tabelle erstellen

| Feld             | Wert                                                          |
| ---------------- | ------------------------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                                            |
| **Bereich**      | DB                                                            |
| **Aufwand**      | XS (<2h)                                                      |
| **Status**       | 🔴 Offen                                                      |
| **Quelle**       | D1 Abschnitt 3.3.1 (Job State unter PostgreSQL Storage Layer) |
| **Abhängig von** | TASK-015, TASK-018                                            |
| **Blockiert**    | –                                                             |

**Beschreibung:** Eine `scheduled_job_runs`-Tabelle erstellen, die den Status geplanter Jobs (Ingestion-Zyklen, Briefing-Generierung, Cleanup) persistiert. Ermöglicht Monitoring, Retry-Logik und Idempotenz-Prüfung.

**Acceptance Criteria:**

- [ ] `scheduled_job_runs`-Tabelle mit Feldern: id (UUID, PK), job_type (TEXT NOT NULL), status (TEXT NOT NULL DEFAULT 'pending'), started_at (TIMESTAMPTZ), completed_at (TIMESTAMPTZ), error_message (TEXT), retry_count (INT DEFAULT 0), metadata (JSONB DEFAULT '{}'), created_at (TIMESTAMPTZ DEFAULT now())
- [ ] Index auf (job_type, status) für schnelle Abfragen laufender Jobs
- [ ] Migration erstellt und anwendbar

**Technische Hinweise:** D1 Abschnitt 2.1 listet „Job State" als PostgreSQL-Zuständigkeit. Status-Werte: pending, running, completed, failed. Retry-Logik gemäß AGENTS.md SchedulerAgent (Max. 3 Retries mit Exponential Backoff).

---

#### TASK-024: Initiale Alembic-Migration mit allen Tabellen erstellen

| Feld             | Wert                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                                           |
| **Bereich**      | DB                                                                                       |
| **Aufwand**      | S (0.5–1 Tag)                                                                            |
| **Status**       | 🔴 Offen                                                                                 |
| **Quelle**       | D1 Abschnitt 8.1 (Lokaler Startup Schritt 4)                                             |
| **Abhängig von** | TASK-015, TASK-016, TASK-017, TASK-018, TASK-019, TASK-020, TASK-021, TASK-022, TASK-023 |
| **Blockiert**    | –                                                                                        |

**Beschreibung:** Eine einzige initiale Alembic-Migration erstellen, die alle PostgreSQL-Tabellen (users, connections, documents, chunks, entities, entity_mentions, briefings, audit_log, scheduled_job_runs) mit sämtlichen Constraints und Indizes anlegt. Diese Migration soll via `alembic upgrade head` eine leere Datenbank vollständig aufsetzen.

**Acceptance Criteria:**

- [ ] Migration unter `backend/migrations/versions/` erstellt (via autogenerate oder manuell)
- [ ] `alembic upgrade head` gegen eine leere PostgreSQL-DB erstellt alle 9 Tabellen korrekt
- [ ] Alle UNIQUE-Constraints, Fremdschlüssel (CASCADE/SET NULL) und Indizes sind korrekt angelegt
- [ ] `alembic downgrade base` entfernt alle Tabellen sauber
- [ ] Migration ist gegen die Docker-Compose-PostgreSQL-Instanz getestet

**Technische Hinweise:** Reihenfolge beachten: users → connections → documents → chunks → entities → entity_mentions → briefings → audit_log → scheduled_job_runs (wegen FK-Abhängigkeiten).

---

#### TASK-025: Weaviate-Collection DocumentChunk einrichten

| Feld             | Wert                                            |
| ---------------- | ----------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                  |
| **Bereich**      | DB                                              |
| **Aufwand**      | S (0.5–1 Tag)                                   |
| **Status**       | 🔴 Offen                                        |
| **Quelle**       | D1 Abschnitt 3.3.2 (Weaviate Collection-Schema) |
| **Abhängig von** | TASK-010, TASK-012                              |
| **Blockiert**    | –                                               |

**Beschreibung:** Ein Initialisierungsskript `app/scripts/init_weaviate.py` erstellen, das die `DocumentChunk`-Collection in Weaviate anlegt. Schema exakt gemäß D1 Abschnitt 3.3.2: HNSW-Vektorindex, kein Vectorizer (Embeddings werden extern generiert), Multi-Tenancy aktiviert. Hybrid-Suche (Vektor + BM25) konfigurieren.

**Acceptance Criteria:**

- [ ] Skript `app/scripts/init_weaviate.py` erstellt die `DocumentChunk`-Collection mit allen Properties: chunkId (uuid), userId (uuid), sourceType (text), content (text), title (text), createdAt (date), language (text)
- [ ] HNSW-Index konfiguriert mit efConstruction=128, maxConnections=16, ef=64
- [ ] Multi-Tenancy ist aktiviert (`multiTenancyConfig.enabled: true`)
- [ ] Vectorizer auf `none` gesetzt (Embeddings werden extern via OpenAI/Sentence Transformers erzeugt)
- [ ] Skript ist idempotent (kann mehrfach ausgeführt werden ohne Fehler)

**Technische Hinweise:** Weaviate Python Client v4 verwenden. Collection-Schema exakt aus D1 Abschnitt 3.3.2. Hybrid-Suche-Default: alpha=0.75 (75% semantisch, 25% keyword-basiert).

---

#### TASK-026: Neo4j-Graph-Schema mit Constraints und Indizes einrichten

| Feld             | Wert                                       |
| ---------------- | ------------------------------------------ |
| **Priorität**    | P0 (kritisch, blockiert alles)             |
| **Bereich**      | DB                                         |
| **Aufwand**      | S (0.5–1 Tag)                              |
| **Status**       | 🔴 Offen                                   |
| **Quelle**       | D1 Abschnitt 3.3.3 (Neo4j Knowledge Graph) |
| **Abhängig von** | TASK-010, TASK-012                         |
| **Blockiert**    | –                                          |

**Beschreibung:** Ein Initialisierungsskript `app/scripts/init_neo4j.py` erstellen, das die Knotentypen (Person, Project, Topic, Decision, Meeting, Document) und Kantentypen aus D1 Abschnitt 3.3.3 als Constraints und Indizes in Neo4j anlegt. Uniqueness-Constraints auf (userId, id)-Kombinationen.

**Acceptance Criteria:**

- [ ] Skript `app/scripts/init_neo4j.py` erstellt Uniqueness-Constraints für alle 6 Knotentypen: Person, Project, Topic, Decision, Meeting, Document (jeweils auf id)
- [ ] Composite-Indizes auf userId für alle Knotentypen (für mandantenisierte Abfragen)
- [ ] Kantentypen dokumentiert und als Cypher-Kommentare im Skript: PARTICIPATED_IN, WORKS_ON, MENTIONED_IN, KNOWS, HAS_TOPIC, HAS_DECISION, DECIDED_IN, AFFECTS, SUPERSEDES, DISCUSSED, RELATES_TO, PRODUCED, MENTIONS, COVERS, REFERENCES, RELATED_TO
- [ ] Skript ist idempotent (CREATE CONSTRAINT IF NOT EXISTS)

**Technische Hinweise:** Neo4j Python Driver verwenden. Alle Knoten tragen die Properties aus D1 Abschnitt 3.3.3 (id, userId, name, etc.). Kanten tragen weight-Property (Float, 0.0–1.0). Alle Queries müssen mandantenisiert sein (WHERE n.userId = $userId).

---

#### TASK-027: PostgreSQL-Verbindungsmanagement mit Connection Pool implementieren

| Feld             | Wert                                                                             |
| ---------------- | -------------------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                                   |
| **Bereich**      | Backend                                                                          |
| **Aufwand**      | S (0.5–1 Tag)                                                                    |
| **Status**       | 🔴 Offen                                                                         |
| **Quelle**       | D1 Abschnitt 8.2 (db/postgres.py), D1 Abschnitt 6.1 (PostgreSQL Connection Pool) |
| **Abhängig von** | TASK-010, TASK-012                                                               |
| **Blockiert**    | –                                                                                |

**Beschreibung:** `app/db/postgres.py` implementieren mit async SQLAlchemy Engine, Connection Pool (asyncpg) und Session-Factory. Pool-Größe konfigurierbar über Pydantic Settings. Health-Check-Funktion bereitstellen.

**Acceptance Criteria:**

- [ ] `app/db/postgres.py` mit `create_async_engine()`, konfigurierbarer Pool-Größe (min=5, max=20 als Defaults)
- [ ] `AsyncSession`-Factory via `async_sessionmaker`
- [ ] `get_db_session()`-Dependency für FastAPI (async context manager)
- [ ] `check_postgres_health()` Funktion, die eine einfache Query ausführt und True/False zurückgibt
- [ ] Engine wird beim App-Startup erstellt und beim Shutdown disposed

**Technische Hinweise:** AsyncSession über asyncpg (D1 Abschnitt 8.2). Pool-Auslastung als Metrik monitoren (D1 Abschnitt 8.5: Alert bei > 80%). Connection-String aus Pydantic Settings (TASK-012).

---

#### TASK-028: Weaviate-Client-Verbindung mit Health-Check implementieren

| Feld             | Wert                                                         |
| ---------------- | ------------------------------------------------------------ |
| **Priorität**    | P0 (kritisch, blockiert alles)                               |
| **Bereich**      | Backend                                                      |
| **Aufwand**      | S (0.5–1 Tag)                                                |
| **Status**       | 🔴 Offen                                                     |
| **Quelle**       | D1 Abschnitt 8.2 (db/weaviate_client.py), D1 Abschnitt 3.3.2 |
| **Abhängig von** | TASK-010, TASK-012                                           |
| **Blockiert**    | –                                                            |

**Beschreibung:** `app/db/weaviate_client.py` implementieren mit Weaviate Python Client v4. Verbindung zur Weaviate-Instanz über URL aus Pydantic Settings. Health-Check-Funktion, die den ready-Endpoint prüft. Singleton-Pattern für den Client.

**Acceptance Criteria:**

- [ ] `app/db/weaviate_client.py` mit Weaviate v4 Client, konfiguriert über WEAVIATE_URL aus Settings
- [ ] `get_weaviate_client()` gibt Singleton-Client-Instanz zurück
- [ ] `check_weaviate_health()` prüft den `/v1/.well-known/ready`-Endpoint und gibt True/False zurück
- [ ] Client wird beim App-Shutdown geschlossen

**Technische Hinweise:** Weaviate Python Client v4 (weaviate-client). URL aus Pydantic Settings. Keine Authentifizierung in der lokalen Entwicklung (AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true in Docker Compose).

---

#### TASK-029: Neo4j-Client-Verbindung mit Health-Check implementieren

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                            |
| **Bereich**      | Backend                                                   |
| **Aufwand**      | S (0.5–1 Tag)                                             |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D1 Abschnitt 8.2 (db/neo4j_client.py), D1 Abschnitt 3.3.3 |
| **Abhängig von** | TASK-010, TASK-012                                        |
| **Blockiert**    | –                                                         |

**Beschreibung:** `app/db/neo4j_client.py` implementieren mit dem offiziellen Neo4j Python Driver. Verbindung über Bolt-Protokoll mit Credentials aus Pydantic Settings. Health-Check via einfache Cypher-Query. Singleton-Pattern.

**Acceptance Criteria:**

- [ ] `app/db/neo4j_client.py` mit Neo4j AsyncDriver, konfiguriert über NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD aus Settings
- [ ] `get_neo4j_driver()` gibt Singleton-Driver-Instanz zurück
- [ ] `check_neo4j_health()` führt `RETURN 1` aus und gibt True/False zurück
- [ ] Driver wird beim App-Shutdown geschlossen (`driver.close()`)

**Technische Hinweise:** Neo4j Python Driver 5.x (neo4j). Bolt-URI aus Pydantic Settings. Credentials verschlüsselt in .env (nicht im Code). Alle produktiven Queries müssen userId-Filter enthalten (wird in höherer Schicht erzwungen).

---

#### TASK-030: Redis-Client-Verbindung mit Health-Check implementieren

| Feld             | Wert                                                                        |
| ---------------- | --------------------------------------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                                                          |
| **Bereich**      | Backend                                                                     |
| **Aufwand**      | XS (<2h)                                                                    |
| **Status**       | 🔴 Offen                                                                    |
| **Quelle**       | D1 Abschnitt 8.2 (db/redis_client.py), D1 Abschnitt 6.4 (Caching-Strategie) |
| **Abhängig von** | TASK-010, TASK-012                                                          |
| **Blockiert**    | –                                                                           |

**Beschreibung:** `app/db/redis_client.py` implementieren mit redis-py (async). Verbindung über REDIS_URL aus Pydantic Settings. Health-Check via PING-Befehl. Wird für Caching, Rate-Limiting und Session-Management verwendet.

**Acceptance Criteria:**

- [ ] `app/db/redis_client.py` mit aioredis/redis.asyncio Client, konfiguriert über REDIS_URL aus Settings
- [ ] `get_redis_client()` gibt Client-Instanz zurück
- [ ] `check_redis_health()` führt PING aus und gibt True/False zurück
- [ ] Client wird beim App-Shutdown geschlossen

**Technische Hinweise:** redis-py mit asyncio-Support verwenden. Redis wird für API Response Cache, Search Result Cache, Embedding Cache und Rate-Limiting eingesetzt (D1 Abschnitt 6.4).

---

#### TASK-031: Kombinierter Health-Check-Endpoint erstellen

| Feld             | Wert                                        |
| ---------------- | ------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                          |
| **Bereich**      | Backend                                     |
| **Aufwand**      | XS (<2h)                                    |
| **Status**       | 🔴 Offen                                    |
| **Quelle**       | D1 Abschnitt 3.6 (GET /api/v1/admin/health) |
| **Abhängig von** | TASK-027, TASK-028, TASK-029, TASK-030      |
| **Blockiert**    | –                                           |

**Beschreibung:** Einen `GET /api/v1/admin/health`-Endpoint implementieren, der alle vier Datenbank-Verbindungen (PostgreSQL, Weaviate, Neo4j, Redis) parallel prüft und den aggregierten Status zurückgibt. Ist eine DB nicht erreichbar, wird der Status auf `degraded` oder `unhealthy` gesetzt.

**Acceptance Criteria:**

- [ ] `GET /api/v1/admin/health` existiert und erfordert keine Authentifizierung
- [ ] Response enthält: overall_status (healthy/degraded/unhealthy), pro DB: status (up/down) und Latenz in ms
- [ ] Wenn alle DBs erreichbar: HTTP 200 mit status=healthy
- [ ] Wenn mindestens eine DB nicht erreichbar: HTTP 200 mit status=degraded und Details zu fehlender DB
- [ ] Health-Checks laufen parallel (async) mit Timeout von 5 Sekunden pro Check

**Technische Hinweise:** Kein Auth auf diesem Endpunkt (wird vom Load Balancer aufgerufen). Parallele Ausführung via `asyncio.gather()`. Timeout pro Check, damit ein hängender Service nicht den gesamten Health-Check blockiert.

---

#### TASK-032: Pydantic-Modell UnifiedDocument implementieren

| Feld             | Wert                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                            |
| **Bereich**      | Backend                                                                   |
| **Aufwand**      | S (0.5–1 Tag)                                                             |
| **Status**       | 🔴 Offen                                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (Unified Document Format), copilot-instructions.md (UDF) |
| **Abhängig von** | TASK-009                                                                  |
| **Blockiert**    | –                                                                         |

**Beschreibung:** Das `UnifiedDocument`-Pydantic-Modell gemäß D1 Abschnitt 3.1 implementieren. Dieses Format ist die zentrale Schnittstelle zwischen Ingestion und Processing. Alle Konnektoren normalisieren ihre Rohdaten in dieses Format.

**Acceptance Criteria:**

- [ ] Pydantic v2 Modell `UnifiedDocument` in `app/schemas/document.py` mit allen Feldern: id (UUID), user_id (UUID), source_type (SourceType Enum), source_id (str), title (str), content (str), content_type (ContentType Enum), metadata (dict), participants (list[str]), created_at (datetime), updated_at (datetime), fetched_at (datetime), language (str), raw_hash (str)
- [ ] `SourceType` Enum mit Werten: GOOGLE_CALENDAR, NOTION, OBSIDIAN, ZOOM (erweiterbar)
- [ ] `ContentType` Enum mit Werten: PLAINTEXT, MARKDOWN, HTML
- [ ] Vollständige Type Annotations, kein `Any` außer bei metadata

**Technische Hinweise:** Format aus D1 Abschnitt 3.1 (Ingestion Service, UDF). raw_hash ist SHA-256 des Rohinhalts für Deduplizierung. metadata als dict[str, Any] ist bewusst flexibel für quellenspezifische Daten.

---

#### TASK-033: Pydantic-Modelle Chunk und Entity implementieren

| Feld             | Wert                                                               |
| ---------------- | ------------------------------------------------------------------ |
| **Priorität**    | P0 (kritisch, blockiert alles)                                     |
| **Bereich**      | Backend                                                            |
| **Aufwand**      | S (0.5–1 Tag)                                                      |
| **Status**       | 🔴 Offen                                                           |
| **Quelle**       | D1 Abschnitt 3.3.1, D4 Datenmodell: Chunk + Entity + EntityMention |
| **Abhängig von** | TASK-009                                                           |
| **Blockiert**    | –                                                                  |

**Beschreibung:** Pydantic v2 Modelle für `Chunk`, `Entity` und `EntityMention` implementieren, die die Processing-Pipeline-Ergebnisse typisieren und als Request/Response-Schemas dienen.

**Acceptance Criteria:**

- [ ] `Chunk`-Modell in `app/schemas/document.py` mit: id (UUID), document_id (UUID), user_id (UUID), chunk_index (int), token_count (int), weaviate_id (UUID | None), content_preview (str | None), created_at (datetime)
- [ ] `Entity`-Modell in `app/schemas/knowledge.py` mit: id (UUID), user_id (UUID), entity_type (EntityType Enum), name (str), normalized_name (str), metadata (dict), first_seen (datetime), last_seen (datetime), mention_count (int), neo4j_node_id (str | None)
- [ ] `EntityType` Enum mit Werten: PERSON, PROJECT, TOPIC, DECISION
- [ ] `EntityMention`-Modell mit: entity_id (UUID), chunk_id (UUID), confidence (float), extraction_method (Literal['rule', 'llm'])

**Technische Hinweise:** Modelle korrespondieren mit den SQLAlchemy-Modellen (TASK-015ff) und den DB-Tabellen. Pydantic v2 mit `model_validator` wo nötig. Strikte Typisierung gemäß copilot-instructions.md.

---

#### TASK-034: Pydantic-Modelle Briefing und SourceRef implementieren

| Feld             | Wert                                                                                |
| ---------------- | ----------------------------------------------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                                                                  |
| **Bereich**      | Backend                                                                             |
| **Aufwand**      | S (0.5–1 Tag)                                                                       |
| **Status**       | 🔴 Offen                                                                            |
| **Quelle**       | D1 Abschnitt 3.3.1 (briefings-Tabelle), D4 Datenmodell: Briefing, D4 API: Briefings |
| **Abhängig von** | TASK-009                                                                            |
| **Blockiert**    | –                                                                                   |

**Beschreibung:** Pydantic v2 Modelle für `Briefing`, `BriefingCreate`, `BriefingResponse` und `SourceRef` implementieren. SourceRef ist die Quellenreferenz-Struktur, die in Briefings und Suchergebnissen verwendet wird, um Erklärbarkeit zu gewährleisten.

**Acceptance Criteria:**

- [ ] `Briefing`-Modell in `app/schemas/briefing.py` mit: id (UUID), user_id (UUID), briefing_type (BriefingType Enum), title (str), content (str), source_chunks (list[UUID]), source_entities (list[UUID] | None), trigger_context (dict | None), generated_at (datetime), expires_at (datetime | None)
- [ ] `BriefingType` Enum mit Werten: MORNING, MEETING_PREP
- [ ] `SourceRef`-Modell mit: chunk_id (UUID), doc_title (str), source_type (SourceType), date (datetime), relevance (float)
- [ ] `BriefingResponse`-Modell mit eingebetteter sources-Liste (list[SourceRef])

**Technische Hinweise:** SourceRef implementiert das Erklärbarkeits-Prinzip aus copilot-instructions.md: Jede LLM-generierte Aussage muss Quellenreferenzen transportieren. BriefingType ist erweiterbar für Phase 3 (PROJECT, WEEKLY).

---

#### TASK-035: Pydantic-Modelle SearchResult und Connection implementieren

| Feld             | Wert                                                           |
| ---------------- | -------------------------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                                             |
| **Bereich**      | Backend                                                        |
| **Aufwand**      | S (0.5–1 Tag)                                                  |
| **Status**       | 🔴 Offen                                                       |
| **Quelle**       | D4 API: Search, D4 Datenmodell: Connection, D4 API: Connectors |
| **Abhängig von** | TASK-009                                                       |
| **Blockiert**    | –                                                              |

**Beschreibung:** Pydantic v2 Modelle für `SearchResult`, `SearchRequest`, `SearchResponse`, `Connection` und `ConnectionStatus` implementieren. Diese Modelle definieren die API-Contracts für Suche und Konnektor-Management.

**Acceptance Criteria:**

- [ ] `SearchResult`-Modell in `app/schemas/search.py` mit: chunk_id (UUID), doc_title (str), source_type (SourceType), date (datetime), content (str), score (float), entities (list[str])
- [ ] `SearchRequest`-Modell mit: query (str), filters (SearchFilters | None), limit (int, default=10, max=50)
- [ ] `SearchResponse`-Modell mit: results (list[SearchResult]), answer (str | None), sources (list[SourceRef]), confidence (float | None)
- [ ] `Connection`-Modell in `app/schemas/connector.py` mit: id (UUID), user_id (UUID), source_type (SourceType), status (ConnectionStatus Enum), watermark (datetime | None), config (dict), created_at (datetime)
- [ ] `ConnectionStatus` Enum: ACTIVE, PAUSED, ERROR, REVOKED

**Technische Hinweise:** SearchFilters gemäß D4 API: source_types (list[SourceType] | None), date_from/date_to (datetime | None), entity_ids (list[UUID] | None). Limit max=50 gemäß AGENTS.md SearchAgent.

---

#### TASK-036: SQLAlchemy-ORM-Modelle für alle PostgreSQL-Tabellen erstellen

| Feld             | Wert                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                                           |
| **Bereich**      | Backend                                                                                  |
| **Aufwand**      | M (2–3 Tage)                                                                             |
| **Status**       | 🔴 Offen                                                                                 |
| **Quelle**       | D1 Abschnitt 3.3.1, D1 Abschnitt 8.2 (models/)                                           |
| **Abhängig von** | TASK-009, TASK-015, TASK-016, TASK-017, TASK-019, TASK-020, TASK-021, TASK-022, TASK-023 |
| **Blockiert**    | TASK-024, TASK-027                                                                       |

**Beschreibung:** SQLAlchemy 2.0 ORM-Modelle (Mapped Classes) für alle 9 PostgreSQL-Tabellen erstellen: User, Connection, Document, Chunk, Entity, EntityMention, Briefing, AuditLog, ScheduledJobRun. Modelle in separaten Dateien unter `app/models/`.

**Acceptance Criteria:**

- [ ] `app/models/user.py` mit User-Modell inkl. Relationships zu Connection, Document, Entity, Briefing
- [ ] `app/models/connection.py` mit Connection-Modell inkl. Relationship zu User
- [ ] `app/models/document.py` mit Document-Modell inkl. Relationships zu Chunks
- [ ] `app/models/chunk.py` mit Chunk-Modell inkl. Relationships zu Document und EntityMentions
- [ ] `app/models/entity.py` mit Entity- und EntityMention-Modellen
- [ ] `app/models/briefing.py` mit Briefing-Modell
- [ ] `app/models/audit.py` mit AuditLog-Modell
- [ ] Alle Modelle verwenden SQLAlchemy 2.0 Syntax (`Mapped`, `mapped_column`, `relationship`)
- [ ] `app/models/__init__.py` exportiert alle Modelle (für Alembic autogenerate)

**Technische Hinweise:** SQLAlchemy 2.0 deklarative Mapped-Syntax verwenden. CASCADE/SET NULL gemäß DB-Schema. Async-kompatibel (kein lazy loading, nur explicit loading). Base-Klasse mit common fields (id, created_at, updated_at) als Mixin.

---

#### TASK-037: FastAPI-App-Skeleton mit Middleware-Stack erstellen

| Feld             | Wert                                                                       |
| ---------------- | -------------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch, blockiert alles)                                             |
| **Bereich**      | Backend                                                                    |
| **Aufwand**      | S (0.5–1 Tag)                                                              |
| **Status**       | 🔴 Offen                                                                   |
| **Quelle**       | D1 Abschnitt 3.6 (API Layer, Middleware-Stack), D1 Abschnitt 8.2 (main.py) |
| **Abhängig von** | TASK-009, TASK-012                                                         |
| **Blockiert**    | TASK-031                                                                   |

**Beschreibung:** `app/main.py` als FastAPI-App-Skeleton erstellen mit Middleware-Stack (CORS, TrustedHost, RequestID), Lifecycle-Events (DB-Connections auf Startup/Shutdown) und Router-Montage-Vorbereitung. Keine vollständige Implementierung der Endpunkte, aber die App muss starten und den Health-Check-Endpunkt bedienen.

**Acceptance Criteria:**

- [ ] `app/main.py` erstellt FastAPI-App mit Titel „PWBS API", Version „0.1.0"
- [ ] CORSMiddleware konfiguriert (erlaubte Origins konfigurierbar via Settings)
- [ ] TrustedHostMiddleware konfiguriert
- [ ] RequestID-Middleware fügt jeder Response eine X-Request-ID hinzu
- [ ] Lifecycle: DB-Engines und -Clients werden beim Startup initialisiert und beim Shutdown geschlossen
- [ ] App startet fehlerfrei mit `uvicorn app.main:app --reload`

**Technische Hinweise:** Middleware-Reihenfolge gemäß D1 Abschnitt 3.6: CORS → TrustedHost → RequestID → (RateLimitMiddleware kommt später) → (AuthMiddleware kommt später). Router-Einbindung vorbereiten mit `app.include_router()` Platzhaltern.

---

#### TASK-038: Frontend Next.js-Projekt mit TypeScript und Tailwind CSS initialisieren

| Feld             | Wert                                                              |
| ---------------- | ----------------------------------------------------------------- |
| **Priorität**    | P1 (Must-Have MVP)                                                |
| **Bereich**      | Infra                                                             |
| **Aufwand**      | S (0.5–1 Tag)                                                     |
| **Status**       | 🔴 Offen                                                          |
| **Quelle**       | D1 Abschnitt 3.7 (Frontend), D1 Abschnitt 8.2 (Frontend-Struktur) |
| **Abhängig von** | TASK-009                                                          |
| **Blockiert**    | –                                                                 |

**Beschreibung:** Next.js-Projekt (App Router) unter `frontend/` initialisieren mit TypeScript strict mode, Tailwind CSS und der in D1 Abschnitt 3.7 definierten Verzeichnisstruktur. Basis-Konfiguration für `tsconfig.json` (strict: true), `next.config.ts` und `tailwind.config.ts`.

**Acceptance Criteria:**

- [ ] `frontend/` mit Next.js 14+ (App Router), TypeScript, Tailwind CSS initialisiert
- [ ] `tsconfig.json` mit `"strict": true`
- [ ] Verzeichnisstruktur gemäß D1 Abschnitt 3.7: `src/app/(auth)/`, `src/app/(dashboard)/`, `src/components/`, `src/lib/`, `src/hooks/`, `src/stores/`, `src/types/`
- [ ] `src/lib/api-client.ts` als Platzhalter-Datei für den typisierten HTTP-Client
- [ ] `npm run dev` startet das Frontend ohne Fehler auf Port 3000
- [ ] Frontend-Dockerfile (`Dockerfile.dev`) existiert

**Technische Hinweise:** Kein `"use client"` in Server Components (nur wo nötig). API-Calls über `src/lib/api-client.ts` abstrahieren, nie direkte `fetch()`-Aufrufe in Komponenten (gemäß copilot-instructions.md).

---

#### TASK-039: Terraform-Grundstruktur für AWS-Deployment erstellen

| Feld             | Wert                                                                               |
| ---------------- | ---------------------------------------------------------------------------------- |
| **Priorität**    | P2 (Should-Have)                                                                   |
| **Bereich**      | Infra                                                                              |
| **Aufwand**      | M (2–3 Tage)                                                                       |
| **Status**       | 🔴 Offen                                                                           |
| **Quelle**       | D1 Abschnitt 8.4 (Infrastructure as Code), D1 Abschnitt 2.2 (Deployment-Topologie) |
| **Abhängig von** | TASK-009                                                                           |
| **Blockiert**    | –                                                                                  |

**Beschreibung:** Die Terraform-Modul-Struktur gemäß D1 Abschnitt 8.4 unter `infra/terraform/` aufsetzen. Module für Networking (VPC, Subnets), ECS (Fargate), RDS (PostgreSQL), EC2 (Weaviate, Neo4j), ElastiCache (Redis), KMS und Monitoring als Skelett-Module anlegen. Environment-Files für staging und production.

**Acceptance Criteria:**

- [ ] `infra/terraform/main.tf` mit Modul-Referenzen gemäß D1 Abschnitt 8.4
- [ ] Module-Verzeichnisse: networking, ecs, rds, ec2_weaviate, ec2_neo4j, elasticache, kms, monitoring
- [ ] Jedes Modul hat `main.tf`, `variables.tf`, `outputs.tf` als Skelett
- [ ] `infra/terraform/environments/staging.tfvars` und `production.tfvars` mit Beispielwerten
- [ ] Region fest auf `eu-central-1` (Frankfurt) für DSGVO-Konformität (D4 NF-018)

**Technische Hinweise:** Terraform-Struktur gemäß D1 Abschnitt 8.4. Deployment-Topologie aus D1 Abschnitt 2.2: ECS Fargate für API, RDS für PostgreSQL, EC2 für Weaviate/Neo4j, ElastiCache für Redis. KMS für Master Encryption Key.

---

#### TASK-040: Staging-Deployment-Workflow für GitHub Actions erstellen

| Feld             | Wert                                               |
| ---------------- | -------------------------------------------------- |
| **Priorität**    | P2 (Should-Have)                                   |
| **Bereich**      | Infra                                              |
| **Aufwand**      | M (2–3 Tage)                                       |
| **Status**       | 🔴 Offen                                           |
| **Quelle**       | D1 Abschnitt 8.3 (CI/CD-Strategie, Deploy-Staging) |
| **Abhängig von** | TASK-013, TASK-039                                 |
| **Blockiert**    | –                                                  |

**Beschreibung:** GitHub Actions Workflow `.github/workflows/deploy-staging.yml` erstellen, der nach erfolgreichem CI-Lauf auf dem main-Branch automatisch ein Docker-Image baut, es in AWS ECR pusht und ein ECS-Update auf der Staging-Umgebung auslöst. Inklusive Terraform-Apply für Infrastrukturchanges.

**Acceptance Criteria:**

- [ ] `.github/workflows/deploy-staging.yml` triggert automatisch nach erfolgreichem CI auf main
- [ ] Workflow baut Docker-Image und pusht es in AWS ECR
- [ ] Workflow führt `terraform apply` auf staging-Environment aus
- [ ] ECS Fargate Service wird auf neues Image aktualisiert
- [ ] Nach Deploy: E2E-Test-Step (Platzhalter, wird später mit Playwright befüllt)

**Technische Hinweise:** Gemäß D1 Abschnitt 8.3. AWS-Credentials via GitHub Secrets (OIDC oder IAM Access Keys). ECR-Repository und ECS-Cluster müssen via Terraform (TASK-039) existieren. Deploy-Dauer Ziel: < 5 Minuten.

---

## Statistik Teil 1

| Bereich | Anzahl | P0  | P1  | P2  | P3  |
| ------- | ------ | --- | --- | --- | --- |
| Backend | 10     | 7   | 3   | 0   | 0   |
| Infra   | 10     | 4   | 2   | 2   | 0   |
| DB      | 12     | 11  | 1   | 0   | 0   |
| Docs    | 8      | 3   | 3   | 1   | 0   |

Phase 1: 8 Tasks | Phase 2 Infra/DB: 32 Tasks | Gesamt: 40 Tasks

<!-- AGENT_1_LAST: TASK-040 -->

---


---

## Konnektoren – Basisinfrastruktur

#### TASK-041: BaseConnector ABC mit fetch/normalize/get_cursor Interface implementieren

| Feld             | Wert                                                       |
| ---------------- | ---------------------------------------------------------- |
| **Priorität**    | P0                                                         |
| **Bereich**      | Backend                                                    |
| **Aufwand**      | M                                                          |
| **Status**       | 🔴 Offen                                                   |
| **Quelle**       | D1 Abschnitt 3.1 (BaseConnector-Interface), D4 F-004–F-007 |
| **Abhängig von** | Pydantic-Modelle (Agent 1)                                 |
| **Blockiert**    | TASK-045, TASK-049, TASK-053, TASK-057                     |

**Beschreibung:** Abstrakte Basisklasse `BaseConnector` im Modul `pwbs/connectors/base.py` implementieren. Definiert das Interface mit den Methoden `authenticate()`, `fetch_incremental(watermark)`, `normalize(raw) → UnifiedDocument` und `source_type()`. Enthält gemeinsame Logik für Exponential Backoff bei Rate-Limit-Fehlern (429, 503) und partielle Batch-Verarbeitung (max. 100 Dokumente pro Run).

**Acceptance Criteria:**

- [ ] `BaseConnector` ist eine abstrakte Klasse mit `@abstractmethod` für `authenticate`, `fetch_incremental`, `normalize` und `source_type`
- [ ] Gemeinsame Retry-Logik mit Exponential Backoff (3 Retries: 1 min → 5 min → 25 min) ist in der Basisklasse implementiert
- [ ] Partielle Erfolge werden unterstützt – ein fehlgeschlagenes Dokument bricht nicht den gesamten Batch ab
- [ ] Vollständige Type Annotations, keine `Any`-Typen

**Technische Hinweise:** Das `BaseConnector`-Interface folgt exakt dem Schema aus D1 Abschnitt 3.1. Alle Konnektoren erben von dieser Klasse. Die max. Batch-Größe von 100 Dokumenten pro Run ist als Klassenkonstante konfigurierbar.

---

#### TASK-042: ConnectorRegistry mit Registrierung, Lookup und Health-Check implementieren

| Feld             | Wert                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                        |
| **Bereich**      | Backend                                                                   |
| **Aufwand**      | S                                                                         |
| **Status**       | 🔴 Offen                                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (Connector Registry), D1 Abschnitt 2.1 (Ingestion Layer) |
| **Abhängig von** | TASK-041                                                                  |
| **Blockiert**    | TASK-045, TASK-049, TASK-053, TASK-057                                    |

**Beschreibung:** `ConnectorRegistry` im Modul `pwbs/connectors/registry.py` implementieren. Sie verwaltet alle registrierten Konnektoren, ermöglicht Lookup nach `SourceType`, und bietet einen Health-Check-Mechanismus, der den Status jedes registrierten Konnektors abfragt (active, paused, error, revoked).

**Acceptance Criteria:**

- [ ] Konnektoren können per `register(connector_class)` registriert und per `get(source_type)` abgefragt werden
- [ ] `health_check()` gibt pro registriertem Konnektor den Status zurück (active/paused/error/revoked)
- [ ] Doppelte Registrierung desselben `SourceType` wirft einen `ConnectorError`
- [ ] Liste aller verfügbaren Konnektoren abrufbar

**Technische Hinweise:** Im MVP läuft die Registry in-process. Die Statuswerte korrespondieren mit der `connections`-Tabelle aus D1 Abschnitt 3.3.1.

---

#### TASK-043: OAuth Token Manager mit verschlüsselter Persistierung implementieren

| Feld             | Wert                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                        |
| **Bereich**      | Backend                                                                   |
| **Aufwand**      | M                                                                         |
| **Status**       | 🔴 Offen                                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (OAuth-Flow), D4 F-010 (OAuth-Token-Rotation), D4 NF-016 |
| **Abhängig von** | DB-Schema (Agent 1)                                                       |
| **Blockiert**    | TASK-045, TASK-049, TASK-057                                              |

**Beschreibung:** `OAuthTokenManager` im Modul `pwbs/connectors/oauth.py` implementieren. Verantwortlich für die verschlüsselte Speicherung von OAuth-Tokens (Access + Refresh) in der `connections`-Tabelle, automatische Token-Rotation bei Ablauf und Refresh-Token-Erneuerung. Tokens werden doppelt verschlüsselt: DB-Level + App-Level mit User-DEK via Fernet.

**Acceptance Criteria:**

- [ ] Tokens werden mit User-DEK via Fernet verschlüsselt in der `credentials_enc`-Spalte gespeichert
- [ ] Automatischer Refresh bei abgelaufenem Access-Token vor jedem API-Call
- [ ] Bei Refresh wird ein neues Refresh-Token ausgestellt und das alte invalidiert (Token Rotation)
- [ ] Bei fehlgeschlagenem Refresh wird der Konnektor-Status auf `error` gesetzt
- [ ] Keine Secrets im Klartext in Logs oder Fehlermeldungen

**Technische Hinweise:** Doppelte Verschlüsselung gemäß D4 NF-016: DB-Encryption + App-Level Fernet mit user-spezifischem DEK. Der DEK wird über den `encryption_key_enc` aus der `users`-Tabelle (D1 Abschnitt 3.3.1) abgeleitet.

---

#### TASK-044: UnifiedDocument-Normalizer-Basislogik und Content-Hashing implementieren

| Feld             | Wert                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                        |
| **Bereich**      | Backend                                                                   |
| **Aufwand**      | S                                                                         |
| **Status**       | 🔴 Offen                                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (Unified Document Format), D1 Abschnitt 1.2 (Idempotenz) |
| **Abhängig von** | Pydantic-Modelle (Agent 1), TASK-041                                      |
| **Blockiert**    | TASK-046, TASK-050, TASK-054, TASK-058                                    |

**Beschreibung:** Gemeinsame Normalizer-Logik implementieren, die von allen Konnektoren genutzt wird: SHA-256 Content-Hashing für Deduplizierung (`raw_hash`/`content_hash`), Sprach-Erkennung (`language`), Participants-Extraktion und Metadaten-Validierung. Idempotenz-Prüfung: Dokumente mit identischem `content_hash` werden nicht erneut verarbeitet.

**Acceptance Criteria:**

- [ ] SHA-256-Hash wird aus dem normalisierten Content berechnet und als `content_hash` gespeichert
- [ ] Duplikaterkennung: Existierender `content_hash` für gleichen `user_id + source_type + source_id` verhindert Neuverarbeitung
- [ ] Spracherkennung liefert ISO 639-1 Code (de, en)
- [ ] Metadaten-Schema-Validierung via Pydantic

**Technische Hinweise:** Das UDF-Schema folgt exakt D1 Abschnitt 3.1. Die Deduplizierung nutzt den UNIQUE-Constraint `(user_id, source_type, source_id)` aus dem DB-Schema (D1 Abschnitt 3.3.1).

---

## Konnektoren – Google Calendar

#### TASK-045: Google Calendar OAuth2-Flow implementieren

| Feld             | Wert                                                                             |
| ---------------- | -------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                               |
| **Bereich**      | Backend                                                                          |
| **Aufwand**      | M                                                                                |
| **Status**       | 🔴 Offen                                                                         |
| **Quelle**       | D1 Abschnitt 3.1 (OAuth-Flow-Diagramm, Konnektoren-Tabelle), D4 US-1.2, D4 F-004 |
| **Abhängig von** | TASK-041, TASK-042, TASK-043                                                     |
| **Blockiert**    | TASK-046                                                                         |

**Beschreibung:** Google Calendar Konnektor (`pwbs/connectors/google_calendar.py`) mit vollständigem OAuth2-Flow implementieren. Scope: `calendar.events.readonly`. Auth-URL-Generierung, Callback-Verarbeitung (Code → Token-Exchange), verschlüsselte Token-Speicherung via `OAuthTokenManager`. Bei abgelehntem Consent oder abgebrochenem Flow wird ein aussagekräftiger Fehler zurückgegeben.

**Acceptance Criteria:**

- [ ] OAuth2-Auth-URL wird mit Scope `calendar.events.readonly` generiert
- [ ] Callback verarbeitet den Authorization Code und tauscht ihn gegen Access+Refresh Token
- [ ] Tokens werden verschlüsselt in der `connections`-Tabelle persistiert
- [ ] Fehlgeschlagener oder abgebrochener OAuth-Flow wird sauber behandelt (kein hängender Zustand)
- [ ] Connection-Status wird auf `active` gesetzt nach erfolgreichem Flow

**Technische Hinweise:** Flow folgt dem OAuth-Sequenzdiagramm aus D1 Abschnitt 3.1. Google API Client Library verwenden. Redirect-URI muss konfigurierbar sein.

---

#### TASK-046: Google Calendar Sync-Logik mit Webhook + Polling-Fallback implementieren

| Feld             | Wert                                                                     |
| ---------------- | ------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                       |
| **Bereich**      | Backend                                                                  |
| **Aufwand**      | L                                                                        |
| **Status**       | 🔴 Offen                                                                 |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle: Webhook + Polling 15 min), D4 F-004 |
| **Abhängig von** | TASK-045, TASK-044                                                       |
| **Blockiert**    | TASK-047                                                                 |

**Beschreibung:** Sync-Logik für den Google Calendar Konnektor implementieren. Primär: Webhook-basierte Push Notifications von der Google Calendar API. Fallback: Polling alle 15 Minuten via `fetch_incremental(watermark)`. Initialer Full-Sync aller Kalendereinträge beim ersten Verbinden. Inkrementeller Sync basierend auf `syncToken`/`updatedMin` als Watermark. Cursor wird nach jedem erfolgreichen Batch persistiert.

**Acceptance Criteria:**

- [ ] Initialer Full-Sync importiert alle Kalendereinträge (paginiert)
- [ ] Inkrementeller Sync nutzt `syncToken` oder `updatedMin` als Watermark
- [ ] Webhook-Empfang für Google Calendar Push Notifications implementiert
- [ ] Polling-Fallback alle 15 Minuten greift automatisch, wenn Webhook nicht verfügbar
- [ ] Watermark wird nach jedem erfolgreichen Batch in der `connections`-Tabelle persistiert

**Technische Hinweise:** Google Calendar API nutzt `syncToken` für inkrementelle Sync. Webhook erfordert einen öffentlichen Endpunkt; im lokalen Dev-Modus wird nur Polling verwendet. Batch-Größe max. 100 Events.

---

#### TASK-047: Google Calendar Normalizer (Events → UnifiedDocument) implementieren

| Feld             | Wert                                                                        |
| ---------------- | --------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                          |
| **Bereich**      | Backend                                                                     |
| **Aufwand**      | M                                                                           |
| **Status**       | 🔴 Offen                                                                    |
| **Quelle**       | D1 Abschnitt 3.1 (Datentypen: Events, Teilnehmer, Beschreibungen), D4 F-004 |
| **Abhängig von** | TASK-046, TASK-044                                                          |
| **Blockiert**    | –                                                                           |

**Beschreibung:** Normalizer für Google Calendar Events, der Rohdaten ins UnifiedDocument Format konvertiert. Extrahiert: Event-Titel, Beschreibung, Teilnehmer (E-Mail + Name), Start-/Endzeit, Wiederholungsregeln, Ort. Teilnehmer werden in das `participants`-Feld und in source-spezifische `metadata` geschrieben. Ganztägige Events und wiederkehrende Events werden korrekt behandelt.

**Acceptance Criteria:**

- [ ] Events werden in UnifiedDocument normalisiert mit Titel, Content (Beschreibung), Participants und Metadaten
- [ ] Teilnehmer werden als `list[str]` (E-Mail oder Name) in das `participants`-Feld extrahiert
- [ ] Ganztägige Events, wiederkehrende Events und Events ohne Beschreibung werden korrekt verarbeitet
- [ ] `source_type` ist `GOOGLE_CALENDAR`, `source_id` ist die Google Event-ID
- [ ] Content-Hash wird berechnet für Deduplizierung

**Technische Hinweise:** Metadaten enthalten mindestens: `start_time`, `end_time`, `location`, `is_recurring`, `attendee_count`. Das Format folgt dem UDF aus D1 Abschnitt 3.1.

---

## Konnektoren – Notion

#### TASK-048: Notion OAuth2-Flow implementieren

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P0                                                        |
| **Bereich**      | Backend                                                   |
| **Aufwand**      | M                                                         |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle), D4 US-1.3, D4 F-005 |
| **Abhängig von** | TASK-041, TASK-042, TASK-043                              |
| **Blockiert**    | TASK-049                                                  |

**Beschreibung:** Notion Integration Konnektor (`pwbs/connectors/notion.py`) mit OAuth2-Flow implementieren. Nutzt die Notion Public Integration OAuth. Callback verarbeitet den Authorization Code, tauscht ihn gegen Access Token (Notion verwendet kein Refresh-Token-Paar, sondern einen dauerhaften Access Token) und speichert diesen verschlüsselt. Nach erfolgreichem Consent werden die freigegebenen Seiten und Datenbanken als Sync-Scope angezeigt.

**Acceptance Criteria:**

- [ ] OAuth2-Auth-URL wird für Notion Public Integration generiert
- [ ] Callback tauscht Authorization Code gegen Access Token
- [ ] Token wird verschlüsselt in der `connections`-Tabelle persistiert
- [ ] Freigegebene Seiten/Datenbanken werden nach Verbindung aufgelistet
- [ ] Connection-Status wird auf `active` gesetzt

**Technische Hinweise:** Notion OAuth unterscheidet sich von Google: Es gibt keinen Refresh-Token. Der Access Token bleibt gültig, bis der Nutzer die Integration widerruft. Notion API Client nutzen.

---

#### TASK-049: Notion Polling-Sync mit last_edited_time-Cursor implementieren

| Feld             | Wert                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                      |
| **Bereich**      | Backend                                                                                 |
| **Aufwand**      | M                                                                                       |
| **Status**       | 🔴 Offen                                                                                |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle: Polling 10 min, last_edited_time-Cursor), D4 F-005 |
| **Abhängig von** | TASK-048, TASK-044                                                                      |
| **Blockiert**    | TASK-050                                                                                |

**Beschreibung:** Polling-basierte Sync-Logik für den Notion Konnektor. Polling-Intervall: alle 10 Minuten. Verwendet `last_edited_time` als Cursor/Watermark für inkrementelle Syncs. Initialer Full-Sync beim ersten Verbinden holt alle freigegebenen Seiten und Datenbanken. Paginierung über Notion API `start_cursor`.

**Acceptance Criteria:**

- [ ] Initialer Full-Sync importiert alle freigegebenen Seiten und Datenbanken (paginiert)
- [ ] Inkrementeller Sync nutzt `last_edited_time` als Watermark und holt nur geänderte Seiten
- [ ] Polling-Intervall beträgt 10 Minuten
- [ ] Cursor/Watermark wird nach jedem erfolgreichen Batch persistiert
- [ ] Gelöschte Notion-Seiten werden erkannt und im System als gelöscht markiert

**Technische Hinweise:** Notion API `POST /search` mit `filter.timestamp = last_edited_time` und `sort.direction = ascending`. Paginierung über `start_cursor` und `has_more`.

---

#### TASK-050: Notion Normalizer (Pages, Databases, Blöcke → UnifiedDocument) implementieren

| Feld             | Wert                                                              |
| ---------------- | ----------------------------------------------------------------- |
| **Priorität**    | P0                                                                |
| **Bereich**      | Backend                                                           |
| **Aufwand**      | L                                                                 |
| **Status**       | 🔴 Offen                                                          |
| **Quelle**       | D1 Abschnitt 3.1 (Datentypen: Pages, Databases, Blöcke), D4 F-005 |
| **Abhängig von** | TASK-049, TASK-044                                                |
| **Blockiert**    | –                                                                 |

**Beschreibung:** Normalizer für Notion-Inhalte, der Pages, Database-Einträge und deren Blöcke ins UnifiedDocument Format konvertiert. Notion-Blöcke (Paragraphs, Headings, Lists, Code, Toggle, Callout etc.) werden rekursiv aufgelöst und in Plaintext/Markdown konvertiert. Page-Properties (Titel, Tags, Daten) werden als Metadaten extrahiert. Verschachtelte Blöcke (Children) werden rekursiv verarbeitet.

**Acceptance Criteria:**

- [ ] Notion Pages werden mit Titel, extrahiertem Textinhalt aus allen Blöcken und Properties normalisiert
- [ ] Block-Typen (paragraph, heading_1/2/3, bulleted_list_item, numbered_list_item, code, toggle, callout) werden in Markdown konvertiert
- [ ] Verschachtelte Blöcke (children) werden rekursiv aufgelöst
- [ ] Database-Einträge werden als individuelle UnifiedDocuments normalisiert
- [ ] Notion-interne Links (@-Mentions, Page-Links) werden als Metadaten extrahiert

**Technische Hinweise:** Notion API `GET /blocks/{block_id}/children` für rekursive Block-Auflösung. Tiefe der Rekursion auf max. 5 Ebenen begrenzen. `content_type` ist `MARKDOWN`.

---

## Konnektoren – Obsidian

#### TASK-051: Obsidian Vault File-System-Watcher implementieren

| Feld             | Wert                                                                                        |
| ---------------- | ------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                          |
| **Bereich**      | Backend                                                                                     |
| **Aufwand**      | M                                                                                           |
| **Status**       | 🔴 Offen                                                                                    |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle: File-System-Watcher via watchdog), D4 US-1.4, D4 F-006 |
| **Abhängig von** | TASK-041, TASK-042                                                                          |
| **Blockiert**    | TASK-052                                                                                    |

**Beschreibung:** Obsidian Vault Konnektor (`pwbs/connectors/obsidian.py`) mit File-System-Watcher via `watchdog`-Library implementieren. Kein OAuth erforderlich – der Nutzer gibt einen lokalen Vault-Pfad an. Initialer Full-Scan aller `.md`-Dateien im Vault. Danach überwacht der Watcher Datei-Änderungen (create, modify, delete) und triggert inkrementelle Verarbeitung. Pfad-Validierung: Prüfung ob der Pfad existiert und Markdown-Dateien enthält.

**Acceptance Criteria:**

- [ ] Nutzer kann einen lokalen Vault-Pfad konfigurieren
- [ ] Pfad-Validierung: Existenz prüfen, mindestens eine `.md`-Datei vorhanden
- [ ] Initialer Full-Scan importiert alle `.md`-Dateien rekursiv
- [ ] File-System-Watcher erkennt create, modify und delete von `.md`-Dateien
- [ ] Gelöschte Dateien werden im System als gelöscht markiert

**Technische Hinweise:** `watchdog`-Library für plattformübergreifendes File-System-Monitoring. `.obsidian/`-Ordner und andere Konfigurationsverzeichnisse vom Scan ausschließen. Watcher läuft als Background-Task im FastAPI-Prozess.

---

#### TASK-052: Obsidian Markdown-Parser mit Frontmatter- und Link-Extraktion implementieren

| Feld             | Wert                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                    |
| **Bereich**      | Backend                                                                               |
| **Aufwand**      | M                                                                                     |
| **Status**       | 🔴 Offen                                                                              |
| **Quelle**       | D1 Abschnitt 3.1 (Datentypen: Markdown-Dateien, Frontmatter, interne Links), D4 F-006 |
| **Abhängig von** | TASK-051, TASK-044                                                                    |
| **Blockiert**    | –                                                                                     |

**Beschreibung:** Markdown-Parser für Obsidian-Dateien, der YAML-Frontmatter, Wikilinks (`[[...]]`), Tags (`#tag`), und Standard-Markdown-Strukturen extrahiert. Frontmatter-Felder (titel, tags, aliases, date) werden als Metadaten in das UnifiedDocument übernommen. Interne Links werden als Beziehungen in den Metadaten gespeichert (für spätere Graph-Verknüpfung). Content wird als Markdown normalisiert.

**Acceptance Criteria:**

- [ ] YAML-Frontmatter wird geparst und als `metadata`-Dict extrahiert
- [ ] Wikilinks `[[Page Name]]` und `[[Page Name|Display Text]]` werden erkannt und in Metadaten gespeichert
- [ ] Tags `#tag` und verschachtelte Tags `#parent/child` werden extrahiert
- [ ] `source_type` ist `OBSIDIAN`, `source_id` ist der relative Dateipfad im Vault
- [ ] Content wird als Markdown normalisiert, Frontmatter wird nicht in den Content aufgenommen

**Technische Hinweise:** `python-frontmatter`-Library für Frontmatter-Parsing. Regex für Wikilink-Extraktion: `\[\[([^\]]+)\]\]`. Content-Type ist `MARKDOWN`.

---

## Konnektoren – Zoom-Transkripte

#### TASK-053: Zoom OAuth2-Flow implementieren

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P0                                                        |
| **Bereich**      | Backend                                                   |
| **Aufwand**      | M                                                         |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle), D4 US-1.5, D4 F-007 |
| **Abhängig von** | TASK-041, TASK-042, TASK-043                              |
| **Blockiert**    | TASK-054                                                  |

**Beschreibung:** Zoom Konnektor (`pwbs/connectors/zoom.py`) mit OAuth2-Flow für den Zoom Marketplace implementieren. Scopes für Transkript-Zugriff (`cloud_recording:read`, `meeting:read`). Callback verarbeitet Authorization Code, tauscht gegen Access+Refresh Token und persistiert verschlüsselt.

**Acceptance Criteria:**

- [ ] OAuth2-Auth-URL wird mit Transkript-relevanten Scopes generiert
- [ ] Callback verarbeitet Authorization Code und tauscht gegen Access+Refresh Token
- [ ] Tokens werden verschlüsselt via `OAuthTokenManager` gespeichert
- [ ] Connection-Status wird auf `active` gesetzt
- [ ] Fehlerzustände (abgebrochener Consent, ungültiger Code) werden sauber behandelt

**Technische Hinweise:** Zoom OAuth2 nutzt Server-to-Server oder User-Level OAuth. Für MVP wird User-Level OAuth verwendet. Token-Rotation via Refresh-Token.

---

#### TASK-054: Zoom Webhook-Receiver für Recording-completed-Events implementieren

| Feld             | Wert                                                                        |
| ---------------- | --------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                          |
| **Bereich**      | Backend                                                                     |
| **Aufwand**      | M                                                                           |
| **Status**       | 🔴 Offen                                                                    |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle: Webhook recording.completed), D4 F-007 |
| **Abhängig von** | TASK-053, TASK-044                                                          |
| **Blockiert**    | TASK-055                                                                    |

**Beschreibung:** Webhook-Endpunkt für Zoom `recording.completed`-Events implementieren. Verarbeitet eingehende Webhook-Payloads, validiert die Zoom-Signatur (Webhook Verification Token), ruft die Transkript-Datei über die Zoom API ab und stößt die Normalisierung an. Idempotenz: Doppelte Webhook-Events (gleiche `recording_id`) werden erkannt und ignoriert.

**Acceptance Criteria:**

- [ ] Webhook-Endpunkt empfängt `recording.completed`-Events
- [ ] Zoom-Signatur wird gegen den Verification Token validiert (Replay-Schutz)
- [ ] Transkript wird über die Zoom Cloud Recording API abgerufen
- [ ] Doppelte Events (gleiche `recording_id`) werden idempotent verarbeitet
- [ ] Webhook-Payload wird mit Pydantic validiert

**Technische Hinweise:** Zoom Webhooks senden einen `event`-Typ und `payload` mit `recording_files`. Nur Dateien vom Typ `TRANSCRIPT` verarbeiten. Zoom erfordert URL-Validation Challenge bei Webhook-Setup.

---

#### TASK-055: Zoom Normalizer (Transkripte, Teilnehmer, Dauer → UnifiedDocument) implementieren

| Feld             | Wert                                                                            |
| ---------------- | ------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                              |
| **Bereich**      | Backend                                                                         |
| **Aufwand**      | M                                                                               |
| **Status**       | 🔴 Offen                                                                        |
| **Quelle**       | D1 Abschnitt 3.1 (Datentypen: Meeting-Transkripte, Teilnehmer, Dauer), D4 F-007 |
| **Abhängig von** | TASK-054, TASK-044                                                              |
| **Blockiert**    | –                                                                               |

**Beschreibung:** Normalizer für Zoom-Transkripte, der Meeting-Aufnahmen ins UnifiedDocument Format konvertiert. Extrahiert: Transkript-Text, Teilnehmerliste (Name + E-Mail), Meeting-Titel, Dauer, Start-/Endzeit. VTT-Format wird in Plaintext konvertiert, Sprecherzuordnung wird soweit vorhanden beibehalten.

**Acceptance Criteria:**

- [ ] Zoom-Transkripte (VTT/TXT-Format) werden in Plaintext konvertiert
- [ ] Teilnehmer werden als `participants`-Liste extrahiert (Name und E-Mail)
- [ ] Meeting-Titel, Dauer, Start-/Endzeit werden als Metadaten gespeichert
- [ ] `source_type` ist `ZOOM`, `source_id` ist die Zoom Meeting-UUID
- [ ] Sprecherzuordnung wird beibehalten, wenn im Transkript vorhanden

**Technische Hinweise:** Zoom liefert Transkripte im VTT-Format. Timestamps im VTT können für spätere Chunk-Referenzierung als Metadaten extrahiert werden. Metadaten enthalten: `duration_minutes`, `start_time`, `end_time`, `participant_count`.

---

## Processing Pipeline – Chunking

#### TASK-056: Chunking Service mit semantischem Splitting implementieren

| Feld             | Wert                                                                          |
| ---------------- | ----------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                            |
| **Bereich**      | Backend                                                                       |
| **Aufwand**      | L                                                                             |
| **Status**       | 🔴 Offen                                                                      |
| **Quelle**       | D1 Abschnitt 3.2 (ChunkingConfig, Pipeline-Stufen), AGENTS.md ProcessingAgent |
| **Abhängig von** | Pydantic-Modelle (Agent 1)                                                    |
| **Blockiert**    | TASK-060                                                                      |

**Beschreibung:** Chunking Service (`pwbs/processing/chunking.py`) implementieren mit drei Strategien: `semantic` (Standard), `paragraph` und `fixed`. Semantisches Splitting teilt an Satzgrenzen auf und erhält semantisch zusammenhängende Abschnitte. Konfiguration: max. 512 Tokens, 64 Token Overlap (D1), Strategie wählbar. Paragraph-Splitting als Fallback für strukturierte Dokumente (Notion, Obsidian). Fixed-Splitting für unstrukturierten Langtext.

**Acceptance Criteria:**

- [ ] Drei Chunking-Strategien implementiert: `semantic`, `paragraph`, `fixed`
- [ ] Semantic Splitting teilt an Satzgrenzen, max. 512 Tokens pro Chunk
- [ ] Token-Overlap von 64 Tokens zwischen aufeinanderfolgenden Chunks
- [ ] Paragraph-Splitting nutzt Markdown-Absätze als natürliche Grenzen
- [ ] Leere oder zu kurze Dokumente (< 32 Tokens) ergeben genau einen Chunk

**Technische Hinweise:** ChunkingConfig aus D1 Abschnitt 3.2: `max_tokens=512`, `overlap_tokens=64`, `strategy="semantic"`. Token-Zählung via `tiktoken` (OpenAI Tokenizer) für Konsistenz mit dem Embedding-Modell.

---

#### TASK-057: Chunking-Strategie-Auswahl nach Dokumenttyp implementieren

| Feld             | Wert                                                 |
| ---------------- | ---------------------------------------------------- |
| **Priorität**    | P1                                                   |
| **Bereich**      | Backend                                              |
| **Aufwand**      | S                                                    |
| **Status**       | 🔴 Offen                                             |
| **Quelle**       | D1 Abschnitt 3.2 (Chunking-Strategie je Dokumenttyp) |
| **Abhängig von** | TASK-056                                             |
| **Blockiert**    | –                                                    |

**Beschreibung:** Automatische Strategieauswahl basierend auf `source_type` und `content_type` des UnifiedDocuments. Obsidian und Notion-Dokumente (`MARKDOWN`) verwenden `paragraph`-Splitting, Zoom-Transkripte `semantic`-Splitting, Kalender-Events `fixed`-Splitting. Überschreibbar per Konfiguration.

**Acceptance Criteria:**

- [ ] Strategie wird automatisch anhand von `source_type` und `content_type` gewählt
- [ ] Mapping ist konfigurierbar (nicht hardcoded)
- [ ] Fallback auf `semantic` wenn kein spezifisches Mapping existiert
- [ ] Strategie wird im Chunk-Modell als Metadatum gespeichert

**Technische Hinweise:** Default-Mapping: `OBSIDIAN` → `paragraph`, `NOTION` → `paragraph`, `ZOOM` → `semantic`, `GOOGLE_CALENDAR` → `fixed`.

---

## Processing Pipeline – Embedding-Generierung

#### TASK-058: OpenAI text-embedding-3-small Integration implementieren

| Feld             | Wert                                                                              |
| ---------------- | --------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                |
| **Bereich**      | Backend                                                                           |
| **Aufwand**      | M                                                                                 |
| **Status**       | 🔴 Offen                                                                          |
| **Quelle**       | D1 Abschnitt 3.2 (Embedding-Tabelle: text-embedding-3-small, 1536 Dim.), D4 F-011 |
| **Abhängig von** | TASK-056, Pydantic-Modelle (Agent 1)                                              |
| **Blockiert**    | TASK-059, TASK-068                                                                |

**Beschreibung:** Embedding-Generator (`pwbs/processing/embedding.py`) implementieren, der Chunks über die OpenAI `text-embedding-3-small`-API in 1536-dimensionale Vektoren konvertiert. Batch-Verarbeitung: max. 64 Chunks pro API-Call. Fehlerbehandlung bei API-Ausfall (Timeout, Rate-Limit) mit Retry-Logik. Das Embedding-Modell ist via Konfiguration austauschbar.

**Acceptance Criteria:**

- [ ] Chunks werden in Batches von max. 64 an die OpenAI Embedding API gesendet
- [ ] Ergebnis: 1536-dimensionale Float-Vektoren pro Chunk
- [ ] Retry-Logik bei API-Fehlern (429, 500, Timeout) mit Exponential Backoff (3 Retries)
- [ ] Modellname ist konfigurierbar (nicht hardcoded)
- [ ] Token-Count pro Batch wird geprüft (OpenAI-Limit: 8191 Tokens pro Input)

**Technische Hinweise:** OpenAI API via `openai`-Library. Batch-Endpoint: `client.embeddings.create(model=..., input=[...])`. Im MVP wird ausschließlich `text-embedding-3-small` verwendet; lokale Modelle (Sentence Transformers) erst ab Phase 3.

---

#### TASK-059: Weaviate-Upsert für Embeddings mit Idempotenz implementieren

| Feld             | Wert                                                                           |
| ---------------- | ------------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                             |
| **Bereich**      | Backend                                                                        |
| **Aufwand**      | M                                                                              |
| **Status**       | 🔴 Offen                                                                       |
| **Quelle**       | D1 Abschnitt 3.3.2 (Weaviate Collection Schema), D1 Abschnitt 1.2 (Idempotenz) |
| **Abhängig von** | TASK-058, DB-Schema (Agent 1)                                                  |
| **Blockiert**    | TASK-068                                                                       |

**Beschreibung:** Weaviate-Storage-Schicht (`pwbs/storage/weaviate.py`) implementieren, die generierte Embeddings idempotent in die `DocumentChunk`-Collection schreibt. Upsert-Logik: Existierender Vektor für gleiche `chunkId` + `userId` wird überschrieben. Multi-Tenancy: Jeder Nutzer ist ein eigener Weaviate-Tenant. Referenz zwischen Weaviate-ID und PostgreSQL `chunks.weaviate_id` wird aktualisiert.

**Acceptance Criteria:**

- [ ] Embeddings werden in die Weaviate `DocumentChunk`-Collection geschrieben
- [ ] Upsert: Existierender Vektor für gleiche `chunkId` wird überschrieben (Idempotenz)
- [ ] Multi-Tenancy: Tenant entspricht der `userId`, kein Cross-User-Zugriff möglich
- [ ] `weaviate_id` wird in der PostgreSQL `chunks`-Tabelle gespeichert
- [ ] Properties `chunkId`, `userId`, `sourceType`, `content`, `title`, `createdAt`, `language` werden gesetzt

**Technische Hinweise:** Weaviate Collection-Schema aus D1 Abschnitt 3.3.2 verwenden. `vectorizer: none` (Vektoren werden extern generiert). HNSW-Index mit `efConstruction=128`, `maxConnections=16`.

---

#### TASK-060: Fehlerbehandlung und Retry-Logik für Embedding-Pipeline implementieren

| Feld             | Wert                                        |
| ---------------- | ------------------------------------------- |
| **Priorität**    | P1                                          |
| **Bereich**      | Backend                                     |
| **Aufwand**      | S                                           |
| **Status**       | 🔴 Offen                                    |
| **Quelle**       | D1 Abschnitt 3.2, AGENTS.md ProcessingAgent |
| **Abhängig von** | TASK-058, TASK-059                          |
| **Blockiert**    | –                                           |

**Beschreibung:** Fehlerbehandlung für die Embedding-Pipeline: Bei OpenAI API-Ausfall werden fehlgeschlagene Batches in eine Retry-Queue geschrieben. Exponential Backoff (1 min → 5 min → 25 min). Dokuemnt-Status in PostgreSQL wird auf `error` gesetzt bei dauerhaftem Fehler (nach 3 Retries). Partielle Erfolge werden gespeichert – wenn 60 von 64 Chunks im Batch erfolgreich sind, werden die 60 persistiert.

**Acceptance Criteria:**

- [ ] Fehlgeschlagene Batches werden mit Exponential Backoff (3 Retries) wiederholt
- [ ] `processing_status` in der `documents`-Tabelle wird auf `error` gesetzt nach 3 Fehlversuchen
- [ ] Partielle Batch-Erfolge werden gespeichert (nicht alles verwerfen bei Teilerfolg)
- [ ] Fehlermeldung wird in den Audit-Log geschrieben

**Technische Hinweise:** Im MVP läuft Retry als Background-Task in FastAPI. Ab Phase 3 über Celery + Redis Queue.

---

## Processing Pipeline – NER & Entitätsextraktion

#### TASK-061: Regelbasierte Entitätsextraktion implementieren

| Feld             | Wert                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                                         |
| **Bereich**      | Backend                                                                                    |
| **Aufwand**      | M                                                                                          |
| **Status**       | 🔴 Offen                                                                                   |
| **Quelle**       | D1 Abschnitt 3.2 (NER regelbasiert: E-Mail, @-Mentions, Kalender-Teilnehmer, Notion-Links) |
| **Abhängig von** | TASK-056, DB-Schema (Agent 1)                                                              |
| **Blockiert**    | TASK-063                                                                                   |

**Beschreibung:** Regelbasierte Entitätsextraktion (`pwbs/processing/ner.py`) als erste Stufe der NER-Pipeline. Erkennt: E-Mail-Adressen → Person-Entities, @-Mentions → Person-Entities, Kalender-Teilnehmer (aus Metadaten) → Person-Entities, Notion-Verlinkungen (aus Metadaten) → diverse Entities. Konfidenz-Score ist 1.0 für regelbasierte Extraktion. Ergebnisse werden in die `entities`- und `entity_mentions`-Tabellen geschrieben.

**Acceptance Criteria:**

- [ ] E-Mail-Adressen werden als Person-Entities mit `extraction_method='rule'` extrahiert
- [ ] @-Mentions (aus Content) werden als Person-Entities extrahiert
- [ ] Kalender-Teilnehmer (aus `participants`-Feld) werden als Person-Entities extrahiert
- [ ] Notion-Links (aus Metadaten) werden als Entities extrahiert
- [ ] Entity-Deduplizierung über `normalized_name` (lowercase, Whitespace-Normalisierung)

**Technische Hinweise:** `confidence=1.0` für regelbasierte Ergebnisse. `UNIQUE(user_id, entity_type, normalized_name)` in der `entities`-Tabelle nutzen für Upsert (Idempotenz). Regex für E-Mail: RFC 5322-konform.

---

#### TASK-062: LLM-basierte Entitätsextraktion mit Structured Output implementieren

| Feld             | Wert                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                                |
| **Bereich**      | LLM                                                                                               |
| **Aufwand**      | L                                                                                                 |
| **Status**       | 🔴 Offen                                                                                          |
| **Quelle**       | D1 Abschnitt 3.2 (ENTITY_EXTRACTION_PROMPT, LLM-basierte Stufe), D1 Abschnitt 3.4 (Token-Budgets) |
| **Abhängig von** | TASK-061, TASK-065                                                                                |
| **Blockiert**    | TASK-063                                                                                          |

**Beschreibung:** LLM-basierte Entitätsextraktion als zweite Stufe der NER-Pipeline. Nutzt den `ENTITY_EXTRACTION_PROMPT` aus D1 mit Structured Output (JSON-Schema) via Claude API (Modell: `claude-haiku` für Kosteneffizienz). Extrahiert: Personen, Projekte, Themen, Entscheidungen, offene Fragen, Termine. Wird nur für Chunks ausgeführt, die die regelbasierte Stufe nicht vollständig abdeckt. Kostenkontrolle: Max. 100 LLM-Extraction-Calls pro Nutzer/Tag.

**Acceptance Criteria:**

- [ ] Structured Output via Claude API (JSON-Schema-Validierung der Antwort)
- [ ] Extrahiert: Personen (Name, Rolle, Kontext), Projekte (Name, Status), Themen, Entscheidungen, offene Fragen, Termine
- [ ] Kostenkontrolle: Max. 100 LLM-Extraction-Calls pro Nutzer/Tag (Counter in Redis/PostgreSQL)
- [ ] Confidence-Score wird pro extrahierter Entity berechnet (nur > 0.75 wird in Graph aufgenommen)
- [ ] LLM-Output wird gegen JSON-Schema validiert, fehlerhafte Antworten werden verworfen und geloggt

**Technische Hinweise:** Token-Budget aus D1: context_tokens=2000, output_tokens=1000, Modell: `claude-haiku`. `extraction_method='llm'` in `entity_mentions`. Prompt-Template liegt in `pwbs/prompts/entity_extraction.md`.

---

#### TASK-063: Entity-Deduplizierung über normalized_name implementieren

| Feld             | Wert                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                       |
| **Bereich**      | Backend                                                                                  |
| **Aufwand**      | M                                                                                        |
| **Status**       | 🔴 Offen                                                                                 |
| **Quelle**       | D1 Abschnitt 3.3.1 (entities-Tabelle: UNIQUE normalized_name), AGENTS.md ProcessingAgent |
| **Abhängig von** | TASK-061, TASK-062                                                                       |
| **Blockiert**    | TASK-064                                                                                 |

**Beschreibung:** Entity-Deduplizierungslogik implementieren, die sicherstellt, dass gleiche Entitäten nicht doppelt existieren. Normalisierung: Lowercase, Whitespace-Trimming, Umlaute normalisieren. Fuzzy-Matching für ähnliche Namen (z.B. „Thomas K." und „Thomas Klein") mit konfigurierbarem Threshold. Merge-Logik: Bei erkanntem Duplikat werden `mention_count`, `last_seen` und `metadata` zusammengeführt.

**Acceptance Criteria:**

- [ ] `normalized_name` wird berechnet: lowercase, whitespace-trimmed, Umlaute normalisiert
- [ ] UPSERT-Logik: Existierender Entity mit gleichem `(user_id, entity_type, normalized_name)` wird aktualisiert statt dupliziert
- [ ] `mention_count` wird inkrementiert, `last_seen` wird aktualisiert
- [ ] Fuzzy-Matching für Kurz-/Langformen implementiert (konfigurierbar, Standard-Threshold: 0.85)

**Technische Hinweise:** PostgreSQL UPSERT via `ON CONFLICT (user_id, entity_type, normalized_name) DO UPDATE`. Fuzzy-Matching zunächst nur für `entity_type=PERSON` via Levenshtein-Distanz.

---

## Processing Pipeline – Graph Builder

#### TASK-064: Neo4j Graph Builder mit MERGE-basierter Idempotenz implementieren

| Feld             | Wert                                                                                          |
| ---------------- | --------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                            |
| **Bereich**      | Backend                                                                                       |
| **Aufwand**      | L                                                                                             |
| **Status**       | 🔴 Offen                                                                                      |
| **Quelle**       | D1 Abschnitt 3.3.3 (Neo4j Schema, Knotentypen, Kantentypen), D1 Abschnitt 3.2 (Graph Builder) |
| **Abhängig von** | TASK-063, DB-Schema (Agent 1)                                                                 |
| **Blockiert**    | TASK-069                                                                                      |

**Beschreibung:** Graph Builder (`pwbs/graph/builder.py`) implementieren, der extrahierte Entities als Knoten und deren Beziehungen als Kanten in Neo4j schreibt. Idempotenz via `MERGE` statt `CREATE`. Knotentypen: Person, Project, Topic, Decision, Meeting, Document. Kantentypen gemäß D1 Schema. Alle Knoten und Queries enthalten `userId` als Pflichtattribut für Mandanten-Isolation.

**Acceptance Criteria:**

- [ ] Knoten werden per `MERGE` erstellt/aktualisiert (kein Duplikat bei erneutem Processing)
- [ ] Alle 6 Knotentypen (Person, Project, Topic, Decision, Meeting, Document) werden unterstützt
- [ ] Alle Kantentypen aus D1 werden erzeugt (PARTICIPATED_IN, WORKS_ON, MENTIONED_IN, etc.)
- [ ] Jeder Cypher-Query enthält `WHERE n.userId = $userId` (Mandanten-Isolation)
- [ ] `neo4j_node_id` wird in der PostgreSQL `entities`-Tabelle als Referenz gespeichert

**Technische Hinweise:** Neo4j-Schema aus D1 Abschnitt 3.3.3. `neo4j`-Python-Driver verwenden. Alle Queries parametrisiert (kein String-Concatenation für Cypher). Batch-Writes: max. 50 Knoten pro Transaction.

---

#### TASK-065: Kantengewichtung und Co-Occurrence-basierte Kantenableitung implementieren

| Feld             | Wert                                                                                |
| ---------------- | ----------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                  |
| **Bereich**      | Backend                                                                             |
| **Aufwand**      | M                                                                                   |
| **Status**       | 🔴 Offen                                                                            |
| **Quelle**       | D1 Abschnitt 3.3.3 (Kantengewichtung: weight-Property, Co-Occurrence, Decay-Faktor) |
| **Abhängig von** | TASK-064                                                                            |
| **Blockiert**    | –                                                                                   |

**Beschreibung:** Kantengewichtung für alle Neo4j-Kanten implementieren. `weight`-Property (Float, 0.0–1.0) basierend auf Häufigkeit der Co-Occurrence und zeitlichem Abstand (Decay-Faktor). Abgeleitete Kanten: `KNOWS`-Beziehung zwischen Personen, die häufig in gleichen Meetings/Dokumenten vorkommen. `RELATED_TO`-Beziehung zwischen Topics mit hoher Co-Occurrence.

**Acceptance Criteria:**

- [ ] Alle Kanten tragen eine `weight`-Property (Float, 0.0–1.0)
- [ ] Gewicht steigt mit Häufigkeit der Co-Occurrence
- [ ] Gewicht sinkt mit zeitlichem Abstand (exponentieller Decay-Faktor)
- [ ] `KNOWS`-Kante zwischen Personen wird automatisch abgeleitet bei Co-Occurrence in ≥ 2 Dokumenten
- [ ] `RELATED_TO`-Kante zwischen Topics bei Co-Occurrence in ≥ 3 Chunks

**Technische Hinweise:** Decay-Formel: `weight = base_weight * exp(-decay_rate * days_since_last_occurrence)`. Kantenableitung läuft als Post-Processing-Schritt nach dem initialen Graph-Build.

---

## LLM Gateway

#### TASK-066: LLM Gateway Service mit Provider-Abstraktion implementieren

| Feld             | Wert                                                                            |
| ---------------- | ------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                              |
| **Bereich**      | LLM                                                                             |
| **Aufwand**      | L                                                                               |
| **Status**       | 🔴 Offen                                                                        |
| **Quelle**       | D1 Abschnitt 3.4 (LLM Orchestration Service, Provider Router, Fallback-Kaskade) |
| **Abhängig von** | Pydantic-Modelle (Agent 1)                                                      |
| **Blockiert**    | TASK-062, TASK-067, TASK-068, TASK-073, TASK-076                                |

**Beschreibung:** LLM Gateway (`pwbs/core/llm_gateway.py`) als Abstraktion über Claude API (primär) und GPT-4 (Fallback) implementieren. Provider Router wählt den Provider basierend auf `model_preference` im PromptTemplate. Fallback-Kaskade: Claude → GPT-4 → Cached Response → Fehlermeldung mit Rohdaten. Request Pipeline: Prompt Assembly → Token Budget Check → Provider Selection → API Call mit Retry → Response Validation → Source Attribution → Confidence Scoring → Cost Logging.

**Acceptance Criteria:**

- [ ] Claude API (primär) und GPT-4 (Fallback) als Provider implementiert
- [ ] Provider Router selektiert automatisch anhand von `model_preference` und Verfügbarkeit
- [ ] Fallback-Kaskade: Claude → GPT-4 → Cached Response → strukturierte Fehlermeldung
- [ ] Retry-Logik mit Exponential Backoff (3 Retries) bei transienten Fehlern (429, 500, Timeout)
- [ ] Cost & Latency Logging pro Aufruf (Modell, Token-Count Input/Output, Dauer, Kosten)

**Technische Hinweise:** Architektur aus D1 Abschnitt 3.4. `anthropic`-Library für Claude, `openai`-Library für GPT-4. Keine Secrets im Code – API-Keys über Umgebungsvariablen.

---

#### TASK-067: Prompt-Management mit versionierten Templates implementieren

| Feld             | Wert                                                                                   |
| ---------------- | -------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                     |
| **Bereich**      | LLM                                                                                    |
| **Aufwand**      | M                                                                                      |
| **Status**       | 🔴 Offen                                                                               |
| **Quelle**       | D1 Abschnitt 3.4 (Prompt Registry, PromptTemplate Dataclass), AGENTS.md (Prompt-Files) |
| **Abhängig von** | TASK-066                                                                               |
| **Blockiert**    | TASK-073, TASK-076                                                                     |

**Beschreibung:** Prompt Registry (`pwbs/prompts/`) implementieren. Prompts werden als versionierte Template-Dateien gespeichert und über eine Registry geladen. `PromptTemplate`-Dataclass mit: `id`, `template` (Jinja2), `model_preference`, `max_output_tokens`, `temperature`, `system_prompt`, `required_context`, `version`. Template-Variablen werden beim Assembly gegen den bereitgestellten Kontext aufgelöst.

**Acceptance Criteria:**

- [ ] `PromptTemplate`-Dataclass mit allen Feldern aus D1 implementiert
- [ ] Prompt Registry lädt Templates aus `pwbs/prompts/`-Verzeichnis
- [ ] Jinja2-basiertes Template-Rendering mit Kontextvariablen
- [ ] Versionierung: Mehrere Versionen eines Prompts können koexistieren, die neueste wird per Default geladen
- [ ] `required_context`-Prüfung: Fehlende Kontextvariablen werfen einen aussagekräftigen Fehler

**Technische Hinweise:** Prompts als `.md` oder `.j2`-Dateien in `pwbs/prompts/`. Benennung: `{use_case}.v{version}.j2` (z.B. `briefing_morning.v1.j2`). Jinja2-Template-Engine mit Auto-Escaping.

---

#### TASK-068: Structured Output mit JSON-Schema-Validierung implementieren

| Feld             | Wert                                                                                            |
| ---------------- | ----------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                              |
| **Bereich**      | LLM                                                                                             |
| **Aufwand**      | M                                                                                               |
| **Status**       | 🔴 Offen                                                                                        |
| **Quelle**       | D1 Abschnitt 3.4 (Response Validation), D1 Abschnitt 3.2 (ENTITY_EXTRACTION_PROMPT JSON-Schema) |
| **Abhängig von** | TASK-066                                                                                        |
| **Blockiert**    | TASK-062                                                                                        |

**Beschreibung:** Structured Output Layer im LLM Gateway implementieren, der LLM-Antworten gegen ein vorgegebenes JSON-Schema validiert. Nutzt Claude's native JSON-Mode / Tool-Use für strukturierte Ausgaben. Fallback: Regex-basiertes JSON-Extraktion aus Freitext-Antworten. Validierung via Pydantic-Modelle. Ungültige Antworten werden geloggt und ein Retry mit angepasstem Prompt ausgelöst.

**Acceptance Criteria:**

- [ ] LLM-Antworten werden gegen ein Pydantic-Schema validiert
- [ ] Claude's JSON-Mode / Tool-Use wird für strukturierte Ausgaben genutzt
- [ ] Fallback: Regex-basierte JSON-Extraktion bei Freitext-Antworten
- [ ] Ungültige Antworten lösen einen Retry aus (max. 1 Retry mit expliziterem Format-Prompt)
- [ ] Validierungsfehler werden mit dem Rohdaten-Response geloggt

**Technische Hinweise:** Claude API unterstützt `tool_use` für strukturierte Outputs. JSON-Schema-Definition als Pydantic-Modelle, die mit `model_json_schema()` exportiert werden.

---

#### TASK-069: Halluzinations-Mitigation mit Quellenreferenz-Pflicht implementieren

| Feld             | Wert                                                                                                  |
| ---------------- | ----------------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                                    |
| **Bereich**      | LLM                                                                                                   |
| **Aufwand**      | M                                                                                                     |
| **Status**       | 🔴 Offen                                                                                              |
| **Quelle**       | D1 Abschnitt 3.4 (Halluzinations-Mitigation, Grounded Generation), D3 Erklärbarkeit, D4 NF-022/NF-023 |
| **Abhängig von** | TASK-066, TASK-067                                                                                    |
| **Blockiert**    | TASK-076, TASK-077                                                                                    |

**Beschreibung:** Halluzinations-Mitigationsschicht im LLM Gateway implementieren. Jeder LLM-Call enthält die Instruktion „Antworte ausschließlich basierend auf den bereitgestellten Quellen." Jede generierte Aussage wird mit `[Quelle: {document_title}, {date}]` annotiert. Confidence Scoring: Aussagen ohne direkte Quellenableitung erhalten einen `low`-Confidence-Indikator. Fakten/Interpretation-Trennung in der Prompt-Struktur.

**Acceptance Criteria:**

- [ ] System-Prompt enthält explizite Grounding-Instruktion für alle LLM-Calls
- [ ] Generierte Aussagen enthalten `[Quelle: Titel, Datum]`-Annotationen
- [ ] Confidence Scoring: `high` (direkte Quelle), `medium` (abgeleitet), `low` (keine direkte Quelle)
- [ ] Aussagen mit `low` Confidence werden im Output gekennzeichnet
- [ ] Prompt-Struktur erzwingt Abschnitte: Fakten, Zusammenhänge, Empfehlungen

**Technische Hinweise:** Grounding-Pattern aus D1 Abschnitt 3.4. Quellenreferenzen werden im Post-Processing gegen die tatsächlich bereitgestellten Chunks validiert. Invalide Referenzen werden entfernt.

---

#### TASK-070: Rate Limiting und Kostenkontrolle pro Nutzer im LLM Gateway implementieren

| Feld             | Wert                                                                                               |
| ---------------- | -------------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                                 |
| **Bereich**      | LLM                                                                                                |
| **Aufwand**      | M                                                                                                  |
| **Status**       | 🔴 Offen                                                                                           |
| **Quelle**       | D1 Abschnitt 3.2 (100 LLM-Extraction-Calls/Nutzer/Tag), D1 Abschnitt 3.4 (Token-Budget-Management) |
| **Abhängig von** | TASK-066                                                                                           |
| **Blockiert**    | –                                                                                                  |

**Beschreibung:** Per-User Rate Limiting und Kostenkontrolle im LLM Gateway implementieren. Token-Budget-Limits pro Use-Case (aus D1 `TOKEN_BUDGETS`): `briefing.morning` (context: 8000, output: 2000), `search.answer` (context: 6000, output: 1500), `entity.extraction` (context: 2000, output: 1000). Täglicher Kostencap pro Nutzer. LLM-Extraction-Calls: max. 100 pro Nutzer/Tag. Counter in PostgreSQL oder Redis.

**Acceptance Criteria:**

- [ ] Token-Budget-Limits pro Use-Case werden vor jedem LLM-Call geprüft
- [ ] Tägliches Limit: Max. 100 LLM-Extraction-Calls pro Nutzer/Tag
- [ ] Bei Überschreitung wird ein `PWBSError` mit klarer Fehlermeldung geworfen (kein stiller Fehler)
- [ ] Verbrauchszähler werden täglich zurückgesetzt
- [ ] Cost Logging: Jeder LLM-Call wird mit geschätzten Kosten (Token-basiert) geloggt

**Technische Hinweise:** Token-Budgets aus D1 Abschnitt 3.4 `TOKEN_BUDGETS`-Dict. Counter-Implementierung im MVP über PostgreSQL; ab Phase 3 Redis.

---

#### TASK-071: LLM Gateway Retry-Logik mit Exponential Backoff implementieren

| Feld             | Wert                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------ |
| **Priorität**    | P1                                                                                         |
| **Bereich**      | LLM                                                                                        |
| **Aufwand**      | S                                                                                          |
| **Status**       | 🔴 Offen                                                                                   |
| **Quelle**       | D1 Abschnitt 3.4 (Fallback-Kaskade, Retry), AGENTS.md SchedulerAgent (Exponential Backoff) |
| **Abhängig von** | TASK-066                                                                                   |
| **Blockiert**    | –                                                                                          |

**Beschreibung:** Retry-Logik für den LLM Gateway implementieren. Bei transienten Fehlern (HTTP 429 Rate Limit, 500 Server Error, Timeout) wird mit Exponential Backoff wiederholt (1 min → 5 min → 25 min, max. 3 Retries). Bei permanenten Fehlern (401, 403) wird sofort auf den Fallback-Provider gewechselt. Idempotenz: Gleicher Request darf keine doppelten Nebenwirkungen erzeugen.

**Acceptance Criteria:**

- [ ] Exponential Backoff: 1 min → 5 min → 25 min bei transienten Fehlern
- [ ] Max. 3 Retries pro Provider, danach Wechsel zum Fallback-Provider
- [ ] Permanente Fehler (401, 403) lösen sofortigen Provider-Wechsel aus
- [ ] Alle Retries und Provider-Wechsel werden geloggt
- [ ] Timeout pro LLM-Call ist konfigurierbar (Default: 30 Sekunden)

**Technische Hinweise:** Retry-Intervalle aus AGENTS.md SchedulerAgent. `tenacity`-Library oder eigene Retry-Implementierung. Jitter hinzufügen um Thundering Herd zu vermeiden.

---

## Semantische Suche – Service-Kern

#### TASK-072: Weaviate Nearest-Neighbor-Suche (Semantic Mode) implementieren

| Feld             | Wert                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                      |
| **Bereich**      | Backend                                                                                 |
| **Aufwand**      | M                                                                                       |
| **Status**       | 🔴 Offen                                                                                |
| **Quelle**       | D1 Abschnitt 3.3.2 (Suchstrategie: Hybrid, alpha=0.75), D4 F-011, AGENTS.md SearchAgent |
| **Abhängig von** | TASK-059, TASK-058                                                                      |
| **Blockiert**    | TASK-074                                                                                |

**Beschreibung:** Semantischen Such-Service (`pwbs/search/service.py`) implementieren mit Weaviate Nearest-Neighbor-Suche. Query-Embedding wird über den gleichen Embedding-Service (TASK-058) generiert. Suche in der `DocumentChunk`-Collection des jeweiligen Nutzer-Tenants. Konfigurierbare Parameter: `top_k` (Default: 10, Max: 50), `alpha` (Default: 0.75 für semantisch-gewichtete Hybrid-Suche).

**Acceptance Criteria:**

- [ ] Query wird in Embedding konvertiert und gegen Weaviate Nearest-Neighbor gesucht
- [ ] Suche ist isoliert auf den Nutzer-Tenant (`userId`-Filter)
- [ ] `top_k` ist konfigurierbar (Default: 10, Max: 50)
- [ ] Ergebnisse enthalten: `chunkId`, `content`, `title`, `sourceType`, `createdAt`, `score`
- [ ] Leerer Query oder Query ohne Ergebnisse gibt leere Liste zurück (kein Fehler)

**Technische Hinweise:** Weaviate `nearVector`-Query mit dem generierten Query-Embedding. `alpha=0.75` für Standard-Suche, `alpha=0.3` für exakte Terme (Projektnamen, Personennamen) gemäß D1 Abschnitt 3.3.2.

---

#### TASK-073: PostgreSQL tsvector Keyword-Suche implementieren

| Feld             | Wert                                                                                                |
| ---------------- | --------------------------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                                  |
| **Bereich**      | Backend                                                                                             |
| **Aufwand**      | M                                                                                                   |
| **Status**       | 🔴 Offen                                                                                            |
| **Quelle**       | D1 Abschnitt 3.3.2 (BM25 Keyword-Suche), D4 F-011 (Hybrid-Suche 25% Keyword), AGENTS.md SearchAgent |
| **Abhängig von** | DB-Schema (Agent 1)                                                                                 |
| **Blockiert**    | TASK-074                                                                                            |

**Beschreibung:** Keyword-Suche über PostgreSQL `tsvector`/`tsquery` implementieren. Volltextindex auf `chunks.content_preview` und `documents.title`. Ranking via `ts_rank_cd`. Unterstützt deutsche und englische Stemming-Konfiguration. Owner-Filter: Jede Query enthält `WHERE user_id = $user_id`.

**Acceptance Criteria:**

- [ ] `tsvector`-Index auf relevanten Spalten erstellt (Content, Titel)
- [ ] `tsquery`-Suche mit Stemming (Deutsch + Englisch konfigurierbar)
- [ ] Ranking via `ts_rank_cd` für Ergebnissortierung
- [ ] `user_id`-Filter als Pflichtparameter bei jeder Query
- [ ] Ergebnisse enthalten: `chunk_id`, `document_id`, `content_preview`, `score`

**Technische Hinweise:** PostgreSQL Full-Text-Search mit `to_tsvector('german', content)` und `to_tsquery('german', query)`. GIN-Index für Performance. Bei mehrsprachigen Dokumenten: Sprachangabe aus `language`-Feld nutzen.

---

#### TASK-074: Hybrid-Suche mit RRF-Fusion implementieren

| Feld             | Wert                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                                               |
| **Bereich**      | Backend                                                                                          |
| **Aufwand**      | M                                                                                                |
| **Status**       | 🔴 Offen                                                                                         |
| **Quelle**       | D1 Abschnitt 3.3.2 (Hybrid-Suche), D4 F-011 (75% semantisch, 25% Keyword), AGENTS.md SearchAgent |
| **Abhängig von** | TASK-072, TASK-073                                                                               |
| **Blockiert**    | TASK-075                                                                                         |

**Beschreibung:** Reciprocal Rank Fusion (RRF) implementieren, die Ergebnisse aus Weaviate (semantisch) und PostgreSQL (Keyword) kombiniert. RRF-Formel: `score = Σ 1/(k + rank_i)` mit k=60. Gewichtung: 75% semantisch, 25% Keyword (konfigurierbar). Deduplizierung: Chunks, die in beiden Ergebnislisten vorkommen, werden zusammengeführt.

**Acceptance Criteria:**

- [ ] RRF-Fusion kombiniert Ergebnisse aus Weaviate und PostgreSQL
- [ ] RRF-Formel mit k=60 korrekt implementiert
- [ ] Gewichtung konfigurierbar (Default: 0.75 semantisch, 0.25 Keyword)
- [ ] Deduplizierung: Gleiche Chunks werden zusammengeführt, nicht doppelt angezeigt
- [ ] `owner_id` als Pflicht-Filter bei allen Teilabfragen

**Technische Hinweise:** RRF ist ein rank-basiertes Fusionsverfahren, das keine Score-Normalisierung erfordert. Standard-Konstante k=60 aus der Originalpublikation. Ergebnisliste wird nach fusioniertem Score sortiert.

---

#### TASK-075: Suchergebnisse mit SourceRef anreichern

| Feld             | Wert                                                                             |
| ---------------- | -------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                               |
| **Bereich**      | Backend                                                                          |
| **Aufwand**      | S                                                                                |
| **Status**       | 🔴 Offen                                                                         |
| **Quelle**       | D4 F-012 (Ergebnisse mit Quellenangabe), D3 Erklärbarkeit, AGENTS.md SearchAgent |
| **Abhängig von** | TASK-074                                                                         |
| **Blockiert**    | –                                                                                |

**Beschreibung:** Suchergebnisse mit `SourceRef`-Objekten anreichern, die alle Informationen für die Quellenangabe im Frontend enthalten. Jedes Ergebnis enthält: Dokumenttitel, Quelltyp (Icon-Mapping), Erstellungs-/Änderungsdatum, relevanter Textausschnitt (Chunk-Content), Relevanz-Score, Original-URL (für „Original öffnen"-Link).

**Acceptance Criteria:**

- [ ] Jedes Suchergebnis enthält ein `SourceRef`-Objekt mit Titel, Quelltyp, Datum, Content-Ausschnitt, Score
- [ ] Original-URL wird aus den Metadaten rekonstruiert (Notion-URL, Google Calendar-Link etc.)
- [ ] Quelltyp wird für Frontend-Icon-Mapping bereitgestellt
- [ ] Ergebnisse sind nach fusioniertem RRF-Score sortiert

**Technische Hinweise:** `SourceRef` als Pydantic-Modell. Original-URL-Rekonstruktion: Notion → `https://notion.so/{page_id}`, Google Calendar → `https://calendar.google.com/event/{event_id}`, Zoom → Recording-URL aus Metadaten.

---

## Briefing Engine

#### TASK-076: Morgenbriefing Kontextassemblierung implementieren

| Feld             | Wert                                                                                                        |
| ---------------- | ----------------------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                                          |
| **Bereich**      | Backend                                                                                                     |
| **Aufwand**      | L                                                                                                           |
| **Status**       | 🔴 Offen                                                                                                    |
| **Quelle**       | D1 Abschnitt 3.5 (Kontextassemblierung Morning Briefing, 8 Schritte), D2 Phase 2 Kontextbriefings, D4 F-017 |
| **Abhängig von** | TASK-046, TASK-072, TASK-064, TASK-066, TASK-067                                                            |
| **Blockiert**    | TASK-078                                                                                                    |

**Beschreibung:** Kontextassemblierung für das Morgenbriefing implementieren, die den 8-Schritte-Prozess aus D1 Abschnitt 3.5 umsetzt: (1) Kalender-Events heute abrufen, (2) Für jeden Termin: Teilnehmer → Neo4j-Abfrage (letzte Interaktionen, gemeinsame Projekte, offene Punkte), (3) Semantische Suche: relevante Dokumente der letzten 7 Tage, gefiltert nach Topics aus heutigen Terminen, (4) Offene Entscheidungen aus Neo4j (Status pending, nach Alter sortiert), (5) Kontext in Token-Budget prüfen und ggf. priorisieren/kürzen.

**Acceptance Criteria:**

- [ ] Kalender-Events des Tages werden abgerufen (aus Google Calendar Connector-Daten)
- [ ] Pro Termin: Neo4j-Abfrage für Teilnehmer-History, gemeinsame Projekte, offene Punkte
- [ ] Semantische Suche: Relevante Dokumente der letzten 7 Tage, gefiltert nach Termin-Topics
- [ ] Offene Entscheidungen (Status `pending`) werden aus Neo4j abgerufen
- [ ] Zusammengestellter Kontext wird auf Token-Budget (8000 Tokens) geprüft und ggf. priorisiert

**Technische Hinweise:** Cypher-Queries für Meeting-Vorbereitung aus D1 Abschnitt 3.3.3 verwenden. Token-Budget: 8000 Context-Tokens für `briefing.morning` (D1 Abschnitt 3.4). Kontext-Priorisierung: Heutige Termine > Offene Entscheidungen > Hintergrund-Dokumente.

---

#### TASK-077: Meeting-Vorbereitung Kontextassemblierung implementieren

| Feld             | Wert                                             |
| ---------------- | ------------------------------------------------ |
| **Priorität**    | P0                                               |
| **Bereich**      | Backend                                          |
| **Aufwand**      | L                                                |
| **Status**       | 🔴 Offen                                         |
| **Quelle**       | D1 Abschnitt 3.5, D4 US-3.2, D4 F-018            |
| **Abhängig von** | TASK-046, TASK-072, TASK-064, TASK-066, TASK-067 |
| **Blockiert**    | TASK-078                                         |

**Beschreibung:** Kontextassemblierung für Meeting-Vorbereitungsbriefings implementieren. Ausgelöst 30 Minuten vor Kalendereintrag mit ≥ 2 Teilnehmern (oder on-demand). Assembliert: Meeting-Thema, Teilnehmer mit History (letzte gemeinsame Meetings, gemeinsame Projekte via Neo4j), offene Punkte aus vorherigen Interaktionen, relevante Dokumente (via semantische Suche). Für unbekannte Teilnehmer: „Neu im System – keine vorherigen Interaktionen gespeichert" statt Halluzination.

**Acceptance Criteria:**

- [ ] Trigger: 30 Minuten vor Meeting mit ≥ 2 Teilnehmern oder on-demand
- [ ] Teilnehmer-History wird aus Neo4j abgerufen (letzte gemeinsame Meetings, Projekte)
- [ ] Offene Punkte aus vorherigen Interaktionen werden extrahiert
- [ ] Relevante Dokumente werden per semantischer Suche abgerufen
- [ ] Unbekannte Teilnehmer werden als „Neu im System" gekennzeichnet (keine Halluzination)

**Technische Hinweise:** Max. 400 Wörter Output (D4 F-018). Cypher-Query für Teilnehmer-History aus D1 Abschnitt 3.3.3. Token-Budget: Kontext auf max. 6000 Tokens begrenzen.

---

#### TASK-078: Briefing LLM-Call mit Prompt-Template und strukturiertem Output implementieren

| Feld             | Wert                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                                                           |
| **Bereich**      | LLM                                                                                                          |
| **Aufwand**      | M                                                                                                            |
| **Status**       | 🔴 Offen                                                                                                     |
| **Quelle**       | D1 Abschnitt 3.4 (Token-Budgets), D1 Abschnitt 3.5 (Briefing Engine, Output-Format), AGENTS.md BriefingAgent |
| **Abhängig von** | TASK-076, TASK-077, TASK-067, TASK-069                                                                       |
| **Blockiert**    | TASK-079                                                                                                     |

**Beschreibung:** LLM-Call für Briefing-Generierung via LLM Gateway implementieren. Assemblierter Kontext wird in das Prompt-Template eingesetzt (Morning oder Meeting Prep). LLM generiert strukturiertes Briefing im Markdown-Format gemäß D1 Output-Format. Temperatur: 0.3 für sachliche Inhalte. Quellenreferenzen werden im Output als `[Quelle: Titel, Datum]` annotiert.

**Acceptance Criteria:**

- [ ] Kontext wird in Jinja2 Prompt-Template eingesetzt und an LLM Gateway übergeben
- [ ] Temperatur: 0.3 (sachliche Inhalte)
- [ ] Output im Markdown-Format gemäß D1 Briefing-Outputformat
- [ ] Morgenbriefing: max. 800 Wörter, Meeting-Briefing: max. 400 Wörter
- [ ] Jede Aussage enthält `[Quelle: Titel, Datum]`-Annotation

**Technische Hinweise:** Prompt-Templates: `briefing_morning.v1.j2` und `briefing_meeting_prep.v1.j2`. Token-Budgets aus D1: Morning (context: 8000, output: 2000), Meeting Prep analog. Modell: `claude-sonnet-4-20250514`.

---

#### TASK-079: Quellenreferenz-Validierung in Briefings implementieren

| Feld             | Wert                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                      |
| **Bereich**      | Backend                                                                                 |
| **Aufwand**      | M                                                                                       |
| **Status**       | 🔴 Offen                                                                                |
| **Quelle**       | D1 Abschnitt 3.5 (Schritt 7: Quellenreferenzen validieren), D4 NF-022, D3 Erklärbarkeit |
| **Abhängig von** | TASK-078                                                                                |
| **Blockiert**    | TASK-080                                                                                |

**Beschreibung:** Post-Processing-Schritt nach der Briefing-Generierung: Quellenreferenzen im generierten Text werden gegen die tatsächlich bereitgestellten Chunks in der Datenbank validiert. Invalide Referenzen (die auf nicht existierende Dokumente verweisen oder vom LLM halluziniert wurden) werden entfernt oder mit einem Warnhinweis versehen. Quellenreferenzen werden in eine strukturierte `source_chunks`-Liste konvertiert.

**Acceptance Criteria:**

- [ ] Jede `[Quelle: Titel, Datum]`-Annotation wird gegen die tatsächlich bereitgestellten Source-Chunks validiert
- [ ] Invalide Referenzen werden entfernt und der Chunk als `low confidence` markiert
- [ ] Valide Referenzen werden als UUID-Liste in `source_chunks` des Briefing-Records gespeichert
- [ ] 100% der verbleibenden Aussagen haben eine validierte Quellenreferenz (D4 NF-022)

**Technische Hinweise:** Matching: Dokumenttitel + Datum gegen `documents`-Tabelle. Fuzzy-Matching bei leicht abweichenden Titeln (LLM kann Titel kürzen/paraphrasieren). Ergebnis wird in `briefings.source_chunks` und `briefings.source_entities` persistiert.

---

#### TASK-080: Briefing-Persistierung in PostgreSQL implementieren

| Feld             | Wert                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                    |
| **Bereich**      | Backend                                                                               |
| **Aufwand**      | S                                                                                     |
| **Status**       | 🔴 Offen                                                                              |
| **Quelle**       | D1 Abschnitt 3.3.1 (briefings-Tabelle), D4 F-022 (Briefing-Caching und Regenerierung) |
| **Abhängig von** | TASK-079, DB-Schema (Agent 1)                                                         |
| **Blockiert**    | –                                                                                     |

**Beschreibung:** Generierte Briefings in der `briefings`-Tabelle in PostgreSQL persistieren. Felder: `user_id`, `briefing_type` (MORNING, MEETING_PREP), `title`, `content` (Markdown), `source_chunks` (UUID-Array), `source_entities` (UUID-Array), `trigger_context` (JSONB), `generated_at`, `expires_at`. Ablaufdaten: Morgenbriefings nach 24h, Meeting-Briefings nach 48h. Nutzer kann Regenerierung auslösen.

**Acceptance Criteria:**

- [ ] Briefing wird vollständig in der `briefings`-Tabelle persistiert (alle Felder)
- [ ] `expires_at` wird gesetzt: Morgenbriefing +24h, Meeting-Briefing +48h
- [ ] `trigger_context` enthält den Auslöser (Kalender-Event-ID, Zeitplan)
- [ ] `source_chunks` und `source_entities` referenzieren die verwendeten Quellen
- [ ] Briefing-Query mit `user_id`-Filter (Mandanten-Isolation)

**Technische Hinweise:** Schema aus D1 Abschnitt 3.3.1 `briefings`-Tabelle. Index `idx_briefings_user_type` für effiziente Abfragen nach Typ und Datum.

---

## Statistik Teil 2

| Bereich                             | Anzahl |
| ----------------------------------- | ------ |
| Konnektoren (Basis + 4 Konnektoren) | 15     |
| Processing Pipeline                 | 10     |
| LLM Gateway                         | 6      |
| Suche-Service                       | 4      |
| Briefing Engine                     | 5      |
| **Gesamt**                          | **40** |

<!-- AGENT_2_LAST: TASK-080 -->

---


---

## Authentifizierung & User Management

#### TASK-081: JWT-Token-Generierung und -Validierung implementieren

| Feld             | Wert                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| **Priorität**    | P0                                                                   |
| **Bereich**      | Auth                                                                 |
| **Aufwand**      | M                                                                    |
| **Status**       | 🔴 Offen                                                             |
| **Quelle**       | D4 F-002, D1 API Layer (Authentifizierung), D4 NF-014                |
| **Abhängig von** | DB-Schema (Agent 1)                                                  |
| **Blockiert**    | TASK-086, TASK-087, TASK-088, TASK-089, TASK-090, TASK-091, TASK-092 |

**Beschreibung:** JWT-Service implementieren, der Access-Tokens (RS256, 15 Minuten Gültigkeit) und Refresh-Tokens (opaque, 30 Tage, in DB gespeichert) generiert und validiert. RSA-Schlüsselpaar-Management über Umgebungsvariablen. Refresh-Tokens sind revokierbar und werden bei jedem Refresh rotiert.

**Acceptance Criteria:**

- [ ] Access-Token wird mit RS256 signiert und enthält `user_id`, `exp`, `iat` Claims
- [ ] Access-Token-Laufzeit beträgt exakt 15 Minuten (konfigurierbar via Umgebungsvariable)
- [ ] Refresh-Token ist opaque (kein JWT), kryptografisch sicher generiert (`secrets.token_urlsafe()`), und wird in der Datenbank persistiert
- [ ] Token-Validierung prüft Signatur, Ablaufzeitpunkt und Revokationsstatus
- [ ] Abgelaufene oder revokierte Tokens werden mit HTTP 401 abgelehnt

**Technische Hinweise:** RS256 statt HS256 gemäß D1 Security Instructions. Private Key über `PWBS_JWT_PRIVATE_KEY` Umgebungsvariable laden, niemals im Code.

---

#### TASK-082: User-Registrierung mit Argon2-Hashing implementieren

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P0                                                        |
| **Bereich**      | Auth                                                      |
| **Aufwand**      | M                                                         |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D4 F-001, D4 US-1.1, D1 Abschnitt 3.3 (PostgreSQL-Schema) |
| **Abhängig von** | TASK-081, DB-Schema (Agent 1)                             |
| **Blockiert**    | TASK-086                                                  |

**Beschreibung:** Registrierungsservice implementieren, der E-Mail, Passwort (≥ 12 Zeichen, mind. 1 Großbuchstabe, 1 Zahl) und Anzeigename entgegennimmt. Passwort wird mit Argon2 gehasht. Bei Erstellung wird ein nutzer-spezifischer Data Encryption Key (DEK) generiert und mit dem Master Key (KEK) verschlüsselt gespeichert. Generische Fehlermeldung bei bereits registrierter E-Mail.

**Acceptance Criteria:**

- [ ] Passwort wird mit Argon2 gehasht und niemals im Klartext gespeichert
- [ ] Passwort-Validierung erzwingt ≥ 12 Zeichen, mind. 1 Großbuchstabe, 1 Zahl
- [ ] User-DEK wird bei Registrierung generiert und verschlüsselt (Fernet + KEK) in `encryption_key_enc` gespeichert
- [ ] Bei bereits registrierter E-Mail wird generische Fehlermeldung „Registrierung fehlgeschlagen" zurückgegeben (kein E-Mail-Leak)
- [ ] Nach erfolgreicher Registrierung wird ein JWT-Token-Paar (Access + Refresh) ausgegeben

**Technische Hinweise:** DEK-Generierung gemäß D1 Envelope-Encryption-Architektur. Pydantic-Validator für Passwort-Komplexität.

---

#### TASK-083: OAuth2-Login-Flow mit Google als Identity Provider implementieren

| Feld             | Wert                                                            |
| ---------------- | --------------------------------------------------------------- |
| **Priorität**    | P1                                                              |
| **Bereich**      | Auth                                                            |
| **Aufwand**      | L                                                               |
| **Status**       | 🔴 Offen                                                        |
| **Quelle**       | D1 API Layer (Authentifizierung), D1 Abschnitt 3.1 (OAuth-Flow) |
| **Abhängig von** | TASK-081, TASK-082, DB-Schema (Agent 1)                         |
| **Blockiert**    | TASK-086                                                        |

**Beschreibung:** OAuth2-Authorization-Code-Flow mit Google als Identity Provider für Social Login implementieren. Nutzer können sich alternativ zur E-Mail/Passwort-Registrierung über ihr Google-Konto anmelden. Bei erstmaligem Google-Login wird automatisch ein PWBS-Account erstellt. Bei erneutem Login wird der bestehende Account verknüpft.

**Acceptance Criteria:**

- [ ] OAuth2-Auth-URL wird mit korrektem `state`-Parameter (CSRF-Schutz) und OpenID-Connect-Scopes generiert
- [ ] Callback-Endpunkt tauscht Authorization-Code gegen ID-Token und verifiziert die Google-E-Mail
- [ ] Bei erstmaligem Login wird automatisch ein PWBS-Nutzer mit DEK erstellt
- [ ] Bei bestehendem Nutzer (gleiche E-Mail) wird der Account verknüpft und ein JWT-Paar ausgegeben
- [ ] `state`-Parameter wird gegen CSRF-Angriffe validiert

**Technische Hinweise:** Google OAuth2-Credentials über Umgebungsvariablen (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`). Callback-URL in Google Cloud Console konfigurieren.

---

#### TASK-084: Token-Refresh-Endpunkt mit Token-Rotation implementieren

| Feld             | Wert                                              |
| ---------------- | ------------------------------------------------- |
| **Priorität**    | P0                                                |
| **Bereich**      | Auth                                              |
| **Aufwand**      | S                                                 |
| **Status**       | 🔴 Offen                                          |
| **Quelle**       | D4 F-003, D4 Abschnitt 8 (Auth API), D1 API Layer |
| **Abhängig von** | TASK-081, DB-Schema (Agent 1)                     |
| **Blockiert**    | TASK-086                                          |

**Beschreibung:** Token-Refresh-Endpunkt implementieren, der bei Vorlage eines gültigen Refresh-Tokens ein neues Access-Token und ein neues Refresh-Token ausstellt. Das alte Refresh-Token wird dabei invalidiert (Token Rotation). Bei Verwendung eines bereits invalidierten Refresh-Tokens werden alle Tokens des Nutzers revokiert (Replay-Detection).

**Acceptance Criteria:**

- [ ] POST /api/v1/auth/refresh akzeptiert `{refresh_token}` und gibt neues Token-Paar zurück
- [ ] Altes Refresh-Token wird nach Verwendung sofort invalidiert
- [ ] Replay-Detection: Wiederverwendung eines invalidierten Refresh-Tokens revokiert alle aktiven Tokens des Nutzers
- [ ] HTTP 401 bei ungültigem oder abgelaufenem Refresh-Token
- [ ] Neues Refresh-Token hat erneut 30 Tage Gültigkeit

**Technische Hinweise:** Refresh-Token-Familie tracken, um Replay-Detection zu ermöglichen. Token-Revokation über DB-Flag oder Löschen des Token-Eintrags.

---

#### TASK-085: Rate-Limiting-Middleware auf allen öffentlichen Endpunkten implementieren

| Feld             | Wert                                                 |
| ---------------- | ---------------------------------------------------- |
| **Priorität**    | P0                                                   |
| **Bereich**      | Backend                                              |
| **Aufwand**      | M                                                    |
| **Status**       | 🔴 Offen                                             |
| **Quelle**       | D4 NF-015, D1 Middleware-Stack (RateLimitMiddleware) |
| **Abhängig von** | DB-Schema (Agent 1)                                  |
| **Blockiert**    | TASK-086, TASK-087, TASK-088, TASK-089               |

**Beschreibung:** Redis-basierte Rate-Limiting-Middleware implementieren. Allgemeines Limit: 100 Requests/Minute pro authentifiziertem Nutzer. Login-Endpunkte: 5 Versuche/Minute pro IP. Manueller Sync: max. 1 pro Konnektor pro 5 Minuten. Briefing-Generierung: Rate Limit gemäß D4 (429 bei Überschreitung).

**Acceptance Criteria:**

- [ ] 100 Requests/Minute pro Nutzer auf allgemeinen Endpunkten; HTTP 429 bei Überschreitung
- [ ] 5 Requests/Minute pro IP auf Login-Endpunkten (POST /auth/login, /auth/register)
- [ ] 1 manueller Sync pro Konnektor pro 5 Minuten (POST /connectors/{type}/sync)
- [ ] Rate-Limit-Header (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) in jeder Response
- [ ] Redis-Ausfall führt zu Fail-Open (Requests werden durchgelassen, nicht blockiert), mit Logging

**Technische Hinweise:** Redis-basiertes Sliding-Window oder Token-Bucket-Muster. Konfigurierbar über Umgebungsvariablen für verschiedene Endpunkt-Gruppen.

---

## API Layer

#### TASK-086: Auth-API-Endpunkte als FastAPI-Router implementieren

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P0                                                        |
| **Bereich**      | Backend                                                   |
| **Aufwand**      | M                                                         |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D4 Abschnitt 8 (Auth API), D1 API Layer (Routenübersicht) |
| **Abhängig von** | TASK-081, TASK-082, TASK-083, TASK-084, TASK-085          |
| **Blockiert**    | TASK-096, TASK-117                                        |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/auth/` mit allen Auth-Endpunkten implementieren: POST /register (→ TASK-082), POST /login (E-Mail/Passwort → JWT-Paar), POST /refresh (→ TASK-084), POST /logout (Refresh-Token invalidieren), GET /me (Nutzerprofil). Request/Response-Modelle als Pydantic v2 Schemas definieren. Fehler-Codes gemäß D4 Abschnitt 8.

**Acceptance Criteria:**

- [ ] POST /register gibt `{user_id, access_token, refresh_token}` zurück; Fehler-Codes 400, 409, 422
- [ ] POST /login gibt `{access_token, refresh_token, expires_in}` zurück; generische Fehlermeldung bei ungültigen Credentials (401)
- [ ] POST /refresh gibt neues Token-Paar zurück; 401 bei ungültigem Token
- [ ] POST /logout invalidiert Refresh-Token; 401 bei fehlendem JWT
- [ ] GET /me gibt `{user_id, email, display_name, created_at}` zurück; 401 bei fehlendem JWT

**Technische Hinweise:** Pydantic v2 Response-Modelle mit `model_config = ConfigDict(...)`. OpenAPI-Tags für Swagger-Dokumentation. Response-Objekte vor Default-Parameter-Dependencies platzieren.

---

#### TASK-087: Connectors-API-Endpunkte implementieren

| Feld             | Wert                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                    |
| **Bereich**      | Backend                                                                               |
| **Aufwand**      | L                                                                                     |
| **Status**       | 🔴 Offen                                                                              |
| **Quelle**       | D4 Abschnitt 8 (Connectors API), D1 Abschnitt 3.1 (Connector-Architektur, OAuth-Flow) |
| **Abhängig von** | TASK-081, TASK-085, TASK-093, DB-Schema (Agent 1)                                     |
| **Blockiert**    | TASK-100                                                                              |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/connectors/` implementieren: GET / (verfügbare Konnektor-Typen), GET /status (Status aller verbundenen Quellen), GET /{type}/auth-url (OAuth2-URL generieren), POST /{type}/callback (OAuth2-Callback), POST /{type}/config (Obsidian-Vault-Pfad), DELETE /{type} (Verbindung trennen + Daten löschen), POST /{type}/sync (manueller Sync). Kaskadierte Löschung bei Disconnect gemäß D4 US-5.1.

**Acceptance Criteria:**

- [ ] GET /connectors/ listet alle verfügbaren Konnektor-Typen mit Name, Beschreibung und Auth-Methode
- [ ] GET /connectors/status gibt pro verbundener Quelle Status, Dokumentenanzahl, letzten Sync-Zeitpunkt und ggf. Fehler zurück
- [ ] POST /{type}/callback tauscht OAuth-Code gegen Token und startet initialen Sync (D1 OAuth-Flow)
- [ ] DELETE /{type} widerruft OAuth-Token und löscht alle Daten der Quelle kaskadierend (PostgreSQL, Weaviate, Neo4j)
- [ ] POST /{type}/sync beachtet Rate-Limit (max. 1/5 Min pro Konnektor); gibt 429 bei Überschreitung

**Technische Hinweise:** OAuth-Tokens verschlüsselt in `credentials_enc` speichern (Fernet + User-DEK). `owner_id`-Filter in jeder Query. UNIQUE-Constraint (user_id, source_type) beachten.

---

#### TASK-088: Search-API-Endpunkt implementieren

| Feld             | Wert                                                   |
| ---------------- | ------------------------------------------------------ |
| **Priorität**    | P1                                                     |
| **Bereich**      | Backend                                                |
| **Aufwand**      | M                                                      |
| **Status**       | 🔴 Offen                                               |
| **Quelle**       | D4 Abschnitt 8 (Search API), D4 F-011–F-016, D4 NF-001 |
| **Abhängig von** | TASK-081, TASK-093, Such-Service (Agent 2)             |
| **Blockiert**    | TASK-099                                               |

**Beschreibung:** FastAPI-Endpunkt POST `/api/v1/search/` implementieren, der den Such-Service (Agent 2) aufruft. Entgegennimmt: Query-String, optionale Filter (source_types, date_from, date_to, entity_ids) und Limit (max. 50). Gibt Ergebnisliste mit Chunk-ID, Dokumenttitel, Quelltyp, Datum, Content, Score und Entitäten zurück. Optional: LLM-generierte Antwort mit Quellenreferenzen und Confidence.

**Acceptance Criteria:**

- [ ] POST /search/ akzeptiert `{query, filters?, limit?}` und gibt Ergebnisse innerhalb < 2 Sekunden (p95) zurück
- [ ] Ergebnisliste enthält pro Eintrag: chunk_id, doc_title, source_type, date, content, score, entities
- [ ] Optionale LLM-Antwort (`answer`) mit klickbaren Quellenreferenzen und Confidence-Indikator
- [ ] `owner_id` wird aus JWT extrahiert und als Filter an den Such-Service übergeben (Mandanten-Isolation)
- [ ] Fehler-Codes: 400 (leere Query), 401 (kein JWT), 422 (ungültige Filter)

**Technische Hinweise:** Der Such-Service (Agent 2) wird direkt als Python-Interface aufgerufen (kein HTTP im MVP, gemäß D1 Modularer Monolith).

---

#### TASK-089: Briefings-API-Endpunkte implementieren

| Feld             | Wert                                                             |
| ---------------- | ---------------------------------------------------------------- |
| **Priorität**    | P1                                                               |
| **Bereich**      | Backend                                                          |
| **Aufwand**      | L                                                                |
| **Status**       | 🔴 Offen                                                         |
| **Quelle**       | D4 Abschnitt 8 (Briefings API), D4 F-017–F-022, D1 Abschnitt 3.5 |
| **Abhängig von** | TASK-081, TASK-093, Briefing Engine (Agent 2)                    |
| **Blockiert**    | TASK-097, TASK-098                                               |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/briefings/` implementieren: GET / (paginierte Liste), GET /latest (letztes Briefing pro Typ), GET /{id} (Einzelnes Briefing mit Quellen), POST /generate (Briefing manuell auslösen, ruft Briefing Engine auf), POST /{id}/feedback (Daumen hoch/runter + optionaler Kommentar), DELETE /{id} (Briefing löschen). Rate-Limit auf /generate.

**Acceptance Criteria:**

- [ ] GET /briefings/ gibt paginierte Liste mit `{briefings, total, has_more}` zurück; filterbar nach Typ (morning, meeting_prep)
- [ ] GET /briefings/{id} gibt vollständiges Briefing mit Quellenliste `{chunk_id, doc_title, source_type, date, relevance}` zurück
- [ ] POST /generate ruft die Briefing Engine (Agent 2) auf und gibt `{briefing_id, status: "generating"}` zurück; 429 bei Rate-Limit
- [ ] POST /{id}/feedback speichert Rating (`positive`/`negative`) und optionalen Kommentar mit Briefing-ID und User-ID
- [ ] Ownership-Check: 403 bei Zugriff auf fremde Briefings

**Technische Hinweise:** Briefing Engine wird im MVP direkt als Python-Modul aufgerufen (`await briefing_engine.generate(...)`). Briefings werden bei Generierung asynchron verarbeitet (FastAPI Background Task).

---

#### TASK-090: Knowledge-API-Endpunkte implementieren

| Feld             | Wert                                                               |
| ---------------- | ------------------------------------------------------------------ |
| **Priorität**    | P2                                                                 |
| **Bereich**      | Backend                                                            |
| **Aufwand**      | M                                                                  |
| **Status**       | 🔴 Offen                                                           |
| **Quelle**       | D4 Abschnitt 8 (Knowledge API), D4 F-023–F-025, D1 Abschnitt 3.3.3 |
| **Abhängig von** | TASK-081, TASK-093, DB-Schema (Agent 1)                            |
| **Blockiert**    | TASK-101                                                           |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/knowledge/` implementieren: GET /entities (paginierte, gefilterte Entitätenliste), GET /entities/{id} (Entität mit Verbindungen), GET /entities/{id}/related (verwandte Entitäten bis Tiefe 2), GET /entities/{id}/documents (Dokumente zu einer Entität), GET /graph (Subgraph für D3.js-Visualisierung).

**Acceptance Criteria:**

- [ ] GET /entities gibt paginierte Liste mit `{entities: [{id, type, name, mention_count, last_seen}], total}` zurück; filterbar nach Typ
- [ ] GET /entities/{id} gibt Entitäts-Detail mit verknüpften Entitäten zurück; 403 bei fremder Entität, 404 bei nicht gefunden
- [ ] GET /graph gibt `{nodes: [{id, type, name, size}], edges: [{source, target, relation, weight}]}` zurück; max. 50 Knoten
- [ ] Alle Queries enthalten `WHERE owner_id = $user_id` (Mandanten-Isolation)
- [ ] Neo4j-Abfragen verwenden parametrisierte Cypher-Queries (keine Injection)

**Technische Hinweise:** Graph-Abfragen gegen Neo4j mit `depth`-Parameter (max. 3). PostgreSQL für Entitätenliste (performanter als Graph-Traversal für Listen).

---

#### TASK-091: Documents-API-Endpunkte implementieren

| Feld             | Wert                                               |
| ---------------- | -------------------------------------------------- |
| **Priorität**    | P2                                                 |
| **Bereich**      | Backend                                            |
| **Aufwand**      | S                                                  |
| **Status**       | 🔴 Offen                                           |
| **Quelle**       | D4 Abschnitt 8 (Documents API), D1 Abschnitt 3.3.1 |
| **Abhängig von** | TASK-081, TASK-093, DB-Schema (Agent 1)            |
| **Blockiert**    | TASK-098                                           |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/documents/` implementieren: GET / (paginierte Dokumentenliste, filterbar nach source_type), GET /{id} (Dokument-Metadaten + Chunks mit Content-Preview und Entitäten), DELETE /{id} (kaskadierte Löschung von Chunks, Weaviate-Vektoren und Graph-Referenzen).

**Acceptance Criteria:**

- [ ] GET /documents/ gibt `{documents: [{id, title, source_type, source_id, chunk_count, created_at, updated_at}], total}` zurück
- [ ] GET /documents/{id} gibt Metadaten und Chunks `{id, index, content_preview, entities}` zurück; 403 bei fremdem Dokument
- [ ] DELETE /documents/{id} löscht Dokument kaskadierend aus PostgreSQL, Weaviate und Neo4j
- [ ] Alle Queries enthalten `owner_id`-Filter
- [ ] Fehler-Codes: 401, 403, 404 gemäß D4 Spezifikation

**Technische Hinweise:** Content-Preview in Chunks: Erste 200 Zeichen aus `content_preview`-Spalte. Kaskadierte Löschung in Weaviate über `weaviate_id`-Referenz.

---

#### TASK-092: User-API-Endpunkte implementieren

| Feld             | Wert                                                                  |
| ---------------- | --------------------------------------------------------------------- |
| **Priorität**    | P1                                                                    |
| **Bereich**      | Backend                                                               |
| **Aufwand**      | L                                                                     |
| **Status**       | 🔴 Offen                                                              |
| **Quelle**       | D4 Abschnitt 8 (User API), D4 F-027–F-030, D4 US-5.2, US-5.3, US-5.4  |
| **Abhängig von** | TASK-081, TASK-093, TASK-104, TASK-105, TASK-106, DB-Schema (Agent 1) |
| **Blockiert**    | TASK-102                                                              |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/user/` implementieren: GET /settings, PATCH /settings (Timezone, Briefing-Autostart, Sprache), POST /export (DSGVO-Export), GET /export/{id} (Export-Status), DELETE /account (Löschung einleiten), POST /account/cancel-deletion, GET /audit-log (letzte 100 Einträge), GET /security (Verschlüsselungsstatus).

**Acceptance Criteria:**

- [ ] PATCH /settings aktualisiert Nutzereinstellungen (timezone, briefing_auto_generate, language); 422 bei ungültigen Werten
- [ ] POST /export startet asynchronen Exportjob und gibt `{export_id, status: "processing"}` zurück; 429 bei laufendem Export
- [ ] DELETE /account erwartet `{password, confirmation: "DELETE"}` und leitet 30-Tage-Karenzfrist ein
- [ ] GET /audit-log gibt letzte 100 Einträge zurück (nur Metadaten, keine Inhalte, kein PII)
- [ ] GET /security gibt Verschlüsselungsstatus pro Speicherschicht, Datenstandort und LLM-Nutzungsinformation zurück

**Technische Hinweise:** Export-Endpunkt delegiert an TASK-104. Account-Löschung delegiert an TASK-105. Audit-Log filtert nach `owner_id`.

---

#### TASK-093: API-Middleware-Stack implementieren

| Feld             | Wert                                                       |
| ---------------- | ---------------------------------------------------------- |
| **Priorität**    | P0                                                         |
| **Bereich**      | Backend                                                    |
| **Aufwand**      | L                                                          |
| **Status**       | 🔴 Offen                                                   |
| **Quelle**       | D1 Middleware-Stack, D1 API Layer, D4 NF-011, NF-013       |
| **Abhängig von** | TASK-081, DB-Schema (Agent 1)                              |
| **Blockiert**    | TASK-087, TASK-088, TASK-089, TASK-090, TASK-091, TASK-092 |

**Beschreibung:** FastAPI-Middleware-Stack in korrekter Reihenfolge implementieren: (1) CORSMiddleware (explizite Allowlist, kein `*` in Produktion), (2) TrustedHostMiddleware, (3) RequestIDMiddleware (UUID pro Request für Tracing), (4) RateLimitMiddleware (→ TASK-085), (5) AuthMiddleware (JWT-Validierung, User-Kontext), (6) AuditMiddleware (schreibende Ops loggen). API-Versionierung `/api/v1/` aufsetzen. Globaler Error-Handler für `PWBSError` und `HTTPException`.

**Acceptance Criteria:**

- [ ] CORS auf explizite Frontend-Domain beschränkt; `credentials: true` aktiviert; kein Wildcard in Produktion
- [ ] Jeder Request erhält eine eindeutige Request-ID im `X-Request-ID` Header (für Tracing)
- [ ] Security-Header gesetzt: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`
- [ ] Globaler Error-Handler gibt strukturierte Fehler `{code, message, detail?}` zurück; keine Stack-Traces in Produktion
- [ ] API-Versionierung über URL-Prefix `/api/v1/`; SwaggerUI und ReDoc in Produktion deaktiviert

**Technische Hinweise:** Middleware-Reihenfolge kritisch: Außen → Innen gemäß D1. Debug-Endpoints über `PWBS_ENV` Umgebungsvariable steuern.

---

## Frontend

#### TASK-094: Next.js App-Router-Grundstruktur und Navigation aufsetzen

| Feld             | Wert                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| **Priorität**    | P0                                                                   |
| **Bereich**      | Frontend                                                             |
| **Aufwand**      | M                                                                    |
| **Status**       | 🔴 Offen                                                             |
| **Quelle**       | D1 Abschnitt 3.7 (Frontend App-Struktur), D2 Phase 2 (Web-Frontend)  |
| **Abhängig von** | –                                                                    |
| **Blockiert**    | TASK-096, TASK-097, TASK-098, TASK-099, TASK-100, TASK-101, TASK-102 |

**Beschreibung:** Next.js-Projekt mit App Router initialisieren. Route-Gruppen anlegen: `(auth)/` für Login/Register (ohne Sidebar), `(dashboard)/` für authentifizierte Seiten (mit Sidebar + Header). Root-Layout mit Provider-Setup (Auth, TanStack Query). Sidebar-Navigation mit Links zu Dashboard, Briefings, Suche, Knowledge Explorer, Konnektoren, Einstellungen. Server/Client-Boundary klar markieren.

**Acceptance Criteria:**

- [ ] Route-Gruppen `(auth)/` und `(dashboard)/` mit separaten Layouts implementiert
- [ ] Sidebar-Navigation mit allen Hauptrouten (Dashboard, Briefings, Suche, Knowledge, Konnektoren, Einstellungen)
- [ ] Root-Layout enthält TanStack Query Provider und Auth-Provider
- [ ] `"use client"` nur wo zwingend nötig; Server Components als Standard
- [ ] Tailwind CSS konfiguriert; TypeScript Strict Mode in `tsconfig.json` aktiviert

**Technische Hinweise:** Struktur gemäß D1 Abschnitt 3.7. Shadcn/ui als Basis-Komponentenbibliothek.

---

#### TASK-095: Typisierte API-Client-Abstraktion erstellen

| Feld             | Wert                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                      |
| **Bereich**      | Frontend                                                                                |
| **Aufwand**      | M                                                                                       |
| **Status**       | 🔴 Offen                                                                                |
| **Quelle**       | D1 Abschnitt 3.7 (lib/api-client.ts), Copilot-Instructions (Code-Konventionen Frontend) |
| **Abhängig von** | TASK-094                                                                                |
| **Blockiert**    | TASK-096, TASK-097, TASK-098, TASK-099, TASK-100, TASK-101, TASK-102                    |

**Beschreibung:** Typisierte Fetch-Abstraktion in `/src/lib/api/` implementieren. Für jeden Endpunkt-Bereich (Auth, Connectors, Search, Briefings, Knowledge, Documents, User) eigene Funktionen mit vollständigen TypeScript-Typen. Automatische Token-Anhängung, 401-Handling mit Refresh-Redirect, Error-Parsing. Niemals direkte `fetch()`-Aufrufe in Komponenten.

**Acceptance Criteria:**

- [ ] API-Client in `/src/lib/api/` mit Funktionen für alle Endpunkte (auth, connectors, search, briefings, knowledge, documents, user)
- [ ] TypeScript-Typen für alle Request/Response-Objekte in `/src/types/api.ts`
- [ ] Automatische JWT-Anhängung im `Authorization`-Header bei authentifizierten Requests
- [ ] Automatischer Token-Refresh bei 401-Response; Redirect zu Login bei Refresh-Fehler
- [ ] Zentrale Error-Handling-Funktion, die Backend-Fehlerstruktur `{code, message}` parst

**Technische Hinweise:** Kein Axios – nativer Fetch mit Wrapper gemäß D1. TanStack Query Hooks in separaten Hook-Dateien (`/src/hooks/`), die den API-Client nutzen.

---

#### TASK-096: Login- und Registrierungsseiten implementieren

| Feld             | Wert                                                  |
| ---------------- | ----------------------------------------------------- |
| **Priorität**    | P0                                                    |
| **Bereich**      | Frontend                                              |
| **Aufwand**      | M                                                     |
| **Status**       | 🔴 Offen                                              |
| **Quelle**       | D4 US-1.1, D4 User Flow 1, D1 Abschnitt 3.7 ((auth)/) |
| **Abhängig von** | TASK-094, TASK-095, TASK-086, TASK-117                |
| **Blockiert**    | TASK-097                                              |

**Beschreibung:** Login-Seite (`/login`) und Registrierungsseite (`/register`) implementieren. Registrierung: E-Mail, Passwort (mit Inline-Validierung der Komplexitätsanforderungen), Anzeigename. Login: E-Mail, Passwort. Optionaler Google-Login-Button. Generische Fehlermeldungen (kein E-Mail-Leak). Nach erfolgreichem Login/Register: Redirect zum Dashboard. Willkommensdialog nach Erstregistrierung gemäß D4 User Flow 1.

**Acceptance Criteria:**

- [ ] Registrierung: Inline-Passwort-Validierung zeigt fehlende Kriterien (≥ 12 Zeichen, Großbuchstabe, Zahl) an
- [ ] Login: Generische Fehlermeldung „E-Mail oder Passwort falsch" bei fehlgeschlagenem Login
- [ ] Google-Login-Button leitet zum OAuth2-Flow weiter (TASK-083)
- [ ] Nach Erstregistrierung: Willkommensdialog mit Konnektor-Optionen gemäß D4 User Flow 1
- [ ] Netzwerk-Fehler: Fehlermeldung „Verbindungsfehler. Bitte prüfe deine Internetverbindung."

**Technische Hinweise:** Client Component (`"use client"`). JWT-Token nach Login im httpOnly-Cookie oder Auth-Context speichern.

---

#### TASK-097: Dashboard mit Briefing-Übersicht implementieren

| Feld             | Wert                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| **Priorität**    | P1                                                                   |
| **Bereich**      | Frontend                                                             |
| **Aufwand**      | L                                                                    |
| **Status**       | 🔴 Offen                                                             |
| **Quelle**       | D4 F-021, D4 User Flow 2, D1 Abschnitt 3.7 (Schlüssel-Interaktionen) |
| **Abhängig von** | TASK-094, TASK-095, TASK-089, Briefing Engine (Agent 2)              |
| **Blockiert**    | –                                                                    |

**Beschreibung:** Dashboard-Seite als Hauptansicht nach Login implementieren. Hauptinhalt: Aktuelles Morgenbriefing (GET /briefings/latest?type=morning). Darunter: „Nächste Termine"-Karten mit Meeting-Briefing-Buttons. Rechts/unten: Konnektor-Status-Widget (GET /connectors/status). „Briefing jetzt generieren"-Button wenn Morgenbriefing noch nicht verfügbar (vor 06:30 Uhr). TanStack Query für Daten-Fetching mit SWR-Pattern.

**Acceptance Criteria:**

- [ ] Dashboard zeigt aktuelles Morgenbriefing als Hauptinhalt; parallel Konnektor-Status-Widget
- [ ] „Nächste Termine"-Karten mit Meeting-Briefing-Buttons (verlinkt auf TASK-098)
- [ ] „Briefing jetzt generieren"-Button wenn kein aktuelles Briefing verfügbar (ruft POST /briefings/generate auf)
- [ ] Edge Case: Keine Termine/kein Briefing → „Keine Termine heute"-Hinweis gemäß D4 User Flow 2
- [ ] Stale-While-Revalidate mit 5 Minuten Stale-Time für Briefing-Daten

**Technische Hinweise:** Parallel-Fetching von Briefing und Konnektor-Status gemäß D1 Dashboard-Load-Sequenz. Server Component für initiales Laden, Client Components für interaktive Elemente.

---

#### TASK-098: Briefing-Detailansicht mit Quellenverweisen implementieren

| Feld             | Wert                                                  |
| ---------------- | ----------------------------------------------------- |
| **Priorität**    | P1                                                    |
| **Bereich**      | Frontend                                              |
| **Aufwand**      | M                                                     |
| **Status**       | 🔴 Offen                                              |
| **Quelle**       | D4 US-3.3, D4 F-019, D1 Abschnitt 3.5 (Output-Format) |
| **Abhängig von** | TASK-094, TASK-095, TASK-089, TASK-091                |
| **Blockiert**    | –                                                     |

**Beschreibung:** Briefing-Detailseite (`/briefings/[id]`) implementieren. Rendert Briefing-Markdown mit eingebetteten Quellenreferenzen als klickbare Links. Klick auf Quellenreferenz navigiert zum Dokument-Detail im PWBS mit hervorgehobenem Chunk. Am Ende: Vollständige Quellenliste mit Typ, Titel, Datum und Relevanz-Score. Feedback-Buttons (Daumen hoch/runter) gemäß D4 US-3.4.

**Acceptance Criteria:**

- [ ] Briefing-Markdown wird korrekt gerendert; Quellenreferenzen `[Quelle: Titel, Datum]` als klickbare Links
- [ ] Klick auf Quellenreferenz navigiert zu `/documents/{id}` mit hervorgehobenem Chunk
- [ ] Quellen-Bereich am Ende des Briefings listet alle verwendeten Quellen mit Typ-Icon, Titel, Datum, Relevanz
- [ ] Feedback-Buttons „Hilfreich" / „Nicht hilfreich" mit optionalem Freitext-Kommentar (POST /briefings/{id}/feedback)
- [ ] „Original öffnen"-Links für Quellen, die zur Ursprungs-App verlinken (Notion, Zoom etc.)

**Technische Hinweise:** Markdown-Rendering mit `react-markdown` oder `next-mdx-remote`. Custom Renderer für Quellenreferenz-Syntax.

---

#### TASK-099: Suchoberfläche mit Filtern implementieren

| Feld             | Wert                                                                   |
| ---------------- | ---------------------------------------------------------------------- |
| **Priorität**    | P1                                                                     |
| **Bereich**      | Frontend                                                               |
| **Aufwand**      | L                                                                      |
| **Status**       | 🔴 Offen                                                               |
| **Quelle**       | D4 US-2.1–US-2.4, D4 F-011–F-016, D1 Abschnitt 3.7 (Semantische Suche) |
| **Abhängig von** | TASK-094, TASK-095, TASK-088                                           |
| **Blockiert**    | –                                                                      |

**Beschreibung:** Suchseite (`/search`) implementieren. Suchfeld mit Debounce (300ms). Ergebnisliste mit Result-Cards: Textausschnitt (Chunk), Quelltyp-Icon, Dokumenttitel, Datum, Relevanz-Score. Filter-Sidebar: Person, Projekt, Thema (Multi-Select), Quelltyp, Zeitraum. Optional: LLM-generierte Zusammenfassung oberhalb der Ergebnisse. „Original öffnen"-Link pro Ergebnis. Empty State bei keinen Ergebnissen.

**Acceptance Criteria:**

- [ ] Suchfeld mit 300ms Debounce; Ergebnisse erscheinen innerhalb 2 Sekunden
- [ ] Result-Cards mit Chunk-Text, Quelltyp-Icon, Dokumenttitel, Datum und Relevanz-Score
- [ ] Filter nach Person/Projekt/Thema (Multi-Select), Quelltyp und Zeitraum; Filter in URL-State (searchParams)
- [ ] Empty State: „Keine Ergebnisse gefunden" mit Vorschlägen zur Umformulierung (D4 US-2.1)
- [ ] „Original öffnen"-Link pro Ergebnis; Fallback-Meldung wenn Quelle nicht mehr verfügbar (D4 US-2.4)

**Technische Hinweise:** Debounced Search Hook (`/src/hooks/use-search.ts`). Filter-State über URL-searchParams für Bookmarkability. LLM-Antwort als optionale Sektion oberhalb der Ergebnisliste.

---

#### TASK-100: Konnektor-Management-Seite implementieren

| Feld             | Wert                                                            |
| ---------------- | --------------------------------------------------------------- |
| **Priorität**    | P1                                                              |
| **Bereich**      | Frontend                                                        |
| **Aufwand**      | L                                                               |
| **Status**       | 🔴 Offen                                                        |
| **Quelle**       | D4 US-1.2–US-1.6, D4 F-008–F-009, D1 Abschnitt 3.1 (OAuth-Flow) |
| **Abhängig von** | TASK-094, TASK-095, TASK-087                                    |
| **Blockiert**    | –                                                               |

**Beschreibung:** Konnektor-Management-Seite (`/connectors`) implementieren. Übersicht aller verfügbaren Konnektoren (Google Calendar, Notion, Obsidian, Zoom) mit Connect-Buttons. Pro verbundenem Konnektor: Status (aktiv/pausiert/Fehler), Dokumentenanzahl, letzter Sync-Zeitpunkt, Sync-Fortschrittsanzeige. OAuth-Connect-Buttons starten OAuth-Flow. Obsidian: Pfad-Eingabe. Disconnect-Button mit Sicherheitsabfrage. Manueller Sync-Button.

**Acceptance Criteria:**

- [ ] Verfügbare Konnektoren werden als Karten angezeigt; verbundene Konnektoren zeigen Status, Doc-Count, letzten Sync
- [ ] OAuth-Connect-Button leitet zum Provider-OAuth-Screen weiter; nach Rückkehr Status „verbunden"
- [ ] Obsidian: Pfad-Eingabefeld mit Validierung; Fehlermeldung bei ungültigem Vault-Pfad (D4 US-1.4)
- [ ] Disconnect-Button mit Sicherheitsabfrage „Alle importierten Daten dieser Quelle werden unwiderruflich gelöscht" (D4 US-5.1)
- [ ] Animierter Sync-Indikator während laufendem Sync; Fortschrittsanzeige mit Anzahl importierter Dokumente

**Technische Hinweise:** OAuth-Redirect-Handling über Callback-Route. Konnektor-Status per Polling (TanStack Query Refetch-Interval) oder WebSocket.

---

#### TASK-101: Knowledge Explorer implementieren

| Feld             | Wert                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| **Priorität**    | P2                                                                   |
| **Bereich**      | Frontend                                                             |
| **Aufwand**      | XL                                                                   |
| **Status**       | 🔴 Offen                                                             |
| **Quelle**       | D4 US-4.1–US-4.3, D4 F-023–F-025, D1 Abschnitt 3.7 (Knowledge Graph) |
| **Abhängig von** | TASK-094, TASK-095, TASK-090                                         |
| **Blockiert**    | –                                                                    |

**Beschreibung:** Knowledge Explorer (`/knowledge`) implementieren. Entitätenliste: Paginiert, filterbar nach Typ (Personen/Projekte/Themen), sortierbar nach Name, Häufigkeit, letzter Erwähnung. Graphvisualisierung: D3.js Force-Directed Graph mit ausgewählter Entität als Zentrum, Tiefe 2, max. 50 Knoten, farbcodiert nach Typ. Entitäts-Detailansicht: Name, Typ, verknüpfte Entitäten, Zeitleiste der Erwähnungen, zugehörige Dokument-Chunks.

**Acceptance Criteria:**

- [ ] Entitätenliste: Filterbar nach Typ (Person, Project, Topic), sortierbar, paginiert (D4 US-4.1)
- [ ] Graphvisualisierung: Force-Directed Graph (D3.js) mit Entity-Zentrum, Tiefe 1–3, max. 50 Knoten, farbcodiert
- [ ] Klick auf Knoten im Graph: Knoten wird neues Zentrum, Graph aktualisiert sich (D4 US-4.2)
- [ ] Entitäts-Detailseite: Zeitleiste der Erwähnungen, verknüpfte Entitäten, Dokument-Chunks mit Quellenangabe (D4 US-4.3)
- [ ] Klick auf Dokument-Chunk navigiert zur Dokument-Detailansicht

**Technische Hinweise:** D3.js Force-Directed Graph als Client Component. Graph-Daten via GET /knowledge/graph. Entitätsliste als Server Component mit Client-Side-Filterung.

---

#### TASK-102: Profil- und Einstellungsseite implementieren

| Feld             | Wert                                             |
| ---------------- | ------------------------------------------------ |
| **Priorität**    | P2                                               |
| **Bereich**      | Frontend                                         |
| **Aufwand**      | M                                                |
| **Status**       | 🔴 Offen                                         |
| **Quelle**       | D4 US-5.1–US-5.4, D4 F-026–F-030, D4 User Flow 4 |
| **Abhängig von** | TASK-094, TASK-095, TASK-092, TASK-107           |
| **Blockiert**    | –                                                |

**Beschreibung:** Einstellungsseite (`/settings`) implementieren mit Tabs: Profil (Anzeigename, Timezone, Benachrichtigungen), Datenquellen (verbundene Quellen einsehen und trennen – verlinkt auf TASK-100), Datenschutz (Datenexport-Button, Account-Löschung), Sicherheit (Verschlüsselungsstatus → TASK-107). Account-Löschung gemäß D4 User Flow 4 mit Vollbild-Dialog, Passwort-Bestätigung und 30-Tage-Karenzzeit-Hinweis.

**Acceptance Criteria:**

- [ ] Tab „Profil": Anzeigename, Timezone, Briefing-Autostart, Sprache editierbar (PATCH /user/settings)
- [ ] Tab „Datenschutz": „Daten exportieren"-Button startet Exportjob; Fortschrittsanzeige; Download-Link nach Fertigstellung
- [ ] Tab „Account": „Account löschen"-Button öffnet Vollbild-Dialog mit Warnung, Checkbox und Passwort-Bestätigung (D4 User Flow 4)
- [ ] Karenzfrist-Banner: „Dein Account wird am [Datum] gelöscht. [Löschung abbrechen]" bei vorgemerkter Löschung (D4 US-5.3)
- [ ] Tab „Sicherheit": Verschlüsselungsstatus-Anzeige (→ TASK-107)

**Technische Hinweise:** Tabs als URL-basierter State (`/settings?tab=privacy`). Datenexport-Status per Polling auf GET /user/export/{id}.

---

#### TASK-103: Konsistente Loading-, Error- und Empty-States implementieren

| Feld             | Wert                                                  |
| ---------------- | ----------------------------------------------------- |
| **Priorität**    | P2                                                    |
| **Bereich**      | Frontend                                              |
| **Aufwand**      | M                                                     |
| **Status**       | 🔴 Offen                                              |
| **Quelle**       | D4 User Flows 1–4 (Fehlerfälle), D4 NF-004, D4 NF-026 |
| **Abhängig von** | TASK-094                                              |
| **Blockiert**    | –                                                     |

**Beschreibung:** Wiederverwendbare UI-Komponenten für Loading-, Error- und Empty-States erstellen, die in allen Views konsistent eingesetzt werden. Loading: Skeleton-Screens für Dashboard, Briefings, Suche; Spinner für Aktionen. Error: Fehlerkarten mit Fehlerbeschreibung und Retry-Button; Netzwerk-Fehler-Banner. Empty: Kontextbezogene Hinweise (z. B. „Verbinde deine erste Datenquelle" auf leerem Dashboard).

**Acceptance Criteria:**

- [ ] Skeleton-Screen-Komponenten für Dashboard, Briefing-Liste, Suchergebnisse und Entitätenliste
- [ ] Error-Boundary-Komponente mit Fehlerbeschreibung und Retry-Button; fängt unerwartete React-Errors
- [ ] Netzwerk-Fehler-Banner: „Verbindungsfehler. Bitte prüfe deine Internetverbindung." bei Timeout
- [ ] Empty-State-Komponenten mit kontextbezogenen CTA-Buttons (z. B. „Erste Quelle verbinden" auf leerem Dashboard)
- [ ] Frontend Time-to-Interactive < 3 Sekunden (p95) gemäß D4 NF-004

**Technische Hinweise:** Shadcn/ui Skeleton-Komponente als Basis. Next.js `loading.tsx` und `error.tsx` pro Route-Segment nutzen.

---

## Datenschutz & DSGVO

#### TASK-104: DSGVO-Datenexport-Endpunkt implementieren

| Feld             | Wert                                               |
| ---------------- | -------------------------------------------------- |
| **Priorität**    | P1                                                 |
| **Bereich**      | Backend                                            |
| **Aufwand**      | L                                                  |
| **Status**       | 🔴 Offen                                           |
| **Quelle**       | D4 F-027, D4 US-5.2, D4 NF-017 (DSGVO Art. 15, 20) |
| **Abhängig von** | TASK-081, DB-Schema (Agent 1)                      |
| **Blockiert**    | TASK-092                                           |

**Beschreibung:** Asynchronen DSGVO-Datenexport implementieren. Bei Anforderung (POST /user/export) wird ein Background-Job gestartet, der alle Nutzerdaten aus PostgreSQL, Weaviate und Neo4j sammelt und als ZIP-Datei (JSON + Markdown) bereitstellt: Dokument-Metadaten, Chunk-Inhalte, extrahierte Entitäten, generierte Briefings und Audit-Log. Download-Link gültig 24 Stunden. E-Mail-Benachrichtigung bei Verarbeitungszeit > 60 Sekunden.

**Acceptance Criteria:**

- [ ] POST /user/export startet asynchronen Exportjob; gibt `{export_id, status: "processing"}` zurück
- [ ] Exportierte ZIP enthält: Dokumente (JSON), Chunks (Markdown), Entitäten (JSON), Briefings (Markdown), Audit-Log (JSON)
- [ ] Download-Link (GET /user/export/{id}) ist 24 Stunden gültig; danach wird die Datei gelöscht
- [ ] E-Mail-Benachrichtigung bei Verarbeitungszeit > 60 Sekunden gemäß D4 US-5.2
- [ ] Rate Limit: 1 Export pro Nutzer gleichzeitig; 429 bei laufendem Export

**Technische Hinweise:** ZIP-Generierung als FastAPI Background Task. Datei temporär auf S3 speichern. Keine PII in exportierten Audit-Log-Metadaten.

---

#### TASK-105: Kaskadierte Account-Löschung implementieren

| Feld             | Wert                                           |
| ---------------- | ---------------------------------------------- |
| **Priorität**    | P1                                             |
| **Bereich**      | Backend                                        |
| **Aufwand**      | XL                                             |
| **Status**       | 🔴 Offen                                       |
| **Quelle**       | D4 F-028, D4 US-5.3, D4 User Flow 4, D4 NF-019 |
| **Abhängig von** | DB-Schema (Agent 1)                            |
| **Blockiert**    | TASK-092                                       |

**Beschreibung:** Vollständigen Account-Lösch-Workflow implementieren. Dreistufig: (1) Löschung vormerken (30-Tage-Karenzfrist), (2) Während Karenzfrist: eingeschränkter Zugriff, Löschung abbrechen möglich, (3) Nach Ablauf: kaskadierte Löschung über alle drei Datenbanken – PostgreSQL (DELETE CASCADE auf user_id), Weaviate (Tenant löschen), Neo4j (alle Knoten mit userId), Redis (Session-Flush), S3 (Export-Dateien). Cleanup-Job als Scheduler-Task.

**Acceptance Criteria:**

- [ ] DELETE /user/account setzt `deletion_scheduled_at` (now + 30 Tage); erfordert Passwort-Bestätigung
- [ ] Während Karenzfrist: Login möglich, Banner sichtbar, keine neuen Imports; POST /account/cancel-deletion hebt Vormerkung auf
- [ ] Cleanup-Job löscht nach Ablauf: PostgreSQL CASCADE, Weaviate-Tenant, Neo4j-Knoten, Redis-Sessions, S3-Exports
- [ ] Fehlerbehandlung: Job-Retry nach 1 Stunde bei Teillöschung; Alert nach 3 Fehlversuchen (D4 User Flow 4)
- [ ] Bestätigungs-E-Mail nach vollständiger Löschung; Audit-Log-Eintrag bleibt mit `user_id = NULL` (ON DELETE SET NULL)

**Technische Hinweise:** Cleanup-Job als Scheduler-Task (CRON `0 3 * * *` gemäß AGENTS.md). Reihenfolge: Weaviate → Neo4j → PostgreSQL (CASCADE). Bei Fehler: Idempotentes Retry.

---

#### TASK-106: Unveränderliches Audit-Log implementieren

| Feld             | Wert                                                        |
| ---------------- | ----------------------------------------------------------- |
| **Priorität**    | P1                                                          |
| **Bereich**      | Backend                                                     |
| **Aufwand**      | M                                                           |
| **Status**       | 🔴 Offen                                                    |
| **Quelle**       | D4 F-030, D1 Abschnitt 3.3.1 (audit_log-Tabelle), D4 NF-017 |
| **Abhängig von** | DB-Schema (Agent 1)                                         |
| **Blockiert**    | TASK-092, TASK-104                                          |

**Beschreibung:** Audit-Log-Service implementieren, der alle sicherheitsrelevanten Aktionen unveränderlich in der `audit_log`-Tabelle protokolliert. Geloggte Aktionen: `user.registered`, `user.login`, `user.login_failed`, `connection.created`, `connection.deleted`, `data.ingested`, `briefing.generated`, `search.executed`, `data.exported`, `user.deleted`. Append-only: Kein UPDATE/DELETE auf Audit-Log-Einträge. Keine PII in Metadaten.

**Acceptance Criteria:**

- [ ] Alle definierten Aktionen werden in `audit_log` mit user_id, action, resource_type, resource_id, ip_address, created_at gespeichert
- [ ] Append-only: Kein UPDATE/DELETE auf audit_log (außer bei Retention-Bereinigung)
- [ ] Metadaten enthalten keine PII (kein Content, keine E-Mail-Adressen – nur IDs, Zählwerte, Fehlercodes)
- [ ] Fehlgeschlagene Login-Versuche werden als Security-Event geloggt (D1 Security Instructions A09)
- [ ] GET /user/audit-log gibt die letzten 100 Einträge zurück; paginiert, gefiltert nach `owner_id`

**Technische Hinweise:** Audit-Middleware in TASK-093 ruft den Audit-Log-Service bei schreibenden Operationen auf. BIGSERIAL für ID (auto-increment, nicht UUIDs).

---

#### TASK-107: Verschlüsselungsstatus-Anzeige im Frontend implementieren

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P3                           |
| **Bereich**      | Frontend                     |
| **Aufwand**      | S                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D4 US-5.4, D4 F-029          |
| **Abhängig von** | TASK-094, TASK-095, TASK-092 |
| **Blockiert**    | –                            |

**Beschreibung:** Sicherheits-Tab auf der Einstellungsseite implementieren (GET /user/security). Anzeige: Verschlüsselungsstatus pro Speicherschicht (PostgreSQL, Weaviate, Neo4j – jeweils „verschlüsselt" mit Verschlüsselungstyp), OAuth-Token-Verschlüsselungsstatus, Datenstandort (EU – Frankfurt), Hinweis „Deine Daten werden nicht für LLM-Training verwendet".

**Acceptance Criteria:**

- [ ] Pro Speicherschicht wird der Verschlüsselungsstatus angezeigt (PostgreSQL: AES-256, Weaviate: Volume Encryption, Neo4j: Volume Encryption)
- [ ] OAuth-Token-Status: „Verschlüsselt mit nutzer-spezifischem Schlüssel (Fernet)"
- [ ] Datenstandort: „EU – Frankfurt (eu-central-1)"
- [ ] LLM-Nutzung: „Deine Daten werden nicht für externes LLM-Training verwendet"
- [ ] Informationen werden von GET /user/security geladen (keine Hardcoded-Werte im Frontend)

**Technische Hinweise:** Statische Informationen vom Backend bereitgestellt (konfiguriert über Umgebungsvariablen). Visuelle Darstellung mit Status-Badges (grüner Haken).

---

## Testing & QA

#### TASK-108: pytest-Setup mit DB-Fixtures aufsetzen

| Feld             | Wert                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                        |
| **Bereich**      | Testing                                                                   |
| **Aufwand**      | L                                                                         |
| **Status**       | 🔴 Offen                                                                  |
| **Quelle**       | D1 Backend Instructions (Tests), Copilot-Instructions (Code-Konventionen) |
| **Abhängig von** | DB-Schema (Agent 1)                                                       |
| **Blockiert**    | TASK-109, TASK-110                                                        |

**Beschreibung:** pytest-Infrastruktur mit Fixtures für alle drei Datenbanken aufsetzen. PostgreSQL: Testcontainers oder In-Memory SQLite-Fallback; Schema-Migration über Alembic. Weaviate: Testcontainer mit Multi-Tenancy. Neo4j: Testcontainer oder Mock-Layer. Redis: fakeredis. LLM: Mock-Responses via `pytest-mock` / `httpx.MockTransport`. `conftest.py` mit Session-scoped DB-Fixtures und Function-scoped Test-Fixtures. `asyncio_mode = "auto"` in pytest.ini.

**Acceptance Criteria:**

- [ ] `conftest.py` mit Session-scoped Fixtures für PostgreSQL, Weaviate, Neo4j, Redis
- [ ] Testcontainers für PostgreSQL, Weaviate und Neo4j (docker-basiert für Integrationstests)
- [ ] Mock-Fixtures für LLM-Calls (kein Netzwerkzugriff in Unit-Tests)
- [ ] `pytest.ini` mit `asyncio_mode = "auto"` und Marker-Definitionen (`unit`, `integration`, `e2e`)
- [ ] Test-Verzeichnisstruktur: `tests/unit/`, `tests/integration/`, `tests/e2e/`

**Technische Hinweise:** `pytest-asyncio`, `testcontainers-python`, `fakeredis` als Test-Dependencies. Alembic-Migrations im Test-Setup ausführen.

---

#### TASK-109: Backend-Unit-Tests mit 80% Abdeckung schreiben

| Feld             | Wert                                           |
| ---------------- | ---------------------------------------------- |
| **Priorität**    | P2                                             |
| **Bereich**      | Testing                                        |
| **Aufwand**      | XL                                             |
| **Status**       | 🔴 Offen                                       |
| **Quelle**       | D4 NF-011, Copilot-Instructions (Tests)        |
| **Abhängig von** | TASK-108, TASK-081–TASK-093, TASK-104–TASK-106 |
| **Blockiert**    | –                                              |

**Beschreibung:** Unit-Tests für alle Backend-Module schreiben: Auth-Service (JWT-Generierung, Passwort-Hashing, Token-Rotation), API-Router (Request/Response-Validierung, Fehler-Codes), Middleware (Rate-Limiting, CORS), DSGVO-Service (Export, Löschung), Audit-Log. Mindestabdeckung 80% über Coverage-Report. Kein Netzwerkzugriff – alle externen Dependencies gemockt.

**Acceptance Criteria:**

- [ ] Unit-Tests für Auth-Service: Token-Generierung, Token-Validierung, Passwort-Hashing, Replay-Detection
- [ ] Unit-Tests für alle API-Router: Valide/invalide Requests, korrekte Fehler-Codes, Ownership-Checks
- [ ] Unit-Tests für Middleware: Rate-Limiting (Limit erreicht/nicht erreicht), CORS-Header, Auth-Middleware
- [ ] Unit-Tests für DSGVO: Export-Generierung, Löschungs-Workflow, Audit-Log-Integrität
- [ ] Coverage-Report ≥ 80% (`pytest --cov=pwbs --cov-report=html`)

**Technische Hinweise:** `pytest-cov` für Coverage. Parametrisierte Tests für Randfälle (leere Listen, None-Werte, abgelaufene Tokens).

---

#### TASK-110: API-Integrationstests gegen Test-Datenbank implementieren

| Feld             | Wert                               |
| ---------------- | ---------------------------------- |
| **Priorität**    | P1                                 |
| **Bereich**      | Testing                            |
| **Aufwand**      | L                                  |
| **Status**       | 🔴 Offen                           |
| **Quelle**       | D4 NF-003, D1 Backend Instructions |
| **Abhängig von** | TASK-108, TASK-086–TASK-093        |
| **Blockiert**    | –                                  |

**Beschreibung:** Integrationstests für alle API-Endpunkte gegen echte Test-Datenbanken (Testcontainers). Tests prüfen den vollständigen Request-Response-Zyklus inkl. Authentifizierung, Datenbank-Operationen und Fehlerbehandlung. Testdaten-Fixtures simulieren realistische Szenarien (Nutzer mit Konnektoren, Dokumenten, Briefings).

**Acceptance Criteria:**

- [ ] Integrationstests für alle Auth-Endpunkte: Registrierung → Login → Refresh → Logout Lifecycle
- [ ] Integrationstests für Connectors: CRUD-Lifecycle inkl. OAuth-Callback-Simulation und kaskadierter Löschung
- [ ] Integrationstests für Search, Briefings, Knowledge, Documents: Korrekte Responses mit realistischen Testdaten
- [ ] Integrationstests für User-Endpunkte: Export-Workflow, Account-Löschung mit Karenzfrist
- [ ] Alle Tests verifizieren Mandanten-Isolation (kein Cross-User-Zugriff in Responses)

**Technische Hinweise:** `httpx.AsyncClient` mit `app=app` für In-Process-Testing. Testcontainers für PostgreSQL + Weaviate + Neo4j. Marker `@pytest.mark.integration`.

---

#### TASK-111: E2E-Tests für Kernflows implementieren

| Feld             | Wert                                   |
| ---------------- | -------------------------------------- |
| **Priorität**    | P2                                     |
| **Bereich**      | Testing                                |
| **Aufwand**      | L                                      |
| **Status**       | 🔴 Offen                               |
| **Quelle**       | D4 User Flows 1–4, D4 NF-025           |
| **Abhängig von** | TASK-096, TASK-097, TASK-100, TASK-102 |
| **Blockiert**    | –                                      |

**Beschreibung:** End-to-End-Tests mit Playwright für die Kern-User-Flows implementieren: (1) Onboarding-Flow: Registrierung → Konnektor verbinden → erstes Briefing (D4 User Flow 1), (2) Täglicher Nutzungsflow: Login → Dashboard → Briefing lesen → Suche nutzen (D4 User Flow 2), (3) DSGVO-Flow: Datenexport → Account-Löschung → Karenzfrist-Banner (D4 User Flow 4).

**Acceptance Criteria:**

- [ ] E2E-Test Onboarding: Registrierung → Willkommensdialog → Konnektor-Simulation → Briefing-Anzeige
- [ ] E2E-Test Täglicher Flow: Login → Dashboard mit Morgenbriefing → Suche durchführen → Ergebnisse prüfen
- [ ] E2E-Test DSGVO: Datenexport anfordern → Account-Löschung einleiten → Karenzfrist-Banner verifizieren → Löschung abbrechen
- [ ] Tests laufen gegen lokale Test-Umgebung (Docker Compose + Frontend Dev-Server)
- [ ] Onboarding-Dauer ≤ 15 Minuten verifiziert (D4 NF-025 – Zeitmessung im Test)

**Technische Hinweise:** Playwright mit TypeScript. Test-Fixtures für Nutzer-Erstellung und Mock-OAuth. CI-Integration über Docker Compose.

---

#### TASK-112: Load-Tests für 20 gleichzeitige Nutzer implementieren

| Feld             | Wert                        |
| ---------------- | --------------------------- |
| **Priorität**    | P2                          |
| **Bereich**      | Testing                     |
| **Aufwand**      | M                           |
| **Status**       | 🔴 Offen                    |
| **Quelle**       | D4 NF-008, D4 NF-001–NF-003 |
| **Abhängig von** | TASK-086–TASK-093           |
| **Blockiert**    | –                           |

**Beschreibung:** Load-Tests mit k6 oder Locust implementieren, die 20 gleichzeitige Nutzer simulieren. Szenarien: (1) Dashboard-Load (parallele Briefing + Connectors-Status Requests), (2) Suchanfragen (POST /search/), (3) Briefing-Generierung (POST /briefings/generate). Zielwerte: API-Endpunkte < 500ms (p95), Suche < 2s (p95), Briefing-Generierung < 10s (p95).

**Acceptance Criteria:**

- [ ] 20 gleichzeitige Nutzer werden simuliert (D4 NF-008)
- [ ] API-Endpunkte (allgemein) antworten in < 500ms (p95)
- [ ] Semantische Suche antwortet in < 2 Sekunden (p95) unter Last
- [ ] Briefing-Generierung < 10 Sekunden (p95) unter Last
- [ ] Keine Fehler-Rate > 1% unter Normallast; Connection-Pool-Limits werden nicht überschritten

**Technische Hinweise:** k6 bevorzugt (JavaScript-basiert, leichtgewichtig). Test-Skripte in `tests/load/`. Ergebnisse als JSON-Report für CI-Integration.

---

## Monitoring & Observability

#### TASK-113: Structured JSON-Logging implementieren

| Feld             | Wert                                                                                |
| ---------------- | ----------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                  |
| **Bereich**      | Backend                                                                             |
| **Aufwand**      | M                                                                                   |
| **Status**       | 🔴 Offen                                                                            |
| **Quelle**       | D1 Middleware-Stack (RequestIDMiddleware), D4 NF-001 (Messmethode: Backend-Logging) |
| **Abhängig von** | TASK-093                                                                            |
| **Blockiert**    | TASK-115                                                                            |

**Beschreibung:** Structured JSON-Logging für alle Backend-Operationen implementieren. Jeder Log-Eintrag enthält: Timestamp, Level, Request-ID (aus Middleware), User-ID (falls authentifiziert), Modul, Message, Dauer (für Performance-Tracking). Keine PII in Logs (kein Content, keine Embeddings, keine Metadaten-Werte). Log-Level konfigurierbar über Umgebungsvariable.

**Acceptance Criteria:**

- [ ] Alle Log-Einträge im JSON-Format mit Feldern: timestamp, level, request_id, user_id, module, message, duration_ms
- [ ] Keine PII in Logs (getestet: kein `content`, kein `email`, keine `metadata`-Werte)
- [ ] Log-Level konfigurierbar via `PWBS_LOG_LEVEL` Umgebungsvariable (DEBUG, INFO, WARNING, ERROR)
- [ ] Request-ID aus TASK-093 (RequestIDMiddleware) wird in jedem Log-Eintrag mitgeführt
- [ ] Request-Dauer wird für alle API-Calls geloggt (Basis für Performance-Metriken)

**Technische Hinweise:** `structlog` oder `python-json-logger` als Logging-Bibliothek. Konfiguration in `pwbs/core/logging.py`.

---

#### TASK-114: Health-Check-Endpunkt implementieren

| Feld             | Wert                                           |
| ---------------- | ---------------------------------------------- |
| **Priorität**    | P1                                             |
| **Bereich**      | Backend                                        |
| **Aufwand**      | S                                              |
| **Status**       | 🔴 Offen                                       |
| **Quelle**       | D1 API Layer (/api/v1/admin/health), D4 NF-006 |
| **Abhängig von** | DB-Schema (Agent 1)                            |
| **Blockiert**    | –                                              |

**Beschreibung:** Health-Check-Endpunkt GET `/api/v1/admin/health` implementieren, der den Status aller drei Datenbanken (PostgreSQL, Weaviate, Neo4j), Redis und der LLM-API-Erreichbarkeit prüft. Keine Authentifizierung erforderlich (für ALB/Monitoring). Response: HTTP 200 wenn alle Komponenten erreichbar, HTTP 503 bei kritischen Ausfällen.

**Acceptance Criteria:**

- [ ] GET /health gibt `{status: "healthy", components: {postgres, weaviate, neo4j, redis, llm_api}}` zurück
- [ ] Pro Komponente: `{status: "up"/"down"/"degraded", latency_ms}` mit tatsächlichem Verbindungstest
- [ ] HTTP 200 wenn PostgreSQL und mindestens eine Suchkomponente (Weaviate oder Keyword-Fallback) erreichbar
- [ ] HTTP 503 wenn PostgreSQL nicht erreichbar (kritischer Ausfall)
- [ ] Kein Auth erforderlich; Rate-Limited auf 10 Requests/Minute pro IP

**Technische Hinweise:** Leichtgewichtige Checks: PostgreSQL `SELECT 1`, Weaviate `/v1/.well-known/ready`, Neo4j Bolt-Ping, Redis PING. Timeout: 5 Sekunden pro Check.

---

#### TASK-115: Error-Tracking mit Sentry einrichten

| Feld             | Wert                |
| ---------------- | ------------------- |
| **Priorität**    | P2                  |
| **Bereich**      | Backend             |
| **Aufwand**      | S                   |
| **Status**       | 🔴 Offen            |
| **Quelle**       | D4 NF-006, D4 AR-08 |
| **Abhängig von** | TASK-093, TASK-113  |
| **Blockiert**    | –                   |

**Beschreibung:** Sentry-SDK für Backend (Python) und Frontend (Next.js) integrieren. Unbehandelte Exceptions automatisch erfassen. Request-ID und User-ID (pseudonymisiert) als Kontext anhängen. PII-Scrubbing aktivieren: Keine E-Mails, Passwörter oder Dokumentinhalte an Sentry. Environment-Tags (development, staging, production). Performance-Tracing für API-Requests.

**Acceptance Criteria:**

- [ ] Sentry-SDK im Backend (FastAPI) und Frontend (Next.js) integriert
- [ ] Unbehandelte Exceptions werden automatisch mit Stack-Trace an Sentry gesendet
- [ ] Request-ID und pseudonymisierte User-ID als Sentry-Context; keine PII (E-Mail, Passwort, Content)
- [ ] Environment-Tags: `PWBS_ENV` wird als Sentry-Environment gesetzt
- [ ] Performance-Tracing: API-Request-Dauer wird als Sentry-Transaction erfasst

**Technische Hinweise:** `sentry-sdk[fastapi]` für Backend. `@sentry/nextjs` für Frontend. DSN über Umgebungsvariable `SENTRY_DSN`. PII-Scrubbing in `before_send` Hook.

---

#### TASK-116: Basis-Metriken erfassen und exponieren

| Feld             | Wert                                                            |
| ---------------- | --------------------------------------------------------------- |
| **Priorität**    | P2                                                              |
| **Bereich**      | Backend                                                         |
| **Aufwand**      | M                                                               |
| **Status**       | 🔴 Offen                                                        |
| **Quelle**       | D4 Abschnitt 10 (Metriken & Erfolgskriterien), D4 NF-001–NF-003 |
| **Abhängig von** | TASK-093, TASK-113                                              |
| **Blockiert**    | –                                                               |

**Beschreibung:** Basis-Metriken für das MVP erfassen: Request-Latenz (p50, p95, p99 pro Endpunkt), Fehlerrate (4xx, 5xx pro Endpunkt), aktive Nutzer (DAU basierend auf Auth-Events), Briefing-Abrufe pro Nutzer/Woche, Suchanfragen pro Nutzer/Woche, verbundene Konnektoren pro Nutzer. Metriken über Structured Logging (TASK-113) und optionalen Prometheus-Endpunkt exponieren.

**Acceptance Criteria:**

- [ ] Request-Latenz (p50, p95, p99) wird pro Endpunkt-Gruppe erfasst und über Logs/Metriken exponiert
- [ ] Fehlerrate (4xx/5xx) wird pro Endpunkt erfasst
- [ ] DAU/MAU-Ratio berechenbar aus Auth-Events im Audit-Log
- [ ] Briefing-Abrufe und Suchanfragen pro Nutzer/Woche aggregierbar
- [ ] Optionaler Prometheus-Endpunkt `/metrics` für Grafana-Integration

**Technische Hinweise:** `prometheus-fastapi-instrumentator` für automatische Request-Metriken. Custom-Metriken für Business-KPIs über Audit-Log-Aggregation.

---

## Ergänzende Tasks

#### TASK-117: Auth-Context-Provider und Token-Refresh im Frontend implementieren

| Feld             | Wert                                                             |
| ---------------- | ---------------------------------------------------------------- |
| **Priorität**    | P0                                                               |
| **Bereich**      | Frontend                                                         |
| **Aufwand**      | M                                                                |
| **Status**       | 🔴 Offen                                                         |
| **Quelle**       | D1 Abschnitt 3.7 (lib/auth.ts, State-Management), D4 User Flow 2 |
| **Abhängig von** | TASK-094, TASK-095, TASK-086                                     |
| **Blockiert**    | TASK-096, TASK-097                                               |

**Beschreibung:** React-Context-Provider für Auth-State implementieren. Verwaltet JWT-Tokens (Access + Refresh), User-Profil und Authentifizierungsstatus. Automatischer Token-Refresh im Hintergrund bei abgelaufendem Access-Token. Redirect zur Login-Seite bei abgelaufenem Refresh-Token. Protected-Route-Wrapper für `(dashboard)/`-Seiten. Session-Persistenz über httpOnly-Cookie oder Secure Storage.

**Acceptance Criteria:**

- [ ] AuthProvider stellt `user`, `isAuthenticated`, `login()`, `logout()`, `refreshToken()` bereit
- [ ] Automatischer Token-Refresh bei 401-Response ohne Nutzer-Unterbrechung (D4 User Flow 2)
- [ ] Redirect zu `/login` bei abgelaufenem Refresh-Token mit Meldung „Sitzung abgelaufen"
- [ ] Protected-Route-Wrapper leitet nicht-authentifizierte Nutzer auf `/login` um
- [ ] Auth-State überlebt Page-Refresh (httpOnly-Cookie oder Secure Storage)

**Technische Hinweise:** React Context für Auth-State gemäß D1 State-Management. Token-Refresh-Logik im API-Client (TASK-095) integriert.

---

#### TASK-118: WebSocket-Verbindung für Echtzeit-Updates implementieren

| Feld             | Wert                                                                             |
| ---------------- | -------------------------------------------------------------------------------- |
| **Priorität**    | P2                                                                               |
| **Bereich**      | Backend                                                                          |
| **Aufwand**      | M                                                                                |
| **Status**       | 🔴 Offen                                                                         |
| **Quelle**       | D1 Abschnitt 3.7 (use-websocket.ts), D1 Abschnitt 3.5 (WebSocket Push), D4 OQ-09 |
| **Abhängig von** | TASK-081, TASK-093                                                               |
| **Blockiert**    | –                                                                                |

**Beschreibung:** WebSocket-Endpunkt in FastAPI implementieren, der authentifizierten Nutzern Echtzeit-Updates sendet. Events: Sync-Fortschritt (Konnektor-Sync gestartet/abgeschlossen), Briefing-Generierung abgeschlossen, Export-Download bereit. Frontend: `use-websocket.ts` Hook, der TanStack Query Cache bei relevanten Events invalidiert.

**Acceptance Criteria:**

- [ ] WebSocket-Endpunkt `/ws` mit JWT-Authentifizierung (Token als Query-Parameter oder Cookie)
- [ ] Server sendet Events: `sync.progress`, `sync.completed`, `briefing.ready`, `export.ready`
- [ ] Frontend-Hook `useWebSocket` verbindet bei Dashboard-Load und invalidiert gezielt TanStack Query Cache
- [ ] Automatische Reconnection bei Verbindungsabbruch (exponentieller Backoff)
- [ ] Graceful Degradation: System funktioniert auch ohne WebSocket (Polling-Fallback)

**Technische Hinweise:** FastAPI WebSocket via `@app.websocket("/ws")`. Fallback: TanStack Query Polling-Intervall (60s) bei WebSocket-Ausfall.

---

#### TASK-119: OpenAPI-Schema-Generierung und API-Dokumentation einrichten

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P2                           |
| **Bereich**      | Backend                      |
| **Aufwand**      | S                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D1 API Layer, D4 Abschnitt 8 |
| **Abhängig von** | TASK-086–TASK-093            |
| **Blockiert**    | –                            |

**Beschreibung:** OpenAPI-Schema-Generierung über FastAPI automatisieren. Alle Endpunkte mit vollständigen Pydantic-Response-Modellen, Fehler-Responses und Beschreibungen versehen. OpenAPI-JSON unter `/api/v1/openapi.json` exportierbar (auch in Produktion). SwaggerUI/ReDoc nur in Development. TypeScript-Typen aus OpenAPI-Schema generierbar (für TASK-095).

**Acceptance Criteria:**

- [ ] OpenAPI 3.1 Schema unter `/api/v1/openapi.json` erreichbar
- [ ] Alle Endpunkte mit Response-Modellen, Fehler-Codes und Beschreibungen dokumentiert
- [ ] SwaggerUI und ReDoc in Development verfügbar; in Produktion deaktiviert
- [ ] TypeScript-Typen können aus Schema generiert werden (`openapi-typescript` oder äquivalent)
- [ ] Schema ist valide (OpenAPI-Validator-Check in CI)

**Technische Hinweise:** FastAPI generiert OpenAPI automatisch aus Pydantic-Modellen. `openapi_url` in Produktion auf `/api/v1/openapi.json` beschränken (ohne UI).

---

#### TASK-120: Frontend-Barrierefreiheit (WCAG 2.1 AA) sicherstellen

| Feld             | Wert                        |
| ---------------- | --------------------------- |
| **Priorität**    | P3                          |
| **Bereich**      | Frontend                    |
| **Aufwand**      | M                           |
| **Status**       | 🔴 Offen                    |
| **Quelle**       | D4 NF-026                   |
| **Abhängig von** | TASK-094, TASK-096–TASK-103 |
| **Blockiert**    | –                           |

**Beschreibung:** Barrierefreiheit gemäß WCAG 2.1 Level AA für alle Kernfunktionen sicherstellen. Semantisches HTML in allen Komponenten. ARIA-Labels für interaktive Elemente (Buttons, Links, Formulare). Keyboard-Navigation für alle Views. Farbkontraste ≥ 4.5:1 für Texte. Fokus-Management bei Dialogen und Modals. Axe/Lighthouse Accessibility-Audit in CI.

**Acceptance Criteria:**

- [ ] Alle interaktiven Elemente sind per Tastatur erreichbar und bedienbar (Tab, Enter, Escape)
- [ ] ARIA-Labels auf allen Buttons, Links und Formularfeldern; semantische HTML-Elemente (nav, main, section)
- [ ] Farbkontraste ≥ 4.5:1 für normalen Text, ≥ 3:1 für großen Text (WCAG AA)
- [ ] Fokus-Management: Dialoge fangen Fokus; Schließen gibt Fokus zurück an Trigger-Element
- [ ] Lighthouse Accessibility Score ≥ 90 auf allen Kernseiten

**Technische Hinweise:** Shadcn/ui-Komponenten sind standardmäßig accessible. `eslint-plugin-jsx-a11y` in ESLint-Konfiguration aktivieren. Axe-core in Playwright-E2E-Tests integrieren.

---

## Statistik Teil 3

| Bereich    | Anzahl |
| ---------- | ------ |
| Auth       | 5      |
| API        | 8      |
| Frontend   | 11     |
| DSGVO      | 4      |
| Testing    | 5      |
| Monitoring | 4      |
| Ergänzend  | 3      |
| **Gesamt** | **40** |

<!-- AGENT_3_LAST: TASK-120 -->

---


---

## Phase 3 – Private Beta & Produktreife (Monate 10–15)

---

#### TASK-121: Celery + Redis Queue-Infrastruktur einrichten

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P1                           |
| **Bereich**      | Infra / DevOps               |
| **Aufwand**      | L                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D1 Abschnitt 6.3, D2 Phase 3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)        |
| **Blockiert**    | TASK-122                     |

**Beschreibung:** Celery als Task-Queue mit Redis als Message Broker aufsetzen. Queue-Topologie gemäß D1 Abschnitt 6.3 konfigurieren (ingestion.high, ingestion.bulk, processing.embed, processing.extract, briefing.generate). Redis-Persistenz (AOF) aktivieren, um Nachrichtenverlust bei Redis-Restart zu minimieren.

**Acceptance Criteria:**

- [ ] Celery-Worker starten erfolgreich und verbinden sich mit Redis als Broker
- [ ] Fünf dedizierte Queues sind konfiguriert mit korrekten Prioritäten und Timeouts
- [ ] Redis AOF-Persistenz ist aktiviert; bei Redis-Neustart gehen keine ausstehenden Tasks verloren
- [ ] Docker-Compose und Terraform-Module sind um Celery-Worker-Services erweitert
- [ ] Health-Check-Endpoint `/api/v1/admin/health` meldet Queue-Status (Tiefe, Worker-Anzahl)

**Technische Hinweise:** Redis wird bereits für Caching genutzt (D1 Abschnitt 6.4). Celery ist Python-nativ und reduziert Infrastrukturkomplexität gegenüber AWS SQS (ADR-011). Kritische Jobs zusätzlich in PostgreSQL loggen als Fallback.

---

#### TASK-122: Ingestion- und Processing-Pipeline auf Queue-Worker migrieren

| Feld             | Wert                                           |
| ---------------- | ---------------------------------------------- |
| **Priorität**    | P1                                             |
| **Bereich**      | Backend                                        |
| **Aufwand**      | L                                              |
| **Status**       | 🔴 Offen                                       |
| **Quelle**       | D1 Abschnitt 3.2, D1 Abschnitt 6.2, D2 Phase 3 |
| **Abhängig von** | TASK-121                                       |
| **Blockiert**    | –                                              |

**Beschreibung:** Die im MVP synchron in FastAPI-Background-Tasks laufende Processing-Pipeline auf asynchrone Celery-Worker umstellen. Ingestion-Jobs (Webhook-getriggert und Bulk-Syncs) und Processing-Steps (Embedding, NER, Graph-Build) als eigenständige Celery-Tasks implementieren. Pipeline-Orchestrierung über Celery-Chains/Chords realisieren.

**Acceptance Criteria:**

- [ ] Ingestion-Jobs werden als Celery-Tasks in die korrekte Queue dispatcht (high für Echtzeit, bulk für Backfill)
- [ ] Processing-Schritte (Chunking → Embedding → NER → Graph-Build) laufen als verkettete Celery-Tasks
- [ ] Idempotenz bleibt gewährleistet: Wiederholte Task-Ausführung erzeugt keine Duplikate
- [ ] Retry-Logik mit Exponential Backoff bei transienten Fehlern (max. 3 Retries)
- [ ] Monitoring: Task-Dauer, Fehlerrate und Queue-Tiefe sind als Prometheus-Metriken exportiert

**Technische Hinweise:** Im MVP laufen Ingestion und Processing synchron im FastAPI-Prozess (D1 Abschnitt 3.2). Die Modul-Interfaces bleiben erhalten – nur die Orchestrierung wechselt von direkten Aufrufen zu Queue-Dispatch.

---

#### TASK-123: Gmail-Konnektor – OAuth2 und Google Pub/Sub Push Notifications

| Feld             | Wert                             |
| ---------------- | -------------------------------- |
| **Priorität**    | P1                               |
| **Bereich**      | Backend                          |
| **Aufwand**      | L                                |
| **Status**       | 🔴 Offen                         |
| **Quelle**       | D1 Konnektor-Tabelle, D2 Phase 3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)            |
| **Blockiert**    | TASK-124                         |

**Beschreibung:** Gmail-Konnektor auf Basis des `BaseConnector`-Interfaces implementieren. OAuth2-Flow mit Google-Scopes `gmail.readonly` aufsetzen. Google Pub/Sub Push Notifications konfigurieren, damit neue E-Mails in Echtzeit als Events empfangen werden. Webhook-Endpoint für Pub/Sub-Messages bereitstellen.

**Acceptance Criteria:**

- [ ] OAuth2-Flow für Gmail funktioniert mit korrekten Scopes; Tokens werden verschlüsselt mit User-DEK gespeichert
- [ ] Google Pub/Sub Topic und Subscription sind konfiguriert; Push-Endpoint empfängt Notifications
- [ ] Bei neuer E-Mail wird automatisch ein Ingestion-Job in die Queue geschoben
- [ ] Token-Rotation (Refresh) funktioniert automatisch bei abgelaufenen Access-Tokens
- [ ] Datenschutz: Nur Metadaten und Content werden importiert, keine Anhänge im MVP (opt-in für Metadaten)

**Technische Hinweise:** D1 listet Gmail mit Auth via OAuth2 (Google), Sync via Push Notifications (Pub/Sub) + History API. Pub/Sub erfordert ein Google Cloud-Projekt mit aktivierter Gmail API und Pub/Sub API.

---

#### TASK-124: Gmail-Konnektor – History API, Thread-Resolution und UDF-Normalisierung

| Feld             | Wert                             |
| ---------------- | -------------------------------- |
| **Priorität**    | P1                               |
| **Bereich**      | Backend                          |
| **Aufwand**      | M                                |
| **Status**       | 🔴 Offen                         |
| **Quelle**       | D1 Konnektor-Tabelle, D2 Phase 3 |
| **Abhängig von** | TASK-123                         |
| **Blockiert**    | –                                |

**Beschreibung:** Gmail History API für inkrementellen Sync implementieren. Watermark als `historyId` persistieren. Thread-Resolution: E-Mail-Threads zusammenführen, damit der vollständige Konversationsverlauf als ein logisches Dokument importiert wird. Normalisierung in das Unified Document Format (UDF) mit korrekten Metadaten (Absender, Empfänger, Datum, Thread-ID).

**Acceptance Criteria:**

- [ ] Inkrementeller Sync über `history.list()` mit persistiertem `historyId`-Watermark
- [ ] E-Mail-Threads werden zu einem UDF-Dokument pro Thread zusammengeführt
- [ ] Participants-Feld im UDF enthält alle Absender und Empfänger des Threads
- [ ] Idempotenz: Re-Import derselben E-Mails erzeugt keine Duplikate (content_hash-Prüfung)

**Technische Hinweise:** Die History API gibt nur geänderte Message-IDs zurück; der Content muss separat per `messages.get()` geholt werden. E-Mail-Body als Plaintext (HTML-Stripping) in UDF-Content übernehmen. Datenminimierung: Keine rohen HTML-Bodies langfristig speichern (D1 Abschnitt 5.2).

---

#### TASK-125: Slack-Konnektor – OAuth2 und Events API

| Feld             | Wert                             |
| ---------------- | -------------------------------- |
| **Priorität**    | P1                               |
| **Bereich**      | Backend                          |
| **Aufwand**      | L                                |
| **Status**       | 🔴 Offen                         |
| **Quelle**       | D1 Konnektor-Tabelle, D2 Phase 3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)            |
| **Blockiert**    | TASK-126                         |

**Beschreibung:** Slack-Konnektor auf Basis des `BaseConnector`-Interfaces implementieren. Slack-App mit OAuth2-Flow erstellen (Scopes: `channels:history`, `channels:read`, `users:read`). Events API konfigurieren für Echtzeit-Nachrichten-Events. URL-Verification-Challenge und Event-Signature-Validierung implementieren.

**Acceptance Criteria:**

- [ ] OAuth2-Flow für Slack funktioniert; Bot-Token und User-Token werden verschlüsselt gespeichert
- [ ] Events API Webhook empfängt `message`-Events und validiert Slack-Signaturen (HMAC-SHA256)
- [ ] Neue Nachrichten in konfigurierten Channels lösen automatisch Ingestion-Jobs aus
- [ ] Channel-Auswahl: Nutzer kann bei der Einrichtung Channels für den Import auswählen
- [ ] Rate-Limiting: Tier-1-Konformität mit Slack-Rate-Limits eingehalten

**Technische Hinweise:** D1 listet Slack mit Events API (Webhook) + Cursor-basiertem Backfill. Slack-Event-Signatures müssen mit dem Signing Secret der App verifiziert werden (OWASP A03: Injection-Schutz). Nur öffentliche und vom Nutzer autorisierte Channels importieren.

---

#### TASK-126: Slack-Konnektor – Cursor-basiertes Backfill und Thread-Auflösung

| Feld             | Wert                             |
| ---------------- | -------------------------------- |
| **Priorität**    | P2                               |
| **Bereich**      | Backend                          |
| **Aufwand**      | M                                |
| **Status**       | 🔴 Offen                         |
| **Quelle**       | D1 Konnektor-Tabelle, D2 Phase 3 |
| **Abhängig von** | TASK-125                         |
| **Blockiert**    | –                                |

**Beschreibung:** Historische Slack-Nachrichten über die `conversations.history`-API mit Cursor-basierter Pagination abrufen. Thread-Replies über `conversations.replies` auflösen und mit dem Parent-Message zusammenführen. Reaktionen als Metadaten erfassen. UDF-Normalisierung mit Channel-Name, Autor, Timestamp und Thread-Kontext.

**Acceptance Criteria:**

- [ ] Initialer Backfill importiert alle Nachrichten der letzten 90 Tage in konfigurierten Channels
- [ ] Cursor wird nach jedem erfolgreichen Batch persistiert; Abbruch und Fortsetzung sind möglich
- [ ] Thread-Replies werden dem Parent-Message als zusammenhängendes UDF-Dokument zugeordnet
- [ ] Reaktionen (Emoji-Reactions) werden als Metadaten im UDF gespeichert

**Technische Hinweise:** Slack-API paginiert mit Cursor und liefert max. 200 Messages pro Request. Thread-Replies sind separate API-Calls. Batch-Größe und Rate-Limiting beachten (Tier-1: ~1 Request/Sekunde).

---

#### TASK-127: Google Docs-Konnektor implementieren

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P2                           |
| **Bereich**      | Backend                      |
| **Aufwand**      | L                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D2 Phase 3, D1 Phase-Mapping |
| **Abhängig von** | MVP-Basis (Agent 1–3)        |
| **Blockiert**    | –                            |

**Beschreibung:** Google Docs-Konnektor auf Basis des `BaseConnector`-Interfaces implementieren. OAuth2-Flow mit Google-Scopes für Drive und Docs API. Inkrementeller Sync über `modifiedTime`-Cursor. Dokumenteninhalt als strukturierten Plaintext exportieren (Google Docs JSON → Markdown-Konvertierung). Normalisierung ins UDF.

**Acceptance Criteria:**

- [ ] OAuth2-Flow für Google Docs/Drive funktioniert mit korrekten Scopes
- [ ] Inkrementeller Sync basiert auf `modifiedTime`-Watermark; nur geänderte Docs werden re-importiert
- [ ] Google Docs-Strukturelemente (Überschriften, Listen, Tabellen) werden als Markdown normalisiert
- [ ] Idempotenz: content_hash-basierte Deduplizierung verhindert redundante Verarbeitung
- [ ] Shared Docs: Nur Docs importieren, auf die der Nutzer Zugriff hat; Ownership wird korrekt dem PWBS-Nutzer zugeordnet

**Technische Hinweise:** Google Docs API liefert strukturiertes JSON des Dokumenteninhalts. Die Konvertierung in Markdown muss Überschriften-Hierarchie, Inline-Formatierungen und Tabellen korrekt abbilden. Drive API für Dateiliste + Metadaten, Docs API für Inhalt.

---

#### TASK-128: Outlook-Mail-Konnektor implementieren

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P2                           |
| **Bereich**      | Backend                      |
| **Aufwand**      | L                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D2 Phase 3, D1 Phase-Mapping |
| **Abhängig von** | MVP-Basis (Agent 1–3)        |
| **Blockiert**    | –                            |

**Beschreibung:** Outlook-Mail-Konnektor über Microsoft Graph API implementieren. OAuth2-Flow mit Azure AD (Scopes: `Mail.Read`). Delta-Sync über `deltaLink` für inkrementelle Abfragen. E-Mail-Threads über `conversationId` zusammenführen. UDF-Normalisierung analog zum Gmail-Konnektor.

**Acceptance Criteria:**

- [ ] OAuth2-Flow über Azure AD / Microsoft Identity Platform funktioniert
- [ ] Delta-Sync über Microsoft Graph `$deltatoken` liefert nur neue/geänderte Mails
- [ ] E-Mail-Threads werden über `conversationId` zu einem logischen UDF-Dokument zusammengeführt
- [ ] HTML-Body wird zu Plaintext konvertiert; Anhänge werden als Metadaten referenziert (kein Download im MVP)

**Technische Hinweise:** Microsoft Graph API verwendet OData-Konventionen und Delta-Queries. Azure-App-Registrierung erforderlich. Tenant-Konfiguration: Sowohl persönliche Microsoft-Konten als auch Azure-AD-Organisationskonten unterstützen.

---

#### TASK-129: Entscheidungsunterstützung – Datenmodell und Graph-Schema erweitern

| Feld             | Wert                                              |
| ---------------- | ------------------------------------------------- |
| **Priorität**    | P1                                                |
| **Bereich**      | Backend                                           |
| **Aufwand**      | M                                                 |
| **Status**       | 🔴 Offen                                          |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 4, D1 Abschnitt 3.3.3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)                             |
| **Blockiert**    | TASK-130                                          |

**Beschreibung:** Das Datenmodell für Entscheidungsunterstützung erweitern. PostgreSQL-Tabelle `decisions` mit Feldern für Pro/Contra-Argumente, Annahmen, Abhängigkeiten und Status (pending, made, revised). Neo4j-Schema erweitern: Entscheidungs-Knoten mit Kanten zu Projekten, Meetings und vorangehenden Entscheidungen (`:SUPERSEDES`). API-Endpoints für CRUD auf Entscheidungen bereitstellen.

**Acceptance Criteria:**

- [ ] Alembic-Migration erstellt `decisions`-Tabelle mit Feldern: pro_arguments, contra_arguments, assumptions, dependencies, status, decided_by, decided_at
- [ ] Neo4j-Schema enthält Decision-Knoten mit AFFECTS-, DECIDED_IN- und SUPERSEDES-Kanten
- [ ] API-Endpoints: GET/POST/PATCH `/api/v1/knowledge/decisions` mit owner_id-Isolation
- [ ] NER extrahiert automatisch Entscheidungen aus Dokumenten und verknüpft sie im Graph

**Technische Hinweise:** D1 Abschnitt 3.3.3 definiert bereits Decision-Knoten im Graph-Schema. D3 Kernfunktion 4 fordert „Sichtbarmachung relevanter früherer Erkenntnisse bei neuen Entscheidungen". Die SUPERSEDES-Kante ermöglicht die Nachverfolgung revidierter Entscheidungen.

---

#### TASK-130: Entscheidungsunterstützung – Pro/Contra-UI und Nachverfolgung

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P1                            |
| **Bereich**      | Frontend                      |
| **Aufwand**      | L                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 4 |
| **Abhängig von** | TASK-129                      |
| **Blockiert**    | –                             |

**Beschreibung:** Frontend-Komponenten für Entscheidungsunterstützung implementieren. Entscheidungs-Detailansicht mit Pro/Contra-Spalten, Annahmen-Liste und Abhängigkeiten. Timeline-Darstellung der Entscheidungshistorie pro Projekt. Kontextuelle Einblendung relevanter früherer Entscheidungen beim Erstellen einer neuen Entscheidung.

**Acceptance Criteria:**

- [ ] Entscheidungs-Detailseite zeigt Pro/Contra-Argumente, Annahmen und Abhängigkeiten strukturiert an
- [ ] Timeline-Ansicht zeigt Entscheidungshistorie pro Projekt mit Status (pending, made, revised)
- [ ] Beim Erstellen einer neuen Entscheidung werden automatisch relevante frühere Entscheidungen als Kontext vorgeschlagen (via SearchAgent)
- [ ] Nachverfolgung: Status-Änderungen einer Entscheidung werden mit Quellenreferenz im Audit-Log protokolliert
- [ ] Quellenreferenzen: Jede Entscheidung verlinkt auf die Dokumente/Meetings, in denen sie getroffen wurde

**Technische Hinweise:** React-Komponenten in `components/decisions/` anlegen. Server Components für initiale Daten, Client Components für interaktive Pro/Contra-Bearbeitung. D3 fordert explizit „Was wurde entschieden, warum, und was ist daraus geworden?"

---

#### TASK-131: Aktive Erinnerungen – Follow-up-Detection und Trigger-Engine

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P1                            |
| **Bereich**      | Backend                       |
| **Aufwand**      | L                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 5 |
| **Abhängig von** | MVP-Basis (Agent 1–3)         |
| **Blockiert**    | TASK-132                      |

**Beschreibung:** Engine für aktive Erinnerungen implementieren. Follow-up-Detection: NER um Erkennung von Follow-up-Commitments erweitern ("Ich schicke dir das morgen", "Bis Freitag liefern wir X"). Trigger-Engine: Regelbasiertes System, das anhand von Zeitablauf, Entitäts-Inaktivität und ungelösten offenen Fragen Erinnerungen generiert. Scheduler-Job für tägliche Prüfung überfälliger Follow-ups.

**Acceptance Criteria:**

- [ ] NER extrahiert Follow-up-Commitments mit Deadline und verantwortlicher Person aus Dokumenten
- [ ] Trigger-Engine prüft täglich: überfällige Follow-ups, inaktive Themen (> 30 Tage ohne Erwähnung), offene Fragen ohne Antwort
- [ ] Erinnerungen werden als strukturierte Objekte in PostgreSQL persistiert mit Status (pending, acknowledged, dismissed)
- [ ] API-Endpoint: GET `/api/v1/reminders` liefert offene Erinnerungen sortiert nach Dringlichkeit

**Technische Hinweise:** D3 Kernfunktion 5 beschreibt: „Hinweise auf vergessene Themen, überfällige Follow-ups, wiederkehrende Probleme." Die Detection basiert auf LLM-basierter NER (Erweiterung des Entity-Extraction-Prompts) plus regelbasierter Zeitprüfung.

---

#### TASK-132: Aktive Erinnerungen – Notification-UI und proaktive Fragen

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P2                            |
| **Bereich**      | Frontend                      |
| **Aufwand**      | M                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 5 |
| **Abhängig von** | TASK-131                      |
| **Blockiert**    | –                             |

**Beschreibung:** Frontend-Komponenten für aktive Erinnerungen implementieren. Notification-Center im Dashboard mit Badge-Counter. Erinnerungs-Cards mit Kontext (wann wurde das Thema zuletzt erwähnt, welche Quelle). Proaktive Fragen als interaktive Cards: "Thema X wurde vor 3 Monaten bearbeitet – ist das noch relevant?" mit Aktionen (Acknowledge, Dismiss, Snooze).

**Acceptance Criteria:**

- [ ] Notification-Center im Dashboard-Header zeigt Anzahl offener Erinnerungen als Badge
- [ ] Erinnerungs-Cards zeigen Kontext, Quellenreferenz und Zeitspanne seit letzter Aktivität
- [ ] Proaktive Fragen sind als interaktive Cards implementiert mit Aktionen: "Noch relevant", "Erledigt", "Später erinnern"
- [ ] Nutzer kann Erinnerungsfrequenz in den Einstellungen konfigurieren (täglich/wöchentlich/aus)

**Technische Hinweise:** D3 beschreibt proaktive Fragen als „Fragen wie: Du hast vor drei Monaten über X nachgedacht – ist das noch relevant?" D2 Annahme: Risiko, dass aktive Erinnerungen als aufdringlich empfunden werden – daher konfigurierbare Frequenz.

---

#### TASK-133: Projektbriefings – Generierung, API und Frontend

| Feld             | Wert                                            |
| ---------------- | ----------------------------------------------- |
| **Priorität**    | P1                                              |
| **Bereich**      | Backend / Frontend                              |
| **Aufwand**      | L                                               |
| **Status**       | 🔴 Offen                                        |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 3, D1 Abschnitt 3.5 |
| **Abhängig von** | MVP-Basis (Agent 1–3), TASK-129                 |
| **Blockiert**    | –                                               |

**Beschreibung:** Projektbriefings als dritten Briefing-Typ implementieren. On-Demand-Generierung pro Projekt: Status, Entscheidungshistorie, offene Punkte, beteiligte Personen, relevante Dokumente. Max. 1200 Wörter. Frontend: Projektübersichtsseite mit Briefing-Integration. BriefingAgent um `ProjectBriefing`-Template erweitern.

**Acceptance Criteria:**

- [ ] API-Endpoint POST `/api/v1/briefings/generate` akzeptiert `type: "project"` mit `project_entity_id` als Kontext
- [ ] Projektbriefing enthält: Projektstatus, Entscheidungshistorie, offene Punkte, beteiligte Personen – alle mit Quellenreferenzen
- [ ] Max. 1200 Wörter, LLM-Temperatur 0.3 (sachliche Inhalte)
- [ ] Frontend: Projektübersichtsseite mit On-Demand-Briefing-Button und persistiertem Briefing-Cache

**Technische Hinweise:** D1 Abschnitt 3.5 definiert bereits die Briefing-Trigger-Logik. ProjectBriefing nutzt Neo4j-Abfrage `get_project_history(project_name, owner_id)` für Entscheidungs-Timeline und Weaviate-Suche für relevante Dokumente.

---

#### TASK-134: Persönliches Lernmodell – Arbeitsmuster-Erkennung

| Feld             | Wert                                   |
| ---------------- | -------------------------------------- |
| **Priorität**    | P2                                     |
| **Bereich**      | Backend                                |
| **Aufwand**      | XL                                     |
| **Status**       | 🔴 Offen                               |
| **Quelle**       | D2 Phase 3, D3 Alleinstellungsmerkmale |
| **Abhängig von** | MVP-Basis (Agent 1–3)                  |
| **Blockiert**    | –                                      |

**Beschreibung:** System zur Erkennung individueller Arbeitsmuster, Prioritäten und Denkgewohnheiten implementieren. Analyse von: Meeting-Häufigkeit pro Woche, häufig bearbeitete Themen, bevorzugte Arbeitszeiten, Entscheidungsmuster (schnell vs. iterativ). Ergebnisse als Nutzer-Profil in PostgreSQL persistieren und für Briefing-Personalisierung nutzen.

**Acceptance Criteria:**

- [ ] Wöchentlicher Analyse-Job extrahiert Arbeitsmuster aus den letzten 30 Tagen Aktivitätsdaten
- [ ] Erkannte Muster umfassen: Top-5-Themen, durchschnittliche Meeting-Last, bevorzugte Arbeitszeiten, Entscheidungsgeschwindigkeit
- [ ] Muster werden in einem `user_profile`-Modell in PostgreSQL gespeichert (mit Versionierung)
- [ ] Briefing-Engine verwendet Nutzerprofil zur Priorisierung: Häufigere Themen werden prominenter dargestellt

**Technische Hinweise:** D3 beschreibt als Alleinstellungsmerkmal das „Persönliche Lernmodell: Es lernt individuelle Denk- und Arbeitsmuster, nicht nur generische Wissensstrukturen." Start mit regelbasierter Musteranalyse; LLM-basierte Analyse als optionale Erweiterung.

---

#### TASK-135: Desktop-App – Tauri-Grundgerüst mit WebView und System Tray

| Feld             | Wert                                    |
| ---------------- | --------------------------------------- |
| **Priorität**    | P1                                      |
| **Bereich**      | Frontend                                |
| **Aufwand**      | XL                                      |
| **Status**       | 🔴 Offen                                |
| **Quelle**       | D1 Client Layer, D1 ADR-008, D2 Phase 3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)                   |
| **Blockiert**    | TASK-136                                |

**Beschreibung:** Tauri-basierte Desktop-App als eigenständiges Projekt aufsetzen. WebView lädt die bestehende Next.js-Web-App. System-Tray-Integration mit Quick-Actions (Suche öffnen, heutiges Briefing, letztes Meeting-Briefing). Native Notifications für neue Briefings und Erinnerungen. Auto-Update-Mechanismus.

**Acceptance Criteria:**

- [ ] Tauri-App startet auf Windows, macOS und Linux und zeigt die PWBS-Web-App im WebView
- [ ] System-Tray-Icon mit Kontextmenü: "Dashboard öffnen", "Suche", "Heutiges Briefing"
- [ ] Native OS-Notifications werden bei neuen Briefings und aktiven Erinnerungen angezeigt
- [ ] Auto-Updater prüft auf neue Versionen und installiert Updates im Hintergrund
- [ ] Binary-Größe < 20 MB (Tauri-Vorteil gegenüber Electron)

**Technische Hinweise:** ADR-008 entscheidet Tauri statt Electron: kleinere Binary (~10 MB vs. ~150 MB), geringerer Speicherverbrauch, Rust-Backend für lokale Operationen. Desktop-App nutzt dasselbe Web-Frontend (WebView), nur der System-Layer ist Tauri/Rust.

---

#### TASK-136: Desktop-App – Offline-Modus mit lokalem Datensync

| Feld             | Wert                                       |
| ---------------- | ------------------------------------------ |
| **Priorität**    | P2                                         |
| **Bereich**      | Frontend / Backend                         |
| **Aufwand**      | XL                                         |
| **Status**       | 🔴 Offen                                   |
| **Quelle**       | D1 Designprinzip Offline-First, D2 Phase 3 |
| **Abhängig von** | TASK-135                                   |
| **Blockiert**    | –                                          |

**Beschreibung:** Offline-Modus für die Tauri-Desktop-App implementieren. Lokales SQLite als Offline-Vault für zuletzt abgerufene Briefings, Suchergebnisse und Entitäten. Sync-Mechanismus: Bei Internetverbindung werden lokale Daten mit dem Cloud-Backend synchronisiert. Obsidian-Vault-Zugriff funktioniert auch offline über den lokalen File-System-Watcher.

**Acceptance Criteria:**

- [ ] Letzte 7 Tage Briefings und Top-50 Entitäten werden lokal im SQLite-Vault gecacht
- [ ] Suche funktioniert offline gegen einen lokalen Embedding-Index (Sentence Transformers via Ollama)
- [ ] Sync-Status wird im UI angezeigt: "Online", "Offline – letzte Sync vor X Minuten"
- [ ] Obsidian-Vault-Watcher funktioniert offline; neue Dokumente werden bei Reconnect synchronisiert

**Technische Hinweise:** D1 OQ-005 identifiziert die Offline-Sync-Architektur als offene Frage: CRDT-basierter Sync oder Last-Write-Wins. Für den MVP des Offline-Modus ist Last-Write-Wins ausreichend; CRDT kann in Phase 4 evaluiert werden.

---

#### TASK-137: Pricing und Billing – Stripe-Integration und Abo-Verwaltung

| Feld             | Wert                  |
| ---------------- | --------------------- |
| **Priorität**    | P1                    |
| **Bereich**      | Backend / Frontend    |
| **Aufwand**      | L                     |
| **Status**       | 🔴 Offen              |
| **Quelle**       | D2 Phase 3            |
| **Abhängig von** | MVP-Basis (Agent 1–3) |
| **Blockiert**    | –                     |

**Beschreibung:** Stripe-Integration für Abonnement-Verwaltung implementieren. Zielkorridor 20–50 €/Monat. Stripe Checkout-Session für Erstabschluss, Customer Portal für Selbstverwaltung (Kündigung, Zahlungsart ändern). Webhook für Zahlungsstatus-Updates. Feature-Gating: Ohne aktives Abo eingeschränkter Zugriff (z.B. nur 1 Konnektor, keine Projektbriefings).

**Acceptance Criteria:**

- [ ] Stripe Checkout leitet Nutzer zum Zahlungsflow weiter und erstellt bei Erfolg ein Subscription-Objekt
- [ ] Webhook-Endpoint verarbeitet Stripe-Events (payment_succeeded, subscription_cancelled, payment_failed) idempotent
- [ ] Feature-Gating: Free-Tier (1 Konnektor, 3 Suchen/Tag), Paid-Tier (unbegrenzt) korrekt durchgesetzt
- [ ] Nutzer kann über Stripe Customer Portal Abo kündigen, Zahlungsmethode ändern und Rechnungen einsehen
- [ ] A/B-Testing-Infrastruktur: Verschiedene Preispunkte können pro Nutzerkohorte konfiguriert werden

**Technische Hinweise:** D2 Phase 3 definiert „Zielkorridor: 20–50 €/Monat" und erwähnt „A/B-Tests verschiedener Preispunkte". Stripe-Webhook-Signatur mit Signing Secret verifizieren (HMAC). Subscription-Status in PostgreSQL cachen, um nicht bei jedem Request Stripe zu befragen.

---

#### TASK-138: Erweiterte NER – Ziele, Risiken, Hypothesen und offene Fragen extrahieren

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P1                            |
| **Bereich**      | Backend                       |
| **Aufwand**      | L                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 2 |
| **Abhängig von** | MVP-Basis (Agent 1–3)         |
| **Blockiert**    | TASK-139                      |

**Beschreibung:** Die NER-Pipeline um zusätzliche Entitätstypen erweitern: Ziele, Risiken, Hypothesen und offene Fragen. LLM-basiertes Entity-Extraction-Prompt erweitern. Neue Entitätstypen in PostgreSQL, Weaviate und Neo4j persistieren. Graph-Schema um entsprechende Knoten-Labels und Kanten erweitern (GOAL, RISK, HYPOTHESIS, OPEN_QUESTION).

**Acceptance Criteria:**

- [ ] Entity-Extraction-Prompt extrahiert neben Personen/Projekten/Themen/Entscheidungen auch: Ziele, Risiken, Hypothesen, offene Fragen
- [ ] Neue Entitätstypen sind in der `entities`-Tabelle als entity_type gespeichert
- [ ] Neo4j-Graph enthält neue Knotentypen mit Kanten zu Projekten und Dokumenten
- [ ] Knowledge Explorer zeigt neue Entitätstypen als filterbare Kategorien an

**Technische Hinweise:** D3 Kernfunktion 2 fordert: „Automatische Extraktion von [...] Zielen, Risiken, offenen Fragen und Hypothesen." Das bestehende LLM-Prompt in `pwbs/prompts/entity_extraction.jinja2` muss um die neuen Kategorien erweitert werden. Konfidenz-Schwelle wie bei bestehender NER: > 0.75 für Graph-Aufnahme.

---

#### TASK-139: Mustererkennung – Wiederkehrende Themen und sich ändernde Annahmen

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P2                            |
| **Bereich**      | Backend                       |
| **Aufwand**      | L                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 2 |
| **Abhängig von** | TASK-138                      |
| **Blockiert**    | –                             |

**Beschreibung:** Mustererkennung über die im Knowledge Graph gespeicherten Entitäten implementieren. Erkennung von: wiederkehrende Themen (selbes Topic in > 3 verschiedenen Kontexten innerhalb von 30 Tagen), sich ändernde Annahmen (Hypothese wird in späterem Dokument widerlegt), ungelöste Muster (offene Frage wird wiederholt gestellt). Ergebnisse als Teil der Briefings und als dedizierte Insights-Seite bereitstellen.

**Acceptance Criteria:**

- [ ] Wöchentlicher Analyse-Job identifiziert wiederkehrende Themen über Neo4j-Graph-Traversals
- [ ] Sich ändernde Annahmen werden durch Vergleich von Hypothesen-Entitäten über Zeitverlauf erkannt
- [ ] Erkannte Muster werden in Morgenbriefings als „Muster im Blick"-Abschnitt integriert
- [ ] Insights-Endpunkt: GET `/api/v1/knowledge/patterns` liefert erkannte Muster mit Quellenreferenzen

**Technische Hinweise:** D3 beschreibt: „Erkennung von Mustern: Was wiederholt sich? Was wurde vergessen? Welche Annahmen ändern sich?" Graph-Queries nutzen zeitliche Co-Occurrence-Analyse und Kantengewichtung (D1 Abschnitt 3.3.3).

---

#### TASK-140: Browser-Extension-Prototyp für Kontextanzeige

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P3                           |
| **Bereich**      | Frontend                     |
| **Aufwand**      | M                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D2 Phase 3, D1 Phase-Mapping |
| **Abhängig von** | MVP-Basis (Agent 1–3)        |
| **Blockiert**    | –                            |

**Beschreibung:** Browser-Extension (Chrome/Firefox) als Prototyp entwickeln. Kontextuelle Sidebar, die beim Besuch von Notion-Seiten, Google Docs oder Gmail relevanten PWBS-Kontext einblendet. Quick-Search direkt aus der Extension. Authentifizierung über bestehenden JWT-Token (Session-Sharing mit Web-App).

**Acceptance Criteria:**

- [ ] Chrome-Extension installierbar und authentifiziert sich über gespeicherten JWT
- [ ] Sidebar zeigt relevante Entitäten und verknüpfte Dokumente basierend auf der aktuell besuchten Seite
- [ ] Quick-Search-Feld in der Extension löst semantische Suche über die PWBS-API aus
- [ ] Prototyp-Scope: Nur Chrome, nur Notion/Google Docs, keine Daten-Ingestion über Extension

**Technische Hinweise:** D1 Phase-Mapping listet Browser-Extension als „Prototyp" in Phase 3, „Extension" in Phase 4. D3 erwähnt Browser-History als potenzielle Datenquelle (nicht im Prototyp). Extension nutzt ausschließlich die bestehende Search-API.

---

#### TASK-141: Slack-Bot-Prototyp für Quick Search und Briefings

| Feld             | Wert                            |
| ---------------- | ------------------------------- |
| **Priorität**    | P3                              |
| **Bereich**      | Backend                         |
| **Aufwand**      | M                               |
| **Status**       | 🔴 Offen                        |
| **Quelle**       | D2 Phase 3, D1 Client Layer     |
| **Abhängig von** | TASK-125, MVP-Basis (Agent 1–3) |
| **Blockiert**    | –                               |

**Beschreibung:** Slack-Bot als Prototyp implementieren, der in Slack-Channels und DMs PWBS-Funktionalität bereitstellt. Slash-Commands: `/pwbs search <query>` für semantische Suche, `/pwbs briefing` für Abruf des aktuellen Morgenbriefings. Bot-Antworten mit Quellenreferenzen und Links zur PWBS-Web-App.

**Acceptance Criteria:**

- [ ] Slash-Command `/pwbs search <query>` führt semantische Suche aus und liefert Top-3-Ergebnisse mit Quellenangabe als Slack-Message
- [ ] Slash-Command `/pwbs briefing` liefert das aktuelle Morgenbriefing als formatierte Slack-Message
- [ ] Bot authentifiziert den Slack-User gegen den PWBS-Account (Mapping Slack-User-ID ↔ PWBS-User-ID)
- [ ] Rate-Limiting: Max. 10 Bot-Anfragen pro Nutzer pro Stunde

**Technische Hinweise:** D1 Client Layer zeigt Slack-Bot als Phase-3-Deliverable mit Funktionen „Context Sidebar" und „Quick Search". Der Bot nutzt die bestehende Search- und Briefing-API. Slack-Bot-Token separat von Connector-Token verwalten.

---

#### TASK-142: Notion-Sidebar-Prototyp

| Feld             | Wert                                   |
| ---------------- | -------------------------------------- |
| **Priorität**    | P3                                     |
| **Bereich**      | Frontend                               |
| **Aufwand**      | M                                      |
| **Status**       | 🔴 Offen                               |
| **Quelle**       | D2 Phase 3, D3 Technische Überlegungen |
| **Abhängig von** | MVP-Basis (Agent 1–3)                  |
| **Blockiert**    | –                                      |

**Beschreibung:** Notion-Integration als Sidebar-Prototyp evaluieren und implementieren. Da Notion keine native Sidebar-API bietet, wird dies als Browser-Extension-Feature realisiert: Wenn eine Notion-Seite im Browser geöffnet ist, zeigt die Extension eine Kontextleiste mit verknüpften Entitäten, verwandten Dokumenten und offenen Fragen zum aktuellen Notion-Thema.

**Acceptance Criteria:**

- [ ] Browser-Extension erkennt geöffnete Notion-Seiten und extrahiert den Seitentitel als Suchkontext
- [ ] Sidebar zeigt verknüpfte PWBS-Entitäten (Personen, Projekte, Entscheidungen) zur aktuellen Notion-Seite
- [ ] Verwandte Dokumente aus anderen Quellen (Zoom-Transkripte, Kalender) werden als Links angezeigt

**Technische Hinweise:** D3 erwähnt „Notion-Sidebar" unter Tool-Integrationen. Da Notion keine direkten Third-Party-Sidebars unterstützt, wird dies über die Browser-Extension (TASK-140) als Feature-Erweiterung realisiert.

---

#### TASK-143: Weekly Briefings implementieren

| Feld             | Wert                               |
| ---------------- | ---------------------------------- |
| **Priorität**    | P2                                 |
| **Bereich**      | Backend                            |
| **Aufwand**      | M                                  |
| **Status**       | 🔴 Offen                           |
| **Quelle**       | D1 Abschnitt 3.5, D1 Phase-Mapping |
| **Abhängig von** | MVP-Basis (Agent 1–3)              |
| **Blockiert**    | –                                  |

**Beschreibung:** Weekly Briefing als vierten Briefing-Typ implementieren. Automatische Generierung freitags 17:00 Uhr (Nutzer-Timezone). Wochenzusammenfassung: Wichtigste Themen, getroffene Entscheidungen, offene Punkte, Fortschritt pro Projekt. Max. 600 Wörter. Scheduler-Job und BriefingAgent-Template erweitern.

**Acceptance Criteria:**

- [ ] Scheduler triggert Weekly Briefing freitags gemäß Nutzer-Timezone
- [ ] Briefing enthält: Top-Themen der Woche, getroffene Entscheidungen, offene Punkte, Projektfortschritt – mit Quellenreferenzen
- [ ] Max. 600 Wörter, LLM-Temperatur 0.3
- [ ] Frontend: Weekly Briefing als eigener Tab in der Briefing-Übersicht abrufbar

**Technische Hinweise:** D1 Abschnitt 3.5 definiert `weekly_digest` mit Schedule `0 8 * * 1` (Montag 08:00). D2 Phase 3 fordert Weekly Briefings. AGENTS.md SchedulerAgent definiert `weekly_briefing` mit `cron "0 17 * * 5"` (Freitag 17:00). Hier Freitag 17:00 gemäß AGENTS.md verwenden.

---

## Phase 4 – Launch & Skalierung (Monate 16–21)

---

#### TASK-144: Multi-Tenancy – Team-Features und gemeinsames Wissensmodell

| Feld             | Wert                                 |
| ---------------- | ------------------------------------ |
| **Priorität**    | P1                                   |
| **Bereich**      | Backend / Frontend                   |
| **Aufwand**      | XL                                   |
| **Status**       | 🔴 Offen                             |
| **Quelle**       | D2 Phase 4, D1 Abschnitt 6.5         |
| **Abhängig von** | MVP-Basis (Agent 1–3), Phase 3-Tasks |
| **Blockiert**    | –                                    |

**Beschreibung:** Multi-Tenancy für Teams (3–10 Personen) implementieren. Gemeinsamer Weaviate-Tenant und Neo4j-Subgraph pro Organisation. Zugriffskontrolle: Owner, Member, Viewer. Private vs. Shared Entities. Onboarding-Unterstützung: Neue Teammitglieder erhalten automatisch relevanten Projektkontext. Wissensübergabe bei Rollenwechseln.

**Acceptance Criteria:**

- [ ] Organisationsmodell in PostgreSQL mit Rollenkonzept (Owner, Member, Viewer)
- [ ] Shared Knowledge Space: Team-Mitglieder teilen Weaviate-Tenant und Neo4j-Subgraph für als „team-sichtbar" markierte Entitäten
- [ ] Onboarding-Briefing: Neues Teammitglied erhält automatisch generiertes Briefing zum aktuellen Projektstand

**Technische Hinweise:** D1 Abschnitt 6.5 beschreibt die Isolation-Strategie: logische Isolation (Phase 3) → physische Isolation (Phase 4+ für Enterprise). D2 Phase 4 fordert Team-Features für 3–10 Personen mit gemeinsamer Wissensbasis.

---

#### TASK-145: Self-Hosting – Docker-Compose und Helm-Chart für On-Premise-Deployment

| Feld             | Wert                                                            |
| ---------------- | --------------------------------------------------------------- |
| **Priorität**    | P1                                                              |
| **Bereich**      | Infra / DevOps                                                  |
| **Aufwand**      | XL                                                              |
| **Status**       | 🔴 Offen                                                        |
| **Quelle**       | D1 Designprinzip Cloud+On-Premise, D2 Phase 4, D1 Abschnitt 5.3 |
| **Abhängig von** | MVP-Basis (Agent 1–3), Phase 3-Tasks                            |
| **Blockiert**    | –                                                               |

**Beschreibung:** Self-Hosting-Option für datenschutzsensible Nutzer und Enterprise-Kunden bereitstellen. Docker-Compose-Setup für einfaches lokales Deployment. Helm-Chart für Kubernetes-Deployment. Konfiguration für lokale LLM-Modelle (Ollama) statt Cloud-APIs. Vollständige Dokumentation für Installation, Konfiguration und Wartung.

**Acceptance Criteria:**

- [ ] `docker compose up` startet die komplette PWBS-Instanz (API, PostgreSQL, Weaviate, Neo4j, Redis) mit einem Befehl
- [ ] Helm-Chart ermöglicht Kubernetes-Deployment mit konfigurierbaren Replicas, Ressourcen und Persistenz
- [ ] LLM-Konfiguration: Umschaltung von Cloud-LLMs auf Ollama (lokal) über Umgebungsvariable

**Technische Hinweise:** D1 Designprinzip: „Self-Hosting ist ein Deployment-Profil, kein Fork." D1 Abschnitt 5.3 definiert On-Premise-Modus mit Docker-Compose auf kundeneigener Infrastruktur. Alle Secrets müssen über Umgebungsvariablen konfigurierbar sein.

---

#### TASK-146: Horizontale Skalierung – Load Balancer, Connection Pooling, Caching und CDN

| Feld             | Wert                       |
| ---------------- | -------------------------- |
| **Priorität**    | P1                         |
| **Bereich**      | Infra                      |
| **Aufwand**      | L                          |
| **Status**       | 🔴 Offen                   |
| **Quelle**       | D1 Abschnitt 6, D2 Phase 4 |
| **Abhängig von** | TASK-121, Phase 3-Tasks    |
| **Blockiert**    | –                          |

**Beschreibung:** Infrastruktur für horizontale Skalierung ausbauen. API-Server auf 3+ ECS-Tasks skalieren mit ALB. PgBouncer für PostgreSQL Connection Pooling. Redis-Cluster für verteiltes Caching. CDN (CloudFront) für statische Frontend-Assets. Read-Replicas für PostgreSQL. Weaviate-Cluster (2 Nodes) für Verfügbarkeit.

**Acceptance Criteria:**

- [ ] API skaliert horizontal auf 3+ Instanzen hinter ALB ohne Session-Abhängigkeit
- [ ] PgBouncer-Pool verwaltet PostgreSQL-Connections mit max. 50 Verbindungen pro Pool
- [ ] Redis-Cluster mit 2+ Nodes für Cache-Hochverfügbarkeit

**Technische Hinweise:** D1 Abschnitt 6.1 identifiziert Bottlenecks: Embedding-Generierung, LLM-Calls, Weaviate Search, Neo4j-Queries, PostgreSQL Writes. D1 Abschnitt 6.4 definiert die Caching-Strategie (API Response Cache, Search Cache, Embedding Cache, LLM Cache).

---

#### TASK-147: Sicherheitsaudit und DSGVO-Zertifizierung

| Feld             | Wert                                 |
| ---------------- | ------------------------------------ |
| **Priorität**    | P1                                   |
| **Bereich**      | Docs / Infra                         |
| **Aufwand**      | L                                    |
| **Status**       | 🔴 Offen                             |
| **Quelle**       | D2 Phase 4, D1 Abschnitt 5           |
| **Abhängig von** | MVP-Basis (Agent 1–3), Phase 3-Tasks |
| **Blockiert**    | TASK-148                             |

**Beschreibung:** Unabhängiges Sicherheitsaudit durch einen externen Dienstleister durchführen. DSGVO-Dokumentation vervollständigen: Technische und Organisatorische Maßnahmen (TOM), Verarbeitungsverzeichnis, Auftragsverarbeitungsverträge (AVV) mit allen Dienstleistern. Transparenzbericht zur Datennutzung veröffentlichen. Optional: DSGVO-Zertifizierung anstreben.

**Acceptance Criteria:**

- [ ] Externes Sicherheitsaudit durchgeführt; alle kritischen und hohen Findings geschlossen
- [ ] DSGVO-Dokumentation vollständig: TOM, Verarbeitungsverzeichnis, AVVs mit AWS/OpenAI/Anthropic/Vercel

**Technische Hinweise:** D1 Abschnitt 5.2 listet bestehende DSGVO-Maßnahmen. D2 Phase 4 fordert „Unabhängiges Sicherheitsaudit; DSGVO-Dokumentation und Zertifizierung; Transparenzbericht zur Datennutzung." AVVs sind in `/legal/avv/` zu dokumentieren.

---

#### TASK-148: Public Beta Infrastruktur und Community-Building

| Feld             | Wert          |
| ---------------- | ------------- |
| **Priorität**    | P2            |
| **Bereich**      | DevOps / Docs |
| **Aufwand**      | M             |
| **Status**       | 🔴 Offen      |
| **Quelle**       | D2 Phase 4    |
| **Abhängig von** | TASK-147      |
| **Blockiert**    | –             |

**Beschreibung:** Infrastruktur für die Public Beta vorbereiten: Skalierung auf 1.000–5.000 aktive Nutzer, Onboarding-Automatisierung, Content-Marketing-Pipeline (Blog, Docs, Tutorials). Community-Kanäle aufsetzen (Discord/Discourse). Monitoring-Dashboards für Wachstumsmetriken und Nutzerfeedback.

**Acceptance Criteria:**

- [ ] Infrastruktur skaliert nachweislich auf 1.000+ gleichzeitige Nutzer (Load-Test mit k6)
- [ ] Automatisierter Onboarding-Flow: Registrierung → erster Konnektor → erstes Briefing ohne manuelle Intervention
- [ ] Community-Plattform (Discord oder Discourse) eingerichtet mit Moderationsregeln und Feedback-Channel

**Technische Hinweise:** D2 Phase 4 beschreibt: „Public Beta mit gezieltem Marketing-Push (Content-Marketing, Community-Building, Partnerschaften mit Produktivitäts-Communities)." Ziel: 1.000–5.000 aktive Nutzer.

---

#### TASK-149: B2B-Pilot Features für Beratungshäuser und Tech-Startups

| Feld             | Wert               |
| ---------------- | ------------------ |
| **Priorität**    | P2                 |
| **Bereich**      | Backend / Frontend |
| **Aufwand**      | L                  |
| **Status**       | 🔴 Offen           |
| **Quelle**       | D2 Phase 4         |
| **Abhängig von** | TASK-144           |
| **Blockiert**    | –                  |

**Beschreibung:** B2B-spezifische Features für erste Pilotkunden implementieren. Admin-Dashboard für Organisations-Admins (Nutzerverwaltung, Konnektor-Konfiguration). Organisations-weite Konnektoren (ein Slack-Workspace für alle Mitglieder). SLA-konforme Uptime-Garantien. Angepasstes Onboarding für B2B-Kunden.

**Acceptance Criteria:**

- [ ] Admin-Dashboard: Organisationsadministratoren können Nutzer einladen, Rollen zuweisen und Konnektoren verwalten
- [ ] Organisations-weite Konnektoren: Ein Slack- oder Google-Workspace-Konnektor kann für alle Teammitglieder geteilt werden
- [ ] B2B-Onboarding-Wizard: Geführter Setup-Prozess für 3–10 Teammitglieder mit Konnektorauswahl und Rollenzuweisung

**Technische Hinweise:** D2 Phase 4: „Erste B2B-Piloten mit Beratungshäusern oder Tech-Startups." Ziel: ≥ 3 zahlende B2B-Pilotkunden. B2B-Features bauen auf der Multi-Tenancy-Grundlage (TASK-144) auf.

---

## Phase 5 – Plattform & Vertikalisierung (Monate 22–36)

---

#### TASK-150: Öffentliche API und Developer Portal

| Feld             | Wert            |
| ---------------- | --------------- |
| **Priorität**    | P1              |
| **Bereich**      | Backend / Docs  |
| **Aufwand**      | XL              |
| **Status**       | 🔴 Offen        |
| **Quelle**       | D2 Phase 5      |
| **Abhängig von** | Phase 3–4 Tasks |
| **Blockiert**    | TASK-151        |

**Beschreibung:** Öffentliche REST-API bereitstellen, über die externe Tools das Wissensmodell lesen und anreichern können. Developer Portal mit interaktiver API-Dokumentation (OpenAPI/Swagger), API-Key-Management, Rate-Limiting pro API-Key und Nutzungsstatistiken. Sandbox-Umgebung für Entwickler.

**Acceptance Criteria:**

- [ ] Öffentliche API v1 mit Endpunkten für Search, Entities, Briefings und Document-Ingestion (rate-limited)
- [ ] Developer Portal mit interaktiver API-Dokumentation, API-Key-Generierung und Nutzungs-Dashboard

**Technische Hinweise:** D2 Phase 5: „Offene API, über die externe Tools das Wissensmodell lesen und anreichern können." Die interne API (D1 Abschnitt 3.6) wird um öffentliche Endpunkte erweitert mit separatem Auth-Mechanismus (API-Keys statt JWT).

---

#### TASK-151: Marketplace für Community-Integrationen

| Feld             | Wert               |
| ---------------- | ------------------ |
| **Priorität**    | P2                 |
| **Bereich**      | Backend / Frontend |
| **Aufwand**      | XL                 |
| **Status**       | 🔴 Offen           |
| **Quelle**       | D2 Phase 5         |
| **Abhängig von** | TASK-150           |
| **Blockiert**    | –                  |

**Beschreibung:** Marketplace-Plattform für Community- und Drittanbieter-Integrationen aufbauen. Plugin-Architektur: Externe Entwickler können Konnektoren, Briefing-Templates und Processing-Schritte als Plugins bereitstellen. Review-Prozess für Sicherheit und Qualität. Installations- und Konfigurationsflow im Frontend.

**Acceptance Criteria:**

- [ ] Plugin-SDK mit Dokumentation für Connector-, Briefing-Template- und Processing-Plugins
- [ ] Marketplace-UI: Nutzer können Plugins durchsuchen, installieren und konfigurieren

**Technische Hinweise:** D2 Phase 5: „Marketplace-Ansatz für Community-Integrationen." Das Plugin-System baut auf dem bestehenden BaseConnector-Interface (D1 Abschnitt 3.1) und BriefingTemplate-Klasse auf. Plugins laufen sandboxed mit eingeschränkten Permissions.

---

#### TASK-152: Mobile Apps – iOS und Android

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P1                            |
| **Bereich**      | Mobile                        |
| **Aufwand**      | XL                            |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 5, D3 Kernfunktion 1 |
| **Abhängig von** | Phase 3–4 Tasks               |
| **Blockiert**    | –                             |

**Beschreibung:** Native oder Cross-Platform Mobile Apps für iOS und Android entwickeln. Kernfunktionen: Briefings lesen, semantische Suche, Schnellnotizen (Text + Sprache), Push-Notifications für Erinnerungen und neue Briefings. Offline-Caching für zuletzt abgerufene Briefings.

**Acceptance Criteria:**

- [ ] iOS- und Android-App im jeweiligen App Store veröffentlicht mit Briefing-Ansicht, Suche, Schnellnotizen und Push-Notifications
- [ ] Offline-Caching: Letzte 3 Briefings und Top-20 Entitäten sind offline verfügbar

**Technische Hinweise:** D2 Phase 5: „iOS- und Android-Applikationen für unterwegs (Schnellnotizen, Spracherfassung, Briefings)." D3 erwähnt „Optionale manuelle Erfassung über Sprache, Fotos, Schnellnotizen" als Datenerfassungsoption.

---

#### TASK-153: RBAC – Rollenbasierte Zugriffssteuerung auf Organisationsebene

| Feld             | Wert       |
| ---------------- | ---------- |
| **Priorität**    | P1         |
| **Bereich**      | Backend    |
| **Aufwand**      | L          |
| **Status**       | 🔴 Offen   |
| **Quelle**       | D2 Phase 5 |
| **Abhängig von** | TASK-144   |
| **Blockiert**    | –          |

**Beschreibung:** Rollenbasierte Zugriffssteuerung (RBAC) für Organisationen implementieren. Rollen: Admin, Manager, Member, Viewer. Permissions: Konnektoren verwalten, Nutzer einladen, Organisationsdaten lesen, Briefings generieren. Vererbbare Rollen auf Projektebene. Audit-Log für Rollenänderungen.

**Acceptance Criteria:**

- [ ] Rollenmodell mit mindestens 4 Rollen und granularen Permissions auf Organisations- und Projektebene
- [ ] Admin-UI für Rollenzuweisung und Permission-Übersicht pro Nutzer

**Technische Hinweise:** D2 Phase 5 fordert „Rollenbasierte Zugriffssteuerung" für „gemeinsame Entscheidungshistorie und Wissensübergabe auf Organisationsebene." Baut auf Multi-Tenancy (TASK-144) auf. Basis-Rollenmodell (Owner, Member, Viewer) aus TASK-144 wird um Manager-Rolle und granulare Permissions erweitert.

---

#### TASK-154: Vertikale Spezialisierungen – Forscher, Berater, Entwickler

| Feld             | Wert                                          |
| ---------------- | --------------------------------------------- |
| **Priorität**    | P2                                            |
| **Bereich**      | Backend / Frontend                            |
| **Aufwand**      | XL                                            |
| **Status**       | 🔴 Offen                                      |
| **Quelle**       | D2 Phase 5, D3 Zielgruppe und Anwendungsfälle |
| **Abhängig von** | Phase 3–4 Tasks                               |
| **Blockiert**    | –                                             |

**Beschreibung:** Angepasste Workflows und Wissensmodelle für drei vertikale Zielgruppen: Forscher (Literaturnachweise, Hypothesen-Tracking, Experiment-Verknüpfung), Berater (Kundenprojekte, Lessons Learned, Cross-Projekt-Muster), Entwickler (Architekturentscheidungen, technische Schulden, Code-Review-Verknüpfung). Vertikale Templates für Briefings und NER.

**Acceptance Criteria:**

- [ ] Mindestens 3 vertikale Profile mit spezialisierten Briefing-Templates und NER-Konfigurationen
- [ ] Nutzer kann ein vertikales Profil auswählen, das Briefing-Inhalte und Entity-Prioritäten anpasst

**Technische Hinweise:** D3 beschreibt als Anwendungsfälle: Forscher (Literaturnachweise, Hypothesen-Tracking), Berater (Kundenprojekte, Lessons Learned), Entwickler (Architekturentscheidungen, technische Schulden). D2 Phase 5 listet diese als „Vertikale Spezialisierungen."

---

#### TASK-155: Langzeit-Intelligenz – Muster über Monate/Jahre und Annahmen-Tracking

| Feld             | Wert                              |
| ---------------- | --------------------------------- |
| **Priorität**    | P2                                |
| **Bereich**      | Backend                           |
| **Aufwand**      | XL                                |
| **Status**       | 🔴 Offen                          |
| **Quelle**       | D2 Phase 5, D3 Langzeitgedächtnis |
| **Abhängig von** | TASK-139, Phase 3–4 Tasks         |
| **Blockiert**    | –                                 |

**Beschreibung:** Langzeit-Intelligenz als strategisches Alleinstellungsmerkmal ausbauen. Erkennung von Mustern über Monate und Jahre: strategische Themenverschiebungen, Entscheidungsqualität im Nachhinein, wiederkehrende Fehler. Annahmen-Tracking: Welche Hypothesen haben sich bestätigt, welche widerlegt? Proaktive Hinweise auf strategische Veränderungen. Jahres- und Quartals-Reviews.

**Acceptance Criteria:**

- [ ] Quartals-Review-Briefing: Automatisch generierte Zusammenfassung der wichtigsten Themen, Entscheidungen und Muster der letzten 3 Monate
- [ ] Annahmen-Tracker: Dashboard zeigt Hypothesen mit Status (bestätigt/widerlegt/offen) und Zeitverlauf

**Technische Hinweise:** D3 beschreibt als Alleinstellungsmerkmal: „Kontinuierliches Langzeitgedächtnis – nicht nur Suche, sondern dauerhaftes Verständnis über Monate und Jahre." D2 Phase 5: „Erkennung von Mustern über Monate und Jahre; Nachverfolgung, welche Annahmen sich als falsch herausgestellt haben." Baut auf Mustererkennung (TASK-139) auf.

---

## Offene Klärungspunkte

| ID    | Frage                                                                                                                                                                                                                                                             | Betroffene Tasks             | Quelle                                 | Priorität |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | -------------------------------------- | --------- |
| KP-01 | **Phasennummerierung inkonsistent zwischen D2 und D3:** D2 zählt 5 Phasen (Discovery, MVP, Private Beta, Launch, Plattform), D3 zählt 4 Phasen (MVP, Private Beta, Launch, Erweiterung+Plattform) mit abweichenden Monatsangaben. Welche Zählung ist verbindlich? | Alle Tasks                   | D2, D3                                 | P1        |
| KP-02 | **Gmail und Slack: MVP- oder Phase-3-Scope?** D1 Konnektor-Tabelle listet Gmail und Slack als MVP-Konnektoren mit vollständiger Spezifikation. D4 listet sie explizit unter "Out of Scope für MVP". Welches Dokument ist maßgeblich?                              | TASK-123–126                 | D1 Abschnitt 3.1, D4 Abschnitt 2       | P1        |
| KP-03 | **Embedding-Modell für Mehrsprachigkeit:** Reicht `text-embedding-3-small` (OpenAI) für deutschsprachige und gemischt DE/EN-Inhalte, oder wird ein dediziertes multilinguales Modell benötigt? Benchmark mit realen Nutzer-Daten fehlt.                           | TASK-138, alle Suche-Tasks   | D1 OQ-001, D4 OQ-01                    | P1        |
| KP-04 | **Offline-Sync-Architektur (Tauri):** Wie wird die Synchronisierung zwischen lokalem Offline-Vault (SQLite) und Cloud-Backend gelöst? CRDT-basierter Sync oder Last-Write-Wins? Conflict Resolution bei gleichzeitiger Offline-Bearbeitung?                       | TASK-136                     | D1 OQ-005                              | P2        |
| KP-05 | **Entity-Deduplizierung über Quellen hinweg:** "Thomas K." in Slack = "Thomas Kramer" im Kalender = "t.kramer@firma.de" in Gmail? E-Mail als Merge-Key allein reicht nicht. LLM-basiertes Entity Resolution ist teuer. Nutzerfeedback-Loop für Korrekturen?       | TASK-123–128, TASK-138       | D1 OQ-009, D4 OQ-05                    | P1        |
| KP-06 | **LLM-Kosten-Deckel und Pricing-Kalkulation:** Wie viele LLM-Calls fallen pro Nutzer/Tag an? Ist der Zielkorridor 20–50 €/Monat deckbar bei geschätzten 3–8 €/Nutzer/Monat LLM-Kosten? Proof-of-Cost fehlt.                                                       | TASK-137                     | D1 OQ-004, D2 Phase 3                  | P1        |
| KP-07 | **AVV mit LLM-Providern:** Reichen die Standard-DPAs von OpenAI und Anthropic, oder müssen individuelle AVVs nach Art. 28 DSGVO abgeschlossen werden? Ohne AVV: DSGVO-Verstoß möglich.                                                                            | TASK-147                     | D4 OQ-06                               | P1        |
| KP-08 | **Desktop-App-Framework:** D1 entscheidet Tauri (ADR-008), D3 erwähnt „Electron oder Tauri" als Alternative. Ist die Entscheidung für Tauri final oder soll Electron nochmals evaluiert werden?                                                                   | TASK-135, TASK-136           | D1 ADR-008, D3 Technische Überlegungen | P2        |
| KP-09 | **Backup und Disaster Recovery für Weaviate/Neo4j:** RPO/RTO-Ziele sind nicht definiert. Weaviate und Neo4j haben keine managed Backups wie RDS. Automatisierte Backup-Lösung muss vor Phase 4 stehen.                                                            | TASK-146                     | D1 OQ-010                              | P1        |
| KP-10 | **Rate-Limiting bei Initial Sync großer Datenquellen:** Was passiert bei Gmail-Initial-Sync mit 10.000+ E-Mails oder Notion-Workspace mit 1.000+ Seiten? LLM-Extraction-Budget (100 Calls/Nutzer/Tag) reicht nicht. Batch-Extraktion oder Backfill-Budget nötig?  | TASK-123, TASK-127, TASK-128 | D1 OQ-006, D4 OQ-07                    | P2        |
| KP-11 | **Browser-History als Datenquelle:** D3 Kernfunktion 1 erwähnt „Browser-History" als Integrationsquelle. D1 und D2 listen keinen Browser-History-Konnektor. Soll dies in Phase 3 als Teil der Browser-Extension umgesetzt werden oder komplett entfallen?         | TASK-140                     | D3 Kernfunktion 1                      | P3        |
| KP-12 | **Neo4j Community vs. Enterprise Edition:** Community Edition hat keine Cluster-Fähigkeit. Bei 500 Nutzern werden 2,5M–25M Knoten geschätzt. Reicht Community Edition bis Phase 4? Wann muss die Migration zur Enterprise Edition erfolgen?                       | TASK-146                     | D1 OQ-003                              | P2        |
| KP-13 | **Meeting-Transkripte ohne Zoom Pro:** Nutzer ohne Zoom-Pro-Abo haben keinen Zugang zu AI-Transkripten. Soll ein manueller Upload-Mechanismus als Fallback bereitgestellt werden? Betrifft auch Teams-Transkripte.                                                | TASK-127                     | D4 OQ-03                               | P2        |

---

## Gesamt-Backlog-Statistik (Vorlage für Merge)

| Teil       | Agent   | Phase                                     | Anzahl Tasks  | Aufwand geschätzt |
| ---------- | ------- | ----------------------------------------- | ------------- | ----------------- |
| Teil 1     | Agent 1 | Phase 1 + Infra/DB                        | _[eintragen]_ | _[eintragen]_     |
| Teil 2     | Agent 2 | Konnektoren + Processing + LLM + Briefing | _[eintragen]_ | _[eintragen]_     |
| Teil 3     | Agent 3 | API + Frontend + Auth + DSGVO + QA        | _[eintragen]_ | _[eintragen]_     |
| Teil 4     | Agent 4 | Phase 3–5                                 | 35            | 8×M, 13×L, 14×XL  |
| **Gesamt** |         |                                           |               |                   |

---

## Statistik Teil 4

Phase 3: 23 Tasks | Phase 4: 6 Tasks | Phase 5: 6 Tasks | Klärungspunkte: 13 | Gesamt Tasks: 35

<!-- AGENT_4_LAST: TASK-155 -->
