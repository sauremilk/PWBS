---
agent: agent
description: "Workspace-Gesamtaudit: Analysiert alle Qualitätsdimensionen (Code, Architektur, Sicherheit, Tests, Doku, Infra) in einer priorisierten Sequenz. Zustandsunabhängig bei jeder Ausführung."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Workspace-Audit

Du führst ein vollständiges Qualitätsaudit des PWBS-Workspaces durch. Dieses Audit ist der Einstiegspunkt für kontinuierliche Workspace-Optimierung.

**Fokus (optional):** ${input:focus:Spezifischer Bereich oder leer für Gesamtaudit}
**Tiefe:** ${input:depth:quick (30min) / standard (2h) / thorough (halber Tag)}

---

## Schritt 1: Blitz-Zustandserfassung

Führe eine schnelle, aber vollständige Bestandsaufnahme durch:

### 1.1 Projektreife bestimmen

```
[ ] Backend-Code existiert (nicht nur __init__.py Stubs)
[ ] Frontend-Code existiert (nicht nur Next.js Boilerplate)
[ ] Tests existieren und laufen
[ ] Docker-Umgebung funktional
[ ] CI/CD Pipeline vorhanden
[ ] Mindestens 1 aktiver Konnektor implementiert
[ ] Mindestens 1 API-Endpunkt funktional
[ ] Datenbankschema migriert
```

**Reifegrad-Einschätzung:**

- 🔴 **Foundation** (0–2 Checks) → Fokus: Infrastruktur, Grundstruktur
- 🟡 **Aufbau** (3–5 Checks) → Fokus: Code-Qualität, Tests, Sicherheit
- 🟢 **Reifung** (6–7 Checks) → Fokus: Performance, Feinschliff, Dokumentation
- 🔵 **Optimierung** (8 Checks) → Fokus: Alle Bereiche auf höchster Ebene

### 1.2 Letzte Änderungen erkennen

```bash
git log --oneline -20  # Letzte 20 Commits
git diff --stat HEAD~5  # Welche Dateien zuletzt geändert
```

Ableiten:

- Welche Module wurden zuletzt bearbeitet? → Dort frische Probleme wahrscheinlich
- Welche Module wurden lange nicht berührt? → Dort Drift-Risiko

---

## Schritt 2: Bedarfsanalyse (Extended Thinking)

Basierend auf Reifegrad und letzten Änderungen, priorisiere die Audit-Bereiche:

### Priorisierungs-Matrix

| Bereich               | Reifegrad-Relevanz      | Letzte-Änderungen-Relevanz   | Priorität |
| --------------------- | ----------------------- | ---------------------------- | --------- |
| 🔒 Sicherheit & DSGVO | IMMER HOCH              | Neue API/Auth-Änderungen?    | ...       |
| 📐 Architektur        | 🔴🟡 Hoch, 🟢🔵 Mittel  | Neue Module hinzugekommen?   | ...       |
| 🧪 Tests              | 🟡🟢 Hoch               | Neuer Code ohne Tests?       | ...       |
| 💻 Code-Qualität      | 🟡🟢🔵 Hoch             | Viel neuer Code?             | ...       |
| ⚡ Performance        | 🟢🔵 Hoch               | Neue DB-Queries/Pipelines?   | ...       |
| 📦 Dependencies       | 🟡🟢🔵 Mittel           | Neue Packages hinzugefügt?   | ...       |
| 📄 Dokumentation      | 🟡🟢🔵 Mittel           | Architektur-Änderungen?      | ...       |
| 🏗️ Infrastruktur      | 🔴🟡 Hoch, 🟢🔵 Niedrig | Docker/Terraform-Änderungen? | ...       |
| 📊 Monitoring         | 🟢🔵 Mittel             | Neue Endpunkte/Metriken?     | ...       |

**Auswahl:** Wähle die **Top 3** Bereiche mit höchster Priorität für diesen Audit.

---

## Schritt 3: Fokussierte Tiefenanalyse

