---
description: "Vertieft und erweitert bereits generierte Fundament-Dokumente auf die Qualitätsstufe eines reifen Workspaces – besonders tasks.md von 20 auf 100+ Tasks mit vollständigem Format. Führe diesen Prompt NACH gen-*.prompt.md aus."
agent: agent
tools:
  - codebase
  - editFiles
  - runCommands
---

# Fundament-Dokumente vertiefen (autonom)

Du vertiefst und erweiterst bereits generierte Fundament-Dokumente – vollständig autonom, ohne Rückfragen. Dieser Prompt wird **nach** `gen-tasks.prompt.md`, `gen-prd-spec.prompt.md` und den anderen gen-\* Prompts ausgeführt und hebt die Dokumentqualität von "Grundstruktur vorhanden" auf "voll ausgearbeitetes Planungsdokument".

> **Worum es geht:** Automatisch generierte Dokumente enthalten oft korrekte Struktur, aber zu wenig Tiefe. tasks.md hat 10 Tasks statt 80+. Personas haben einen Satz pro Schmerzpunkt statt einer konkreten Konsequenz. Architecture-Prinzipien fehlen die Implikations-Spalte. Dieser Prompt schließt genau diese Lücken.

> **Nicht anfassen:** Korrekte, bereits tiefe Abschnitte werden NICHT verändert. Nur ergänzen und vertiefen, nicht ersetzen oder umstrukturieren.

> **Robustheitsregeln:**
>
> 1. Prüfe vor jedem Dateizugriff, ob die Datei existiert.
> 2. Falls kein Fundament vorhanden (keine tasks.md, keine PRD-SPEC): Abbruch. "Keine generierten Fundament-Dokumente gefunden. Führe zuerst `bootstrap-foundation.prompt.md` aus."
> 3. Arbeite inkrementell: Lies → Analysiere Lücken → Erweitere → Schreibe zurück.

---

## Phase 1: Bestandsaufnahme

Lies alle existierenden Fundament-Dokumente und bewerte die Tiefe:

| Dokument     | Pfad                       | Tiefe | Hauptlücken |
| ------------ | -------------------------- | ----- | ----------- |
| Vision       | `vision*.md` / `VISION.md` | ?     | ?           |
| Roadmap      | `ROADMAP.md`               | ?     | ?           |
| Architecture | `ARCHITECTURE.md`          | ?     | ?           |
| PRD-SPEC     | `PRD-SPEC.md`              | ?     | ?           |
| Tasks        | `tasks.md`                 | ?     | ?           |

**Tiefenbewertung (intern):**

- **Flach:** Tabellen ohne Fließtext, < 3 Acceptance Criteria pro Task, Personas ohne Zeitangaben, < 30 Tasks
- **Mittel:** Struktur vorhanden, einige Abschnitte ausgearbeitet, 30–60 Tasks
- **Tief:** Vollständige Paragrafen, 5+ Acceptance Criteria, stundengenauer Tagesablauf, 80+ Tasks

---

## Phase 2: tasks.md vertiefen

> Dies ist die kritischste Phase – tasks.md ist oft am stärksten unterversorgt.

### 2a – Format-Analyse

Prüfe das Format aller existierenden Tasks in tasks.md:

**Das korrekte vollständige Task-Format ist:**

```markdown
#### TASK-[NNN]: [Präziser Titel – konkrete Aktion, nicht abstrakt]

| Feld             | Wert                                                                    |
| ---------------- | ----------------------------------------------------------------------- |
| **Priorität**    | P0 (kritisch) / P1 (Must-Have MVP) / P2 (Should-Have) / P3 (Could-Have) |
| **Bereich**      | Backend / Frontend / Infra / Auth / DB / LLM / Testing / Docs / DevOps  |
| **Aufwand**      | XS (<2h) / S (0.5–1 Tag) / M (2–3 Tage) / L (1 Woche) / XL (>1 Woche)   |
| **Status**       | 🔴 Offen / 🟡 In Arbeit / 🟢 Fertig / ⛔ Blockiert                      |
| **Quelle**       | [Exakte Quellenangabe: Dokument + Abschnitt/Heading]                    |
| **Abhängig von** | [TASK-NNN, TASK-NNN] oder –                                             |
| **Blockiert**    | [TASK-NNN, TASK-NNN] oder –                                             |

**Beschreibung:** [2–4 Sätze. Was genau muss implementiert werden? Welche Randfälle sind relevant? Welche Entscheidungen sind zu treffen? Nicht allgemein – konkret auf dieses Projekt bezogen.]

**Acceptance Criteria:**

- [ ] [Testbares Kriterium mit konkreten Zahlen/Bedingungen]
- [ ] [Testbares Kriterium – Grenzfall oder Fehlerfall]
- [ ] [Testbares Kriterium – Happy Path]
- [ ] [Testbares Kriterium – Integration oder Monitoring]

**Technische Hinweise:** [2–3 Sätze. Welche Technologie, welches Muster, welche Bibliothek? Verweise auf spezifische Abschnitte in Architecture/PRD-SPEC/ADRs. Was ist NICHT in Scope dieses Tasks?]
```

