---
agent: agent
description: "Kontinuierlicher Verbesserungszyklus: Orchestriert die gesamte Optimierungssuite in einer priorisierten Sequenz. Analysiert den Workspace-Zustand, wählt die wirkungsvollsten Optimierungsbereiche und führt sie gezielt durch – bei jeder Ausführung frisch und adaptiv."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Kontinuierlicher Verbesserungszyklus (Kaizen)

> **Fundamentalprinzip: Zustandslose Frische**
>
> Dieser Prompt ist der Einstiegspunkt für kontinuierliche Workspace-Optimierung. Er operiert bei **jeder Ausführung** als vollständig neuer Zyklus – ohne Erinnerung an vorherige Durchläufe, ohne Annahmen über den aktuellen Zustand, ohne „das wurde schon geprüft"-Shortcut.
>
> **Warum das funktioniert:** Jeder Optimierungszyklus sieht den Workspace so, wie er _jetzt_ ist – nach allen Änderungen, neuen Features, Refactorings und externen Entwicklungen seit dem letzten Lauf.

> **Robustheitsregeln:**
>
> - Der Workspace kann in jedem Zustand sein – von leerem Grundgerüst bis zu vollständig implementiertem MVP.
> - Passe Tiefe und Fokus an den aktuellen Bedarf an: ein halbleerer Workspace braucht Aufbau-Empfehlungen, ein reifer braucht Feinschliff.
> - Plattformgerechte Befehle verwenden.
> - Wenn ein Optimierungsbereich nicht analysierbar ist (fehlendes Tooling, nicht installierte Dependencies): dokumentiere als Blocker und mache mit dem nächsten Bereich weiter.

---

## Schritt 1: Blitz-Zustandserfassung (3 Minuten)

Führe eine schnelle, aber vollständige Bestandsaufnahme durch:

### 1.1 Projektreife bestimmen

```
[ ] Backend-Code existiert (nicht nur __init__.py Stubs)
[ ] Frontend-Code existiert (nicht nur next.js Boilerplate)
[ ] Tests existieren und laufen
[ ] Docker-Umgebung funktional
[ ] CI/CD Pipeline vorhanden
[ ] Mindestens 1 Konnektor implementiert
[ ] Mindestens 1 API-Endpunkt funktional
[ ] Datenbankschema migriert
```

**Reifegrad-Einschätzung:**

- 🔴 **Fundament** (0–2 Checks) → Fokus: Infrastruktur, Grundstruktur
- 🟡 **Aufbau** (3–5 Checks) → Fokus: Code-Qualität, Tests, Sicherheit
- 🟢 **Reifung** (6–7 Checks) → Fokus: Performance, Feinschliff, Dokumentation
- 🔵 **Optimierung** (8 Checks) → Fokus: Alle Bereiche auf höchster Ebene

### 1.2 Letzte Änderungen erkennen

```bash
git log --oneline -20  # Letzte 20 Commits
git diff --stat HEAD~5  # Welche Dateien zuletzt geändert
```

Aus den letzten Änderungen ableiten:

- Welche Module wurden zuletzt bearbeitet? → Dort frische Probleme wahrscheinlich.
- Welche Module wurden lange nicht berührt? → Dort Drift-Risiko.

---

## Schritt 2: Bedarfsanalyse (Extended Thinking)

Basierend auf dem Reifegrad und den letzten Änderungen, priorisiere die Optimierungsbereiche:

### Priorisierungs-Matrix

