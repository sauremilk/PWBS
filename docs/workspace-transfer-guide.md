# Workspace-Transfer-Guide: Was diesen Workspace so effektiv macht

**Erstellt:** 14. März 2026
**Zweck:** Analyse der Erfolgsfaktoren dieses Workspaces und Anleitung zur Übertragung auf andere Projekte.

---

## Kurzfassung: Die 4 Schichten des Systems

```
Schicht 1 – KI-Kontext-Konfiguration (.github/copilot-instructions.md + instructions/)
Schicht 2 – Wiederverwendbare Prompt-Workflows (.github/prompts/)
Schicht 3 – Lebende Architekturdokumentation (AGENTS.md, ORCHESTRATION.md, docs/adr/)
Schicht 4 – Maschinenlesbarer Prozess (task-state.json, PR-Template, tasks.md)
```

Jede Schicht verstärkt die anderen. Fehlt eine, verliert das Gesamtsystem deutlich an Wirkung.

---

## Schicht 1: KI-Kontext-Konfiguration

### `.github/copilot-instructions.md` – Das "Gehirn"

Diese Datei ist der **wichtigste Hebel**. Sie wird von jedem Copilot/Claude-Gespräch im Workspace automatisch geladen und setzt den vollständigen Kontext, bevor du auch nur eine Frage stellst.

**Was sie enthält (und warum es wirkt):**

| Abschnitt                 | Inhalt                                                                           | Wirkung                                           |
| ------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------- |
| **Modellkonfiguration**   | Welches Modell, wann Extended Thinking nutzen                                    | KI aktiviert Tiefenanalyse bei komplexen Aufgaben |
| **Pflicht-Denkmuster**    | 5-Stufen-Schema: Verstehen → Analysieren → Abwägen → Implementieren → Validieren | Verhindert voreiliges Code-Schreiben              |
| **Qualitätsstandard**     | „Keine TODOs" – vollständig oder `NotImplementedError`                           | Keine halbfertigen Ergebnisse                     |
| **Tech-Stack-Tabelle**    | Alle eingesetzten Technologien auf einen Blick                                   | KI wählt idiomatische Lösungen                    |
| **Architekturprinzipien** | 5 nicht verhandelbare Regeln (DSGVO, Idempotenz, etc.)                           | Verhindert Architekturverstöße                    |
| **Code-Konventionen**     | Konkrete Patterns mit Beispielen (falsch vs. richtig)                            | Konsistenter Codestil ohne Nachfragen             |
| **Agent-Rollen**          | Welcher Agent für welches Modul zuständig ist                                    | KI weiß immer, wo Code hingehört                  |

**Das Kernprinzip:** Je mehr kontextuelle "Vorarbeit" du in diese Datei investierst, desto weniger musst du bei jedem Gespräch wiederholen – und desto weniger Fehler macht die KI.

### `.github/instructions/` – Granulare, dateitypgebundene Regeln

Instruction-Dateien mit `applyTo`-YAML-Frontmatter werden **automatisch** für passende Dateien geladen:

```yaml
---
applyTo: "**/*.py"
---
# Diese Regeln gelten für alle Python-Dateien
```

**Im PWBS aktive Instruction-Dateien:**

| Datei                      | `applyTo`                | Inhalt                                                               |
| -------------------------- | ------------------------ | -------------------------------------------------------------------- |
| `backend.instructions.md`  | `**/*.py`                | Pydantic v2-Patterns, FastAPI-Regeln, Async-Konventionen, Idempotenz |
| `frontend.instructions.md` | `frontend/**/*.{ts,tsx}` | TypeScript strict, Server/Client-Boundary, API-Abstraktion           |
| `security.instructions.md` | `**/*.{py,ts,tsx}`       | OWASP Top 10, DSGVO-Mandanten-Isolation, Logging-Regeln              |
| `agents.instructions.md`   | Agent-Modulpfade         | Agenten-spezifische Implementierungsregeln                           |

**Warum das wirkt:** Die KI bekommt immer den richtigen Regelkontext für die Datei, an der sie gerade arbeitet – ohne dass du ihn jedes Mal erwähnen musst.

