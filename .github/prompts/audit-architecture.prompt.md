---
agent: agent
description: "Architektur-Audit: Vollständige Prüfung der Systemarchitektur gegen PWBS-Prinzipien. Soll-Ist-Abgleich, Abhängigkeitsanalyse, Datenflüsse, Schichtentrennung."
tools:
  - codebase
  - editFiles
  - problems
---

# Architektur-Audit

Du führst ein vollständiges Architektur-Audit für das PWBS durch.

**Scope:** ${input:scope:Modulpfad (z.B. "pwbs/connectors/") oder "all" für Gesamtsystem}

---

## Phase 0: Ist-Architektur kartieren (Extended Thinking)

Bevor du analysierst, konstruiere die **reale** Architektur aus dem Code:

### 0.1 Modul-Inventar

```
pwbs/
├── api/            [?] Existiert / Implementiert / Stub
├── connectors/     [?] ...
├── ingestion/      [?] ...
├── processing/     [?] ...
├── storage/        [?] ...
├── briefing/       [?] ...
├── search/         [?] ...
├── graph/          [?] ...
├── scheduler/      [?] ...
├── core/           [?] ...
└── models/         [?] ...
```

Für jedes Modul:

- Existiert mit echtem Code (nicht nur `__init__.py`)?
- Welche Klassen/Funktionen werden exportiert?
- Welche Abhängigkeiten hat es?

### 0.2 Abhängigkeitsgraph konstruieren

```
[Modul A] ──imports──> [Modul B]
[Modul B] ──imports──> [Modul C]
...
```

Identifiziere:

- Legitime Abhängigkeiten (entsprechend Schichtenmodell)
- Fragwürdige Abhängigkeiten (potenzielle Verletzungen)
- Zirkuläre Abhängigkeiten

### 0.3 Soll-Ist-Vergleich

Lies ARCHITECTURE.md und AGENTS.md, dann vergleiche:

| Aspekt         | Dokumentiert | Implementiert | Abweichung |
| -------------- | ------------ | ------------- | ---------- |
| Module         |              |               |            |
| Datenfluss     |              |               |            |
| Agenten-Rollen |              |               |            |
| Schichten      |              |               |            |

---

## Phase 1: Architekturprinzipien prüfen

### 1.1 DSGVO by Design

- [ ] Jedes Datenmodell hat `owner_id: UUID`
- [ ] Nutzerdaten haben `expires_at: datetime | None`
- [ ] Jede DB-Query enthält `WHERE owner_id = ...`
- [ ] Keine PII in Logs
- [ ] Löschkaskade (`ON DELETE CASCADE`) implementiert
- [ ] Kein LLM-Training mit Nutzerdaten

### 1.2 Erklärbarkeit

- [ ] LLM-Outputs enthalten immer `sources: list[SourceRef]`
- [ ] Fakten und Interpretationen sind trennbar
- [ ] Keine stillen Halluzinationen (ohne Kennzeichnung)

### 1.3 Idempotenz

- [ ] Alle DB-Writes als UPSERT (`ON CONFLICT DO UPDATE`)
- [ ] Weaviate: `source_id` + `owner_id` als Dedup-Schlüssel
- [ ] Neo4j: `MERGE` statt `CREATE`
- [ ] Cursor/Watermark nach erfolgreichem Batch persistiert
- [ ] Pipeline kann ohne Datenverlust neu gestartet werden

### 1.4 Modularität

- [ ] Keine zirkulären Imports zwischen Modulen
- [ ] Module kommunizieren über Python-Interfaces (kein HTTP im MVP)
- [ ] Abhängigkeiten über Dependency Injection
- [ ] `BaseConnector`, `BaseAgent` als abstrakte Basisklassen

---

## Phase 2: Modul-Grenzen und Kopplung

### 2.1 Erlaubte Import-Richtungen

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

Prüfe für jedes Modul:

- [ ] Keine Imports gegen erlaubte Richtung (Dependency Inversion)
- [ ] `pwbs/core/` importiert nichts aus anderen `pwbs/`-Modulen
- [ ] API-Layer greift nicht direkt auf Storage zu (muss durch Services/Agents)

### 2.2 Interface-Qualität

- [ ] Interfaces sind schmal – nur nötige Oberfläche exponiert
- [ ] Keine Implementierungsdetails durchsickern (Leaky Abstraction)
- [ ] Protokoll-Klassen (`Protocol`) wo sinnvoll

### 2.3 Kohäsion

Pro Modul bewerten:

- Gehört alles thematisch zusammen (hohe Kohäsion)?
- Gibt es Klassen/Funktionen, die besser in ein anderes Modul gehören?
- Ist das Modul zu groß und sollte aufgeteilt werden?

---

## Phase 3: Datenfluss-Analyse

### 3.1 Primärer Datenfluss (Ingestion → Storage)