| Bereich                   | Reifegrad-Relevanz      | Letzte-Änderungen-Relevanz   | Gesamt-Priorität |
| ------------------------- | ----------------------- | ---------------------------- | ---------------- |
| 🔒 Sicherheit & DSGVO     | IMMER HOCH              | Neue API/Auth-Änderungen?    | ...              |
| 📐 Architektur            | 🔴🟡 Hoch, 🟢🔵 Mittel  | Neue Module hinzugekommen?   | ...              |
| 🧪 Tests                  | 🟡🟢 Hoch               | Neuer Code ohne Tests?       | ...              |
| 💻 Code-Qualität          | 🟡🟢🔵 Hoch             | Viel neuer Code?             | ...              |
| ⚡ Performance            | 🟢🔵 Hoch               | Neue DB-Queries/Pipelines?   | ...              |
| 📦 Dependencies           | 🟡🟢🔵 Mittel           | Neue Packages hinzugefügt?   | ...              |
| 📄 Dokumentation          | 🟡🟢🔵 Mittel           | Architektur-Änderungen?      | ...              |
| 🏗️ Infrastruktur          | 🔴🟡 Hoch, 🟢🔵 Niedrig | Docker/Terraform-Änderungen? | ...              |
| 📝 Prompts & Instructions | 🟢🔵 Mittel             | Neue Conventions/Features?   | ...              |

**Auswahl:** Wähle die **Top 3** Bereiche mit höchster Gesamt-Priorität.

---

## Schritt 3: Fokussierte Tiefenoptimierung

Führe für die Top-3-Bereiche eine fokussierte Analyse durch. Nutze die Struktur der spezialisierten Prompts als Leitfaden:

### Bereich 1: [Höchste Priorität]

Wende die relevante Analyse aus dem entsprechenden Optimierungsprompt an:

- `optimize-security.prompt.md` für Sicherheit & DSGVO
- `optimize-architecture.prompt.md` für Architektur
- `optimize-testing.prompt.md` für Tests
- `optimize-code-quality.prompt.md` für Code-Qualität
- `optimize-performance.prompt.md` für Performance
- `optimize-dependencies.prompt.md` für Dependencies
- `optimize-documentation.prompt.md` für Dokumentation
- `optimize-infrastructure.prompt.md` für Infrastruktur
- `optimize-prompts.prompt.md` für Prompts & Instructions

**Wichtig:** Führe die Analyse INLINE durch, nicht als separaten Prompt-Aufruf. Nutze die Phasen-Struktur des jeweiligen Prompts als Checkliste, aber passe die Tiefe an die verfügbare Zeit an.

### Bereich 2: [Zweithöchste Priorität]

[Analog zu Bereich 1]

### Bereich 3: [Dritthöchste Priorität]

[Analog zu Bereich 1]

---

## Schritt 4: Quick Wins identifizieren

Unabhängig von den Top-3-Bereichen – suche nach Quick Wins, die sofort umsetzbar sind:

### 4.1 Automatische Checks (falls Tooling verfügbar)

```bash
# Python Linting – sofortige Fixes
cd backend && ruff check --fix pwbs/ tests/

# TypeScript Type-Check
cd frontend && npm run type-check 2>&1 | head -50

# Compiler Errors/Warnings
# (nutze das problems-Tool für IDE-Fehler)
```

### 4.2 Schnell-Scan-Patterns

Suche nach offensichtlichen Problemen (je 1 Minute):

```
# Fehlende owner_id in DB-Queries
grep -rn "session.execute" pwbs/ | grep -v "owner_id"

# Hardcodierte Secrets
grep -rn "password\|secret\|api_key\|token" pwbs/ --include="*.py" | grep -v "test" | grep -v "#"

# TODO-Kommentare
grep -rn "TODO\|FIXME\|HACK\|XXX" pwbs/ tests/

# Bare except
grep -rn "except:" pwbs/ --include="*.py"

# Any in Type Hints
grep -rn ": Any" pwbs/ --include="*.py"
```

---

## Schritt 5: Implementierung

### 5.1 Priorisierte Fixes

1. **🔴 Sicherheitskritisch:** SOFORT beheben (owner_id, Secrets, Injection)
2. **🟡 Qualitätskritisch:** In diesem Zyklus beheben
3. **🟢 Verbesserungen:** Die besten 5 implementieren
4. **🔵 Empfehlungen:** Als README oder Kommentar dokumentieren

