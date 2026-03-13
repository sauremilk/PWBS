---
applyTo: "pwbs/{connectors,ingestion,processing,briefing,search,graph,scheduler}/**/*.py"
---

# Agent-Instruktionen: KI-Agenten-Architektur im PWBS

## Agenten-Übersicht

Im PWBS gibt es sechs klar abgegrenzte Agenten-Rollen. Alle Agenten sind im MVP nicht autonom – sie werden von der API-Schicht oder dem Scheduler aufgerufen und geben Kontrolle nach jeder Aufgabe zurück.

```
IngestionAgent  →  ProcessingAgent  →  [GraphAgent, StorageLayer]
                                             ↓
BriefingAgent  ←  SearchAgent  ←  [Weaviate, Neo4j, PostgreSQL]
```

## IngestionAgent

**Zuständigkeit:** Datenquellen anbinden, Rohdaten abrufen, ins UDF normalisieren.

```python
class BaseAgent:
    """Basisklasse für alle PWBS-Agenten."""

    async def run(self, context: AgentContext) -> AgentResult:
        """Einstiegspunkt. Gibt immer AgentResult zurück."""
        ...

    async def on_error(self, error: PWBSError, context: AgentContext) -> AgentResult:
        """Fehlerbehandlung. Niemals Exception unkontrolliert propagieren."""
        ...
```

**Regeln für IngestionAgent:**

- Cursor/Watermark nach jedem erfolgreichen Batch persistieren.
- Partielle Erfolge sind akzeptabel – nicht den ganzen Batch verwerfen, wenn ein Dokument fehlschlägt.
- Exponential Backoff bei Rate-Limit-Fehlern (429, 503) der Quell-API.
- Max. Batch-Größe: 100 Dokumente pro Run.

## ProcessingAgent

**Zuständigkeit:** Chunking, Embedding-Generierung, NER, Graph-Befüllung.

**Regeln:**

- Chunking vor Embedding – niemals rohe lange Dokumente direkt embedden.
- Chunk-Strategie: Semantisches Chunking bevorzugen (128–512 Token, bei 32-Token-Überlappung).
- Embedding-Batching: Max. 64 Chunks pro Batch an Embedding-API.
- NER-Ergebnisse mit Konfidenz-Score speichern. Threshold: > 0.75 für Graph-Aufnahme.
- Graph-Befüllung idempotent: `MERGE` statt `CREATE` in Cypher-Queries.

## BriefingAgent

**Zuständigkeit:** Kontextbriefings generieren (morgens, pre-meeting, projekt).

**Typen:**
| Typ | Trigger | Max. Länge | Pflichtfeld |
|-----|---------|-----------|------------|
| `MorningBriefing` | Täglich 06:30 Uhr | 800 Wörter | `agenda_items`, `open_threads` |
| `MeetingBriefing` | 30 Min. vor Meeting | 400 Wörter | `attendees`, `last_status`, `open_questions` |
| `ProjectBriefing` | On-Demand | 1200 Wörter | `decisions`, `open_risks`, `next_steps` |

**Regeln:**

- Jede Briefing-Passage enthält `sources: list[SourceRef]` mit Verweis auf Original-Dokumente.
- Fakten ("Letztes Meeting war am 5.3.") von Interpretationen ("scheinbar wurde entschieden...") trennen.
- Structured Output für Briefing-Struktur (JSON-Schema), dann Rendering in Template.
- LLM-Temperatur: 0.3 für sachliche Briefings, 0.1 für strukturierte Daten.

## SearchAgent

**Zuständigkeit:** Semantische Suche, Hybrid-Suche, Antworten mit Quellenbelegen.

**Such-Modi:**

1. **Semantic:** Weaviate-Nearest-Neighbor über Embeddings.
2. **Keyword:** PostgreSQL Full-Text-Search mit `tsvector`.
3. **Hybrid:** Kombination aus 1+2 mit RRF-Fusion (Reciprocal Rank Fusion).
4. **Graph-Traversal:** Neo4j-Abfragen über Entitäts-Beziehungen.

**Regeln:**