Für jeden existierenden Task ohne `Beschreibung`-Paragraph, `Acceptance Criteria` oder `Technische Hinweise`: **Sofort ergänzen** durch Ableitung aus Roadmap/Architecture/PRD-SPEC.

### 2b – Abdeckungsanalyse

**Ziel:** Jede implementierbare Arbeitseinheit hat einen Task. Prüfe systematisch alle folgenden Kategorien und erstelle fehlende Tasks:

#### Kategorie A: Features & Module (aus Architecture + PRD-SPEC)

Für jedes Architektur-Modul und jedes FR:

- [ ] Gibt es einen Task für die **Grundstruktur** des Moduls? (Ordner, Interfaces, Basisklassen)
- [ ] Gibt es einen Task für die **Kern-Implementierung**?
- [ ] Gibt es einen Task für **Tests** (Unit + Integration)?
- [ ] Gibt es einen Task für **API-Exposition** (falls zutreffend)?

#### Kategorie B: Datenbank & Schema

- [ ] **Migration** für jede neue Tabelle/Entität
- [ ] **Indizes** für häufig abgefragte Felder
- [ ] **Seed-Daten** für Entwicklungsumgebung
- [ ] **Schema-Validierung** (Pydantic-Schemas, DTO-Klassen)

#### Kategorie C: Auth & Sicherheit

- [ ] **Authentifizierung** (Login, Token-Ausstellung)
- [ ] **Autorisierung** (Middleware, Owner-Filter)
- [ ] **OAuth-Flow** (falls externe Services)
- [ ] **Token-Rotation** (Refresh-Token-Logik)
- [ ] **Rate Limiting** auf API-Endpunkten
- [ ] **Input-Validierung** für alle Endpunkte

#### Kategorie D: Infrastruktur & DevOps

- [ ] **Docker-Compose** für Entwicklungsumgebung
- [ ] **Dockerfile** für Production-Build
- [ ] **CI/CD-Pipeline** (Lint, Test, Build, Deploy)
- [ ] **Environment-Konfiguration** (`.env.example`, Settings-Klasse)
- [ ] **Health-Check-Endpunkte**
- [ ] **Logging-Infrastruktur**

#### Kategorie E: Dokumentation & Planung

- [ ] **ADRs** für jede signifikante Tech-Entscheidung
- [ ] **API-Dokumentation** (OpenAPI, README)
- [ ] **Setup-Guide** (lokale Entwicklung)
- [ ] **Deployment-Dokumentation**

#### Kategorie F: Externe Integrationen (aus Connectors/API-Clients)

Für jeden externen Service/Konnektor:

- [ ] **OAuth-Setup** (Credentials, Scopes)
- [ ] **Client-Implementierung** mit Retry-Logik
- [ ] **Rate-Limit-Handling**
- [ ] **Fehlerbehandlung** (APIError, Timeout, 429)
- [ ] **Tests mit gemockter API**

#### Kategorie G: Qualitätssicherung

- [ ] **Test-Fixtures und Factories** für Testdaten
- [ ] **Integration-Test-Setup** (Test-DBs, Container)
- [ ] **Performance-Tests** für kritische Pfade (falls NF definiert)
- [ ] **Security-Audit** (OWASP Top 10 Review)

### 2c – Neue Tasks generieren

Für jede identifizierte Lücke aus 2b: Erstelle einen vollständigen Task im Format aus 2a. Mit:

- Präzisem Titel (Verb + konkretes Objekt + Kontext)
- Exakter Quellenangabe (welcher Roadmap-Abschnitt / welches FR / welche Architecture-Komponente)
- `Abhängig von` basierend auf logischer Reihenfolge
- `Blockiert` – welche anderen Tasks werden durch diesen ermöglicht?
- 3–5 Acceptance Criteria (konkret und testbar)
- Technische Hinweise (3–5 Sätze mit spezifischen Implementierungshinweisen)

**Mengen-Orientierung:** Ein ernstgemeintes Projekt mit 5+ API-Modulen und 10+ FRs sollte ≥ 80 Tasks haben. Planes Projekt mit < 40 Tasks ist fast immer unterversorgt – überprüfe Categories A–G nochmals.

### 2d – Source-Referenzen präzisieren

