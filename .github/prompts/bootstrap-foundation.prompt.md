---
description: "Generiert autonom alle 5 Fundament-Dokumente in Sequenz (Vision → Roadmap → Architecture → PRD-SPEC → Tasks) – vollständig aus dem Workspace abgeleitet, ohne Rückfragen."
agent: agent
tools:
  - codebase
  - editFiles
  - runCommands
---

# Workspace-Fundament generieren (autonom)

Du generierst **alle 5 Fundament-Dokumente** für diesen Workspace in einem einzigen, vollständig autonomen Durchlauf. Keine Rückfragen, keine Review-Schritte, kein manuelles Eingreifen.

> **Autonomie-Prinzip:** Sämtliches Wissen wird aus dem Workspace extrahiert – Code, Konfiguration, existierende Dokumentation, README, Tests. Falls Informationen nicht ableitbar sind, werden sie mit `<!-- REVIEW: ... -->` markiert. Du stellst dem Nutzer keine Fragen.

> **Semantische Kette:** Die 5 Dokumente bilden eine hierarchische Argumentationskette. Jede Schicht referenziert die vorherige und beantwortet eine eigenständige Frage:
>
> | Schicht | Dokument | Beantwortet |
> |---------|----------|-------------|
> | 1 | Vision | *Warum existiert dieses Projekt? Wofür ist es NICHT da?* |
> | 2 | Roadmap | *In welcher Reihenfolge wird gebaut – und was ist wann fertig?* |
> | 3 | Architecture | *Welche technischen Entscheidungen erzwingt die Vision – und welche Alternativen wurden verworfen?* |
> | 4 | PRD-SPEC | *Was genau ist in Scope? Wer sind die Nutzer – tief genug, dass Code-Entscheidungen daraus folgen?* |
> | 5 | Tasks | *Was muss konkret in welcher Reihenfolge implementiert werden – und warum?* |

> **Robustheitsregeln:**
> 1. Prüfe vor jedem Dateizugriff, ob die Datei existiert.
> 2. Verwende plattformgerechte Shell-Befehle.
> 3. Falls ein Dokument bereits existiert: Lies es, bewerte Qualität, verbessere es ODER überspringe es (wenn Qualität ausreichend).
> 4. Falls der Workspace leer ist (kein Code, keine README, keine Docs): Abbruch mit Meldung "Workspace enthält zu wenig Material für autonome Fundament-Generierung."

---

## Phase 0: Bestandsaufnahme

### 0a – Workspace-Struktur analysieren

