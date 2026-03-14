---
description: "Generiert autonom das Task-Backlog mit atomaren Tasks, Quellenrückverfolgbarkeit und DAG-Validierung – vollständig aus dem Workspace abgeleitet, ohne Rückfragen."
agent: agent
tools:
  - codebase
  - editFiles
  - runCommands
---

# Task-Backlog generieren (autonom)

Du generierst das **Task-Backlog** (`tasks.md`) für diesen Workspace – vollständig autonom, ohne Rückfragen. Das Task-Backlog ist die fünfte und letzte Schicht der semantischen Kette und beantwortet: *Was muss konkret in welcher Reihenfolge implementiert werden – und warum?*

> **Autonomie-Prinzip:** Tasks werden systematisch aus existierenden Dokumenten und Code abgeleitet. Jeder Task hat ein `Quelle`-Feld, das auf das Ursprungsdokument verweist. Du stellst keine Fragen. Falls etwas nicht ableitbar ist: `<!-- REVIEW: ... -->`.

> **Kernregel:** Jeder Task muss atomar sein (1 Entwickler, ≤ 1 Tag), ein klares Akzeptanzkriterium haben und eine Quellenreferenz auf ein Roadmap-Deliverable, ein PRD-FR oder eine Architektur-Komponente enthalten. "API bauen" ist kein Task – "POST /api/connectors/{id}/sync Endpunkt implementieren" ist einer.

> **Robustheitsregeln:**
> 1. Prüfe vor jedem Dateizugriff, ob die Datei existiert.
> 2. Verwende plattformgerechte Shell-Befehle.
> 3. Falls tasks.md bereits existiert: Lies sie, identifiziere neue Tasks aus aktuellen Dokumenten, ergänze sie.
> 4. Falls weder Roadmap noch PRD-SPEC existieren: **Abbruch.** Gib aus: "Keine Roadmap oder PRD-SPEC gefunden. Führe zuerst `gen-roadmap.prompt.md` und `gen-prd-spec.prompt.md` aus."

---

## Schritt 1: Quelldokumente laden

### Pflichtquellen (mindestens eine muss vorhanden sein)
1. **Roadmap** → Phasen, Deliverables pro Phase, aktuelle Phase
2. **PRD-SPEC** → FRs mit Acceptance Criteria, NFs

### Erweiterte Quellen (falls vorhanden)
3. **Architecture** → Komponenten, Module, Schnittstellen, Tech-Stack
4. **Vision** → Kernfunktionen, "Was es nicht ist"
5. **Existierende tasks.md** → Bereits definierte Tasks (Status prüfen)

### Code-Analyse (für Ist-Stand)
6. **Implementierte Module** → Welche Komponenten existieren bereits?
7. **Tests** → Welche FRs sind bereits getestet?
8. **Migrations** → Welche DB-Schemas sind bereits definiert?
9. **Docker/CI-Konfiguration** → Welche Infrastruktur existiert?

---

## Schritt 2: Task-Quellen systematisch extrahieren

### 2a – Aus Roadmap-Deliverables

Für jede Phase der Roadmap (Fokus auf aktuelle + nächste Phase):
→ Für jedes Deliverable: Zerlege in atomare Implementierungs-Schritte
→ Prüfe Code: Ist das Deliverable bereits (teil-)implementiert?
→ Status zuweisen: `done` / `in-progress` / `open`

### 2b – Aus PRD-SPEC Functional Requirements

Für jedes FR:
→ Ist es implementiert? (Prüfe API-Routen, Module, Tests)
→ Falls ja: Status `done`
→ Falls teilweise: Welche Acceptance Criteria fehlen noch? → Tasks daraus
→ Falls nein: Zerlege FR in Implementierungs-Tasks

### 2c – Aus PRD-SPEC Non-Functional Requirements

Für jedes NF:
→ Ist die Anforderung bereits erfüllt? (z.B. Rate-Limiting konfiguriert?)
→ Falls nicht: Task erstellen

### 2d – Aus Architecture-Komponenten

Für jede Architektur-Komponente:
→ Existiert die Implementierung?
→ Falls nein: Tasks für Grundstruktur + Integration erstellen

### 2e – Erkannte Lücken

Vergleiche Soll (Dokumente) vs. Ist (Code):
→ Fehlende Tests → Test-Tasks
→ Fehlende Migrations → Schema-Tasks
→ Fehlende Konfiguration → Setup-Tasks

---

## Schritt 3: Tasks normalisieren und strukturieren

### 3a – Atomarität prüfen

Für jeden Task prüfen:
- Kann ein Entwickler das in ≤ 1 Tag abschließen?
- Falls nein → In Sub-Tasks zerlegen
- Hat der Task ein einzelnes, messbares Akzeptanzkriterium?
- Falls nein → Präzisieren oder aufteilen

