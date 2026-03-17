# AGENTS.md – KI-Agenten-Orchestrierung im PWBS

Dieses Dokument definiert die Agenten-Architektur des PWBS und gibt KI-Assistenten (GitHub Copilot, Claude, GPT-4) klare Anweisungen, wie sie beim Entwickeln an diesem System denken und arbeiten sollen.

---

## Wie KI-Assistenten dieses Projekt unterstützen

Wenn du als KI-Assistent an diesem Projekt arbeitest, halte folgende Prinzipien ein:

1. **Lies zuerst, schreib dann.** Verstehe den bestehenden Code, bevor du Änderungen vorschlägst.
2. **Respektiere die Modul-Grenzen.** Im MVP kommunizieren Module über Python-Interfaces, NICHT über HTTP.
3. **DSGVO first.** Jede neue Datenstruktur braucht `owner_id`, `expires_at` und muss löschbar sein.
4. **Idempotenz erzwingen.** Neue Writes in DB immer als Upsert, nicht blindes INSERT.
5. **Erklärbarkeit.** Jede LLM-Ausgabe im System braucht `sources: list[SourceRef]`.
6. **Denken vor Implementieren.** Bei komplexen Aufgaben erst Implikationen und Alternativen durchdenken (Extended Thinking), dann implementieren.
7. **Vollständigkeit.** Keine Platzhalter-Implementierungen – Methoden sind vollständig oder mit `raise NotImplementedError("...")` explizit markiert.
8. **MVP-Scope einhalten.** Nur aktive Module und Kern-4-Konnektoren bearbeiten. Deaktivierte Module in `_deferred/` NICHT importieren, referenzieren oder weiterentwickeln. Siehe `copilot-instructions.md` → "MVP-Fokussierung (ADR-016)".
9. **Neo4j ist optional.** `get_neo4j_driver()` kann `None` zurückgeben. Jeder Code der Neo4j nutzt, MUSS mit `driver is None` umgehen können. `NullGraphService`-Fallbacks verwenden.

### Opus 4.6 Verhaltensregeln (Anthropic Best Practices)

Die folgenden Regeln sind spezifisch für Claude Opus 4.6 optimiert:

10. **Implementieren statt Vorschlagen.** Bei unklarer Absicht die wahrscheinlichste nützliche Aktion ableiten und ausführen. Tools nutzen um fehlende Details zu ermitteln, nicht raten.

11. **Neutrale Tool-Sprache.** Aggressive Formulierungen ("CRITICAL", "MUST", "ALWAYS") vermeiden – sie führen bei Opus 4.6 zu Overtriggering. Einfach: "Use this tool when..." genügt.

12. **Parallele Tool-Calls.** Unabhängige Tool-Aufrufe parallel ausführen (z.B. 3 Dateien gleichzeitig lesen). Bei Abhängigkeiten: sequentiell, niemals mit geratenen Parametern.

13. **Sichere Autonomie.** Lokale, reversible Aktionen (Edits, Tests, Commits) ohne Rückfrage. Destruktive/externe Aktionen (push --force, delete, PR-Comments) nur nach Bestätigung.

14. **Halluzinations-Prävention.** Dateien LESEN bevor über ihren Inhalt gesprochen wird. Keine Spekulation über nicht-geöffneten Code.

15. **Overengineering verhindern.** Nur angeforderte Änderungen. Keine zusätzlichen Features, unnötigen Abstraktionen oder "Future-Proofing". Minimale Komplexität für die aktuelle Aufgabe.

Vollständige Dokumentation: `.github/instructions/opus-4.6-behavior.instructions.md`

---

## Agenten-Rollen (System-interne KI-Agenten)

### IngestionAgent

**Primäres Modul:** `pwbs/connectors/`, `pwbs/ingestion/`

> **⚠️ MVP-Scope (ADR-016):** Im MVP nur die **Kern-4-Konnektoren** aktiv: Google Calendar, Notion, Zoom, Obsidian. Phase-3-Konnektoren (Gmail, Slack, Google Docs, Outlook) liegen in `backend/_deferred/connectors/` und werden NICHT importiert oder weiterentwickelt.

```
Aufgaben:
  - Datenquellen via OAuth/API anbinden
  - Rohdaten cursor-basiert abrufen (Watermarking)
  - Ins Unified Document Format (UDF) normalisieren
  - Cursor nach erfolgreichem Batch persistieren

Wird aufgerufen von:
  - SchedulerAgent (alle 15 Minuten)
  - API-Endpunkt POST /api/connectors/{id}/sync (manuell)

Output:
  - list[UnifiedDocument] → ProcessingAgent
```