Lies und analysiere:
1. **Verzeichnisstruktur** – Welche Top-Level-Ordner und Dateien existieren?
2. **README.md** (falls vorhanden) – Projektbeschreibung, Setup-Anweisungen
3. **Package-Files** – `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `pom.xml` etc.
4. **Docker/CI-Konfiguration** – `Dockerfile`, `docker-compose.yml`, `.github/workflows/`
5. **Existierende Dokumentation** – `docs/`, `*.md` im Wurzelverzeichnis
6. **Quellcode-Überblick** – Hauptmodule, Einstiegspunkte, API-Definitionen

### 0b – Bestandsaufnahme der 5 Fundament-Dokumente

Prüfe ob bereits existieren (und deren Qualität):

| Dokument | Erwarteter Pfad | Existiert? | Qualität |
|----------|----------------|------------|----------|
| Vision | `vision*.md` ODER in README | ? | ? |
| Roadmap | `ROADMAP.md` | ? | ? |
| Architecture | `ARCHITECTURE.md` | ? | ? |
| PRD-SPEC | `PRD-SPEC.md` | ? | ? |
| Tasks | `tasks.md` | ? | ? |

**Qualitätsbewertung** (intern, nicht ausgeben):
- **Gut:** Dokument folgt den Qualitätskriterien der jeweiligen gen-*.prompt.md → Überspringen
- **Teilweise:** Grundstruktur vorhanden aber Lücken → Verbessern
- **Schlecht/Fehlend:** Neu generieren

### 0c – Projektkontext synthetisieren

Aus allen gesammelten Informationen intern beantworten (nicht ausgeben):
1. Was ist der Zweck dieses Projekts?
2. Wer ist die Zielgruppe?
3. Welcher Tech-Stack wird verwendet?
4. In welcher Entwicklungsphase befindet sich das Projekt?
5. Welche Kernfähigkeiten hat das System bereits?
6. Was sind erkennbare Architekturprinzipien?

---

## Phase 1: Vision generieren

> Nur ausführen, wenn Vision nicht existiert oder Qualität < "Gut".

Folge der Logik von `gen-vision.prompt.md`:

1. **Quellen:** README, Package-Beschreibung, existierende Docs, Domain-Kontext aus Code
2. **Konstruiere:**
   - Problemstellung (aus README/Docs oder aus Code-Domäne ableiten)
   - Zielgruppe (aus Domäne + Implementierungskontext)
   - Kernprinzipien (aus Code-Patterns: Architekturstil, Sicherheitsmuster, Tech-Entscheidungen)
   - "Was es NICHT ist" (aus Scope-Grenzen: welche benachbarten Probleme werden nicht gelöst?)
   - Kernfähigkeiten (aus implementierten Modulen + README-Beschreibung)
3. **Validiere:** Prinzipien haben Implikations-Spalte, "Was es nicht ist" hat ≥ 3 Einträge
4. **Schreibe:** `vision-[projektname].md` oder `VISION.md`

---

## Phase 2: Roadmap generieren

> Nur ausführen, wenn Roadmap nicht existiert oder Qualität < "Gut".
> Setzt Vision (Phase 1) voraus – lies die gerade generierte oder existierende Vision.

Folge der Logik von `gen-roadmap.prompt.md`:

1. **Quellen:** Vision (gerade generiert oder existierend), Code-Stand, Package-Versionen
2. **Bestimme aktuelle Phase** anhand Code-Reife:
   - Kein lauffähiger Code → Phase 1 (Foundation)
   - Kernfeatures implementiert, keine Tests → Phase 2 (MVP)
   - Tests + CI vorhanden → Phase 3 (Production)
   - Monitoring + Skalierung → Phase 4 (Growth)
3. **Konstruiere Phasen** mit Deliverables, Zeitrahmen, Metriken
4. **Validiere:** Jede Phase hat messbare Erfolgskriterien, Risiken haben Mitigations-Strategien
5. **Schreibe:** `ROADMAP.md`

---

## Phase 3: Architecture generieren

> Nur ausführen, wenn Architecture nicht existiert oder Qualität < "Gut".
> Setzt Vision + Roadmap voraus.

Folge der Logik von `gen-architecture.prompt.md`:

1. **Quellen:** Vision, Roadmap, gesamter Code (Module, Dependencies, Konfiguration)
2. **Konstruiere:**
   - Designprinzipien (aus Code-Patterns abgeleitet, mit Implikations-Spalte)
   - Tech-Stack-Tabelle (aus Package-Files + Imports)
   - Komponentendiagramm (aus Modul-Struktur)
   - Datenfluss (aus Code-Aufrufe zwischen Modulen)
   - Datenmodell (aus Models/Schemas/Migrations)
3. **Validiere:** Jede Tech-Entscheidung hat Begründung, Prinzipien referenzieren Vision
4. **Schreibe:** `ARCHITECTURE.md`

---

## Phase 4: PRD-SPEC generieren

> Nur ausführen, wenn PRD-SPEC nicht existiert oder Qualität < "Gut".
> Setzt Vision + Roadmap + Architecture voraus.

Folge der Logik von `gen-prd-spec.prompt.md`:

1. **Quellen:** Vision, Roadmap, Architecture, API-Routen, Models, Tests
2. **Konstruiere:**
   - Personas (aus Zielgruppe + Domänekontext, stundengenauer Tagesablauf)
   - Produkthypothese (falsifizierbar, aus Vision + Roadmap-Metriken)
   - FRs (aus implementierten + geplanten Features, mit Persona-Referenz)
   - NFs (aus Code-Mustern: Auth, Caching, Rate-Limiting)
3. **Validiere:** Personas haben tiefe Schmerzpunkte mit Konsequenz, jedes FR hat Persona-Bezug
4. **Schreibe:** `PRD-SPEC.md`

---

## Phase 5: Task-Backlog generieren

> Nur ausführen, wenn Tasks nicht existiert oder Qualität < "Gut".
> Setzt mindestens Roadmap + PRD-SPEC voraus.

Folge der Logik von `gen-tasks.prompt.md`:

1. **Quellen:** Roadmap-Deliverables, PRD-FRs, Architecture-Komponenten, Code-Stand
2. **Konstruiere:**
   - Atomare Tasks (≤ 1 Tag, mit Akzeptanzkriterium)
   - `Quelle`-Feld für jeden Task (Rückverfolgbarkeit)
   - Abhängigkeiten (depends_on)
   - Prioritäten (basierend auf Abhängigkeitstiefe + Phase)
3. **Validiere:** DAG ohne Zyklen, kritischer Pfad identifiziert, alle FRs haben Tasks
4. **Schreibe:** `tasks.md`

---

## Phase 6: Semantische Ketten-Validierung

Nach Generierung aller 5 Dokumente, prüfe die Konsistenz der Kette:

### 6a – Vorwärts-Referenzen prüfen

| Von | Nach | Prüfung |
|-----|------|---------|
| Vision → Roadmap | Jede Vision-Kernfähigkeit taucht als Roadmap-Deliverable auf |
| Roadmap → Architecture | Jedes Roadmap-Deliverable ist einer Architektur-Komponente zuordenbar |
| Architecture → PRD-SPEC | Jede Architektur-Komponente ist in mindestens einem FR referenziert |
| PRD-SPEC → Tasks | Jedes FR hat mindestens einen zugehörigen Task |

### 6b – Rückwärts-Referenzen prüfen

| Von | Nach | Prüfung |
|-----|------|---------|
| Tasks → PRD-SPEC | Jeder Task hat ein `Quelle`-Feld, das existiert |
| PRD-SPEC → Vision | Jede Persona referenziert ein Problem aus der Vision |
| Architecture → Vision | Jedes Architekturprinzip referenziert ein Vision-Prinzip |

### 6c – Lücken korrigieren

Falls Lücken gefunden werden:
1. Fehlende Referenz in einem Dokument → Dokument aktualisieren
2. Vision-Kernfähigkeit ohne Roadmap-Deliverable → Roadmap ergänzen
3. FR ohne Task → Task hinzufügen
4. Task ohne Quelle → Quelle zuweisen oder Task in Frage stellen

---

## Phase 7: Abschlussbericht

Gib eine kompakte Zusammenfassung aus:

```
## Fundament-Generierung abgeschlossen

| Dokument | Aktion | Qualität |
|----------|--------|----------|
| Vision | [Generiert / Verbessert / Übersprungen] | [Gut / Teilweise] |
| Roadmap | ... | ... |
| Architecture | ... | ... |
| PRD-SPEC | ... | ... |
| Tasks | ... | ... |

### Statistiken
- Erkannte Projektphase: [Phase X]
- Personas erstellt: [N]
- FRs dokumentiert: [N] (davon implementiert: [N])
- Tasks erstellt: [N] (davon offen: [N])
- Kritischer Pfad: [N Tasks]

### Review-Marker
[N] Stellen wurden mit `<!-- REVIEW -->` markiert.
Diese erfordern manuelle Überprüfung:
1. [Datei]: [Kurzbeschreibung]
2. ...

### Semantische Kette
- Vorwärts-Referenzen: [N/N vollständig]
- Rückwärts-Referenzen: [N/N vollständig]
- Korrekturen durchgeführt: [N]
```
