---
agent: agent
description: "Meta-Optimierung: Optimiert die Prompt- und Instruction-Dateien des PWBS-Workspaces selbst. Prüft alle .prompt.md und .instructions.md auf Vollständigkeit, Konsistenz, Opus-4.6-Optimierung und Wirksamkeit – zustandsunabhängig und selbstreferenziell."
tools:
  - codebase
  - editFiles
  - problems
---

# Prompt- und Instruction-Selbstoptimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Prompts und Instructions sind lebende Dokumente, die mit dem Projekt wachsen müssen. Bei jeder Ausführung alle Prompt- und Instruction-Dateien von Grund auf analysieren – einschließlich dieser Datei selbst. Kein Prompt ist je „fertig optimiert".

> **Robustheitsregeln:**
>
> - Lies jede Datei in `.github/prompts/` und `.github/instructions/` vollständig.
> - Lies auch `copilot-instructions.md` und `AGENTS.md` als Kontext.
> - Verändere die Semantik von Prompts nur, wenn ein klarer Verbesserungsgrund vorliegt.
> - Bewahre die Kern-Identität jedes Prompts – optimiere die Ausführung, nicht den Zweck.

---

## Phase 0: Prompt-Inventar (Extended Thinking)

### 0.1 Prompts kartieren

Lies alle `.github/prompts/*.prompt.md` und erfasse:

| Prompt              | Zweck | Tools | Input-Variablen | Extended Thinking? | Zustandslos? |
| ------------------- | ----- | ----- | --------------- | ------------------ | ------------ |
| architecture-review | ...   | ...   | ...             | ...                | ...          |
| briefing-feature    | ...   | ...   | ...             | ...                | ...          |
| db-migration        | ...   | ...   | ...             | ...                | ...          |
| debug-agent         | ...   | ...   | ...             | ...                | ...          |
| extended-thinking   | ...   | ...   | ...             | ...                | ...          |
| new-connector       | ...   | ...   | ...             | ...                | ...          |
| orchestrator-init   | ...   | ...   | ...             | ...                | ...          |
| task-executor       | ...   | ...   | ...             | ...                | ...          |
| optimize-\*         | ...   | ...   | ...             | ...                | ...          |

### 0.2 Instructions kartieren

| Instruction              | Geltungsbereich         | Kern-Regeln | Widersprüche? |
| ------------------------ | ----------------------- | ----------- | ------------- |
| agents.instructions.md   | pwbs/{agents}/\*_/_.py  | ...         | ...           |
| backend.instructions.md  | \*_/_.py                | ...         | ...           |
| frontend.instructions.md | frontend/\*_/_.{ts,tsx} | ...         | ...           |
| security.instructions.md | \*_/_.{py,ts,tsx}       | ...         | ...           |

### 0.3 copilot-instructions.md analysieren

- Stimmen die Regeln in `copilot-instructions.md` mit den Instructions-Dateien überein?
- Gibt es Redundanzen oder Widersprüche?
- Ist die Gewichtung der Prinzipien klar?

---

## Phase 1: Opus 4.6 Optimierung

### 1.1 Extended Thinking Integration

Für jeden Prompt prüfen:

- [ ] **Trigger klar definiert:** Wann soll Extended Thinking aktiviert werden?
- [ ] **Denk-Struktur vorgegeben:** Schritt-für-Schritt-Analyse statt vager „Denke nach"-Anweisungen
- [ ] **Trade-off-Analysen:** Mindestens 2 Alternativen bewerten vor Implementierung
- [ ] **Selbst-Validierung:** „Prüfe deinen generierten Code auf X, Y, Z" als expliziter Schritt

### 1.2 Kognitive Verstärker

Prüfe, ob Prompts diese Opus-4.6-Stärken explizit nutzen:

- [ ] **Multi-Schritt-Reasoning:** Komplexe Probleme in Teilschritte zerlegen
- [ ] **Perspektiven-Wechsel:** Problem aus verschiedenen Rollen betrachten
- [ ] **Kontra-Analyse:** Gegenargumente für eigene Empfehlungen formulieren
- [ ] **Muster-Erkennung:** Über Einzelfälle hinaus Systemmuster erkennen
- [ ] **Kausalketten:** Jedes Problem bis zur Root Cause verfolgen
- [ ] **Zukunftsprojektion:** Auswirkungen auf spätere Phasen antizipieren

### 1.3 Prompt-Vollständigkeit

Jeder Prompt sollte enthalten:

- [ ] **YAML-Frontmatter:** `agent`, `description`, `tools`
- [ ] **Robustheitsregeln:** Zustandsunabhängig, Existenzprüfungen, Plattform-Awareness
- [ ] **Phase 0 (Zustandserfassung):** Den aktuellen Zustand ERST lesen, DANN analysieren
- [ ] **Strukturierte Analyse-Phasen:** Nummeriert, mit klaren Prüfpunkten
- [ ] **Priorisierung:** Findings nach Schwere/Impact ordnen
- [ ] **Implementierungs-Phase:** Nicht nur identifizieren, sondern beheben
- [ ] **Output-Template:** Strukturierter Bericht am Ende
- [ ] **Opus 4.6 Kognitive Verstärker:** Spezifische Denkmuster für den Bereich

---

## Phase 2: Konsistenz-Prüfung

### 2.1 Cross-Prompt-Konsistenz

- [ ] Gleiche Konventionen in allen Prompts (Terminologie, Format, Struktur)
- [ ] Keine widersprüchlichen Anweisungen zwischen Prompts
- [ ] Referenzen auf andere Prompts sind korrekt (Dateinamen, Pfade)
- [ ] DSGVO-Anforderungen konsistent formuliert
- [ ] Idempotenz-Anforderungen konsistent formuliert