Vage `Quelle`-Felder wie "Roadmap" oder "PRD FR-003" → Ersetzen durch spezifische Referenzen:

- ✗ `Roadmap Phase 2`
- ✓ `ROADMAP.md §Phase 2 Kern-Deliverables: "Authentifizierung"`
- ✗ `PRD FR-003`
- ✓ `PRD-SPEC.md FR-003 §Acceptance Criteria: "API-Tokens rotieren nach 30 Tagen"`

### 2e – Abhängigkeitsgraph in tasks.md einfügen/aktualisieren

Falls noch nicht vorhanden oder unvollständig: Füge nach allen Tasks einen Abschnitt ein:

```markdown
## Abhängigkeitsgraph

### Kritischer Pfad

[Längste Abhängigkeitskette – TASK-NNN → TASK-NNN → ...]
Gesamtaufwand kritischer Pfad: [Schätzung]

### Parallelisierbare Tracks

- **Track A** (Backend-Grundstruktur): TASK-NNN, TASK-NNN, ...
- **Track B** (Frontend): TASK-NNN, TASK-NNN, ...
- **Track C** (Infrastruktur): TASK-NNN, TASK-NNN, ...
```

---

## Phase 3: PRD-SPEC vertiefen

Prüfe und ergänze nur wenn nötig:

### 3a – Persona-Tiefe

Für jede Persona prüfen:

- **Tagesablauf:** Enthält er ≥ 6 Zeitpunkte mit Stunden (07:00, 09:30, ...)? Falls nicht: Erweitern
- **Schmerzpunkte:** Hat jeder Schmerzpunkt eine konkrete Konsequenz (Zeitverlust / Business-Auswirkung)?
  - ✗ "Verbringt viel Zeit mit der Suche nach Informationen"
  - ✓ "Verbringt 45 Min/Tag mit der Suche nach Meeting-Notizen → verpasst Kontext für Folge-Meetings, was zu Rückfragen und Vertrauensverlust beim Kunden führt"
- **Datenschutz-Implikation:** Endet das Feld mit einer konkreten System-Anforderung (→ braucht X)?

### 3b – NF-Zahlen

Für jede NF ohne konkrete Zahl: Leite eine aus dem Tech-Stack ab oder schätze nach Projekttyp:

- REST-API: p95 ≤ 200ms, 99.5% Uptime
- Semantische Suche: p95 ≤ 1000ms
- LLM-Aufruf: p95 ≤ 10s (mit timeout 30s)
  Markiere Schätzungen mit `<!-- REVIEW: geschätzt, zu validieren -->`

### 3c – FR-Vollständigkeit

Für jedes erkannte API-Modul / jede UI-Seite aus dem Code: Gibt es ein FR? Falls nicht → ergänzen.

---

## Phase 4: Architecture vertiefen

Prüfe und ergänze nur wenn nötig:

### 4a – Prinzipien-Tabelle

Die Designprinzipien-Tabelle muss eine **Implikations-Spalte** haben:

```
| Prinzip | Bedeutung | Implikation für Entwickler |
|---------|-----------|---------------------------|
```

Falls die Spalte fehlt: Hinzufügen. Für jedes Prinzip ableiten, was das konkret bedeutet (z.B. "Idempotenz → alle DB-Writes als UPSERT, nie blind INSERT").

### 4b – Verworfene Alternativen

Für jede Tech-Entscheidung (PostgreSQL, FastAPI, etc.): Falls kein "Warum nicht X?" dokumentiert ist, ergänze:

```markdown
**Verworfene Alternative:** [Name]
**Grund:** [1–2 Sätze warum abgelehnt]
```

---

## Phase 5: Abschluss

Nach allen Änderungen: Führe die Dateien konsistent zusammen (keine doppelten Task-IDs, korrekte Nummerierung) und gib aus:

```
## Anreicherung abgeschlossen

### tasks.md
- Tasks vorher: [N]
- Tasks nachher: [N] (+[Delta])
- Neue Beschreibungen hinzugefügt: [N]
- Neue Acceptance Criteria hinzugefügt: [N] gesamt
- Neue Technische Hinweise hinzugefügt: [N]
- Fehlende Kategorien abgedeckt: [Liste]

### PRD-SPEC.md
- Personas vertieft: [N]
- NFs mit konkreten Zahlen: [N] (davon geschätzt: [N])
- FRs ergänzt: [N]

### ARCHITECTURE.md
- Prinzipien mit Implikations-Spalte: [N]
- Verworfene Alternativen dokumentiert: [N]

### Offene Review-Marker
[Liste aller <!-- REVIEW --> Stellen die manuell überprüft werden sollten]
```
