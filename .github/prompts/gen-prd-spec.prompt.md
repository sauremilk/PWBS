---
description: "Generiert autonom die PRD-SPEC mit tiefen Personas, falsifizierbarer Hypothese und FRs mit Acceptance Criteria – vollständig aus dem Workspace abgeleitet, ohne Rückfragen."
agent: agent
tools:
  - codebase
  - editFiles
  - runCommands
---

# PRD-SPEC generieren (autonom)

Du generierst das **PRD-SPEC-Dokument** für diesen Workspace – vollständig autonom, ohne Rückfragen. Die PRD-SPEC ist die vierte Schicht der semantischen Kette und beantwortet: *Was genau ist in Scope? Wer sind die Nutzer – tief genug, dass Code-Entscheidungen daraus folgen?*

> **Autonomie-Prinzip:** Sämtliches Wissen wird aus dem Workspace extrahiert. Personas werden aus der Vision-Zielgruppe, dem Domänenkontext und den implementierten Features konstruiert. Funktionale Anforderungen werden aus dem Code reverse-engineered. Du stellst keine Fragen. Falls etwas nicht ableitbar ist: `<!-- REVIEW: ... -->`.

> **Kernregel:** Personas müssen so tief sein, dass ein Entwickler daraus ableiten kann, welche Kompromisse bei einem Feature sinnvoll sind. "Entwickler, 30 Jahre" ist wertlos – "Markus, Senior PM, 8 Meetings am Tag, muss vertrauliche Kundendaten schützen → braucht Audit-Log + Lösch-Button" beeinflusst konkreten Code.

> **Robustheitsregeln:**
> 1. Prüfe vor jedem Dateizugriff, ob die Datei existiert.
> 2. Verwende plattformgerechte Shell-Befehle.
> 3. Falls PRD-SPEC bereits existiert: Lies sie, identifiziere Lücken, verbessere sie.
> 4. Falls Vision fehlt: **Abbruch.** Gib aus: "Keine Vision-Datei gefunden. Führe zuerst `gen-vision.prompt.md` aus."

---

## Schritt 1: Quelldokumente laden

### Pflichtquellen (Abbruch falls nicht vorhanden)
1. **Vision-Dokument** → Problem, Zielgruppe, Kernfunktionen, "Was es nicht ist"

### Erweiterte Quellen (falls vorhanden)
2. **Roadmap** → Aktuelle Phase, Out of Scope, Metriken
3. **Architecture** → Tech-Stack, Datenmodell, Komponenten, API-Endpunkte
4. **Existierende PRD-SPEC** → Verbessern statt ersetzen

### Code-Analyse
5. **API-Routen / Controller / Handler** → Tatsächlich implementierte Features = FRs
6. **Models / Schemas** → Datenmodell, Entitäten
7. **Auth-Implementierung** → Welche Auth-Flows existieren?
8. **Frontend-Seiten** (falls vorhanden) → Welche UI-Flows gibt es?
9. **Tests** → Test-Descriptions zeigen erwartetes Verhalten = Acceptance Criteria

---

## Schritt 2: Personas konstruieren

### 2a – Zielgruppe aus Vision extrahieren

Lies den "Zielgruppe"-Abschnitt der Vision. Identifiziere:
- Primäre Zielgruppe (Rolle + Kontext)
- Sekundäre Zielgruppe (falls vorhanden)

### 2b – Personas ableiten (2–3 Personas)

Für jede erkannte Zielgruppen-Rolle, konstruiere eine **vollständige Persona** nach diesem Schema:

**Ableitung des Tagesablaufs:** Nutze den Domänenkontext des Projekts. Wenn das Projekt z.B. ein Tool für Entwickler ist, beschreibe einen realistischen Entwickler-Arbeitstag mit Meetings, Code-Reviews, Debugging-Sessions. Wenn es für PMs ist, beschreibe einen PM-Arbeitstag mit Stakeholder-Syncs, Sprint-Meetings, Kundeninterviews.

**Ableitung der Schmerzpunkte:** Aus der Vision-Problemstellung + den Features des Systems. Wenn das System eine Suchfunktion hat, leidet die Persona unter "kann Information nicht finden". Wenn es ein Dashboard hat, leidet sie unter "hat keinen Überblick". **Immer mit Konsequenz:** Nicht "findet X schwierig", sondern "verliert 30 Min/Tag mit X, was dazu führt, dass Y".