---

## Schicht 2: Wiederverwendbare Prompt-Workflows

### `.github/prompts/` – Spezialisierte Agenten-Workflowdateien

Prompt-Dateien mit `agent: agent`-Frontmatter werden in VS Code über **„Use Prompt File"** oder `#` im Chat aufgerufen. Sie starten standardisierte, komplexe Workflows.

```yaml
---
description: "Kurze Beschreibung (erscheint in der Prompt-Auswahl)"
agent: agent
tools: ["codebase", "editFiles", "runCommands", "problems"]
---
```

**Prompt-Kategorien im PWBS:**

#### Feature-Prompts (domänenspezifisch)

➜ Für Features, die wiederholt vorkommen (neuer Konnektor, neues Briefing-Feature)

| Prompt                       | Zweck                                                         |
| ---------------------------- | ------------------------------------------------------------- |
| `new-connector.prompt.md`    | Führt durch alle Schritte eines neuen Datenquellen-Konnektors |
| `briefing-feature.prompt.md` | Entwickelt oder debuggt Briefing-Features                     |
| `db-migration.prompt.md`     | Erstellt Alembic-Migrationen mit korrekter Struktur           |
| `debug-agent.prompt.md`      | Systematische Agenten-Fehlerdiagnose                          |

#### Review-Prompts (Qualitätssicherung)

➜ Für Code-Reviews, Architektur-Audits

| Prompt                          | Zweck                                                                          |
| ------------------------------- | ------------------------------------------------------------------------------ |
| `architecture-review.prompt.md` | Vollständige Architekturprüfung mit DSGVO-, Sicherheits- und Design-Checkliste |
| `extended-thinking.prompt.md`   | Tiefenanalyse komplexer Architekturthemen mit Opus 4.6                         |

#### Optimierungssuite (iterative Verbesserung)

➜ Systematische Verbesserung des gesamten Workspaces

| Prompt                            | Fokus                                       |
| --------------------------------- | ------------------------------------------- |
| `optimize-all.prompt.md`          | Meta-Orchestrator: Alle Bereiche auf einmal |
| `optimize-architecture.prompt.md` | Modul-Grenzen, Abhängigkeiten               |
| `optimize-code-quality.prompt.md` | Typing, Patterns, Konsistenz                |
| `optimize-security.prompt.md`     | OWASP, DSGVO-Compliance                     |
| `optimize-testing.prompt.md`      | Coverage, Edge Cases, Fixtures              |
| `optimize-performance.prompt.md`  | Queries, Latenz, Bundles                    |

#### Orchestrierungs-Prompts (Multi-Agent-Koordination)

➜ Für parallele Entwicklungsarbeit

| Prompt                        | Zweck                                                                     |
| ----------------------------- | ------------------------------------------------------------------------- |
| `orchestrator-init.prompt.md` | Initialisiert eine autonome Orchestrator-Session (Claim→Implement→Commit) |
| `task-executor.prompt.md`     | Führt einen einzelnen Task vollständig durch                              |

---

## Schicht 3: Lebende Architekturdokumentation

### `AGENTS.md` – KI-Verhaltensleitfaden

Diese Datei erklärt **der KI selbst**, wie sie im Kontext dieses Projekts denken und arbeiten soll. Sie definiert:

- Arbeitsregeln für KI-Assistenten (was sie tun und was nicht)
- Interne System-Agenten-Rollen mit klaren Zuständigkeiten
- Kommunikationsmuster zwischen Agenten
- Einen Entscheidungsbaum: "Welcher Agent/Modul ist zuständig?"

**Schlüsselwirkung:** Schreibt die KI Code für `pwbs/connectors/`, weiß sie dank AGENTS.md, dass sie `BaseConnector` implementieren, Cursor-Pagination verwenden und Idempotenz sicherstellen muss – ohne dass du es jedes Mal sagst.

### `docs/adr/` – Architecture Decision Records

Für jede bedeutende Architekturentscheidung existiert ein ADR nach dem Template `000-template.md`:

- Kontext (warum war eine Entscheidung nötig?)
- Entscheidung (was wurde gewählt?)
- Bewertete Optionen (Vergleichstabelle)
- Konsequenzen (positiv + negativ)
- DSGVO-Implikationen

**Wirkung:** Die KI kann ADRs lesen und versteht, _warum_ der Code so aussieht wie er aussieht – und wird keine "Verbesserungen" vorschlagen, die gegen bewusste Entscheidungen verstoßen.

### `ORCHESTRATION.md` – Multi-Orchestrator-Protokoll

Wenn mehrere KI-Instanzen oder Entwickler gleichzeitig am Backlog arbeiten, koordiniert dieses Dokument:

- Work Streams mit Slot-Zuweisung
- Claiming-Protokoll (wer arbeitet an was)
- Merge-Konflikt-Strategien
- Commit-Konventionen

---

## Schicht 4: Maschinenlesbarer Prozess

### `docs/orchestration/task-state.json` – Koordinationszustand

Maschinenlesbarer Status aller Tasks: `open`, `in_progress`, `done`, `blocked`. Ermöglicht mehreren KI-Instanzen, ohne Konflikte parallel zu arbeiten.

### `.github/pull_request_template.md` – Qualitätscheckliste

Jeder PR erzwingt die Überprüfung von:

- Code-Qualität (Type Annotations, Commit-Struktur)
- Tests (Unit, Integration)
- DSGVO (`owner_id`-Filter, `expires_at`, Lösch-Kaskade, kein PII in Logs)
- Sicherheit (Auth, Crypto, API)

**Wirkung:** Nichts "rutscht durch" – die Checkliste erinnert auch dann, wenn man müde ist.

### `tasks.md` – Strukturiertes Task-Backlog

Jeder Task enthält:

- Priorität, Bereich, Abhängigkeiten
- Beschreibung + Acceptance Criteria
- Technische Hinweise (Modul, Bibliothek, Algorithmus)

Die KI kann dieses Format lesen und selbst Tasks vollständig implementieren.

---

## Was als Nächstes: Übertragung auf ein anderes Projekt

### Schritt 1 – Universelle Basis-Dateien kopieren (tech-unabhängig)

Diese Dateien enthalten generische Muster und müssen nur minimal angepasst werden:

```
.github/
├── pull_request_template.md     ← Nur DSGVO-Section entfernen/anpassen
├── instructions/
│   └── security.instructions.md ← Nahezu universell einsetzbar
└── prompts/
    ├── architecture-review.prompt.md  ← Checkliste anpassen
    ├── optimize-all.prompt.md          ← Projektnamen ersetzen
    ├── optimize-security.prompt.md    ← Universell
    ├── optimize-testing.prompt.md     ← Framework-Namen anpassen
    ├── orchestrator-init.prompt.md    ← Streamnamen anpassen
    └── task-executor.prompt.md        ← Nahezu universell
docs/
└── adr/
    └── 000-template.md          ← Universell
```

### Schritt 2 – Projekt-spezifische Kerndateien erstellen

Diese Dateien müssen für jedes Projekt neu geschrieben werden:

#### `AGENTS.md` (neu schreiben, 30–60 Min.)

Beantworte für dein Projekt:

- Welche Rollen/Agenten/Module gibt es?
- Was ist deren Zuständigkeit?
- Wie kommunizieren sie (MVP: direkte Aufrufe, Phase 2: Queue)?
- Welche Invarianten müssen immer gelten (analog zu DSGVO/Idempotenz hier)?

#### `.github/copilot-instructions.md` (neu schreiben, 60–90 Min.)

Fülle diese Abschnitte:

1. Modellkonfiguration (welches Modell, wann Extended Thinking)
2. Pflicht-Denkmuster (5-Schritte oder projektspezifisch)
3. Projektkontext (1 Paragraph: Was ist das Projekt?)
4. Tech-Stack-Tabelle
5. Architekturprinzipien (3–7 nicht verhandelbare Regeln)
6. Code-Konventionen mit Beispielen (falsch/richtig)
7. Sicherheitsanforderungen

#### `.github/instructions/backend.instructions.md` / `frontend.instructions.md`

Übernimm die Struktur, ersetze:

- Framework-spezifische Sections (FastAPI → dein Framework)
- Module-Struktur (deine Verzeichnisstruktur)
- Spezifische Patterns (Pydantic v2 → dein ORM/Validator)

### Schritt 3 – Feature-spezifische Prompt-Dateien erstellen

Identifiziere die 3–5 häufigsten wiederkehrenden Entwicklungsaufgaben in deinem Projekt und erstelle je einen Prompt:

```markdown
---
description: "Kurze Beschreibung der Aufgabe"
agent: agent
tools: ["codebase", "editFiles", "runCommands"]
---

# [Aufgaben-Titel]

> **Robustheitsregeln:**
>
> - Prüfe vor jedem Dateizugriff, ob die Datei existiert.
> - Verwende plattformgerechte Shell-Befehle.

## Input

**[Parameter]:** ${input:param_name:Beschreibung, z.B. Modulname}

## Ausführungs-Protokoll

### Phase 1 – Kontext laden

1. Lese [relevante Dateien]
2. Verstehe den bestehenden Code

### Phase 2 – Implementieren

[Konkrete Schritte mit Pflichtregeln]

### Phase 3 – Validieren

[Tests, Checks, Commit-Format]
```

### Schritt 4 – Orchestrierung einrichten (optional, für komplexe Projekte)

Wenn das Projekt groß genug für Parallel-Entwicklung ist:

1. Erstelle `docs/orchestration/task-state.json` mit anfänglicher Struktur:

```json
{
  "version": "1.0",
  "tasks": {},
  "streams": {}
}
```

2. Erstelle `ORCHESTRATION.md` mit deinen Work Streams
3. Definiere `tasks.md` mit dem initialen Backlog

### Schritt 5 – ADRs für bestehende Entscheidungen nacherfassen

Für ein bestehendes Projekt: Schreibe für die 5 wichtigsten bereits getroffenen Architekturentscheidungen je ein ADR (30 Min. Investition, spart viel Kontext-Overhead in KI-Gesprächen).

---

## Zusammenfassung: Prioritätsreihenfolge bei knapper Zeit

| Priorität | Datei                                    | Aufwand              | ROI                                                 |
| --------- | ---------------------------------------- | -------------------- | --------------------------------------------------- |
| **P0**    | `.github/copilot-instructions.md`        | 60–90 Min.           | Extrem hoch – wirkt bei jedem Gespräch              |
| **P0**    | `AGENTS.md`                              | 30–60 Min.           | Sehr hoch – verhindert falsche Modul-Entscheidungen |
| **P1**    | `.github/instructions/*.instructions.md` | 20–30 Min. pro Datei | Hoch – automatische kontextuelle Regeln             |
| **P1**    | `.github/pull_request_template.md`       | 15 Min.              | Hoch – Qualitätssicherung ohne Overhead             |
| **P2**    | `.github/prompts/optimize-*.prompt.md`   | 10 Min. kopieren     | Mittel – sofort einsetzbare Workflows               |
| **P2**    | `docs/adr/000-template.md`               | 5 Min. kopieren      | Mittel – Dokumentationskultur starten               |
| **P3**    | `ORCHESTRATION.md` + `task-state.json`   | 45 Min.              | Hoch – aber nur nötig bei Parallel-Arbeit           |

---

## Anti-Patterns: Was man vermeiden sollte

- **Zu generische copilot-instructions.md:** „Schreib guten Code" bringt nichts. Konkrete Beispiele (falsch/richtig) sind das, was wirkt.
- **Instructions zu früh schreiben:** Erst Architekturentscheidungen treffen (ADRs), dann die Instructions daraus ableiten – nicht umgekehrt.
- **Prompt-Dateien ohne Robustheitsregeln:** Ohne „prüfe ob Datei existiert" brechen Prompts in 30% der Fälle ab.
- **Keine `applyTo`-Muster:** Instructions ohne `applyTo` gelten für alle Dateien und können zu Konflikten führen.
- **task-state.json ohne Commits:** Wenn Status-Updates nicht atomar committet werden, entstehen Konflikte bei paralleler Arbeit.
