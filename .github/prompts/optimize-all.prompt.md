---
agent: agent
description: "Meta-Orchestrator: Führt eine vollständige, zustandsunabhängige Optimierungsanalyse des gesamten PWBS-Workspaces durch. Erkennt Verbesserungspotenziale in Code, Architektur, Sicherheit, Dokumentation, Tests, Infrastruktur und Prompts – bei jeder Ausführung frisch und ohne Annahmen über vorherige Läufe."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
  - fetch
---

# PWBS Workspace-Gesamtoptimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Dieser Prompt operiert bei **jeder Ausführung** so, als würde er den Workspace zum ersten Mal sehen. Er trifft keine Annahmen über vorherige Optimierungsläufe, akzeptiert keinen „gut genug"-Zustand und analysiert jede Schicht von Grund auf neu. Die Optimierungskraft ist unabhängig davon, wie oft dieser Prompt bereits ausgeführt wurde.

> **Robustheitsregeln:**
>
> - Prüfe vor jedem Dateizugriff, ob die Datei/das Verzeichnis existiert. Passe dein Vorgehen dynamisch an den tatsächlichen Workspace-Zustand an.
> - Verwende plattformgerechte Shell-Befehle (PowerShell auf Windows, Bash auf Linux/macOS).
> - Überspringe Optimierungsbereiche, für die noch keine Artefakte existieren – dokumentiere diese als „Aufbaupotenzial".
> - Falls ein Bereich bereits auf hohem Niveau ist, suche nach Verfeinerungen auf der nächsten Qualitätsstufe.

---

## Phase 0: Zustandserfassung (Extended Thinking)

Bevor du optimierst, erfasse den **exakten aktuellen Zustand** des Workspaces:

1. **Projektstruktur** – Lies die Verzeichnisstruktur. Welche Module existieren tatsächlich? Welche sind leer oder nur Stubs?
2. **Konfigurationslage** – Lies `pyproject.toml`, `package.json`, `docker-compose.yml`, `tsconfig.json`, `alembic.ini`. Welche Versionen, welche Lücken?
3. **Dokumentationslage** – Existieren ARCHITECTURE.md, ROADMAP.md, CHANGELOG.md, ADRs? Sind sie aktuell?
4. **Code-Umfang** – Wie viel implementierter Code existiert tatsächlich (nicht nur Stubs)?
5. **Test-Situation** – Existieren Tests? Welche Frameworks, welche Abdeckung?
6. **Orchestrierungs-Status** – Lies `docs/orchestration/task-state.json`. Welche Streams/Tasks sind done, open, blocked?
7. **Prompt- & Instruction-Qualität** – Lies alle `.github/prompts/*.prompt.md` und `.github/instructions/*.instructions.md`.

Erstelle daraus ein internes **Zustandsbild** mit Reifegraden:

| Bereich              | Reifegrad                               | Nächste Stufe |
| -------------------- | --------------------------------------- | ------------- |
| Backend-Code         | 🔴 Stub / 🟡 Partial / 🟢 Implementiert | ...           |
| Frontend-Code        | ...                                     | ...           |
| Tests                | ...                                     | ...           |
| Dokumentation        | ...                                     | ...           |
| Sicherheit           | ...                                     | ...           |
| Infrastruktur        | ...                                     | ...           |
| Prompts/Instructions | ...                                     | ...           |

---

## Phase 1: Tiefenanalyse je Bereich

Führe für **jeden existierenden Bereich** eine eigenständige Analyse durch. Nutze Extended Thinking, um verborgene Probleme zu identifizieren:

### 1.1 Code-Qualität (Backend + Frontend)

- Lies **jeden existierenden Python-Source-Datei** in `pwbs/` und prüfe gegen:
  - Vollständige Type Annotations (PEP 484/526, kein `Any`)
  - Pydantic v2 Patterns (`model_config`, `model_dump()`, nicht veraltete API)
  - Async-Konsistenz (`async def` für I/O, kein Blocking im Event-Loop)
  - Fehlerbehandlung-Hierarchie (`PWBSError`-Ableitungen)
  - Import-Ordnung und -Qualität (absolute Imports, keine zirkulären)
  - Dead Code, Duplikation, übermäßige Komplexität
- Lies **jeden existierenden TypeScript/TSX-Datei** in `frontend/src/` und prüfe gegen:
  - Strict TypeScript (kein `any`, explizite Props-Interfaces)
  - Server/Client Component Boundaries (`"use client"` nur wo nötig)
  - API-Abstraktion (kein direktes `fetch()` in Komponenten)
  - Styling-Konsistenz (Tailwind, `cn()`)

### 1.2 Architektur

- Prüfe Modul-Grenzen: Kommunizieren Module nur über Python-Interfaces?
- Dependency-Graph: Gibt es zirkuläre Imports oder unerwartete Kopplungen?
- Sind Agenten-Rollen klar getrennt (IngestionAgent, ProcessingAgent, etc.)?
- Stimmt die implementierte Architektur mit ARCHITECTURE.md überein?
- Gibt es Abstraktions-Lecks oder Schichten-Verletzungen?

### 1.3 Sicherheit & DSGVO

