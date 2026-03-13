# PWBS – Orchestrierungs-Protokoll

**Version:** 1.0 | **Stand:** 13. März 2026

Dieses Dokument definiert, wie mehrere Claude-Opus-4.6-Instanzen (Orchestratoren) gleichzeitig und koordiniert am PWBS-Entwicklungs-Backlog arbeiten – konfliktfrei, nachvollziehbar und ohne gegenseitige Blockierungen.

---

## Überblick

```
tasks.md   ←  Lesbare Task-Definitionen (Beschreibung, Acceptance Criteria, Technische Hinweise)
task-state.json  ←  Maschinenlesbarer Koordinationszustand (Status, Claiming, Blocking)
```

Jeder Orchestrator liest beide Dateien. Statusänderungen schreibt er **ausschließlich** in `task-state.json` und committet atomar per `git commit`.

---

## Work Streams und Slot-Zuweisung

Jeder Stream hat einen festen **Orchestrator-Slot**. Eine Opus-4.6-Instanz übernimmt genau einen Slot.

| Slot       | Stream                                                             | Phase | Unabhängig parallel zu |
| ---------- | ------------------------------------------------------------------ | ----- | ---------------------- |
| **ORCH-A** | STREAM-FOUNDATION (PoC, DSGVO, ADRs)                               | 1     | – (Baseline)           |
| **ORCH-B** | STREAM-INFRA (Docker, CI/CD, Terraform)                            | 2     | ORCH-C                 |
| **ORCH-C** | STREAM-DB (PostgreSQL, Weaviate, Neo4j, Clients)                   | 2     | ORCH-B                 |
| **ORCH-D** | STREAM-MODELS (Pydantic, ORM, App-Skeleton)                        | 2     | – (nach ORCH-C)        |
| **ORCH-E** | STREAM-CONNECTORS (BaseConnector, 4 MVP-Konnektoren)               | 2     | ORCH-F                 |
| **ORCH-F** | STREAM-PROCESSING (Chunking, Embedding, NER, Graph, LLM, Briefing) | 2     | ORCH-E                 |
| **ORCH-G** | STREAM-AUTH-API (JWT, OAuth2, alle FastAPI-Routen)                 | 2     | ORCH-H                 |
| **ORCH-H** | STREAM-FRONTEND (Next.js, alle Seiten)                             | 2     | ORCH-G                 |
| **ORCH-I** | STREAM-DSGVO-QA (DSGVO, Tests, Monitoring)                         | 2     | ORCH-H                 |
| **ORCH-J** | STREAM-PHASE3 (Celery, Gmail, Slack, Google Docs)                  | 3     | – (nach MVP)           |
| **ORCH-K** | STREAM-PHASE4 (Entscheidungen, Desktop, erweiterte KI)             | 4     | –                      |
| **ORCH-L** | STREAM-PHASE5 (Platform, Multi-Tenancy, Scale)                     | 5     | –                      |

### Parallele Start-Matrix (MVP)

```
Phase 2 MVP – wer kann gleichzeitig beginnen (nach ORCH-A fertig):

  ORCH-B ──────────────── ORCH-D ──────┬── ORCH-E ─── ORCH-G ─── ORCH-I
                                        │
  ORCH-C ──────────────── ORCH-D ──────┘── ORCH-F ─── ORCH-H
```

---

## Claiming-Protokoll

### 1. Schritt: Nächste Aufgabe finden

```python
# Pseudocode – führe als ersten Schritt jeder Session aus
import json

with open("docs/orchestration/task-state.json") as f:
    state = json.load(f)

my_stream = "STREAM-CONNECTORS"  # deinen Slot eintragen
my_id = "ORCH-E"

# Alle offenen Tasks meines Streams, deren Blocker alle done sind
def is_unblocked(task_id, tasks):
    task = tasks[task_id]
    return all(tasks[dep]["status"] == "done" for dep in task["blocked_by"])

candidates = [
    tid for tid, t in state["tasks"].items()
    if t["stream"] == my_stream
    and t["status"] == "open"
    and is_unblocked(tid, state["tasks"])
]
# Ersten nach Priorität (P0 > P1 > P2 > P3) wählen
```

### 2. Schritt: Task claimen

Ändere in `task-state.json`:

```json
"TASK-041": {
  "status": "in_progress",
  "claimed_by": "ORCH-E",
  "claimed_at": "2026-03-13T09:00:00Z"
}
```

Danach sofort committen:

```bash
git add docs/orchestration/task-state.json
git commit -m "claim: ORCH-E nimmt TASK-041 in Bearbeitung"
git push
```

### 3. Schritt: Task implementieren

Lies die vollständige Task-Definition aus `tasks.md` (Suche nach `#### TASK-041`).
Implementiere vollständig gemäß Acceptance Criteria und Technischen Hinweisen.

### 4. Schritt: Task abschließen

```json
"TASK-041": {
  "status": "done",
  "completed_at": "2026-03-13T11:30:00Z"
}
```

```bash
git add .
git commit -m "feat(connectors): BaseConnector ABC implementiert (TASK-041)"
git push
```

---