### ProcessingAgent

**Primäres Modul:** `pwbs/processing/`

```
Aufgaben:
  - Chunking (semantisch, 128-512 Token, 32 Token Überlappung)
  - Embedding-Generierung (Batch-Größe 64)
  - NER (Extraktion von Personen, Projekten, Entscheidungen)
  - Graph-Befüllung (MERGE in Neo4j)
  - Weaviate-Indexierung (Upsert nach source_id)

Wird aufgerufen von:
  - IngestionAgent (nach UDF-Normalisierung)
  - SchedulerAgent (Reprocessing bei Modell-Updates)

Input:  list[UnifiedDocument]
Output: list[ProcessedDocument] mit Embeddings + Entities
```

### BriefingAgent

**Primäres Modul:** `pwbs/briefing/`

```
Briefing-Typen:
  - MorningBriefing    → täglich 06:30, max. 800 Wörter
  - MeetingBriefing    → 30 Min. vor Meeting, max. 400 Wörter
  - ProjectBriefing    → on-demand, max. 1200 Wörter
  - WeeklyBriefing     → freitags 17:00, max. 600 Wörter

Prozess:
  1. SearchAgent aufrufen (relevante Dokumente abrufen)
  2. GraphAgent aufrufen (Beziehungen und Kontext) – ⚠️ MVP: gibt leere Ergebnisse zurück wenn Neo4j unavailable
  3. LLM-Aufruf via LLMGateway (Structured Output)
  4. Quellenreferenzen aus Suchergebnissen verknüpfen
  5. Briefing persistieren + an Frontend ausliefern

Regeln:
  - Niemals ohne Quellenreferenzen ausliefern
  - LLM-Temperatur: 0.3 (sachliche Inhalte)
  - Kein LLM-Vorwissen verwenden (nur RAG)
```

### SearchAgent

**Primäres Modul:** `pwbs/search/`

```
Such-Modi:
  1. Semantic    → Weaviate Nearest-Neighbor
  2. Keyword     → PostgreSQL tsvector
  3. Hybrid      → RRF-Fusion (Reciprocal Rank Fusion)
  4. Graph       → Neo4j Traversal (⚠️ MVP: optional, Fallback auf leere Resultmenge)

API:
  search(
    query: str,
    owner_id: UUID,
    mode: SearchMode = "hybrid",
    top_k: int = 10,          # Max: 50
    filters: SearchFilters | None = None
  ) -> list[SearchResult]

Sicherheit:
  - owner_id IMMER als Filter – keine Cross-User-Ergebnisse möglich
```

### GraphAgent

**Primäres Modul:** `pwbs/graph/`

> **⚠️ MVP-Scope (ADR-016):** Neo4j ist im MVP **optional**. `get_neo4j_driver()` gibt `None` zurück, wenn Neo4j nicht erreichbar ist. Alle GraphAgent-Operationen MÜSSEN mit `driver is None` umgehen können und `NullGraphService`-Fallbacks nutzen. Docker Compose startet Neo4j nur mit `--profile graph`.

```
Graph-Schema (Neo4j):
  Nodes:    Person, Project, Decision, Document, Topic, Entity
  Relations: MENTIONED_IN, MADE_IN, DISCUSSED_IN, INVOLVED_IN, RELATED_TO

Operationen:
  - get_context(entity_id, depth=2) → Nachbarknoten bis Tiefe 2
  - find_patterns(owner_id) → Wiederkehrende Themen, Entscheidungsmuster
  - get_project_history(project_name, owner_id) → Timeline + Decisions

Pflicht:
  - Alle Queries mit WHERE n.owner_id = $owner_id
  - MERGE statt CREATE (Idempotenz)
  - Graceful Degradation: Operationen geben leere Ergebnisse zurück wenn Neo4j unavailable
```

### SchedulerAgent

**Primäres Modul:** `pwbs/scheduler/`

```
Jobs:
  morning_briefing:  cron "30 6 * * *"    → BriefingAgent.generate(type=morning)
  ingestion_cycle:   cron "*/15 * * * *"  → IngestionAgent.run_all_connectors()
  cleanup_expired:   cron "0 3 * * *"     → CleanupAgent.delete_expired()
  weekly_briefing:   cron "0 17 * * 5"    → BriefingAgent.generate(type=weekly)

Fehlerbehandlung:
  - Max. 3 Retries mit Exponential Backoff (1min → 5min → 25min)
  - Alert nach 3 aufeinanderfolgenden Fehlern
  - Job-Ausführungen in scheduled_job_runs persistieren
```

