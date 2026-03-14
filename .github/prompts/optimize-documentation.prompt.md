---
agent: agent
description: "Tiefenoptimierung der Dokumentation im PWBS-Workspace. Prüft ADRs, README, ARCHITECTURE, ROADMAP, CHANGELOG, API-Docs, Code-Kommentare und Inline-Dokumentation auf Vollständigkeit, Aktualität und Konsistenz."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Dokumentations-Optimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Dokumentation veraltet kontinuierlich. Bei jeder Ausführung jede Dokumentations-Quelle gegen den aktuellen Code-Zustand abgleichen. Was gestern korrekt war, kann heute veraltet sein.

> **Robustheitsregeln:**
>
> - Prüfe Existenz jeder referenzierten Datei. Fehlende Dokumentation ist ein Finding, kein Fehler.
> - Unterscheide zwischen „noch nicht geschrieben" und „veraltet" – beides ist ein Problem, aber unterschiedlicher Natur.
> - Generiere keine Dokumentation für nicht-existierenden Code. Markiere als „Dokumentation vorbereiten, sobald implementiert".

---

## Phase 0: Dokumentations-Inventar (Extended Thinking)

Erfasse den vollständigen Dokumentationsbestand:

### 0.1 Hauptdokumente

| Dokument         | Existiert? | Letzte Änderung | Inhalt aktuell? |
| ---------------- | ---------- | --------------- | --------------- |
| README.md        | ...        | ...             | ...             |
| ARCHITECTURE.md  | ...        | ...             | ...             |
| ROADMAP.md       | ...        | ...             | ...             |
| CHANGELOG.md     | ...        | ...             | ...             |
| AGENTS.md        | ...        | ...             | ...             |
| ORCHESTRATION.md | ...        | ...             | ...             |
| PRD-SPEC.md      | ...        | ...             | ...             |
| GOVERNANCE.md    | ...        | ...             | ...             |

### 0.2 ADR-Verzeichnis

Liste alle ADRs in `docs/adr/` und prüfe:

- [ ] Jede bisherige Architekturentscheidung ist als ADR dokumentiert
- [ ] ADR-Nummern sind lückenlos
- [ ] Status (Proposed/Accepted/Deprecated/Superseded) ist aktuell
- [ ] Kontext und Entscheidung sind verständlich ohne Vorwissen

### 0.3 Technische Dokumentation

| Dokument                  | Pfad                        | Aktuell? |
| ------------------------- | --------------------------- | -------- |
| DSGVO-Konzept             | docs/dsgvo-erstkonzept.md   | ...      |
| Verschlüsselungsstrategie | docs/encryption-strategy.md | ...      |
| PoC-Ergebnisse            | docs/poc-results.md         | ...      |
| Backlog-Dokumente         | docs/backlog/\*.md          | ...      |

### 0.4 Code-nahe Dokumentation

- Prompt-Dateien in `.github/prompts/`
- Instructions in `.github/instructions/`
- `copilot-instructions.md`
- Docstrings in Python-Code
- JSDoc/TSDoc in TypeScript-Code
- OpenAPI-Schema (automatisch via FastAPI)

---

## Phase 1: Aktualitäts-Prüfung

### 1.1 ARCHITECTURE.md vs. Code

Für jeden in ARCHITECTURE.md beschriebenen Aspekt prüfen:

- [ ] Beschriebene Modul-Struktur stimmt mit tatsächlicher Verzeichnisstruktur überein
- [ ] Beschriebene Datenmodelle (UDF, etc.) stimmen mit Pydantic-Modellen überein
- [ ] Beschriebene Technologieversionen stimmen mit `pyproject.toml`/`package.json` überein
- [ ] Beschriebene DB-Schemas stimmen mit Alembic-Migrationen überein
- [ ] Beschriebene API-Endpunkte existieren im Code

### 1.2 ROADMAP.md vs. Fortschritt

- [ ] Aktueller Phasen-Status korrekt
- [ ] Erreichte Meilensteine als erledigt markiert
- [ ] KPIs realistisch und messbar
- [ ] Zeitplanung noch plausibel

### 1.3 CHANGELOG.md

- [ ] Jede signifikante Änderung dokumentiert
- [ ] Format konsistent (Keep a Changelog oder ähnlich)
- [ ] Versions-Nummern korrelieren mit Git-Tags
- [ ] Unreleased-Section aktiv gepflegt

### 1.4 README.md

- [ ] Projektbeschreibung aktuell und klar
- [ ] Setup-Anweisungen funktional (docker compose up, Backend, Frontend)
- [ ] Voraussetzungen vollständig aufgelistet
- [ ] Keine toten Links

---

## Phase 2: ADR-Vollständigkeit

### 2.1 Fehlende ADRs identifizieren

Durchsuche den Code nach Architekturentscheidungen, die nicht als ADR dokumentiert sind:

- Neue Technologien oder Libraries eingebunden
- Ungewöhnliche Patterns oder Konventionen
- Trade-off-Entscheidungen (z.B. Wahl zwischen zwei Ansätzen)
- Sicherheitsentscheidungen

### 2.2 ADR-Qualität

Für jeden existierenden ADR prüfen:

- [ ] **Kontext:** Problem klar beschrieben
- [ ] **Entscheidung:** Konkret und eindeutig
- [ ] **Alternativen:** Mindestens 2 Alternativen mit Begründung für Ablehnung
- [ ] **Konsequenzen:** Positive UND negative Folgen dokumentiert
- [ ] **Status:** Aktuell (Accepted/Deprecated/Superseded)

---

## Phase 3: Konsistenz-Prüfung

### 3.1 Cross-Dokument-Konsistenz

Prüfe auf Widersprüche zwischen:

- ARCHITECTURE.md ↔ AGENTS.md (Modul-Zuordnungen)
- ARCHITECTURE.md ↔ Instructions (Konventionen, Schichtenmodell)
- ROADMAP.md ↔ task-state.json (Phasen, Prioritäten)
- copilot-instructions.md ↔ Instructions-Dateien (Keine Widersprüche)
- ORCHESTRATION.md ↔ task-state.json (Stream-Definitionen)
- Prompts ↔ Instructions (Gleiche Konventionen)

### 3.2 Terminologie-Konsistenz

- [ ] Gleiche Konzepte haben überall den gleichen Namen (z.B. `owner_id` vs. `user_id`)
- [ ] Abkürzungen sind beim ersten Vorkommen erklärt
- [ ] Technische Begriffe konsistent geschrieben

---

## Phase 4: Code-Dokumentation

### 4.1 Python Docstrings

- [ ] Alle öffentlichen Module haben Module-Level-Docstrings
- [ ] Alle öffentlichen Klassen haben Class-Docstrings mit Verantwortlichkeit
- [ ] Alle öffentlichen Methoden haben Docstrings mit Args, Returns, Raises
- [ ] Komplexe Algorithmen haben erklärende Inline-Kommentare
- [ ] Keine Kommentare, die nur den Code wiederholen

### 4.2 TypeScript/React Dokumentation

- [ ] Komplexe Props-Interfaces mit JSDoc-Kommentaren
- [ ] Custom Hooks mit Verwendungsbeispielen dokumentiert
- [ ] API-Client Funktionen mit Parameter- und Return-Beschreibungen

### 4.3 API-Dokumentation

- [ ] OpenAPI-Schema vollständig und korrekt generiert
- [ ] Alle Endpunkte mit Beschreibungen, Beispielen, Fehlercodes
- [ ] Request/Response-Schemas dokumentiert

---

## Phase 5: Optimierungen implementieren

### Priorisierung

| Prio | Kategorie    | Beschreibung                                       |
| ---- | ------------ | -------------------------------------------------- |
| 🔴   | Irreführend  | Dokumentation, die zu falschem Verhalten leitet    |
| 🟡   | Veraltet     | Dokumentation, die nicht mehr zum Code passt       |
| 🟠   | Fehlend      | Wichtige Dokumentation, die nicht existiert        |
| 🟢   | Verbesserbar | Existierende Dokumentation, die klarer sein könnte |

### Für jedes Finding:

1. **Irreführende Dokumentation:** Sofort korrigieren
2. **Veraltete Dokumentation:** Aktualisieren oder als deprecated markieren
3. **Fehlende Dokumentation:** Erstellen (vollständig, kein Stub)
4. **Verbesserbare Dokumentation:** Konkrete Verbesserung vorschlagen

---

## Phase 6: Dokumentationsbericht

```markdown
# Dokumentationsbericht – [Datum]

## Dokumentations-Coverage

| Bereich     | Coverage                              | Aktualität |
| ----------- | ------------------------------------- | ---------- |
| ADRs        | .../... Entscheidungen dokumentiert   | ...        |
| API-Docs    | .../... Endpunkte dokumentiert        | ...        |
| Code-Docs   | .../... öffentliche APIs dokumentiert | ...        |
| Architektur | ...                                   | ...        |

## Korrigierte Dokumente

1. ...

## Neuerstelle Dokumente

1. ...

## Verbleibende Lücken

1. ...
```

---

## Opus 4.6 – Kognitive Verstärker

- **Perspektiven-Wechsel:** Lies jedes Dokument aus Sicht eines neuen Entwicklers, der das Projekt zum ersten Mal sieht. Ist alles verständlich?
- **Lücken-Detektion:** Welche Fragen würde ein neuer Entwickler stellen, die keine vorhandene Dokumentation beantwortet?
- **Konsistenz-Netzwerk:** Baue mental ein Netz aller Querverweise zwischen Dokumenten – wo sind die Bruchstellen?
- **Zukunfts-Relevanz:** Welche Dokumentation wird in Phase 3/4 kritisch, die jetzt erstellt werden sollte?
