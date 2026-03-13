---
description: "Führt einen einzelnen PWBS-Task vollständig durch: Definition lesen, implementieren, testen, Status aktualisieren, committen."
tools: ["codebase", "editFiles", "runCommands"]
---

# PWBS Task Executor

Du implementierst **genau einen Task** aus dem PWBS-Backlog vollständig.

## Input

**Task-ID:** `$TASK_ID_PLACEHOLDER` (z.B. `TASK-041`)
**Orchestrator-Slot:** `$ORCH_SLOT_PLACEHOLDER` (z.B. `ORCH-E`)

---

## Ausführungs-Protokoll

### Phase 1 – Task-Definition lesen

1. Öffne `tasks.md` und suche nach `#### $TASK_ID_PLACEHOLDER`
2. Lies vollständig:
   - **Priorität** und **Bereich**
   - **Abhängig von** – stelle sicher, dass alle genannten Tasks in `task-state.json` auf `done` stehen
   - **Beschreibung** – was genau zu bauen ist
   - **Acceptance Criteria** – deine Definition of Done
   - **Technische Hinweise** – konkrete Vorgaben (Modulname, Bibliothek, Algorithmus)

### Phase 2 – Kontext laden

Lese ergänzend:

- `ARCHITECTURE.md` (Abschnitt zum betreffenden Modul)
- `AGENTS.md` (welche Agenten-Rolle ist zuständig)
- `.github/instructions/backend.instructions.md` (für Python-Dateien)
- `.github/instructions/frontend.instructions.md` (für TypeScript/TSX-Dateien)
- `.github/instructions/security.instructions.md` (immer)
- Existierende Dateien im Zielmodul (falls vorhanden): lese sie bevor du schreibst

### Phase 3 – Implementieren

**Pflichtregeln:**

- Vollständige Type Annotations (Python: PEP 484/526, TypeScript: strict)
- Keine `# TODO: implement` Platzhalter – vollständig oder `raise NotImplementedError("$TASK_ID_PLACEHOLDER: [Beschreibung]")`
- Jede neue Datenstruktur mit `owner_id: UUID` und `expires_at: datetime | None`
- Alle DB-Writes als UPSERT/MERGE (Idempotenz)
- Absolute Imports: `from pwbs.connectors.base import BaseConnector`
- Exceptions: Von `PWBSError` ableiten (in `pwbs.core.exceptions`)
- Async für alle I/O-Operationen: `async def`

**Datei-Konventionen:**

```
backend/pwbs/
├── connectors/     ← STREAM-CONNECTORS
├── processing/     ← STREAM-PROCESSING
├── briefing/       ← STREAM-PROCESSING (Briefing-Engine)
├── search/         ← STREAM-PROCESSING (Search-Service)
├── graph/          ← STREAM-PROCESSING (GraphAgent)
├── api/            ← STREAM-AUTH-API
│   └── routers/    ← einzelne FastAPI-Router
├── models/         ← STREAM-MODELS (Pydantic)
├── db/             ← STREAM-MODELS (SQLAlchemy ORM)
├── scheduler/      ← SchedulerAgent
└── core/           ← Shared (Settings, Exceptions, Types)

frontend/src/
├── app/            ← Next.js App Router Pages
├── components/     ← React Components
├── lib/api/        ← API-Client-Abstraktion
└── types/          ← TypeScript-Typen
```

### Phase 4 – Qualitätsprüfung

Vor dem Commit, prüfe intern:

**Backend:**

- [ ] Alle `owner_id`-Filter in DB-Queries vorhanden?
- [ ] Keine `.all()` oder DB-Reads ohne `WHERE owner_id = ?`?
- [ ] Pydantic `model_validator` statt deprecated Patterns?
- [ ] FastAPI-Response-Objekte korrekt annotiert (nicht `Response | None`)?
- [ ] Rate-Limiting auf öffentlichen Endpunkten?

**Frontend:**

- [ ] Keine direkten `fetch()`-Aufrufe in Komponenten (nur via `lib/api/`)?
- [ ] `"use client"` nur wo unbedingt nötig?
- [ ] Alle Props mit expliziten TypeScript-Interfaces?

**Allgemein:**

- [ ] Keine Secrets im Code?
- [ ] Input-Validierung an allen Systemgrenzen?
- [ ] Acceptance Criteria vollständig erfüllt?

### Phase 5 – Tests ausführen

```bash
# Backend-Tasks:
cd backend
pytest tests/unit/ -v -k "test_$(echo $TASK_ID_PLACEHOLDER | tr '[:upper:]' '[:lower:]' | tr '-' '_')" 2>/dev/null || pytest tests/unit/ -v --tb=short -q

# Frontend-Tasks:
cd frontend
npm run type-check
npm run lint
```

Bei Fehlern: Behebe sie, bevor du mit Phase 6 fortfährst.

### Phase 6 – Status aktualisieren und committen

1. Aktualisiere `docs/orchestration/task-state.json`:

   ```json
   "$TASK_ID_PLACEHOLDER": {
     "status": "done",
     "completed_at": "<aktueller ISO-8601-Timestamp>"
   }
   ```

2. Prüfe: Welche Tasks werden durch diesen Abschluss **entblockt**?
   (Tasks in `blocked_by`, die jetzt alle Deps erfüllt haben)

3. Commit mit Konvention:

   ```
   feat(<modul>): <kurze Beschreibung> ($TASK_ID_PLACEHOLDER)

   - <Acceptance Criterion 1 ✅>
   - <Acceptance Criterion 2 ✅>

   Entblockt: TASK-XXX, TASK-YYY
   ```

4. Push: `git push`

---

## Sonderfälle

### Task unvollständig implementierbar (fehlende Dependency)

```json
"$TASK_ID_PLACEHOLDER": {
  "status": "blocked",
  "notes": "ORCH-X: Warte auf TASK-YYY (STREAM-ZZZ). [Warum wird es benötigt]"
}
```

→ Zurück zum Orchestrator-Init-Prompt, nächsten ungeklärten Task wählen.

### Task benötigt externe Credentials (OAuth-Keys, API-Keys)

→ Task auf `blocked` setzen, `notes`: "Benötigt: [KEY_NAME] in .env – bitte Nutzer um Bereitstellung"
→ Niemals Demo-Keys oder Platzhalter-Secrets in den Code schreiben

### Scope Creep erkannt

Wenn während der Implementierung klar wird, dass weitere Sub-Tasks notwendig sind:
→ Diese **nicht** sofort implementieren
→ Einen Kommentar mit `# TASK-XXX: [Beschreibung ausstehend]` hinterlassen
→ Neuen Task in `task-state.json` unter einem passenden Stream als `open` eintragen
