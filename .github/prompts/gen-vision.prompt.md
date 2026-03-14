---
description: "Generiert autonom das Vision-Dokument. Leitet Problem, Zielgruppe, Abgrenzung und Kernfähigkeiten vollständig aus dem Workspace ab – ohne Rückfragen."
agent: agent
tools:
  - codebase
  - editFiles
  - runCommands
---

# Vision-Dokument generieren (autonom)

Du generierst das **Vision-Dokument** für diesen Workspace – vollständig autonom, ohne Rückfragen. Die Vision ist die erste Schicht der semantischen Kette und beantwortet: *Warum existiert dieses Projekt? Für wen? Und was ist es bewusst NICHT?*

> **Autonomie-Prinzip:** Sämtliches Wissen wird aus dem Workspace extrahiert. Du stellst keine Fragen. Du zeigst keine Drafts zur Bestätigung. Du schreibst die finale Version direkt. Falls eine Information nicht im Workspace dokumentiert ist, markiere die Stelle mit `<!-- REVIEW: [Was fehlt und warum es nicht ableitbar war] -->` – aber generiere trotzdem den bestmöglichen Inhalt basierend auf dem Vorhandenen.

> **Robustheitsregeln:**
> 1. Prüfe vor jedem Dateizugriff, ob die Datei/das Verzeichnis existiert.
> 2. Verwende plattformgerechte Shell-Befehle (PowerShell auf Windows, Bash auf Linux/macOS).
> 3. Falls ein Vision-Dokument bereits existiert: Lies es, identifiziere Lücken gemäß der Qualitätscheckliste, und verbessere es – statt es von Grund auf neu zu schreiben.
> 4. Falls Informationen in mehreren Dateien widersprüchlich sind: Priorisiere (1) existierende Docs, (2) README, (3) Code-Analyse.

---

## Schritt 1: Workspace-Tiefenanalyse

Lies **systematisch und vollständig** – überspringe keine Quelle:

### 1a – Projektidentität
- `README.md`, `README`, `readme.md` (Hauptquelle für Projektbeschreibung)
- Alle `.md`-Dateien im Wurzelverzeichnis (oft Vision, Mission, Contributing-Guides)
- `docs/`-Verzeichnis vollständig scannen (Titel + erste 50 Zeilen jeder Datei)
- `.github/copilot-instructions.md` (enthält oft Projektkontext)
- `AGENTS.md` (falls vorhanden – enthält Systemrollen und Zielabsichten)

### 1b – Tech-Stack und Domäne (um das "Was" zu verstehen)
- `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` / `Gemfile` / `pom.xml` / `build.gradle`
  → Projektname, Beschreibungsfeld, Dependencies
- `docker-compose.yml` / `Dockerfile` (welche Services, welche Ports)
- Haupteinstiegspunkte: `src/main.*`, `app/main.*`, `index.*`, `manage.py`, `main.go`

### 1c – Modulstruktur (um Kernfähigkeiten abzuleiten)
- Verzeichnisstruktur bis Tiefe 3
- Zentrale Module/Packages lesen: `src/`, `app/`, `lib/`, `internal/`, `pkg/`
- Router/Controller/Handler-Dateien (zeigen die Features des Systems)
- Schema/Model-Dateien (zeigen die Kernentitäten)

### 1d – Bestandsdokumentation
- Existierende Vision-Datei? → Verbessern statt neu schreiben
- Existierende Roadmap, PRD, Architecture? → Als Kontextquelle nutzen

---

## Schritt 2: Interne Wissens-Synthese

Bevor du schreibst, beantworte intern (nicht ausgeben) diese Fragen aus dem, was du gelesen hast:

1. **Was ist das Projekt?** → Aus README-Beschreibung, `description`-Feld in Package-Dateien, Docs
2. **Welches Problem löst es?** → Aus README "Motivation"/"Problem"/"Why", existierenden Docs, Code-Kommentaren
3. **Für wen ist es?** → Aus README "Zielgruppe"/"Users"/"For whom", existierenden Personas, dem Domänenkontext
4. **Was ist es NICHT?** → Aus README "Non-Goals", existierenden Docs, und durch Ableitung: Was könnte man verwechselnd erwarten, was das Projekt aber erkennbar nicht tut?
5. **Was sind die Kernfähigkeiten?** → Aus den Top-Level-Modulen und den implementierten Features
6. **Was ist die Kernthese?** → Aus dem Zusammenspiel von Problem + Lösung + Zielgruppe