Führe für die Top-3-Bereiche eine fokussierte Analyse durch.

### Domänen-Referenz

Verwende die Checklisten aus `.github/checklists/{domain}.md` falls vorhanden, sonst die eingebetteten Kernchecks:

| Domain           | Kernchecks                                                       |
| ---------------- | ---------------------------------------------------------------- |
| `security`       | owner_id-Audit, OWASP Top 10, OAuth-Sicherheit, PII-Scanning     |
| `architecture`   | Modul-Grenzen, Datenfluss, Schichtentrennung, Soll-Ist-Abgleich  |
| `code-quality`   | Type Annotations, Pydantic v2, Async-Konsistenz, Import-Qualität |
| `testing`        | Coverage-Map, Fixture-Qualität, Edge Cases, Async-Tests          |
| `documentation`  | ADR-Vollständigkeit, README-Aktualität, Cross-Doc-Konsistenz     |
| `infrastructure` | Docker-Config, Terraform, CI/CD, Dev-Environment                 |
| `performance`    | DB-Queries, Caching, API-Latenz, Frontend-Bundles                |
| `dependencies`   | CVE-Scan, Version-Gaps, Tech Debt, Deprecated Packages           |
| `monitoring`     | Logging, Health-Checks, Metriken, Alerting                       |

### Analyse-Protokoll pro Bereich

Für jeden gewählten Bereich:

1. **Inventar:** Was existiert tatsächlich in diesem Bereich?
2. **Analyse:** Wende domänenspezifische Checks an
3. **Findings:** Dokumentiere mit Priorität (🔴/🟡/🟢/🔵)
4. **Quick Wins:** Identifiziere sofort umsetzbare Verbesserungen

---

## Schritt 4: Quick Wins identifizieren

Unabhängig von den Top-3-Bereichen – suche nach sofort umsetzbaren Verbesserungen:

### 4.1 Automatische Checks (falls Tooling verfügbar)

```bash
# Python Linting – sofortige Fixes
cd backend && ruff check --fix pwbs/ tests/

# TypeScript Type-Check
cd frontend && npm run type-check 2>&1 | head -50

# Security Audits
cd backend && pip-audit
cd frontend && npm audit
```

### 4.2 Schnell-Scan-Patterns (je 1 Minute)

```bash
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
2. **🟡 Qualitätskritisch:** In diesem Audit beheben
3. **🟢 Verbesserungen:** Die besten 5 implementieren
4. **🔵 Empfehlungen:** Als Task oder Kommentar dokumentieren

### 5.2 Validierung nach jedem Fix

- Linting läuft durch
- Bestehende Tests brechen nicht
- Neuer Fix ist konsistent mit Architektur-Prinzipien

---

## Schritt 6: Audit-Bericht

```markdown
# Workspace-Audit – [Datum]

## Zustandsbild

- **Reifegrad:** [🔴/🟡/🟢/🔵] – [Kurzbeschreibung]
- **Fokus-Bereiche:** [Top 3 aus Priorisierung]

## Findings nach Priorität

### 🔴 Kritisch (sofort)

| #   | Bereich | Finding | Aktion |
| --- | ------- | ------- | ------ |

### 🟡 Wichtig (nächster Sprint)

...

### 🟢 Nice-to-have (Backlog)

...

### 🔵 Aufbaupotenzial

...

## Durchgeführte Fixes

1. [Bereich]: [Was wurde geändert] – [Warum]
2. ...

## Empfehlungen für nächsten Audit-Zyklus

- Fokus auf: ...
- Neue Checks für: ...
```

---

## Opus 4.6 – Kognitive Verstärker

Nutze Extended Thinking für:

1. **Muster-Erkennung:** Gibt es wiederkehrende Probleme über mehrere Bereiche?
2. **Root-Cause-Analyse:** Sind Findings Symptome eines tieferliegenden Problems?
3. **Impact-Projektion:** Welche Findings haben die größte Hebelwirkung?
4. **Kontra-Check:** Gibt es gute Gründe, ein Finding NICHT zu fixen?