- **owner_id-Audit:** Jede DB-Query mit User-Bezug MUSS `WHERE owner_id = ...` enthalten
- **expires_at-Audit:** Jedes nutzerbezogene Datum MUSS ein Ablaufdatum haben
- **PII-in-Logs:** Suche nach Logging-Statements, die personenbezogene Daten enthalten könnten
- **Secret-Exposition:** Keine hardcodierten API-Keys, Passwörter, Tokens
- **OWASP Top 10:** Injection, Broken Access Control, Cryptographic Failures systematisch prüfen
- **OAuth-Sicherheit:** PKCE, State-Parameter, Token-Rotation, Scope-Minimierung

### 1.4 Dokumentation

- Sind ADRs vollständig und aktuell?
- Stimmen README.md, ARCHITECTURE.md, ROADMAP.md mit dem aktuellen Code-Zustand überein?
- Gibt es undokumentierte Architekturentscheidungen im Code?
- CHANGELOG.md – Ist es gepflegt?
- API-Dokumentation – Sind OpenAPI-Schemas aktuell?

### 1.5 Tests

- Welche Module haben Tests, welche nicht?
- Test-Qualität: Testen sie Verhalten oder nur Implementierung?
- Edge Cases: Leere Listen, None-Werte, abgelaufene Tokens, DB-Fehler abgedeckt?
- Async-Tests: Verwenden sie `pytest-asyncio` korrekt?
- Mocking: Sind externe Abhängigkeiten (DBs, LLM, APIs) gemockt?
- Gibt es Integration-Tests mit Docker?

### 1.6 Infrastruktur & DevOps

- `docker-compose.yml` – Sind alle Services korrekt konfiguriert?
- `Dockerfile` / `Dockerfile.dev` – Multi-Stage, Layer-Caching, Sicherheit?
- Terraform – Ist die IaC vollständig und anwendbar?
- CI/CD – Existiert eine Pipeline? Ist sie umfassend?
- Entwicklungsumgebung – Lässt sich das Projekt einfach aufsetzen?

### 1.7 Prompts & Instructions

- Sind Prompts konsistent im Format und vollständig?
- Decken Instructions alle relevanten Bereiche ab?
- Gibt es Widersprüche zwischen verschiedenen Prompt/Instruction-Dateien?
- Sind die Prompts für Opus 4.6 optimiert (Extended Thinking, Tiefenanalyse)?

---

## Phase 2: Priorisierung und Synthese (Extended Thinking)

Konsolidiere alle Findings in eine priorisierte Optimierungsliste:

### Priorisierung nach Impact × Aufwand

| #   | Bereich | Finding | Schwere                                    | Aufwand | Empfehlung |
| --- | ------- | ------- | ------------------------------------------ | ------- | ---------- |
| 1   | ...     | ...     | 🔴 Kritisch / 🟡 Wichtig / 🟢 Nice-to-have | S/M/L   | ...        |

**Sortierung:** Kritische Sicherheits- und DSGVO-Probleme immer zuerst, dann nach Impact/Aufwand-Verhältnis.

### Kategorisierung

**🔴 Sofort beheben (Sicherheit, DSGVO, Breaking Bugs):**

- ...

**🟡 Nächster Sprint (Qualität, Performance, Robustheit):**

- ...

**🟢 Backlog (Verfeinerungen, Nice-to-haves):**

- ...

**🔵 Aufbaupotenzial (noch nicht existierende Bereiche):**

- ...

---

## Phase 3: Implementierung

Für jedes Finding in der 🔴-Kategorie:

1. **Analysiere** den betroffenen Code im Detail
2. **Implementiere** den Fix vollständig (keine Platzhalter)
3. **Validiere** durch Linting, Type-Checking oder Tests
4. **Dokumentiere** die Änderung kurz

Für 🟡-Findings: Implementiere die Top 5 nach Impact/Aufwand-Verhältnis.

Für 🟢- und 🔵-Findings: Erstelle eine priorisierte Empfehlungsliste mit konkreten nächsten Schritten.

---

## Phase 4: Optimierungsbericht

Erstelle einen strukturierten Abschlussbericht:

```markdown
# PWBS Optimierungsbericht – [Datum]

## Zustandsbild vor Optimierung

[Reifegrad-Tabelle aus Phase 0]

## Durchgeführte Optimierungen

1. [Bereich]: [Was wurde geändert] – [Warum]
2. ...

## Verbleibende Empfehlungen

### Hohe Priorität

- ...

### Mittlere Priorität

- ...

### Aufbaupotenzial

- ...

## Nächste Optimierungsrunde

Empfohlene Fokus-Bereiche für die nächste Ausführung:

1. ...
2. ...
3. ...
```

---

## Opus 4.6 – Kognitive Verstärker

Nutze bei dieser Analyse bewusst folgende Opus-4.6-Stärken:

- **Multi-Perspektiven-Denken:** Betrachte jedes Finding aus der Perspektive von Entwickler, Reviewer, Angreifer und Endnutzer.
- **Kausalketten:** Verfolge jedes Problem bis zur Wurzelursache – nicht nur Symptome behandeln.
- **Kontra-Analyse:** Für jede Empfehlung: Was spricht dagegen? Welche Trade-offs entstehen?
- **Muster-Erkennung:** Identifiziere wiederkehrende Problemmuster über Bereiche hinweg (z.B. konsistent fehlende Validierung, systematisch fehlende Tests).
- **Zukunftsprojektion:** Welche aktuellen Design-Entscheidungen werden in Phase 3/4/5 zu Problemen?