### 3b – Abhängigkeiten bestimmen

Für jeden Task:
- Welche anderen Tasks müssen vorher abgeschlossen sein?
- `depends_on` als Task-ID-Liste setzen

### 3c – Priorität bestimmen

Verwende diese Heuristik:
| Bedingung | Priorität |
|-----------|-----------|
| Blockiert ≥ 3 andere Tasks | `critical` |
| Ist in aktueller Roadmap-Phase + hat keine Blocker | `high` |
| Ist in aktueller Roadmap-Phase + hat Blocker | `medium` |
| Ist in nächster Phase | `low` |
| Nice-to-have / Optimierung | `low` |

### 3d – Phasen-Zuordnung

Jeder Task gehört zu einer Roadmap-Phase. Falls keine Roadmap existiert, verwende:
- Phase 1: Setup + Grundstruktur
- Phase 2: Kernfunktionalität
- Phase 3: Erweiterung + Optimierung

---

## Schritt 4: DAG-Validierung (intern)

Prüfe die Abhängigkeitskette:
1. **Keine Zyklen:** Kein Task darf transitiv von sich selbst abhängen
2. **Keine verwaisten Abhängigkeiten:** Jede Task-ID in `depends_on` muss existieren
3. **Kritischer Pfad:** Identifiziere die längste Abhängigkeitskette → Das ist der Mindest-Implementierungszeitraum
4. **Parallelisierbarkeit:** Tasks ohne gegenseitige Abhängigkeit können parallel ausgeführt werden

Falls Probleme gefunden → Sofort korrigieren.

---

## Schritt 5: Dokument generieren

Erstelle `tasks.md` im Wurzelverzeichnis (oder aktualisiere existierende):

```markdown
# Task-Backlog: [Projekt]

| Feld | Wert |
|------|------|
| Generiert | [Datum] |
| Aktuelle Phase | [Phase aus Roadmap] |
| Tasks gesamt | [N] |
| Davon offen | [N] |
| Kritischer Pfad | [N Tasks, geschätzte Dauer] |

---

## Legende

| Feld | Beschreibung |
|------|-------------|
| **ID** | Eindeutiger Task-Identifier (z.B. T-042) |
| **Status** | `done` / `in-progress` / `open` / `blocked` |
| **Priorität** | `critical` / `high` / `medium` / `low` |
| **Quelle** | Referenz auf Ursprungsdokument (z.B. "Roadmap §Phase2, Deliverable 3" oder "PRD FR-007") |
| **Depends** | Task-IDs, die vorher abgeschlossen sein müssen |
| **Akzeptanzkriterium** | Messbares Kriterium – wann ist dieser Task "done"? |

---

## Phase [N]: [Name]

### [Themengruppe]

#### T-[NNN]: [Kurzer, präziser Task-Titel]
| Feld | Wert |
|------|------|
| **Status** | open |
| **Priorität** | high |
| **Quelle** | [Roadmap §X / PRD FR-NNN / Architecture §Y] |
| **Depends** | [T-NNN, T-NNN] oder – |
| **Akzeptanzkriterium** | [Konkretes, testbares Kriterium] |

[Wiederhole für jeden Task, gruppiert nach Thema innerhalb der Phase]

---

## Abhängigkeitsgraph (Zusammenfassung)

[Nur kritischer Pfad + wichtige Parallelisierungsmöglichkeiten]

```
T-001 → T-003 → T-007 → T-012 (Kritischer Pfad: 4 Tasks)
T-002 ──┤
T-004 → T-008 ──┤ (Parallel zu T-003..T-007)
```
```

---

## Schritt 6: Qualitätsvalidierung

Prüfe und **korrigiere sofort**:

- [ ] Jeder Task hat ein `Quelle`-Feld (nicht leer, referenziert existierendes Dokument)
- [ ] Jeder Task hat ein testbares Akzeptanzkriterium (nicht "funktioniert gut")
- [ ] Kein Task dauert > 1 Tag (Faustregel: max. ~8h Implementierung)
- [ ] DAG hat keine Zyklen
- [ ] Alle `depends_on`-Referenzen zeigen auf existierende Task-IDs
- [ ] Tasks, die im Code bereits implementiert sind, haben Status `done`
- [ ] Kritischer Pfad ist dokumentiert
- [ ] Jede Roadmap-Phase hat mindestens einen Task
- [ ] Kein FR aus der PRD-SPEC ist ohne zugehörigen Task

---

## Schritt 7: Datei schreiben und abschließen

Schreibe die finale Datei. Gib abschließend aus:
- Tasks gesamt (davon: done / open / blocked)
- Anzahl Phasen abgedeckt
- Länge des kritischen Pfads
- Anzahl `<!-- REVIEW -->`-Marker
- Abdeckung: Wieviele Roadmap-Deliverables und PRD-FRs haben Tasks?
