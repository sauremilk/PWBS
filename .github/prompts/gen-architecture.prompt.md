---
description: "Generiert autonom das Architektur-Dokument. Leitet Tech-Stack, Muster, Komponenten und Designprinzipien mit Implikationen vollständig aus dem Code ab – ohne Rückfragen."
agent: agent
tools:
  - codebase
  - editFiles
  - runCommands
---

# Architektur-Dokument generieren (autonom)

Du generierst das **Architektur-Dokument** für diesen Workspace – vollständig autonom, ohne Rückfragen. Die Architektur ist die dritte Schicht der semantischen Kette und beantwortet: *Wie wird es gebaut? Welche Prinzipien gelten – und was bedeuten sie konkret für den Code?*

> **Autonomie-Prinzip:** Sämtliches Wissen wird aus dem Workspace extrahiert. Du stellst keine Fragen. Du schreibst die finale Version direkt. Die Architektur ist zu 80–90% aus dem Code ableitbar – nutze das. Für die restlichen 10–20% (Designprinzipien, Skalierungspfad) leite aus dem Gesamtkontext ab und markiere Unsicherheiten mit `<!-- REVIEW: ... -->`.

> **Kernregel:** Jedes Designprinzip hat eine **Implikations-Spalte**. Ein Prinzip ohne "Was bedeutet das konkret für den Code?" ist wertlos.

> **Robustheitsregeln:**
> 1. Prüfe vor jedem Dateizugriff, ob die Datei existiert.
> 2. Verwende plattformgerechte Shell-Befehle.
> 3. Falls ein Architektur-Dokument bereits existiert: Lies es, identifiziere Lücken, verbessere es.
> 4. Falls Vision und Roadmap nicht existieren: Arbeite trotzdem – der Großteil kommt aus dem Code. Markiere Vision/Roadmap-Referenzen mit `<!-- REVIEW: Vision/Roadmap fehlt -->`.

---

## Schritt 1: Systematische Code-Analyse

Untersuche **jede dieser Quellen** – überspringe keine:

### 1a – Tech-Stack erkennen
- **Dependency-Dateien lesen:** `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, `pom.xml`, `build.gradle`, `requirements.txt`, `Pipfile`
  → Extrahiere: Sprache, Framework, Libraries, Versionen
- **Lock-Files scannen** (nur Überschriften/Versionen): `package-lock.json`, `poetry.lock`, `Cargo.lock`
  → Bestätige indirekte Abhängigkeiten

### 1b – Architekturmuster erkennen
- **Verzeichnisstruktur** bis Tiefe 4
  → Ist es Monolith, Modular Monolith, Microservices, Serverless, Monorepo?
- **Einstiegspunkte:** `main.*`, `app.*`, `index.*`, `server.*`, `manage.py`
  → Wie startet die Anwendung? Wie viele Prozesse?
- **Import-Analyse:** Suche nach internen Imports in 5–10 zentralen Dateien
  → Kommunizieren Module über direkte Imports, HTTP, Events, Queue?

### 1c – Datenbanken & Persistenz
- `docker-compose.yml`: Welche DB-Services sind definiert?
- Migrations-Ordner: `migrations/`, `alembic/`, `prisma/`, `db/migrate/`
  → Schema-Änderungen lesen → Datenmodell ableiten
- ORM-Models / Schema-Dateien: `models/`, `schemas/`, `entities/`
  → Kernentitäten + Beziehungen

### 1d – API-Oberfläche
- Router/Controller/Handler-Dateien finden und lesen
  → Alle Endpunkte mit HTTP-Methode + Pfad extrahieren
- OpenAPI/Swagger-Spec (falls vorhanden): `openapi.json`, `swagger.yml`
- GraphQL-Schema (falls vorhanden): `schema.graphql`, `schema.gql`

### 1e – Infrastruktur & Deployment
- `Dockerfile`, `docker-compose.yml` → Container-Topologie
- `terraform/`, `pulumi/`, `cdk/` → Cloud-Infrastruktur
- `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile` → CI/CD-Pipeline
- `nginx.conf`, `caddy`, Reverse-Proxy-Konfiguration

### 1f – Sicherheit & Auth (erkennbar aus Code)
- Auth-Middleware, JWT-Handling, OAuth-Implementierungen finden
- Verschlüsselung: Suche nach `encrypt`, `decrypt`, `Fernet`, `KMS`, `bcrypt`, `argon2`
- CORS-Konfiguration
- Rate-Limiting-Implementierung
- Umgebungsvariablen-Handling (`.env.example`, Config-Klassen)

### 1g – Test-Strategie
- Test-Verzeichnisse und -Dateien: Wie viele? Welches Framework?
- Fixtures, Mocks, Factories → Wie werden externe Abhängigkeiten gehandhabt?
- Führe aus: `find . -name "test_*" -o -name "*_test.*" -o -name "*.test.*" -o -name "*.spec.*" | wc -l` (oder Äquivalent)

---

## Schritt 2: Kontext aus existierenden Docs

Lies (falls vorhanden):
1. **Vision** → Architekturphilosophie und Designprinzipien ableiten
2. **Roadmap** → Evolutionsstufen und Skalierungspfad bestimmen
3. **Existierende Architecture-Docs** → Verbessern statt ersetzen
4. **ADR-Verzeichnis** (`docs/adr/`) → Bereits getroffene Entscheidungen respektieren
5. **`.github/copilot-instructions.md`** → Oft enthält es Architekturprinzipien

---

## Schritt 3: Designprinzipien ableiten

Leite Prinzipien aus dem ab, was der Code **tatsächlich tut** (nicht was er tun sollte):

| Erkennungsmuster im Code | Abgeleitetes Prinzip | Implikation |
|---|---|---|
| `owner_id` in Models, `WHERE owner_id =` in Queries | Mandanten-Isolation | Jede DB-Query gegen Nutzerdaten muss `owner_id`-Filter enthalten |
| `encrypt`/`decrypt`, Fernet, KMS-Referenzen | Encryption at Rest | PII-Felder spaltenweise verschlüsselt, Key-Rotation implementiert |
| `ON CONFLICT DO UPDATE`, `MERGE` in Cypher | Idempotenz | Writes als Upsert, Pipeline ohne Datenverlust neu startbar |
| Async-Handlers, `asyncio`, `await` | Async-First I/O | Alle I/O-Operationen async, Blocking-Code in Thread-Pool |
| Umfangreiche Tests, Fixtures | Testbarkeit | Module über Interfaces entkoppelt, externe Deps mockbar |
| `expires_at`-Felder, Cleanup-Jobs | Datenminimierung / DSGVO | Jedes Datum hat Ablaufdatum, automatisierte Löschung |
| Feature-Flags, Config-basierte Toggles | Progressive Rollout | Neue Features hinter Flags, A/B-testbar |

Falls keine Prinzipien erkennbar: Leite aus dem Anwendungstyp (API, App, Library) generische Best Practices ab und markiere mit `<!-- REVIEW: Abgeleitet, nicht im Code verifiziert -->`.

---

## Schritt 4: Dokument generieren

Erstelle `ARCHITECTURE.md` im Wurzelverzeichnis (oder aktualisiere existierende):

```markdown
# Architektur: [Projektname]

**Version:** 0.1.0
**Stand:** [Heutiges Datum]
**Scope:** [Aktuelle Phase aus Roadmap, oder "Initial" falls keine Roadmap]

---

## 1. Überblick

### 1.1 Architekturphilosophie
[1 Paragraph: Was macht diese Architektur aus? Abgeleitet aus Code-Mustern + Vision.]

### 1.2 Designprinzipien
| Prinzip | Implikation (was es KONKRET für Code bedeutet) |
|---------|------------------------------------------------|
| [Name]  | [Actionable Konsequenz – abgeleitet aus Code]   |

