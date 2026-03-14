---
agent: agent
description: "Tiefenoptimierung der Performance im gesamten PWBS-Stack. Analysiert Datenbankqueries, API-Latenz, Embedding-Pipeline, Frontend-Bundles und Caching-Strategien – zustandsunabhängig bei jeder Ausführung."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Performance-Optimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Performance-Charakteristiken ändern sich mit jedem neuen Feature. Bei jeder Ausführung alle Performance-kritischen Pfade von Grund auf analysieren. Keine Annahmen über vorherige Optimierungen.

> **Robustheitsregeln:**
>
> - Analysiere nur Code, der existiert. Theoretische Performance-Probleme in Stubs sind keine Findings.
> - Bewerte Performance im Kontext des MVP (10–20 Nutzer). Over-Optimization ist ein Anti-Pattern.
> - Messe vor dem Optimieren: Vermutete Bottlenecks sind oft nicht die tatsächlichen.
> - Berücksichtige Trade-offs: Performance vs. Lesbarkeit, Caching vs. Konsistenz.

---

## Phase 0: Performance-Profil erstellen (Extended Thinking)

### 0.1 Kritische Pfade identifizieren

Identifiziere die Top-10 Performance-kritischsten Operationen:

| #   | Operation                   | Erwartete Häufigkeit    | Latenz-Budget    | Kritikalität |
| --- | --------------------------- | ----------------------- | ---------------- | ------------ |
| 1   | Semantische Suche           | Mehrfach pro Nutzer/Tag | < 500ms          | Hoch         |
| 2   | Morning Briefing generieren | 1x pro Nutzer/Tag       | < 30s            | Mittel       |
| 3   | Ingestion-Zyklus (15min)    | 96x/Tag gesamt          | < 5min           | Hoch         |
| 4   | Embedding-Generierung       | Pro Ingestion-Batch     | < 60s/100 Chunks | Hoch         |
| 5   | API-Endpoint-Response       | Jeder Request           | < 200ms (P95)    | Hoch         |
| 6   | Graph-Traversal (Kontext)   | Pro Briefing/Suche      | < 200ms          | Mittel       |
| 7   | NER-Extraktion              | Pro Dokument            | < 5s             | Niedrig      |
| 8   | Frontend Initial Load       | Pro Session             | < 2s (LCP)       | Hoch         |
| 9   | OAuth Token Refresh         | Pro abgelaufenem Token  | < 1s             | Mittel       |
| 10  | DSGVO Data Export           | Selten (on-demand)      | < 60s            | Niedrig      |

### 0.2 Ressourcen-Topologie

```
User Request → Frontend (Vercel CDN)
  → API (FastAPI, ECS Fargate)
    → PostgreSQL (RDS t3.medium)
    → Weaviate (EC2 t3.xlarge)
    → Neo4j (EC2 t3.large)
    → Redis (ElastiCache)
    → LLM API (Claude, extern)
```

Identifiziere Engpässe an jeder Transition.

---

## Phase 1: Datenbank-Performance

### 1.1 PostgreSQL

Durchsuche alle SQLAlchemy-Queries und SQL-Operationen:

- [ ] **N+1 Queries:** Eager Loading (`selectinload`, `joinedload`) wo nötig
- [ ] **Fehlende Indexes:** Jede `WHERE`-Bedingung und `JOIN`-Spalte hat einen Index
- [ ] **Index-Analyse:** `owner_id` hat Index auf jeder Nutzer-bezogenen Tabelle
- [ ] **Query-Komplexität:** Keine verschachtelten Subqueries, die als JOIN lösbar wären
- [ ] **Pagination:** Cursor-basiert statt OFFSET (Performance degradiert mit hohem Offset)
- [ ] **Connection Pooling:** Pool-Size angemessen (min 5, max 20 für MVP)
- [ ] **Prepared Statements:** SQLAlchemy nutzt automatisch, aber prüfe Raw Queries
- [ ] **Batch Operations:** Bulk Inserts/Updates wo möglich (nicht Zeile für Zeile)

