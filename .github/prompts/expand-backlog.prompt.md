---
description: "Erweitert tasks.md und task-state.json mit neuen atomaren Tasks für eine neue Phase oder ein neues Feature-Thema. Liest bestehende Struktur, leitet neue Tasks ab, hängt sie korrekt formatiert an beide Dateien an – vollständig autonom."
agent: agent
tools: ["codebase", "editFiles", "runCommands"]
---

# Backlog erweitern – neue Tasks in tasks.md + task-state.json

Du erweiterst den Entwicklungs-Backlog des PWBS-Projekts um neue atomare Tasks. Du arbeitest **vollständig autonom** – keine Rückfragen, keine Platzhalter, keine unvollständigen Einträge.

> **Robustheitsregeln (vor jeder Aktion anwenden):**
> 1. Prüfe vor jedem Dateizugriff, ob Datei/Verzeichnis existiert.
> 2. Verwende plattformgerechte Shell-Befehle (PowerShell auf Windows, Bash auf Linux/macOS).
> 3. Schreibe niemals einen Task als Platzhalter – Tasks sind entweder vollständig definiert oder werden nicht geschrieben.
> 4. Committe atomar nach dem Schreiben beider Dateien.

---

## Eingabe-Parameter

**Thema / Phase der neuen Tasks:**
`${input:thema:Thema oder Phase, z.B. "Phase 6 – KI-Assistenten-Marktplatz" oder "Feature: Obsidian-Plugin"}`

**Anzahl neuer Tasks (Richtwert):**
`${input:anzahl:Ungefähre Anzahl neuer Tasks, z.B. 10}`

**Neuer Stream-Name (leer lassen wenn existierender Stream):**
`${input:stream:Stream-Name, z.B. STREAM-PHASE6 oder leer lassen}`

**Orchestrator-Slot (für neuen Stream, sonst leer):**
`${input:orch_slot:Orchestrator-Slot, z.B. ORCH-M oder leer lassen}`

---

## Schritt 1 – Bestandsaufnahme

### 1a – Quelldokumente laden

Lese folgende Dateien in dieser Reihenfolge (überspringe fehlende):
1. `ROADMAP.md` → Phasen, Deliverables, KPIs
2. `PRD-SPEC.md` → Functional Requirements, Non-Functional Requirements, User Stories
3. `ARCHITECTURE.md` → Systemkomponenten, Module, Schnittstellen
4. `AGENTS.md` → Agenten-Rollen (welche Module sind zuständig?)
5. `.github/copilot-instructions.md` → Architekturprinzipien und Code-Konventionen

### 1b – Bestehenden Backlog analysieren

Lese `tasks.md` und `docs/orchestration/task-state.json`.

Extrahiere:
- Höchste existierende Task-ID → `MAX_ID` (Zahl, z.B. 155)
- Alle existierenden Stream-Namen → `EXISTING_STREAMS`
- Alle Tasks mit Status `done`, `in-progress`, `ready`, `open` → Überblick was bereits existiert
- Existierende Sektionen in `tasks.md` (Phasen-Überschriften)

Ausgabe (intern):
```
MAX_ID: 155
Neue Tasks starten bei: TASK-156
Existierende Streams: STREAM-FOUNDATION, STREAM-INFRA, ..., STREAM-PHASE5
```

---

## Schritt 2 – Neue Tasks ableiten

Leite aus dem angegebenen **Thema** und den Quelldokumenten konkrete atomare Tasks ab.

### Ableitung-Regeln

**Atomarität:**
- Jeder Task = 1 Entwickler, ≤ 1 Woche (Aufwand max. L)
- Schlechtes Beispiel: "Gmail-Integration implementieren"
- Gutes Beispiel: "GmailConnector: OAuth2-Handshake + Token-Refresh implementieren"

**Vollständigkeit der Task-Definition:**
Jeder Task braucht alle Pflichtfelder:

| Feld | Mögliche Werte |
|------|---------------|
| `Priorität` | P0 (kritisch) / P1 (Must-Have) / P2 (Should-Have) / P3 (Could-Have) |
| `Bereich` | Backend / Frontend / Infra / Auth / DB / LLM / Testing / Docs / DevOps / Mobile |
| `Aufwand` | XS (<2h) / S (0.5–1 Tag) / M (2–3 Tage) / L (1 Woche) / XL (>1 Woche) |
| `Abhängig von` | TASK-XXX oder – |
| `Blockiert` | TASK-XXX oder – |
| `Quelle` | Referenz auf Dokument + Abschnitt (z.B. "ROADMAP.md Phase 3 Kern-Deliverables") |
| `Status` | 🔴 Offen |

**Abhängigkeits-Graph (DAG-Regeln):**
- Keine Kreisabhängigkeiten
- Neue Tasks können auf existierende Tasks (bereits in tasks.md) verweisen
- Innerhalb der neuen Tasks: niedrigere IDs sind Voraussetzungen für höhere
- Prüfe: Falls neuer Task auf existierenden Task blockiert, ist dieser `done`? → Falls nicht, setze `blocked_by` entsprechend in task-state.json

**Inhaltliche Ableitung nach Priorität:**
1. Roadmap-Deliverables des Themas → direkte Implementierungs-Tasks
2. PRD-FRs die noch nicht in tasks.md abgedeckt sind → Neue Tasks
3. Architektur-Lücken → Infra/DB/Auth-Tasks
4. Test-Coverage-Lücken → Testing-Tasks
5. Dokumentation → Docs-Tasks (nur P2/P3)

---

## Schritt 3 – tasks.md aktualisieren

### 3a – Neue Phase-Sektion anlegen (falls neuer Stream/Phase)

