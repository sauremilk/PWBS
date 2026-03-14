---
agent: agent
description: "Tiefenoptimierung der PWBS-Architektur. Analysiert Modul-Grenzen, Abhängigkeiten, Datenflüsse, Schichtentrennung und Skalierbarkeit – zustandsunabhängig und bei jeder Ausführung frisch."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Architektur-Optimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Analysiere die Architektur bei jeder Ausführung von Grund auf. Keine Annahmen über vorherige Reviews. Jede Abhängigkeit, jeder Datenfluss, jede Schichtgrenze wird neu geprüft.

> **Robustheitsregeln:**
>
> - Analysiere was **existiert**, nicht was geplant ist. Referenziere ARCHITECTURE.md nur zum Abgleich (Soll vs. Ist).
> - Leere Module oder Stubs sind keine Architektur-Fehler – sie sind offene Baustellen.
> - Bewerte Architektur relativ zum aktuellen Projektstand (MVP Phase 2), nicht nach Enterprise-Maßstäben.

---

## Phase 0: Architektur-Zustandserfassung (Extended Thinking)

### 0.1 Ist-Architektur kartieren

Lies den tatsächlichen Code und konstruiere die **reale** Architektur:

1. **Modul-Inventar:** Welche Module unter `pwbs/` existieren mit echtem Code (nicht nur `__init__.py`)?
2. **Abhängigkeitsgraph:** Welches Modul importiert was? Zeichne den Graph mental.
3. **Datenfluss:** Wie bewegen sich Daten tatsächlich durch das System? Stimmt es mit dem geplanten Flow überein?
4. **Schichtenmodell:** API → Service → Repository → Storage – wird es eingehalten?
5. **Agenten-Mapping:** Welche Agenten-Rollen existieren als Code, welche nur als Dokumentation?

### 0.2 Soll-Ist-Abgleich

Vergleiche die reale Architektur mit:

- `ARCHITECTURE.md`
- `AGENTS.md`
- `.github/instructions/agents.instructions.md`
- `.github/instructions/backend.instructions.md`

Dokumentiere jede Abweichung als Finding.

---

## Phase 1: Modul-Grenzen und Kopplung

### 1.1 Abhängigkeitsanalyse

Für jedes Modul-Paar:

```
pwbs/api/         → darf importieren: core, schemas, services
pwbs/connectors/  → darf importieren: core, models, storage
pwbs/ingestion/   → darf importieren: core, connectors, models
pwbs/processing/  → darf importieren: core, models, storage
pwbs/briefing/    → darf importieren: core, search, graph, prompts
pwbs/search/      → darf importieren: core, storage, models
pwbs/graph/       → darf importieren: core, storage, models
pwbs/scheduler/   → darf importieren: core, alle Agenten-Module
pwbs/storage/     → darf importieren: core, models
pwbs/core/        → darf importieren: NICHTS aus pwbs/ (Basis-Layer)
```

Prüfe:

- [ ] Keine Imports gegen die erlaubte Richtung (Dependency Inversion)
- [ ] Keine zirkulären Abhängigkeiten
- [ ] `pwbs/core/` importiert nichts aus anderen `pwbs/`-Modulen
- [ ] API-Layer greift nicht direkt auf Storage zu (muss durch Services/Agents)

### 1.2 Interface-Qualität

- [ ] Module kommunizieren über definierte Python-Interfaces/Protocols (nicht über HTTP im MVP)
- [ ] Interfaces sind schmal – nur die nötige Oberfläche exponieren
- [ ] Abhängigkeiten über Dependency Injection, nicht über direkte Instanziierung
- [ ] `BaseConnector`, `BaseAgent` etc. als abstrakte Basisklassen korrekt definiert

### 1.3 Kohäsion

Pro Modul bewerten:

- Gehört alles im Modul thematisch zusammen (hohe Kohäsion)?
- Gibt es Klassen/Funktionen, die besser in ein anderes Modul gehören?
- Gibt es ein Modul, das zu groß geworden ist und aufgeteilt werden sollte?

---

## Phase 2: Datenfluss-Analyse (Extended Thinking)

### 2.1 Primärer Datenfluss (Ingestion → Processing → Storage)

Verfolge den Weg eines Dokuments durch das System:

```
Externe Quelle → Connector.fetch_since() → RawDocument
  → Normalizer.normalize() → UnifiedDocument
    → Chunker.chunk() → list[Chunk]
      → Embedder.embed() → list[EmbeddedChunk]
        → NER.extract() → list[Entity]
          → GraphBuilder.merge() → Neo4j Nodes/Relations
            → VectorStore.upsert() → Weaviate
              → RelationalStore.upsert() → PostgreSQL
```