```python
# LANGSAM – N+1:
documents = await session.execute(select(Document).filter_by(owner_id=uid))
for doc in documents:
    chunks = await session.execute(select(Chunk).filter_by(document_id=doc.id))

# SCHNELL – Eager Loading:
documents = await session.execute(
    select(Document).options(selectinload(Document.chunks)).filter_by(owner_id=uid)
)
```

### 1.2 Weaviate (Vektor-Suche)

- [ ] **Batch-Indexierung:** Embeddings in Batches upserten (≥ 64 pro Batch)
- [ ] **Index-Konfiguration:** HNSW-Parameter optimiert (efConstruction, maxConnections)
- [ ] **Filter-Performance:** `owner_id`-Filter als Pre-Filter (nicht Post-Filter)
- [ ] **Vektor-Dimensionen:** 1536 (text-embedding-3-small) → ggf. Quantization evaluieren
- [ ] **Concurrent Queries:** Read-Performance unter parallelen Anfragen

### 1.3 Neo4j (Graph-DB)

- [ ] **Index auf owner_id:** Für alle Node-Labels
- [ ] **Traversal-Tiefe:** Begrenzt auf depth=2 (exponentielles Wachstum vermeiden)
- [ ] **MERGE Performance:** Idempotente Writes mit MERGE sind langsamer als CREATE – akzeptabel für Korrektheit
- [ ] **Query-Profiling:** `PROFILE` oder `EXPLAIN` auf komplexe Cypher-Queries
- [ ] **Driver-Pool:** Connection-Pool-Size angemessen

---

## Phase 2: API-Performance

### 2.1 FastAPI Endpunkte

- [ ] **Async überall:** Keine sync-Operationen im Request-Handler
- [ ] **Response-Modelle:** Nur nötige Felder serialisieren (nicht das gesamte Modell)
- [ ] **Dependency Injection:** Teure Dependencies cachen (Session Factory statt neue Session pro Request)
- [ ] **Streaming:** Für große Responses (z.B. Data Export) Streaming verwenden
- [ ] **Background Tasks:** Nicht-kritische Operationen in `BackgroundTask` auslagern
- [ ] **Middleware-Overhead:** Nur nötige Middleware aktiv

### 2.2 Caching-Strategie

| Datenmuster     | Cache-Strategie       | TTL          | Invalidierung          |
| --------------- | --------------------- | ------------ | ---------------------- |
| Nutzer-Profil   | Redis                 | 15min        | Bei Änderung           |
| Such-Ergebnisse | HTTP Cache-Control    | 30s          | Stale-While-Revalidate |
| Briefings       | Redis + DB            | 30min        | Bei neuen Daten        |
| Embeddings      | Weaviate (persistent) | ∞            | Bei Reprocessing       |
| OAuth Tokens    | In-Memory + DB        | Token Expiry | Bei Refresh            |

Prüfe:

- [ ] Redis als Cache-Layer implementiert
- [ ] Cache-Keys enthalten `owner_id` (Tenant-Isolation)
- [ ] Cache-Invalidierung korrekt bei Datenänderung
- [ ] Kein Cache-Stampede bei gleichzeitigem Ablauf

### 2.3 Rate Limiting

- [ ] Implementiert auf allen öffentlichen Endpunkten
- [ ] Separate Limits für Auth-Endpunkte (strenger) vs. Daten-Endpunkte
- [ ] LLM-API-Calls rate-limited (extern + intern)
- [ ] Redis-basiert für konsistente Limits über mehrere Prozesse

---

## Phase 3: Processing-Pipeline-Performance

### 3.1 Embedding-Pipeline

- [ ] **Batch-Größe:** 64 Chunks pro Batch (optimal für lokale + Cloud Embeddings)
- [ ] **Parallelisierung:** Concurrent Embedding-Requests an API
- [ ] **Caching:** Bereits eingebettete Chunks nicht erneut einbetten (Hash-basiertes Caching)
- [ ] **Fallback:** Timeout/Fehler beim Cloud-Embedding → lokaler Fallback
- [ ] **Queue-Depth:** Limit für gleichzeitige Embedding-Jobs