**Ableitung der Datenschutz-Sensibilität:** Aus dem Domänenkontext + erkannten Sicherheitsmustern im Code. B2B → hoch (NDA-Material). Gesundheit → sehr hoch (HIPAA). Consumer → mittel. **Immer mit Implikation:** Nicht "mittel", sondern "arbeitet mit vertraulichen Kundenstrategien → braucht verschlüsselte Speicherung + granulare Löschfunktion".

### 2c – Persona-Qualitätsprüfung (intern)

Prüfe für jede Persona, bevor du weitermachst:
- [ ] Hat einen realistischen Namen + Rolle + Unternehmen
- [ ] Hat stundengenauer Tagesablauf (min. 6 Zeitpunkte von morgens bis abends)
- [ ] Hat Top-3-Schmerzpunkte mit Zeitverlust ODER Konsequenz
- [ ] Hat Erwartungen, die konkret genug sind, um Features daraus abzuleiten
- [ ] Hat Datenschutz-Feld mit konkreter Implikation für das System

---

## Schritt 3: Funktionale Anforderungen ableiten

### 3a – Aus implementiertem Code (Ist-Zustand)

Für jeden API-Endpunkt / jede UI-Seite / jedes Modul:
→ Formuliere ein FR: "Das System muss [Fähigkeit] unterstützen."
→ Leite Acceptance Criteria aus Test-Beschreibungen ab (falls Tests existieren).

### 3b – Aus Vision-Kernfunktionen (Soll-Zustand)

Für jede Vision-Kernfunktion, die noch nicht implementiert ist:
→ Formuliere ein FR mit dem Hinweis "→ Noch nicht implementiert"
→ Leite Acceptance Criteria aus der Vision-Beschreibung ab.

### 3c – Aus Roadmap-Deliverables (falls Roadmap existiert)

Für jedes Deliverable der aktuellen Phase:
→ Prüfe, ob ein FR existiert. Falls nicht: erstelle eines.

### 3d – Persona-Referenz zuweisen

Für jedes FR: Bestimme, welchen Schmerzpunkt welcher Persona es adressiert.
Falls kein Persona-Bezug erkennbar → FR ist möglicherweise überflüssig oder gehört in eine spätere Phase.

---

## Schritt 4: Nicht-funktionale Anforderungen ableiten

Untersuche den Code auf:
- **Performance:** Caching-Layer? DB-Indizes? Pagination? → Leite Latenz/Throughput-Anforderungen ab
- **Sicherheit:** Auth, Encryption, CORS, Rate-Limiting → Dokumentiere als NFs
- **Verfügbarkeit:** Health-Checks, Retry-Logik, Circuit Breakers → Uptime-Anforderungen
- **Skalierbarkeit:** Worker-Pools, Queue-Konfiguration, Sharding → Kapazitäts-Anforderungen
- **Compliance:** DSGVO-Muster, `owner_id`-Filter, `expires_at` → Datenschutz-NFs

Für jede NF: Bestimme eine konkrete Zahl. Falls nicht aus Code ableitbar, schätze basierend auf Projekttyp:
- Web-API: < 200ms p95 Response Time, 99.5% Uptime
- Consumer-App: < 3s Time to Interactive, > 60% 14-Day Retention
- B2B-SaaS: < 500ms p95, 99.9% Uptime
- Markiere Schätzungen mit `<!-- REVIEW: Geschätzt -->`

---

## Schritt 5: Produkthypothese formulieren

Konstruiere die Hypothese aus:
- **Zielgruppe** → Vision §Zielgruppe
- **Problem** → Vision §Problemstellung
- **Lösung** → Vision §Kernfunktionen
- **Messbares Verhalten** → Roadmap-Metriken (falls vorhanden) oder aus Projekttyp ableiten
- **Metrik** → Aus Roadmap oder schätzen

Format:
> "Wir glauben, dass **[Zielgruppe]** das Problem hat, dass **[konkretes Problem]**. Wenn wir **[Lösung]** bauen, werden **[messbares Nutzerverhalten]**, messbar durch **[Metrik mit Zahl]**."

---

## Schritt 6: Dokument generieren

Erstelle `PRD-SPEC.md` im Wurzelverzeichnis (oder aktualisiere existierende):