### 5.2 Validierung nach jedem Fix

- Linting läuft durch
- Bestehende Tests brechen nicht
- Neuer Fix ist konsistent mit Architektur-Prinzipien

---

## Schritt 6: Zyklus-Bericht

```markdown
# Optimierungszyklus – [Datum]

## Workspace-Reifegrad

[🔴/🟡/🟢/🔵] – [Kurzbeschreibung]

## Fokus-Bereiche (Top 3)

1. [Bereich]: [Wichtigstes Finding] → [Aktion]
2. [Bereich]: [Wichtigstes Finding] → [Aktion]
3. [Bereich]: [Wichtigstes Finding] → [Aktion]

## Durchgeführte Optimierungen

| #   | Bereich | Beschreibung | Dateien |
| --- | ------- | ------------ | ------- |
| 1   | ...     | ...          | ...     |

## Quick Wins umgesetzt

1. ...

## Empfehlungen für den nächsten Zyklus

Die folgenden Bereiche sollten als nächstes fokussiert werden:

1. [Bereich]: [Warum] → Nutze `optimize-[bereich].prompt.md`
2. [Bereich]: [Warum] → Nutze `optimize-[bereich].prompt.md`
3. [Bereich]: [Warum] → Nutze `optimize-[bereich].prompt.md`
```

---

## Opus 4.6 – Kognitive Verstärker

- **Kontextuelle Priorisierung:** Nicht jeder Bereich ist in jedem Projektzustand gleich wichtig. Der Reifegrad bestimmt den Fokus.
- **Effizienz-Maximierung:** Begrenzte Zeit → maximaler Impact. Quick Wins + tiefe Analyse der kritischsten Bereiche.
- **Adaptivität:** Jeder Lauf passt sich dynamisch an – neuer Code, neue Dependencies, neue Risiken → neuer Fokus.
- **Ganzheitliche System-Perspektive:** Auch wenn nur 3 Bereiche tief analysiert werden – die Blitz-Erfassung sieht alles. Nichts fällt durchs Raster.
- **Compound Effect:** Jeder Zyklus verbessert den Workspace inkrementell. Nach 10 Zyklen ist jeder Bereich mehrfach optimiert worden.

---

## Verfügbare Spezialisierte Optimierungs-Prompts

Für tiefgehende Analyse einzelner Bereiche stehen folgende Prompts zur Verfügung:

| Prompt                              | Fokus                                     | Wann nutzen                                |
| ----------------------------------- | ----------------------------------------- | ------------------------------------------ |
| `optimize-all.prompt.md`            | Vollständige Analyse aller Bereiche       | Umfassender Review (selten, dafür tief)    |
| `optimize-code-quality.prompt.md`   | Python + TypeScript Code-Qualität         | Nach großen Code-Änderungen                |
| `optimize-architecture.prompt.md`   | Modul-Grenzen, Datenflüsse, Skalierung    | Nach neuen Modulen oder Refactorings       |
| `optimize-security.prompt.md`       | DSGVO, OWASP, OAuth, Verschlüsselung      | Nach Auth/API/Datenbank-Änderungen         |
| `optimize-documentation.prompt.md`  | ADRs, README, API-Docs, Inline-Docs       | Nach Architektur-Entscheidungen            |
| `optimize-testing.prompt.md`        | Coverage, Test-Qualität, Edge Cases       | Nach neuem Code ohne Tests                 |
| `optimize-infrastructure.prompt.md` | Docker, Terraform, CI/CD, DevOps          | Nach Infrastruktur-Änderungen              |
| `optimize-performance.prompt.md`    | Queries, API-Latenz, Embeddings, Frontend | Vor Releases oder nach Nutzerfeedback      |
| `optimize-dependencies.prompt.md`   | CVEs, Versions, Tech Debt                 | Monatlich oder nach Dependency-Updates     |
| `optimize-prompts.prompt.md`        | Prompts & Instructions selbst             | Quartalsweise oder nach neuen Konventionen |