### 1.3 Evolutionsstufen
[ASCII-Diagramm das den aktuellen Stand und geplante Stufen zeigt.
Abgeleitet aus: Aktueller Code-Zustand → Roadmap-Phasen → Vision-Zielbild.]

```
Phase 1          Phase 2          Phase 3
[IST-Stand]      [Nächste Phase]  [Zukunft]
─────────────────────────────────────────────
[Was existiert]  [Was geplant]    [Vision-Ziel]
```

## 2. System-Übersicht

[ASCII-Diagramm aller Komponenten + Datenflüsse.
Abgeleitet aus: docker-compose.yml + Modulstruktur + Import-Analyse.]

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ [Komp.1] │────▶│ [Komp.2] │────▶│ [Komp.3] │
└──────────┘     └──────────┘     └──────────┘
```

## 3. Komponenten-Architektur

### 3.1 [Komponentenname – aus Verzeichnisstruktur]
- **Verantwortung:** [Abgeleitet aus Code in diesem Modul]
- **Abhängigkeiten:** [Abgeleitet aus Imports]
- **Interface:** [Abgeleitet aus exportierten Klassen/Funktionen]
- **Dateien:** [Hauptdateien in diesem Modul]

[Wiederholen für jede erkannte Komponente]

## 4. Datenfluss

[Von externem Input zu persistiertem Output – als Text + Diagramm.
Abgeleitet aus: API-Routen → Service-Layer → Repository → Datenbank.]

## 5. Datenmodell

[Kernentitäten mit Feldern und Beziehungen.
Abgeleitet aus: ORM-Models / Schema-Dateien / Migrations.]

### [Entität 1]
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| ... | ... | ... |

## 6. Sicherheit & Compliance

[Abgeleitet aus erkannten Sicherheitsmustern im Code (Auth, Encryption, CORS, Rate Limiting).
Falls nichts erkennbar: Markiere als Lücke.]

## 7. Skalierungsstrategie

[Abgeleitet aus Architekturmuster + Roadmap.
Monolith → Modular Monolith → Service-Split? Oder schon Services?]

## 8. Tech-Stack

| Schicht | Technologie | Version | Begründung |
|---------|-------------|---------|------------|
| [Schicht] | [Aus Dependencies] | [Aus Lock-Files] | [Aus ADRs, oder abgeleitet] |

## 9. Entwicklungs- und Deployment-Setup

[Abgeleitet aus: docker-compose.yml, Makefiles, package.json scripts, CI/CD.]

```bash
# Entwicklung starten
[Erkannte Befehle aus Makefile/package.json/README]

# Tests ausführen
[Erkannte Test-Befehle]
```
```

---

## Schritt 5: Qualitätsvalidierung

Prüfe und **korrigiere sofort**:

- [ ] **Jedes Designprinzip hat eine Implikations-Spalte** – kein Prinzip ohne konkrete Code-Konsequenz
- [ ] Tech-Stack hat Version + Begründungsspalte
- [ ] Evolutionsstufen referenzieren Roadmap-Phasen (oder sind als "TBD → Roadmap erstellen" markiert)
- [ ] Komponentenbeschreibungen haben klare Verantwortungsgrenzen (nicht "macht verschiedene Sachen")
- [ ] Sicherheitsabschnitt ist **projektspezifisch**, nicht generische OWASP-Liste
- [ ] ASCII-Diagramme sind vorhanden (System-Übersicht + Datenfluss)
- [ ] Datenmodell enthält die realen Entitäten aus dem Code (nicht erfunden)
- [ ] Entwicklungs-Setup-Befehle sind **aus dem Workspace verifiziert** (Makefile, package.json scripts)

---

## Schritt 6: Datei schreiben und abschließen

Schreibe die finale Datei. Gib abschließend aus:
- Erkannte Architekturmuster
- Anzahl Komponenten dokumentiert
- Anzahl Designprinzipien (und wie viele aus Code vs. Docs abgeleitet)
- Anzahl `<!-- REVIEW -->`-Marker
