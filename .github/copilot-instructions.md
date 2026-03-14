# GitHub Copilot – Workspace-Instruktionen: PWBS

---

## Modellkonfiguration: Claude Opus 4.6

Dieser Workspace ist für **Claude Opus 4.6** konfiguriert und optimiert. Das Modell verfügt über erweiterte Reasoning-Fähigkeiten, die gezielt eingesetzt werden sollen.

### Extended Thinking aktivieren bei

- Architekturentscheidungen mit Auswirkungen auf mehrere Module
- Komplexen Algorithmen oder Datenstrukturen (> 50 LOC)
- Debugging-Szenarien mit mehreren potenziellen Ursachen
- DSGVO- und Sicherheits-Audits mit Wechselwirkungen
- Performance-Optimierungen mit Trade-offs zwischen Latenz, Speicher und Konsistenz

### Pflicht-Denkmuster vor jeder Implementierung

1. **Verstehen:** Was ist das genaue Ziel? Welche Constraints gelten (DSGVO, Idempotenz, Typen)?
2. **Analysieren:** Welche anderen Module sind betroffen? Gibt es Breaking Changes?
3. **Abwägen:** Mindestens zwei Lösungsansätze skizzieren und begründet wählen.
4. **Implementieren:** Erst dann Code schreiben – vollständig, korrekt typisiert, ohne Platzhalter.
5. **Validieren:** Generierten Code intern auf Logikfehler, fehlende `owner_id`-Filter und nicht-idempotente Writes prüfen.

### Qualitätsstandard für Opus 4.6

- Keine `# TODO: implement`-Platzhalter – Methoden sind entweder vollständig oder explizit mit `raise NotImplementedError("...")` markiert.
- Alle Randfälle explizit behandeln (leere Listen, `None`-Werte, abgelaufene Tokens, DB-Fehler).
- Bei Unsicherheit: Mögliche Probleme **benennen**, nicht stillschweigend ignorieren.
- Sicherheitsimplikationen jeder neuen Funktion proaktiv im Code-Kommentar oder ADR erwähnen.

---

## Projektkontext

Das **Persönliche Wissens-Betriebssystem (PWBS)** ist eine kognitive Infrastruktur für Wissensarbeiter. Es ist kein klassisches SaaS-Dashboard, sondern eine aktive Denkebene, die heterogene persönliche Daten zusammenführt, semantisch durchdringt und im richtigen Moment kontextbezogen aufbereitet.

**Aktueller Stand:** Phase 2 – MVP (modularer Monolith)
**Entwicklungsprinzip:** Progressive Complexity – von klaren Modulen im MVP zum Service-Split in Phase 3

---

## Tech-Stack

| Schicht       | Technologie                                                              |
| ------------- | ------------------------------------------------------------------------ |
| Backend       | Python 3.12+, FastAPI, Pydantic v2                                       |
| Datenbanken   | PostgreSQL (relational), Weaviate (Vektorsuche), Neo4j (Knowledge Graph) |
| LLM           | Claude API (primär), GPT-4 (Fallback), Ollama (lokal/offline)            |
| Embeddings    | Sentence Transformers (lokal), OpenAI Ada (Cloud)                        |
| Frontend      | Next.js (App Router), React, TypeScript, Tailwind CSS                    |
| Infrastruktur | Docker Compose (lokal), Vercel (Frontend), AWS (Backend+DBs)             |
| Aufgabenqueue | Celery + Redis (Phase 3), direkte Verarbeitung im MVP                    |

---

## Architekturprinzipien (NICHT verletzen)

1. **DSGVO by Design:** Jedes Datum hat einen Owner, einen Zweck und ein Ablaufdatum. Verschlüsselung und Löschbarkeit sind Grundstruktur, keine Features. Niemals Nutzerdaten für externes LLM-Training verwenden.
2. **Erklärbarkeit:** Jede LLM-generierte Aussage muss Quellenreferenzen transportieren. Der Knowledge Graph ist die Audit-Schicht. Keine Halluzinationen ohne Kennzeichnung.
3. **Idempotenz:** Jeder Ingestion- und Processing-Schritt ist idempotent. Konnektoren verwenden Cursor/Watermarks. Pipeline muss ohne Datenverlust neu startbar sein.
4. **Modularität:** Konnektoren, Processing-Schritte und Storage-Backends sind austauschbar. Neue Datenquellen erfordern nur einen neuen Konnektor.
5. **Modularer Monolith:** Im MVP kommunizieren Module über Python-Interfaces, NICHT über HTTP. Service-Split erst in Phase 3.

---

## Code-Konventionen

### Python / Backend

