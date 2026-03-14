---
description: "Generiert autonom die Roadmap. Leitet Phasen, Metriken, Risiken und Out-of-Scope vollständig aus Vision + Workspace ab – ohne Rückfragen."
agent: agent
tools:
  - codebase
  - editFiles
  - runCommands
---

# Roadmap generieren (autonom)

Du generierst die **Roadmap** für diesen Workspace – vollständig autonom, ohne Rückfragen. Die Roadmap ist die zweite Schicht der semantischen Kette und beantwortet: *Wann wird was gebaut? Wie messen wir Erfolg? Was sind die Risiken?*

> **Autonomie-Prinzip:** Sämtliches Wissen wird aus dem Workspace extrahiert. Du stellst keine Fragen. Du zeigst keine Drafts. Du schreibst die finale Version direkt. Falls eine Information nicht ableitbar ist, markiere die Stelle mit `<!-- REVIEW: [Was fehlt] -->`.

> **Robustheitsregeln:**
> 1. Prüfe vor jedem Dateizugriff, ob die Datei existiert.
> 2. Verwende plattformgerechte Shell-Befehle.
> 3. Falls eine Roadmap bereits existiert: Lies sie, identifiziere Lücken, und verbessere sie.
> 4. Falls keine Vision existiert: **Abbruch.** Gib aus: "Keine Vision-Datei gefunden. Führe zuerst `gen-vision.prompt.md` aus." und beende die Ausführung.

---

## Schritt 1: Quelldokumente laden

### Pflichtquellen
1. **Vision-Dokument** finden und vollständig lesen. Suchstrategie: `vision.md`, `vision-*.md`, `VISION.md` im Wurzelverzeichnis. Falls nicht dort: `docs/vision*`. Falls nicht gefunden → **Abbruch.**
2. **Existierende Roadmap** (falls vorhanden) → Verbessern statt neu schreiben.

### Analyse-Quellen (um den aktuellen Projektstand zu bestimmen)
3. **Verzeichnisstruktur** bis Tiefe 3 – sind Module Stubs oder implementiert?
4. **Dependency-Dateien** (`package.json`, `pyproject.toml`, etc.) – welche Libs sind installiert?
5. **Git-Zustand:** Führe `git log --oneline -20` aus → Gibt es viele Commits? Welche Muster (feat, fix, refactor)?
6. **`CHANGELOG.md`** (falls vorhanden) → Was wurde bereits geliefert?
7. **Tests:** Existieren Tests? Wie viele? → `find . -name "test_*" -o -name "*_test.*" -o -name "*.test.*" | wc -l` (oder Äquivalent)
8. **Docker/Infra:** `docker-compose.yml`, `Dockerfile`, Terraform → Wie weit ist die Infrastruktur?
9. **`README.md`**, `ARCHITECTURE.md`, `PRD-SPEC.md` (falls vorhanden) → Zusatzkontext

---

## Schritt 2: Projektstand bestimmen

Bestimme den aktuellen Stand automatisch basierend auf diesen Heuristiken:

| Stand | Erkennungsmerkmale |
|-------|-------------------|
| **Idee** | Nur Docs, kein Code. Oder nur leere Projektstruktur. |
| **PoC / Discovery** | Einzelne Skripte, Notebooks, Proof-of-Concepts. Kein Produktionscode. Wenige Tests. |
| **MVP in Entwicklung** | Modulstruktur vorhanden, teilweise implementiert, einige Tests, Docker existiert. |
| **MVP fertig** | Kernfeatures implementiert, Tests passieren, Deployment-Config vollständig. |
| **Beta / Produktion** | CI/CD, Monitoring, Migration-History, viele Commits, Release-Tags. |

Ordne das Projekt einer dieser Stufen zu und nutze das für die Phasen-Einteilung.

---

## Schritt 3: Phasen ableiten

### 3a – Vergangene Phasen (bereits erledigt)

Aus Git-History, CHANGELOG und implementiertem Code: Was wurde bereits geliefert? Erstelle retrospektive Phasen (kurz, als Kontext).

### 3b – Aktuelle Phase

Was wird gerade gebaut? Ableiten aus:
- Offene TODO/FIXME im Code (`grep -rn "TODO\|FIXME" --include="*.py" --include="*.ts" --include="*.tsx" | head -30`)
- Existierende Task-Dateien (`tasks.md`, `TODO.md`, Issue-Tracker-Referenzen)
- Stubs und `NotImplementedError` im Code
- Module die existieren, aber noch leer/minimal sind

