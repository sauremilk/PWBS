# PWBS – Backlog Teil 1: Phase 1, Setup & Infrastruktur

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