- Suchergebnisse immer mit `score` und `source_ref` zurückgeben.
- Ergebnisse NIEMALS ohne `owner_id`-Filter abrufen.
- Top-K: Default 10, Maximum 50.
- Antwort-Generierung: Nur Inhalte aus Suchergebnissen verwenden (RAG), nie aus LLM-Vorwissen halluzinieren.

## GraphAgent

**Zuständigkeit:** Knowledge-Graph-Abfragen, Beziehungsanalysen, Mustererkennung.

**Graph-Schema (Neo4j):**

```cypher
// Kern-Entitäten
(:Person {id, name, email, owner_id})
(:Project {id, name, status, owner_id})
(:Decision {id, text, date, rationale, owner_id})
(:Document {id, source, source_id, owner_id})
(:Topic {id, name, owner_id})

// Kern-Relationen
(:Person)-[:MENTIONED_IN]->(:Document)
(:Decision)-[:MADE_IN]->(:Document)
(:Project)-[:DISCUSSED_IN]->(:Document)
(:Person)-[:INVOLVED_IN]->(:Project)
(:Decision)-[:RELATED_TO]->(:Topic)
```

**Regeln:**

- Alle Node-Creates als `MERGE` (Idempotenz).
- `owner_id` auf jedem Node als Pflichtproperty.
- Keine Graph-Queries ohne `WHERE n.owner_id = $owner_id`.

## SchedulerAgent

**Zuständigkeit:** Zeitgesteuerte Jobs verwalten.

**Job-Definitionen:**

```python
SCHEDULED_JOBS = [
    {"id": "morning_briefing", "cron": "30 6 * * *", "agent": "BriefingAgent"},
    {"id": "ingestion_cycle", "cron": "*/15 * * * *", "agent": "IngestionAgent"},
    {"id": "cleanup_expired", "cron": "0 3 * * *", "agent": "CleanupAgent"},
]
```

**Regeln:**

- Job-Ausführungen in DB persistieren (Start, Ende, Status, Fehler).
- Overlapping-Execution verhindern (Distributed Lock via Redis im MVP: einfaches DB-Flag).
- Fehlgeschlagene Jobs maximal 3× mit Backoff retry.
- Alerting bei 3 aufeinanderfolgenden Fehlern desselben Jobs.

---

## Reasoning-Anforderungen beim Agenten-Design (Claude Opus 4.6)

Bevor ein Agent implementiert oder geändert wird, folgende Analyse durchführen:

### 1. Ausführungspfad-Analyse

Den vollständigen Fluss end-to-end tracing:
```
Eingabe → Validierung → Verarbeitung → Nebeneffekte → Ausgabe → Fehlerfall → Cleanup
```
Für jeden Schritt: Was kann schiefgehen? Wie wird der Zustand bei Fehler konsistent gehalten?

### 2. Konkurrenz- und Race-Condition-Prüfung

- Kann der Scheduler denselben Job parallel zweimal starten?
- Greift der Ingestion-Cursor atomar auf den letzten Stand zu?
- Gibt es Shared-State zwischen Agenten, der Locking erfordert?

### 3. Downstream-Impact-Analyse

- Welche nachgelagerten Agenten konsumieren den Output?
- Was passiert, wenn der Output-Typ oder -Umfang sich verändert?
- Sind Consumers gegen `None`-Rückgaben oder Empty-Lists abgesichert?

### 4. DSGVO-Kontrollpfad

Für jede neue Datenstruktur, die ein Agent einführt:
- `owner_id` vorhanden? Referenziert auf `users.id` mit `CASCADE DELETE`?
- `expires_at` vorhanden und in der Cleanup-Pipeline berücksichtigt?
- Keine PII in Agent-Logs oder Fehlermeldungen?

### 5. Idempotenz-Garantie

Explizit nachweisen, dass ein Neustart des Agenten ohne Datenverlust oder Duplikate möglich ist:
- Cursors persistent und atomar gespeichert?
- Alle Writes als Upsert (nicht INSERT)?
- Verarbeitete Dokumente idempotent identifizierbar (via `source_id` + `owner_id`)?