### 2.2 Prompt-Instruction-Alignment

- [ ] Jede Regel in Instructions wird von mindestens einem Prompt durchgesetzt
- [ ] Prompts fordern nichts, was Instructions widersprechen
- [ ] Neue Module/Features werden von bestehenden Instructions abgedeckt

### 2.3 Terminologie-Konsistenz

Einheitliche Begriffe in allen Dateien:

- `owner_id` vs. `user_id` – welcher wird wo verwendet?
- `UnifiedDocument` vs. `UDF` – konsistente Verwendung
- Agent-Namen konsistent geschrieben
- Modul-Pfade konsistent referenziert

---

## Phase 3: Wirksamkeits-Analyse

### 3.1 Prompt-Spezifität

Für jeden Prompt bewerten:

| Aspekt                    | Bewertung | Verbesserung |
| ------------------------- | --------- | ------------ |
| Ziel klar definiert?      | 1-5       | ...          |
| Schritte eindeutig?       | 1-5       | ...          |
| Output klar spezifiziert? | 1-5       | ...          |
| Edge Cases abgedeckt?     | 1-5       | ...          |
| Für Opus 4.6 optimiert?   | 1-5       | ...          |

### 3.2 Abdeckungs-Analyse

Welche Workspace-Bereiche werden von keinem Prompt abgedeckt?

| Bereich                | Abgedeckt durch                            | Lücke? |
| ---------------------- | ------------------------------------------ | ------ |
| Backend Code-Qualität  | optimize-code-quality                      | ...    |
| Frontend Code-Qualität | optimize-code-quality                      | ...    |
| Architektur            | optimize-architecture, architecture-review | ...    |
| Sicherheit             | optimize-security                          | ...    |
| DSGVO                  | optimize-security                          | ...    |
| Tests                  | optimize-testing                           | ...    |
| Dokumentation          | optimize-documentation                     | ...    |
| Infrastruktur          | optimize-infrastructure                    | ...    |
| Performance            | optimize-performance                       | ...    |
| Dependencies           | optimize-dependencies                      | ...    |
| Prompts selbst         | optimize-prompts (dieser)                  | ...    |
| Orchestrierung         | orchestrator-init                          | ...    |
| Neue Features          | task-executor, neue Konnektoren            | ...    |
| Debugging              | debug-agent                                | ...    |
| DB-Migrationen         | db-migration                               | ...    |

### 3.3 Fehlende Prompts identifizieren

Gibt es Bereiche, die einen eigenen Optimierungs-Prompt benötigen?

- Monitoring & Observability?
- API-Design & Versionierung?
- Nutzer-Onboarding & DX?
- Branchenspezifische Optimierungen?

---

## Phase 4: Instructions-Optimierung

### 4.1 Geltungsbereich-Analyse

Für jede Instruction-Datei:

- [ ] `applyTo`-Pattern korrekt und vollständig
- [ ] Keine Dateien fallen durch alle Patterns hindurch
- [ ] Keine widersprüchlichen Rules aus überlappenden Patterns

### 4.2 Regel-Qualität

- [ ] Jede Regel ist falsifizierbar (man kann prüfen, ob sie eingehalten wird)
- [ ] Keine vagen Anweisungen („Schreibe guten Code")
- [ ] Konkrete Beispiele für Do's und Don'ts
- [ ] Regeln sind nach Priorität geordnet

### 4.3 Fehlende Instructions

- [ ] Gibt es Code-Bereiche ohne zugehörige Instructions?
- [ ] Sind neue Technologien/Patterns aufgetaucht, die Instructions brauchen?
- [ ] Brauchen neue Module eigene Instruction-Dateien?

---

## Phase 5: Optimierungen implementieren

### 5.1 Sofort-Fixes

- Widersprüche zwischen Dateien auflösen
- Fehlende Robustheitsregeln ergänzen
- Formatierungsfehler in YAML-Frontmatter korrigieren

### 5.2 Inhaltliche Verbesserungen

- Opus 4.6 kognitive Verstärker wo fehlend ergänzen
- Zustandsunabhängigkeit sicherstellen
- Output-Templates vereinheitlichen
- Checklisten vervollständigen

### 5.3 Neue Dateien erstellen

Falls Lücken identifiziert wurden:

- Neue Prompt-Dateien erstellen
- Instructions erweitern
- copilot-instructions.md aktualisieren

---

## Phase 6: Meta-Optimierungsbericht

```markdown
# Prompt-Optimierungsbericht – [Datum]

## Inventar

- Prompts: .../... analysiert und optimiert
- Instructions: .../... analysiert und optimiert
- copilot-instructions.md: analysiert

## Konsistenz-Score

| Aspekt                       | Score (1-5) |
| ---------------------------- | ----------- |
| Cross-Prompt-Konsistenz      | ...         |
| Prompt-Instruction-Alignment | ...         |
| Terminologie                 | ...         |
| Opus 4.6 Optimierung         | ...         |

## Durchgeführte Verbesserungen

1. ...

## Empfehlungen

1. ...
```

---

## Opus 4.6 – Kognitive Verstärker

- **Meta-Kognition:** Du optimierst das System, das dich selbst steuert. Sei kritisch gegenüber deinen eigenen Anweisungen.
- **Rekursive Verbesserung:** Wenn ein Prompt nach Optimierung besser ist, was bedeutet das für die Optimierungsmethodik selbst?
- **Perspektive des Endnutzers:** Wie würde ein Entwickler diesen Prompt verwenden? Ist der Ablauf natürlich und produktiv?
- **Diminishing Returns:** Wann ist ein Prompt „gut genug" und weitere Optimierung nur noch Rauschen?