### 3.2 Chunking-Performance

- [ ] Semantisches Chunking-Overhead akzeptabel?
- [ ] Chunk-Größe (128–512 Token) optimal für Such-Qualität?
- [ ] Overlap (32 Token) notwendig oder reduzierbar?

### 3.3 LLM-Integration

- [ ] **Streaming:** LLM-Responses streamen (bessere Time to First Token)
- [ ] **Structured Output:** JSON-Schema für deterministische Parsing-Performance
- [ ] **Prompt-Größe:** Token-Budget nicht verschwenden – Kontext auf Relevantes beschränken
- [ ] **Caching:** Identische Anfragen cachen (z.B. NER auf unverändertem Content)
- [ ] **Timeout:** 60s für LLM-Calls, Graceful Degradation bei Überschreitung

---

## Phase 4: Frontend-Performance

### 4.1 Core Web Vitals

- [ ] **LCP < 2.5s:** Largest Contentful Paint (Server-Side Rendering nutzen)
- [ ] **FID < 100ms:** First Input Delay (JavaScript-Bundle minimieren)
- [ ] **CLS < 0.1:** Cumulative Layout Shift (Platzhalter für asynchrone Inhalte)

### 4.2 Bundle-Analyse

- [ ] Next.js Bundle-Size analysieren (`npm run build` → Output prüfen)
- [ ] Code-Splitting: Nur benötigter Code pro Route laden
- [ ] Tree-Shaking: Keine unbenutzten Imports in Production-Bundle
- [ ] Fonts: Self-Hosted oder preload für Web Fonts

### 4.3 Data Fetching

- [ ] Server Components für statische Daten
- [ ] ISR (Incremental Static Regeneration) für semi-statische Daten
- [ ] SWR/React Query für Client-seitige Daten-Revalidierung
- [ ] Keine Wasserfall-Requests (paralleles Fetching)

---

## Phase 5: Optimierungen implementieren

### Priorisierung: Impact vs. Aufwand

| #   | Optimierung | Erwarteter Impact  | Aufwand | Risiko |
| --- | ----------- | ------------------ | ------- | ------ |
| 1   | ...         | Hoch/Mittel/Gering | S/M/L   | ...    |

**Regel:** Erst messen, dann optimieren. Vermutete Bottlenecks mit Profiling bestätigen.

Implementiere:

1. Quick Wins (hoher Impact, geringer Aufwand) sofort
2. Strategische Optimierungen (hoher Impact, mittlerer Aufwand) als Empfehlung
3. Premature Optimizations (geringer Impact, hoher Aufwand) verwerfen

---

## Phase 6: Performance-Bericht

```markdown
# Performance-Bericht – [Datum]

## Identifizierte Bottlenecks

| #   | Operation | Problem | Impact | Status                       |
| --- | --------- | ------- | ------ | ---------------------------- |
| 1   | ...       | ...     | ...    | Behoben/Empfohlen/Akzeptiert |

## Implementierte Optimierungen

1. ...

## Performance-Metriken (geschätzt)

| Metrik              | Vorher | Nachher | Ziel             |
| ------------------- | ------ | ------- | ---------------- |
| API P95 Latenz      | ...    | ...     | < 200ms          |
| Embedding-Durchsatz | ...    | ...     | > 100 Chunks/min |
| Frontend LCP        | ...    | ...     | < 2.5s           |

## Empfehlungen

1. ...
```

---

## Opus 4.6 – Kognitive Verstärker

- **Systemweites Denken:** Performance ist eine Systemeigenschaft – lokale Optimierung kann globale Degradation verursachen.
- **Amdahls Gesetz:** Identifiziere den sequenziellen Engpass im System – nur dessen Optimierung bringt echten Gewinn.
- **Trade-off-Bewusstsein:** Jede Performance-Optimierung hat Kosten (Komplexität, Konsistenz, Lesbarkeit). Bewerte den Netto-Effekt.
- **Antizipative Analyse:** Welche aktuell akzeptable Performance wird bei 100/1000 Nutzern zum Problem?