### 3c – Zukünftige Phasen

Ableiten aus:
- Vision-Kernfunktionen, die noch NICHT implementiert sind
- Roadmap-Abschnitte in existierenden Docs
- Architektur-Evolutionsstufen (falls `ARCHITECTURE.md` existiert)
- Out-of-Scope-Listen in existierenden Docs

### 3d – Metriken ableiten

Für jede Phase: Bestimme messbare Erfolgsindikatoren basierend auf:
- Art des Projekts (API → Latenz/Uptime, App → Retention/DAU, Library → Downloads/Adoption, Intern → Nutzungsrate)
- Vision-Zielgruppe (wie viele Early Adopters? Welche Retention?)
- Bereits vorhandene Metriken in Docs

Falls keine Metriken aus dem Workspace ableitbar sind, schätze realistische Werte basierend auf:
- Primäre Zielgruppe aus der Vision
- Phase des Projekts
- Markiere mit `<!-- REVIEW: Geschätzte Metrik, bitte validieren -->`

### 3e – Risiken ableiten

Für jede Phase: Identifiziere Risiken basierend auf:
- Tech-Stack-Komplexität (viele Datenbanken → Ops-Risiko, externe APIs → Abhängigkeitsrisiko)
- Zielgruppe (B2B → Compliance-Risiko, Konsumenten → Adoption-Risiko)
- Erkennbare Schwachstellen im Code (fehlende Tests → Regressionsrisiko, keine Auth → Security-Risiko)
- Abhängigkeiten von externen Services

---

## Schritt 4: Dokument generieren

Erstelle `ROADMAP.md` im Wurzelverzeichnis (oder aktualisiere existierende). **Jede Phase muss exakt diese Struktur haben:**

```markdown
# Roadmap: [Projektname]

[1 Paragraph: Zusammenfassung des Entwicklungsansatzes – abgeleitet aus Vision.]

---

## Phase X: [Name] (Zeitrahmen)

**Ziel der Phase**
[1-2 Sätze, direkt abgeleitet aus Vision-Kernfunktionen. Referenz: "→ Vision §Kernfunktion X"]

**Kern-Deliverables**
- [Konkretes Liefergegenstand 1 – kein vages "Verbesserungen"]
- [Konkretes Liefergegenstand 2]

**Messbare Erfolgsindikatoren**
- ≥ [Zahl] [Metrik] innerhalb von [Zeitraum]
- [Zweite Metrik mit konkreter Zahl]

**Annahmen & Risiken**
- **Annahme:** [Konkret – was wir glauben, aber nicht bewiesen haben]
- **Risiko:** [Konkretes Risiko] → **Konsequenz:** [Was passiert, wenn es eintritt]

**Out of Scope für diese Phase**
- [Was bewusst nicht gebaut wird – abgeleitet aus Vision-Kernfunktionen späterer Phasen]
```

---

## Schritt 5: Qualitätsvalidierung

Prüfe und **korrigiere sofort**:

- [ ] Jede Phase hat ≥ 2 messbare Erfolgsindikatoren mit **konkreten Zahlen**
- [ ] Jede Phase hat ≥ 1 Risiko mit **Konsequenz** (nicht nur "könnte schwierig werden")
- [ ] Jede Phase hat ≥ 1 Annahme, die sich als falsch herausstellen könnte
- [ ] "Out of Scope" ist explizit pro Phase definiert und nicht leer
- [ ] Phase-Ziele sind **rückverfolgbar zu Vision-Kernfunktionen** (explizite Referenz)
- [ ] Deliverables sind konkret genug, um atomare Tasks daraus abzuleiten
- [ ] Phasen-Reihenfolge ist logisch (Fundament vor Features, Backend vor Frontend, Auth vor geschützten Features)
- [ ] Keine Phase enthält nur vage Aussagen wie "Performance verbessern" oder "UX optimieren"
- [ ] Zeitrahmen sind plausibel relativ zur Projektgröße

---

## Schritt 6: Datei schreiben und abschließen

Schreibe die finale Datei. Gib abschließend aus:
- Erkannter Projektstand (und woraus abgeleitet)
- Anzahl Phasen generiert
- Anzahl `<!-- REVIEW -->`-Marker (und wofür)