Falls eine Antwort nicht aus dem Workspace ableitbar ist:
- Leite den bestmöglichen Inhalt aus dem Kontext ab
- Markiere die Stelle mit `<!-- REVIEW: ... -->`

---

## Schritt 3: Dokument generieren

Erstelle das Vision-Dokument (Dateiname: `vision.md` im Wurzelverzeichnis, oder ersetze eine existierende Vision-Datei) mit **exakt diesen Pflichtabschnitten**:

```markdown
# Vision: [Projektname – aus Package-Datei oder README]

## Executive Summary

[2-3 Sätze: Problem + Lösung + Kernthese. Muss alleinstehend verständlich sein.]

**Kernthese:** [Ein einziger falsifizierbarer Satz: "X löst Y für Z, weil W."]

---

## Problemstellung

### Das eigentliche Problem

[Nummerierte Liste der Schmerzpunkte – konkret, nicht abstrakt.
Abgeleitet aus: README-Motivation, existierenden Docs, Domänenanalyse.]

1. **[Schmerzpunkt]:** [Beschreibung mit Konsequenz]
2. ...

### Warum bisherige Lösungen nicht ausreichen

| Alternative | Stärke | Lücke (was fehlt) |
|-------------|--------|--------------------|
| [Tool/Ansatz 1] | [Was es kann] | [Was es NICHT kann, das dieses Projekt löst] |
| [Tool/Ansatz 2] | ... | ... |

---

## Zielbild

### Was das System ist

[Nummerierte Fähigkeiten – abgeleitet aus den implementierten/geplanten Modulen.]

1. [Fähigkeit – nicht Feature-Name, sondern was es für den Nutzer bedeutet]
2. ...

### Was es nicht ist

[Mindestens 3 Abgrenzungen – abgeleitet durch Analyse, was das Projekt erkennbar NICHT tut,
obwohl man es einer ähnlichen Software zuschreiben könnte.]

- **Kein [X]** – [Begründung, warum nicht / was stattdessen]
- **Kein [Y]** – ...
- **Kein [Z]** – ...

---

## Zielgruppe

### Primäre Zielgruppe

**[Rolle/Bezeichnung]:** [Beschreibung – konkret genug, dass man sich eine Person vorstellen kann.
Abgeleitet aus README, Docs, dem Domänenkontext der implementierten Features.]

### Sekundäre Zielgruppe

[Falls aus dem Workspace ableitbar, sonst weglassen.]

---

## Kernfunktionen

[Für jede Top-Level-Fähigkeit des Systems – abgeleitet aus Modulstruktur + API-Routen + Features:]

### 1. [Fähigkeit]

- [Was sie tut]
- [Welches Problem sie löst]
- [Wie sie sich von Alternativen unterscheidet]

### 2. [Fähigkeit]
...

---

## Alleinstellungsmerkmale

| Merkmal | Beschreibung |
|---------|-------------|
| [USP 1] | [Warum das anders/besser ist als bei Alternativen] |
| [USP 2] | ... |
```

---

## Schritt 4: Qualitätsvalidierung

Prüfe das generierte Dokument gegen diese Checkliste. **Korrigiere Verletzungen sofort**, bevor du die Datei schreibst:

- [ ] ≥ 3 "Was es NICHT ist"-Abgrenzungen vorhanden
- [ ] Kernthese ist in einem Satz formuliert und falsifizierbar
- [ ] Zielgruppe ist konkret genug, dass man sich eine reale Person vorstellen kann
- [ ] **Kein Abschnitt enthält Technologie-Entscheidungen** (Sprachen, Frameworks, DBs gehören in ARCHITECTURE.md, nicht hierher)
- [ ] Executive Summary funktioniert alleinstehend
- [ ] Jeder Abschnitt enthält Substanz – keine leeren Platzhalter, kein "TBD", keine `[Hier einfügen]`-Stellen
- [ ] `<!-- REVIEW: ... -->`-Marker sind begründet und die umliegenden Inhalte trotzdem sinnvoll

---

## Schritt 5: Datei schreiben und abschließen

Schreibe das finale Dokument. Erstelle es als neue Datei oder aktualisiere die existierende. Gib abschließend eine knappe Zusammenfassung:
- Welche Quellen im Workspace den meisten Inhalt geliefert haben
- Wie viele `<!-- REVIEW -->`-Marker gesetzt wurden (und wofür)