Prüfe an jeder Transition:

- [ ] Datenformat ist klar definiert (Pydantic-Modelle)
- [ ] Fehlerbehandlung: Was passiert, wenn ein Schritt fehlschlägt?
- [ ] Idempotenz: Kann der Schritt ohne Datenverlust wiederholt werden?
- [ ] Teilausfall: Was passiert, wenn Weaviate verfügbar aber Neo4j nicht?

### 2.2 Sekundärer Datenfluss (Search/Briefing → User)

```
User Query → SearchAgent.search()
  → Weaviate (Semantic) + PostgreSQL (Keyword) → RRF Fusion
    → GraphAgent.get_context() → Neo4j Kontext
      → BriefingAgent.generate() → LLM + Sources
        → API Response → Frontend
```

Prüfe:

- [ ] Alle Queries mit `owner_id`-Filter
- [ ] Quellenreferenzen durchgängig transportiert
- [ ] Graceful Degradation bei Teil-Ausfällen

### 2.3 Datenformat-Konsistenz

- [ ] UDF (UnifiedDocument) konsistent zwischen Modulen
- [ ] Keine impliziten Konvertierungen ohne Validierung
- [ ] Pydantic-Modelle als Single Source of Truth für Datenstrukturen

---

## Phase 3: Skalierbarkeits-Bewertung

### 3.1 Horizontal Scaling Readiness

- [ ] Stateless Processing (kein In-Memory-State zwischen Requests)
- [ ] DB-Connections über Connection Pools
- [ ] Keine File-System-Abhängigkeiten für Shared State
- [ ] Session-State in Redis/DB, nicht im Prozess

### 3.2 Bottleneck-Identifikation

Für aktuelle und geplante Last (10 → 100 → 1000 Nutzer):

| Komponente          | 10 User | 100 User | 1000 User | Bottleneck? |
| ------------------- | ------- | -------- | --------- | ----------- |
| PostgreSQL Queries  | ...     | ...      | ...       | ...         |
| Weaviate Embeddings | ...     | ...      | ...       | ...         |
| Neo4j Traversals    | ...     | ...      | ...       | ...         |
| LLM API Calls       | ...     | ...      | ...       | ...         |
| Ingestion Pipeline  | ...     | ...      | ...       | ...         |

### 3.3 Phase-3-Readiness

Bewerte, wie einfach der Übergang von modularem Monolith zu Service-Split wäre:

- [ ] Module haben klar definierte Eingänge und Ausgänge
- [ ] Keine Shared Mutable State zwischen Modulen
- [ ] Serialisierbare Nachrichten an Modul-Grenzen (Celery-Ready)

---

## Phase 4: Architektur-Anomalien

Suche nach Anti-Patterns:

- **God Class:** Eine Klasse, die zu viel Verantwortung hat
- **Feature Envy:** Code, der mehr mit fremden Modulen interagiert als mit dem eigenen
- **Shotgun Surgery:** Eine konzeptuelle Änderung erfordert Edits in > 3 Dateien
- **Leaky Abstraction:** Implementierungsdetails, die durch Interfaces durchsickern
- **Premature Optimization:** Über-Engineerte Lösungen für Probleme, die noch nicht existieren
- **Missing Abstraction:** Wiederholte Patterns ohne gemeinsame Basis

---

## Phase 5: Empfehlungen und Umsetzung

### Priorisierte Architektur-Optimierungen

| #   | Finding | Schwere  | Empfehlung | Betroffene Module |
| --- | ------- | -------- | ---------- | ----------------- |
| 1   | ...     | 🔴/🟡/🟢 | ...        | ...               |

### Für jedes 🔴-Finding:

1. **Ursache:** Warum existiert dieses Problem?
2. **Auswirkung:** Was passiert, wenn es nicht behoben wird?
3. **Fix:** Konkreter, vollständiger Lösungsansatz
4. **Migration:** Schrittweiser Plan ohne Breaking Changes

### ADR-Kandidaten

Für bedeutsame Architektur-Findings – erstelle einen ADR-Entwurf nach `docs/adr/000-template.md`.

---

## Opus 4.6 – Kognitive Verstärker

- **Systemdenken:** Betrachte das System als Ganzes – wie beeinflussen lokale Änderungen das Gesamtverhalten?
- **Kontrafaktische Analyse:** „Was wäre wenn" – Spiele alternative Architektur-Entscheidungen durch.
- **Temporale Analyse:** Welche Teile der Architektur waren für den aktuellen Stand richtig, werden aber in 6 Monaten zum Engpass?
- **Emergenz-Erkennung:** Welche Systemverhalten entstehen aus dem Zusammenspiel der Module, die in keinem einzelnen Modul geplant waren?
