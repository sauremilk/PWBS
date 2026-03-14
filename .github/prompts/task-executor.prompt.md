---
description: "Führt einen einzelnen PWBS-Task vollständig durch: Definition lesen, implementieren, testen, Status aktualisieren, committen."
agent: agent
tools: ["codebase", "editFiles", "runCommands", "problems"]
---

# PWBS Task Executor

Du implementierst **genau einen Task** aus dem PWBS-Backlog vollständig.

> **Robustheitsregeln (vor jeder Aktion anwenden):**
>
> 1. **Existenzprüfung:** Prüfe vor jedem Dateizugriff, ob Datei/Verzeichnis existiert. Fehlt etwas, dokumentiere dies und fahre adaptiv fort.
> 2. **OS-Erkennung:** Verwende plattformgerechte Shell-Befehle (PowerShell auf Windows, Bash auf Linux/macOS). Shell-Beispiele in diesem Prompt sind Pseudo-Code – übersetze sie in die Syntax der aktuellen Shell.
> 3. **Workspace-Zustand:** Prüfe zu Beginn den aktuellen Projektzustand (existierende Module, installierte Tools) und passe dein Vorgehen an.
> 4. **Idempotenz:** Jeder Schritt muss bei Wiederholung dasselbe Ergebnis liefern.

## Input

**Task-ID:** ${input:task_id:Task-ID, z.B. TASK-041}
**Orchestrator-Slot:** ${input:orch_slot:Orchestrator-Slot, z.B. ORCH-E}

---

## Ausführungs-Protokoll

### Phase 1 – Task-Definition lesen

1. **Existenzprüfung:** Stelle sicher, dass `tasks.md` existiert. Falls nicht: suche nach alternativen Task-Definitionen in `docs/backlog/` oder frage den Nutzer.
2. Suche in `tasks.md` nach `#### ${input:task_id}`. Falls nicht gefunden: suche case-insensitiv und mit Varianten. Falls immer noch nicht gefunden: Abbruch mit klarer Fehlermeldung.
3. Lies vollständig:
   - **Priorität** und **Bereich**
   - **Abhängig von** – prüfe in `docs/orchestration/task-state.json`, ob alle genannten Tasks auf `done` stehen. Falls `task-state.json` nicht existiert, erstelle sie mit dem aktuellen Task als erstem Eintrag.
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
- Keine `# TODO: implement` Platzhalter – vollständig oder `raise NotImplementedError("${input:task_id}: [Beschreibung]")`
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

**Backend-Tasks:**

1. Wechsle nach `backend/`.
2. Versuche zuerst, nur Tests für den aktuellen Task zu filtern (Name aus `${input:task_id}` ableiten, z.B. `TASK-041` → `test_task_041`). Falls kein passender Test existiert, führe alle Unit-Tests aus: `pytest tests/unit/ -v --tb=short -q`.
3. Falls `pytest` nicht verfügbar ist: prüfe ob die virtuelle Umgebung aktiviert ist oder `pyproject.toml` die Test-Dependencies enthält.

**Frontend-Tasks:**

1. Wechsle nach `frontend/`.
2. Führe `npm run type-check` und `npm run lint` aus.
3. Falls `node_modules/` fehlt: `npm install` zuerst ausführen.

**Bei Fehlern:** Analysiere die Fehlermeldung, behebe das Problem und wiederhole den Test. Erst nach erfolgreichen Tests mit Phase 6 fortfahren.

### Phase 6 – Status aktualisieren und committen

1. **task-state.json aktualisieren:** Falls `docs/orchestration/task-state.json` existiert, aktualisiere den Eintrag:

   ```json
   "${input:task_id}": {
     "status": "done",
     "completed_at": "<aktueller ISO-8601-Timestamp>"
   }
   ```

   Falls die Datei nicht existiert, erstelle sie mit dem korrekten JSON-Schema (prüfe `docs/orchestration/task-state.schema.json` als Vorlage).

2. **Entblockte Tasks identifizieren:** Prüfe, welche Tasks durch diesen Abschluss entblockt werden (Tasks, deren `blocked_by` jetzt vollständig auf `done` stehen).

3. **Commit** mit Konvention:

   ```
   feat(<modul>): <kurze Beschreibung> (${input:task_id})

   - <Acceptance Criterion 1 ✅>
   - <Acceptance Criterion 2 ✅>

   Entblockt: TASK-XXX, TASK-YYY
   ```

4. **Push:** `git push` (nur wenn der Nutzer dies explizit erlaubt hat oder die Session es vorsieht).

---

## Sonderfälle

### Task unvollständig implementierbar (fehlende Dependency)

Setze in `docs/orchestration/task-state.json`:

```json
"${input:task_id}": {
  "status": "blocked",
  "notes": "${input:orch_slot}: Warte auf TASK-YYY (STREAM-ZZZ). [Warum wird es benötigt]"
}
```

→ Zurück zum Orchestrator-Init-Prompt, nächsten verfügbaren Task wählen.

### Task benötigt externe Credentials (OAuth-Keys, API-Keys)

→ Task auf `blocked` setzen, `notes`: "Benötigt: [KEY_NAME] in .env – bitte Nutzer um Bereitstellung"
→ Niemals Demo-Keys oder Platzhalter-Secrets in den Code schreiben

### Scope Creep erkannt

Wenn während der Implementierung klar wird, dass weitere Sub-Tasks notwendig sind:
→ Diese **nicht** sofort implementieren
→ Einen Kommentar mit `# TASK-XXX: [Beschreibung ausstehend]` hinterlassen
→ Neuen Task in `task-state.json` unter einem passenden Stream als `open` eintragen