---

## Agenten-Kommunikation (MVP)

Im MVP (Phase 2) kommunizieren Agenten **nicht über HTTP**, sondern über direkte Python-Methodenaufrufe:

```python
# Korrekt (MVP):
ingestion_result = await ingestion_agent.run(context)
processing_result = await processing_agent.process(ingestion_result.documents)

# Falsch (erst ab Phase 3):
response = await httpx.post("/api/internal/process", json=...)
```

Ab Phase 3 werden Agenten über eine Message-Queue (Celery + Redis) orchestriert.

---

## Entscheidungsbaum: Welcher Agent ist zuständig?

```
Neue Datenquelle anbinden?          → IngestionAgent + neuer Konnektor
Embeddings/Index veraltet?          → ProcessingAgent (Reprocessing-Job)
Briefing generieren?                → BriefingAgent (ruft Search + Graph auf)
Nutzer stellt eine Frage?           → SearchAgent → BriefingAgent für Antwort
Beziehungen analysieren?            → GraphAgent
Zeitgesteuerte Aufgabe hinzufügen?  → SchedulerAgent
```

---

## Prompt-Files (Wiederverwendbare KI-Workflows)

### Kern-Workflows

| Datei                                        | Verwendung                                               |
| -------------------------------------------- | -------------------------------------------------------- |
| `.github/prompts/new-connector.prompt.md`    | Neuen Datenquellen-Konnektor implementieren              |
| `.github/prompts/scaffold-feature.prompt.md` | Feature-Scaffolding: Backend, Frontend, Tests generieren |
| `.github/prompts/deep-analysis.prompt.md`    | Tiefenanalyse: Debugging, Architektur, Performance       |
| `.github/prompts/db-migration.prompt.md`     | Alembic-Migration erstellen                              |
| `.github/prompts/debug-agent.prompt.md`      | Agenten-Fehler diagnostizieren                           |

### Orchestrierung

| Datei                                         | Verwendung                                                         |
| --------------------------------------------- | ------------------------------------------------------------------ |
| `.github/prompts/orchestrator-init.prompt.md` | Parallele Orchestrator-Session initialisieren (Claim → Implement)  |
| `.github/prompts/task-executor.prompt.md`     | Einzelnen Task vollständig durchführen (Implement → Test → Commit) |
| `.github/prompts/expand-backlog.prompt.md`    | Task-Backlog erweitern und vertiefen                               |

### Audit-Suite (parametrisiert)

| Datei                                          | Verwendung                                                                                                                                 |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `.github/prompts/audit-workspace.prompt.md`    | Meta-Orchestrator: Ganzheitliche Workspace-Analyse mit Roadmap                                                                             |
| `.github/prompts/audit-domain.prompt.md`       | Domain-Audit: security, architecture, code-quality, testing, documentation, infrastructure, performance, dependencies, monitoring, prompts |
| `.github/prompts/audit-architecture.prompt.md` | Modul-Grenzen, Datenfluss, Skalierbarkeit, Anti-Patterns                                                                                   |

---

## Instruction-Files (Automatisch angewendete Kontextregeln)

| Datei                                           | Gilt für                                          |
| ----------------------------------------------- | ------------------------------------------------- |
| `.github/instructions/backend.instructions.md`  | `**/*.py`                                         |
| `.github/instructions/frontend.instructions.md` | `frontend/**/*.{ts,tsx}`                          |
| `.github/instructions/security.instructions.md` | `**/*.{py,ts,tsx}`                                |
| `.github/instructions/agents.instructions.md`   | `backend/pwbs/{connectors,ingestion,...}/**/*.py` |
| `.github/instructions/audit.instructions.md`    | Audit-Workflows (gemeinsame Konventionen)         |

---

## Entwicklungsumgebung starten

```bash
# Alle Services (PostgreSQL, Weaviate, Neo4j, Redis) starten
docker compose up -d

# Backend starten (hot-reload)
cd backend && uvicorn pwbs.api.main:app --reload

# Frontend starten
cd frontend && npm run dev

# Tests ausführen
cd backend && pytest tests/unit/ -v
cd backend && pytest tests/integration/ -v --docker  # benötigt laufende DBs
```

---

## ADR-Verzeichnis

Architekturentscheidungen werden in `docs/adr/` dokumentiert (Vorlage: `docs/adr/000-template.md`).
Vor jeder bedeutenden Architekturentscheidung ein ADR erstellen.