```markdown
# PRD-SPEC: [Projekt] – [Scope]

| Feld | Wert |
|------|------|
| Status | Draft |
| Version | 0.1.0 |
| Datum | [Heutiges Datum] |
| Scope | [Aktuelle Phase aus Roadmap, oder "MVP" falls keine Roadmap] |

[1-2 Sätze: Was dieses Dokument spezifiziert und für wen es gedacht ist.
Referenzen auf Vision und Architecture.]

---

## 1. Produktüberblick

### Problem Statement
[Verdichtung aus Vision – max 1 Paragraph. Nicht kopieren, sondern auf die Essenz reduzieren.]

### Produkthypothese
"Wir glauben, dass [Zielgruppe] ... messbar durch [Metrik]."

### Out of Scope für [aktuelle Phase]
- [Von Roadmap ableiten, oder von Vision "Was es nicht ist"]

---

## 2. Zielgruppe & Personas

### Persona 1: [Name] – [Rolle]

| Attribut | Beschreibung |
|----------|-------------|
| **Name** | [Realistischer Name] |
| **Rolle** | [Konkrete Berufsbezeichnung] |
| **Unternehmen** | [Typ, Größe, Branche] |
| **Typischer Arbeitstag** | [STUNDENGENAU: 07:00 ..., 09:00 ..., 11:00 ..., 14:00 ..., 17:00 ...] |
| **Top-3-Schmerzpunkte** | 1. [MIT KONSEQUENZ] 2. [MIT ZEITVERLUST] 3. [MIT AUSWIRKUNG] |
| **Erwartungen an [Projekt]** | [Konkret genug für Feature-Ableitung] |
| **Technische Affinität** | [Konkret: CLI-Profi / Kann OAuth / Braucht GUI] |
| **Datenschutz-Sensibilität** | [MIT IMPLIKATION: "... → braucht X im System"] |

[Wiederhole für jede Persona]

---

## 3. Funktionale Anforderungen

### FR-001: [Name]
**Beschreibung:** [Was das System tut – konkret]
**Persona-Referenz:** [Persona X, Schmerzpunkt Y]
**Status:** [Implementiert / In Entwicklung / Geplant]
**Acceptance Criteria:**
- [ ] [Testbares Kriterium – abgeleitet aus Tests oder Domänenlogik]
- [ ] [Testbares Kriterium]

[Wiederhole für jedes FR – sortiert nach Priorität]

---

## 4. Nicht-funktionale Anforderungen

### NF-001: [Name]
| Attribut | Wert |
|----------|------|
| **Kategorie** | Performance / Security / Availability / Compliance |
| **Anforderung** | [MIT KONKRETER ZAHL] |
| **Messmethode** | [Wie wird das geprüft?] |
| **Abgeleitet aus** | [Code-Muster / Roadmap / Domäne] |

---

## 5. Datenmodell (Überblick)

[Kernentitäten – aus Models/Schemas/Migrations. Details verweisen auf ARCHITECTURE.md.]

### [Entität]
| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|-------------|
| ... | ... | ... | ... |

---

## 6. API-Übersicht

[Endpunkte nach Modul gruppiert – aus Router/Controller-Dateien.]

| Methode | Pfad | Beschreibung | Auth |
|---------|------|-------------|------|
| GET | /api/... | ... | Ja/Nein |
```

---

## Schritt 7: Qualitätsvalidierung

Prüfe und **korrigiere sofort**:

- [ ] Jede Persona hat stundengenauer Tagesablauf (≥ 6 Zeitpunkte)
- [ ] Jede Persona hat Top-3-Schmerzpunkte mit Zeitverlust ODER konkreter Konsequenz
- [ ] Jede Persona hat Datenschutz-Feld mit **Implikation** (nicht nur "mittel" oder "hoch")
- [ ] Produkthypothese enthält falsifizierbare Metrik mit konkreter Zahl
- [ ] Jedes FR referenziert mindestens eine Persona + ihren Schmerzpunkt
- [ ] Out of Scope ist nicht leer
- [ ] NFs haben konkrete Zahlen (nicht "schnell", sondern "< 200ms p95")
- [ ] API-Übersicht stimmt mit tatsächlich implementierten Endpunkten überein
- [ ] Datenmodell enthält reale Entitäten aus dem Code (keine erfundenen)
- [ ] FRs decken alle erkannten Kernfunktionen aus der Vision ab

---

## Schritt 8: Datei schreiben und abschließen

Schreibe die finale Datei. Gib abschließend aus:
- Anzahl Personas erstellt
- Anzahl FRs (davon: implementiert / geplant)
- Anzahl NFs
- Anzahl `<!-- REVIEW -->`-Marker