## Konflikt-Vermeidung

**Regel 1 – Streams sind exklusiv:** Jeder Orchestrator arbeitet nur in seinem Stream. Kein Griff in fremde Streams ohne explizite Übergabe.

**Regel 2 – Übergabe bei Stream-Überschneidung:** Wenn eine Task in einem anderen Stream auf eine eigene Vorarbeit wartet, Kommentar in `task-state.json` hinterlassen:

```json
"notes": "ORCH-E: TASK-043 OAuth Token Manager fertig. ORCH-F kann TASK-058/059 starten."
```

**Regel 3 – Blocker eskalieren:** Wenn ein Task nicht weiterkommt (blocked_by noch nicht done, externer Blocker), Status auf `"blocked"` setzen und `notes` befüllen. Nicht warten.

**Regel 4 – Pull vor Claims:** Immer `git pull` vor dem Claimen, um Konflikte in `task-state.json` zu vermeiden.

**Regel 5 – Ein Task gleichzeitig:** Jeder Orchestrator hält maximal einen Task auf `in_progress`. Erst abschließen, dann nächsten claimen.

---

## Cross-Stream-Abhängigkeiten (kritische Schnittstellen)

| Upstream-Task     | Erzeugt                           | Downstream-Task        | Wartet                  |
| ----------------- | --------------------------------- | ---------------------- | ----------------------- |
| TASK-032 (ORCH-D) | `UnifiedDocument` Pydantic-Modell | TASK-041, 044 (ORCH-E) | BaseConnector-Interface |
| TASK-033 (ORCH-D) | `Chunk`, `Entity` Modelle         | TASK-056 (ORCH-F)      | Chunking-Service        |
| TASK-027 (ORCH-C) | PostgreSQL Connection Pool        | TASK-082, 085 (ORCH-G) | Auth-Routen             |
| TASK-037 (ORCH-D) | FastAPI-App-Skeleton              | TASK-085, 093 (ORCH-G) | Middleware-Stack        |
| TASK-075 (ORCH-F) | SearchResult mit SourceRef        | TASK-088 (ORCH-G)      | Search-API-Endpoint     |
| TASK-080 (ORCH-F) | Briefing-Persistierung            | TASK-089 (ORCH-G)      | Briefings-API           |
| TASK-086 (ORCH-G) | Auth-Routen aktiv                 | TASK-094, 095 (ORCH-H) | Frontend API-Client     |
| TASK-086 (ORCH-G) | Auth-Routen aktiv                 | TASK-104–106 (ORCH-I)  | DSGVO-Endpunkte         |

---

## Status-Übersicht generieren

```powershell
# Schnelle Übersicht aller in_progress und blocked Tasks
$state = Get-Content "docs\orchestration\task-state.json" | ConvertFrom-Json
$state.tasks.PSObject.Properties |
  Where-Object { $_.Value.status -in @("in_progress","blocked") } |
  ForEach-Object { "$($_.Name) [$($_.Value.status)] — $($_.Value.claimed_by) — $($_.Value.title)" }
```

```bash
# Fortschritt pro Stream
node -e "
const s = require('./docs/orchestration/task-state.json');
const streams = {};
Object.entries(s.tasks).forEach(([id, t]) => {
  const k = t.stream;
  if (!streams[k]) streams[k] = {open:0,ip:0,done:0};
  if (t.status==='open') streams[k].open++;
  if (t.status==='in_progress') streams[k].ip++;
  if (t.status==='done') streams[k].done++;
});
Object.entries(streams).forEach(([stream, c]) =>
  console.log(stream.padEnd(25), 'done:'+c.done, 'ip:'+c.ip, 'open:'+c.open));
"
```

---

## Commit-Konventionen

| Situation                   | Commit-Prefix     | Beispiel                                                     |
| --------------------------- | ----------------- | ------------------------------------------------------------ |
| Task claimen                | `claim:`          | `claim: ORCH-E nimmt TASK-041`                               |
| Task abschließen (Backend)  | `feat(modul):`    | `feat(connectors): BaseConnector implementiert (TASK-041)`   |
| Task abschließen (Frontend) | `feat(frontend):` | `feat(frontend): Login-Seite implementiert (TASK-096)`       |
| Task abschließen (DB)       | `feat(db):`       | `feat(db): users-Schema + Migration (TASK-015, TASK-018)`    |
| Bug während Task gefunden   | `fix:`            | `fix(auth): Token-Rotation Race Condition (TASK-084)`        |
| Task geblockt               | `chore:`          | `chore: TASK-059 blocked – Weaviate-Client fehlt (TASK-028)` |

---

## Schnellstart für neuen Orchestrator

```
1. git clone / git pull
2. Lese ORCHESTRATION.md (diese Datei)
3. Lese deinen Stream in docs/orchestration/task-state.json
4. Öffne .github/prompts/orchestrator-init.prompt.md in GitHub Copilot Chat
5. Ersetze STREAM_PLACEHOLDER mit deinem Stream (z.B. STREAM-CONNECTORS)
6. Starte die Session → Copilot führt dich durch Claim → Implement → Commit-Zyklus
```