- **Typing:** Immer vollständige Type Annotations verwenden (PEP 484/526). `Any` vermeiden.
- **Pydantic v2:** Für alle Datenmodelle und Konfigurationen. `model_validator` statt veralteten Patterns.
- **FastAPI:** Response-Objekte in Route-Signaturen als `Response` annotieren (nicht `Response | None`), vor Default-Parameter-Dependencies platzieren.
- **Fehlerbehandlung:** Eigene Exception-Klassen ableiten von `PWBSError`. HTTP-Fehler als `HTTPException` mit strukturiertem `detail`-Dict.
- **Async:** Konsequent `async def` für I/O-gebundene Operationen. Blocking Code in `asyncio.to_thread()` auslagern.
- **Imports:** Absolute Imports bevorzugen. Module-Struktur: `pwbs.connectors`, `pwbs.processing`, `pwbs.storage`, `pwbs.briefing`, `pwbs.api`.
- **Tests:** pytest + pytest-asyncio. Fixtures für alle externen Abhängigkeiten (DBs, LLM). Kein echter Netzwerkzugriff in Unit-Tests.

### TypeScript / Frontend

- **Strict Mode:** `tsconfig.json` mit `"strict": true`. Keine impliziten `any`.
- **Komponenten:** Funktionale Komponenten mit expliziten Props-Interfaces. Server/Client-Boundary klar markieren (`"use client"` nur wenn nötig).
- **State:** Zustand-Server-First (Next.js Server Components). Client-State minimal halten.
- **API-Calls:** Immer über `/src/lib/api/` abstrahieren. Niemals direkte `fetch()`-Aufrufe in Komponenten.

---

## Sicherheitsanforderungen

- **Keine Secrets im Code:** API-Keys, DB-Passwörter etc. über Umgebungsvariablen (`.env`, nie committen).
- **Input-Validierung:** Alle externen Eingaben (Webhook-Payloads, API-Requests) mit Pydantic validieren.
- **Nutzer-Datentrennung:** Mandanten-Isolation auf Datenbankebene. Jede Query muss `owner_id` als Filter enthalten (`user_id` aus JWT → `owner_id` in DB).
- **OAuth:** Token-Rotation implementieren. Refresh-Tokens verschlüsselt in DB speichern.
- **Rate Limiting:** Auf allen öffentlichen API-Endpunkten. LLM-Calls absichern gegen Missbrauch.

---

## Datenmodell (Unified Document Format – UDF)

Jedes ingested Dokument wird ins UDF normalisiert:

```python
class UnifiedDocument(BaseModel):
    id: UUID
    owner_id: UUID
    source: SourceType          # z.B. "google_calendar", "notion", "zoom_transcript"
    source_id: str              # Original-ID in der Quell-App
    content: str                # Normalisierter Textinhalt
    metadata: dict[str, Any]    # Source-spezifische Metadaten
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None  # DSGVO: Ablaufdatum
    embedding: list[float] | None
    entities: list[Entity] | None
```

---

## Agent-Rollen im System

Folgende KI-Agenten-Rollen existieren im PWBS. Beim Entwickeln neuer Features prüfen, welche Agenten-Rolle zuständig ist:

| Agent               | Verantwortlichkeit                                             | Primäre Module                      |
| ------------------- | -------------------------------------------------------------- | ----------------------------------- |
| **IngestionAgent**  | Datenquellen anbinden, Rohdaten abrufen, ins UDF normalisieren | `pwbs.connectors`, `pwbs.ingestion` |
| **ProcessingAgent** | Chunking, Embedding, NER, Graph-Befüllung                      | `pwbs.processing`                   |
| **BriefingAgent**   | Kontextbriefings generieren (morgens, pre-meeting, projekt)    | `pwbs.briefing`                     |
| **SearchAgent**     | Semantische Suche, Hybrid-Suche, Antworten mit Quellenbelegen  | `pwbs.search`                       |
| **GraphAgent**      | Knowledge-Graph-Abfragen, Beziehungsanalysen, Mustererkennung  | `pwbs.graph`                        |
| **SchedulerAgent**  | Zeitgesteuerte Jobs (Ingestion-Zyklen, Briefing-Generierung)   | `pwbs.scheduler`                    |

---

## Entwicklungs-Workflow

1. **Neue Konnektoren:** Basisklasse `BaseConnector` implementieren. Cursor-basierte Pagination zwingend.
2. **Neue Briefing-Typen:** `BriefingTemplate` ableiten. Immer mit Quellenreferenzen ausstatten.
3. **Schema-Änderungen:** Alembic-Migration erstellen. Niemals Schema direkt mutieren.
4. **LLM-Prompts:** In `pwbs/prompts/` als separate Dateien versionieren. Prompt-Engineering mit Structured Output (JSON-Schema).
5. **ADR:** Architekturentscheidungen in `docs/adr/` dokumentieren (Vorlage: `docs/adr/000-template.md`).