Falls das Thema eine neue Phase darstellt, hänge ans Ende von `tasks.md` an:

```markdown
---

## Phase N: [Thema] (Monate X–Y)

---
```

Falls das Thema in eine bestehende Phase passt, hänge unter die entsprechende Sektion an.

### 3b – Tasks in tasks.md schreiben

Für jeden neuen Task, hänge ans Ende der entsprechenden Sektion (oder ans Ende der Datei) an:

```markdown
#### TASK-NNN: [Präziser, aktionsorientierter Titel]

| Feld             | Wert                                                                    |
| ---------------- | ----------------------------------------------------------------------- |
| **Priorität**    | [P0/P1/P2/P3] ([Begründung])                                            |
| **Bereich**      | [Backend/Frontend/Infra/...]                                            |
| **Aufwand**      | [XS/S/M/L/XL] ([Zeitrahmen])                                            |
| **Status**       | 🔴 Offen                                                                |
| **Quelle**       | [Quelldokument, Abschnitt]                                              |
| **Abhängig von** | [TASK-XXX oder –]                                                       |
| **Blockiert**    | [TASK-XXX oder –]                                                       |

**Beschreibung:** [2–4 Sätze: Was wird implementiert? Warum? Welcher Nutzen?]

**Acceptance Criteria:**

- [ ] [Messbar, falsifizierbar, konkret – kein "funktioniert"]
- [ ] [Mindestens 2, maximal 5 Kriterien]
- [ ] [Formulierung: "X liefert Y bei Eingabe Z" oder "Test schlägt fehl wenn..."]

**Technische Hinweise:** [Welche Module, Klassen, Patterns? Welche Fallstricke? Referenzen auf existierenden Code.]

---
```

**Wichtig:** Kein Task ohne alle Felder. Kein `<!-- TODO -->`. Kein "TBD".

---

## Schritt 4 – task-state.json aktualisieren

### 4a – Neuen Stream eintragen (falls neuer Stream)

Falls `${input:stream}` nicht leer und nicht in `streams` vorhanden:

```json
"${input:stream}": {
  "name": "[Lesbarer Name des Streams]",
  "description": "[1 Satz was dieser Stream liefert]",
  "phase": [Phasennummer als Integer],
  "orchestrator_slot": "${input:orch_slot}"
}
```

### 4b – Neue Tasks in `tasks`-Dict eintragen

Für jeden neuen Task füge unter `"tasks"` ein neues Objekt ein:

```json
"TASK-NNN": {
  "stream": "[STREAM-NAME – falls neuer Stream: ${input:stream}; sonst passenden existierenden Stream wählen]",
  "title": "[Exakt gleicher Titel wie in tasks.md]",
  "priority": "[P0/P1/P2/P3]",
  "effort": "[XS/S/M/L/XL]",
  "area": "[Backend/Frontend/Infra/Auth/DB/LLM/Testing/Docs/DevOps/Mobile]",
  "status": "open",
  "claimed_by": null,
  "claimed_at": null,
  "completed_at": null,
  "blocked_by": ["TASK-XXX"]
}
```

Regeln:
- `blocked_by` = leeres Array `[]` wenn keine Abhängigkeit
- `blocked_by` = Array von Task-IDs wenn Abhängigkeiten existieren
- Status-Mappings: 🔴 Offen → `"open"`, bereits erledigt → `"done"` (falls so bewertet)
- Alle neuen Tasks starten mit `"status": "open"` außer sie sind trivial ableitbar als bereits erledigt

### 4c – `meta.total_tasks` aktualisieren

Setze `meta.total_tasks` auf `MAX_ID + Anzahl neuer Tasks`.

Setze `meta.generated_at` auf den aktuellen ISO-8601-Timestamp.

---

## Schritt 5 – Validierung

Führe folgende Prüfungen aus und korrigiere Fehler sofort:

```
✅  Jede neue TASK-ID ist eindeutig (kein Duplikat in tasks.md + task-state.json)
✅  Jede TASK-ID in blocked_by referenziert einen existierenden Task
✅  Kein Zyklus in Abhängigkeiten (DAG-Check: keine Kette A→B→A)
✅  Anzahl neuer Einträge in tasks.md == Anzahl neuer Einträge in task-state.json
✅  meta.total_tasks == Anzahl Einträge in "tasks"-Dict
✅  Jeder Task hat alle Pflichtfelder (stream, title, priority, effort, area, status, blocked_by)
```

Falls ein Check fehlschlägt: Korrigiere, dann weiter.

---

## Schritt 6 – Commit

```bash
git add tasks.md docs/orchestration/task-state.json
git commit -m "feat(backlog): [N] neue Tasks fuer [Thema] (TASK-[FIRST]..TASK-[LAST])

- Stream: [STREAM-NAME]
- Neue Tasks: TASK-[FIRST] bis TASK-[LAST]  
- Prioritäten: [z.B. 3x P1, 5x P2, 2x P3]
- Bereiche: [z.B. Backend, LLM, Frontend]
- meta.total_tasks: [ALTER WERT] → [NEUER WERT]"
```

---

## Ausgabe-Zusammenfassung

Gib nach dem Commit aus:

```
✅ Backlog erweitert

Neue Tasks: TASK-[FIRST] bis TASK-[LAST] ([N] Tasks)
Stream: [STREAM-NAME] ([ORCH-SLOT])

Übersicht:
  P0: [N] Tasks
  P1: [N] Tasks  
  P2: [N] Tasks
  P3: [N] Tasks

Nächster freier Task (kein blocked_by): TASK-[NNN]
→ Starte mit: .github/prompts/orchestrator-init.prompt.md (Stream: [STREAM-NAME], Slot: [ORCH-SLOT])
```