```
Externe Quelle
  → Connector.fetch_since()
    → RawDocument
      → Normalizer.normalize()
        → UnifiedDocument
          → Chunker.chunk()
            → list[Chunk]
              → Embedder.embed()
                → list[EmbeddedChunk]
                  → NER.extract()
                    → list[Entity]
                      → GraphBuilder.merge() → Neo4j
                      → VectorStore.upsert() → Weaviate
                      → RelationalStore.upsert() → PostgreSQL
```

An jeder Transition prüfen:

- [ ] Datenformat klar definiert (Pydantic-Modelle)
- [ ] Fehlerbehandlung: Was passiert bei Fehlschlag?
- [ ] Idempotenz: Kann der Schritt wiederholt werden?
- [ ] Teilausfall: Was wenn Weaviate verfügbar, Neo4j nicht?

### 3.2 Sekundärer Datenfluss (Search → User)

```
User Query
  → SearchAgent.search()
    → Weaviate (Semantic) + PostgreSQL (Keyword)
      → RRF Fusion
        → GraphAgent.get_context() → Neo4j Kontext (optional)
          → BriefingAgent.generate()
            → LLM + Sources
              → API Response → Frontend
```

Prüfen:

- [ ] Alle Queries mit `owner_id`-Filter
- [ ] Quellenreferenzen durchgängig transportiert
- [ ] Graceful Degradation bei Teil-Ausfällen (Neo4j optional!)

### 3.3 Datenformat-Konsistenz

- [ ] UDF (UnifiedDocument) konsistent zwischen Modulen
- [ ] Keine impliziten Konvertierungen ohne Validierung
- [ ] Pydantic-Modelle als Single Source of Truth

---

## Phase 4: Skalierbarkeits-Bewertung

### 4.1 Horizontal Scaling Readiness

- [ ] Stateless Processing (kein In-Memory-State zwischen Requests)
- [ ] DB-Connections über Connection Pools
- [ ] Keine File-System-Abhängigkeiten für Shared State
- [ ] Session-State in Redis/DB, nicht im Prozess

### 4.2 Bottleneck-Identifikation

| Komponente | 10 User | 100 User | 1000 User | Potentieller Bottleneck |
| ---------- | ------- | -------- | --------- | ----------------------- |
| PostgreSQL |         |          |           |                         |
| Weaviate   |         |          |           |                         |
| Neo4j      |         |          |           |                         |
| LLM API    |         |          |           |                         |
| Ingestion  |         |          |           |                         |

### 4.3 Phase-3-Readiness (Service-Split)

Bewerte, wie einfach der Übergang von modularem Monolith zu Services wäre:

- [ ] Module haben klar definierte Ein-/Ausgänge
- [ ] Keine Shared Mutable State zwischen Modulen
- [ ] Serialisierbare Nachrichten an Modul-Grenzen (Celery-Ready)

---

## Phase 5: Anti-Patterns suchen

- **God Class:** Klasse mit zu viel Verantwortung
- **Feature Envy:** Code interagiert mehr mit fremden als eigenen Modulen
- **Shotgun Surgery:** Konzeptuelle Änderung erfordert Edits in > 3 Dateien
- **Leaky Abstraction:** Implementierungsdetails sickern durch Interfaces
- **Premature Optimization:** Über-Engineering für nicht-existierende Probleme
- **Missing Abstraction:** Wiederholte Patterns ohne gemeinsame Basis

---

## Phase 6: Findings und Empfehlungen

### Priorisierte Findings

| Prio | Finding | Betroffene Module | Impact | Empfehlung |
| ---- | ------- | ----------------- | ------ | ---------- |
| 🔴   |         |                   |        |            |
| 🟡   |         |                   |        |            |
| 🟢   |         |                   |        |            |

### ADR-Kandidaten

Signifikante Findings, die als ADR dokumentiert werden sollten:

1. **ADR-XXX: [Titel]**
   - Kontext: ...
   - Entscheidung: ...
   - Konsequenzen: ...

### Fixes implementieren

Für 🔴-Findings:

1. **Ursache:** Warum existiert dieses Problem?
2. **Auswirkung:** Was passiert, wenn es nicht behoben wird?
3. **Fix:** Konkreter, vollständiger Lösungsansatz
4. **Migration:** Schrittweiser Plan ohne Breaking Changes

---

## Opus 4.6 – Kognitive Verstärker

Nutze Extended Thinking für:

1. **Transitive Abhängigkeiten:** Welche Module hängen transitiv ab?
2. **Verborgene DSGVO-Risiken:** Nicht-offensichtliche PII (Kalender-IDs, IPs)?
3. **Lastszenario-Schwachstellen:** Was bei 1000 gleichzeitigen Dokumenten?
4. **State-Konsistenz:** Was bei Absturz während Pipeline-Phase 2 von 3?
5. **Angriffsflächen:** Welche Inputs sind extern kontrollierbar?
