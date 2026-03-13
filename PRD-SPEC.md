# PRD-SPEC: Persönliches Wissens-Betriebssystem (PWBS) – MVP

---

| Feld         | Wert                                                               |
| ------------ | ------------------------------------------------------------------ |
| **Status**   | Draft                                                              |
| **Version**  | 0.1.0                                                              |
| **Autor**    | _[Name eintragen]_                                                 |
| **Datum**    | März 2026                                                          |
| **Reviewer** | _[Technischer Lead]_, _[Design Lead]_, _[Datenschutzbeauftragter]_ |
| **Scope**    | Phase 2 – MVP (Monate 4–9), 10–20 Early Adopters                   |

Dieses Dokument spezifiziert die Product Requirements für das MVP des Persönlichen Wissens-Betriebssystems. Es richtet sich an Entwickler, Designer und Investoren und definiert Funktionsumfang, nicht-funktionale Anforderungen, Datenmodell, API-Übersicht, Metriken und Risiken für den Zeitraum Monate 4–9 der Roadmap. Architekturdetails sind in [ARCHITECTURE.md](ARCHITECTURE.md) dokumentiert; die Produktvision in [vision-wissens-os.md](vision-wissens-os.md).

---

## 2. Produktüberblick

### Problem Statement

Wissensarbeiter – Gründer, Produktmanager, Entwickler, Berater – verlieren täglich substanzielle Denkzeit durch kognitive Fragmentierung. Ihre Informationen sind über Kalender, Notiz-Apps, Meeting-Transkripte und Wissensdatenbanken verteilt. Vor Meetings fehlt der relevante Kontext, nach Unterbrechungen der Faden, über Wochen hinweg die Übersicht über Entscheidungen und offene Punkte. Bestehende Tools (Notion, Obsidian, Meeting-Assistenten) speichern Informationen, aber denken nicht mit – sie verknüpfen weder semantisch noch liefern sie proaktiv den richtigen Kontext zur richtigen Zeit. Das PWBS löst dieses Problem, indem es heterogene persönliche Wissensquellen automatisch zusammenführt, semantisch versteht und als kontextbezogene Briefings und durchsuchbares Wissensmodell aufbereitet.

### Produkthypothese

Wir glauben, dass **Wissensarbeiter mit hoher Kontextlast** (Gründer, PMs, Berater) das Problem haben, dass ihr **fragmentiertes Wissen über 4+ digitale Quellen verteilt** ist und sie vor Meetings, nach Unterbrechungen und bei Entscheidungen den relevanten Kontext nicht griffbereit haben. Wenn wir ein System bauen, das **Kalender, Notizen, Obsidian-Vaults und Meeting-Transkripte automatisch einliest, semantisch verknüpft und als tägliche Kontextbriefings sowie natürlichsprachliche Suche aufbereitet**, werden Early Adopters **mindestens dreimal pro Woche auf ihr Morgenbriefing zugreifen und die semantische Suche der manuellen Suche in Einzelquellen vorziehen**, messbar durch **≥ 60 % 14-Tage-Retention und ≥ 3 Briefing-Abrufe pro aktivem Nutzer pro Woche**.

### Out of Scope für MVP

Die folgenden Funktionen und Bereiche werden im MVP bewusst **nicht** umgesetzt:

- Team-Features (gemeinsame Wissensbasis, Onboarding-Unterstützung, Rollenbasierte Zugriffssteuerung)
- Mobile Apps (iOS, Android)
- Gmail-Integration
- Slack-Integration
- Pricing / Billing / Zahlungssystem
- Self-Hosting / On-Premise-Deployment
- Desktop-App (Tauri / Electron)
- Entscheidungsunterstützung (Pro/Contra-Strukturierung, Entscheidungsnachverfolgung)
- Aktive Erinnerungen (proaktive Hinweise auf vergessene Themen, Follow-ups)
- Projektbriefings (projektspezifische Statusübersichten)

---

## 3. Zielgruppe & User Personas

### Persona 1: Jana – Gründerin, Early-Stage-Startup

| Attribut                     | Beschreibung                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Name**                     | Jana Möller                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **Rolle**                    | CEO & Co-Founder                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Unternehmen**              | ClimateTech-Startup, 5 Personen, Pre-Seed-Phase                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **Typischer Arbeitstag**     | 06:30 Uhr Check der E-Mails und Slack-Nachrichten. 08:00–10:00 Uhr Produktbesprechung mit CTO. 10:30–12:00 Uhr Investorengespräch (Zoom). 13:00 Uhr kurzes Stand-up. 14:00–16:00 Uhr Pitch-Deck überarbeiten in Notion. 16:30 Uhr Kundengespräch. 18:00 Uhr Strategie-Notizen in Obsidian schreiben. Abends: offene Punkte prüfen, Termine für morgen sichten.                                                                                                                                                                                                                                         |
| **Top-3-Schmerzpunkte**      | 1. Vor Investorengesprächen muss sie 20–30 Minuten in Notion, Kalender und alten Meeting-Notizen recherchieren, welche Themen beim letzten Gespräch besprochen wurden und welche Zahlen sie kommuniziert hat. 2. Nach einem intensiven Meeting-Tag hat sie keinen Überblick, welche Entscheidungen getroffen und welche Aufgaben verteilt wurden – die Information liegt verstreut in Transkripten, Notion und ihrem Kopf. 3. Wissen geht verloren: Ein Gesprächspartner erwähnt einen Kontakt, den Jana vor drei Wochen in einem anderen Meeting erhalten hat, aber sie kann ihn nicht mehr zuordnen. |
| **Erwartungen an PWBS**      | Automatisches Morgenbriefing zeigt ihr die heutigen Termine mit Kontext. Vor jedem Investoren-Zoom sieht sie den letzten Stand auf einen Blick. Semantische Suche findet auch Informationen, bei denen sie nur vage weiß, dass „irgendjemand im Meeting vor zwei Wochen etwas zu Partnerschaften gesagt hat".                                                                                                                                                                                                                                                                                          |
| **Technische Affinität**     | Hoch. Nutzt Obsidian mit Plugins, hat GitHub-Erfahrung, kann CLI bedienen, versteht Markdown.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **Datenschutz-Sensibilität** | Mittel-Hoch. Investor-Gespräche und strategische Notizen sind vertraulich. Erwartet EU-Datenresidenz und dass ihre Daten nicht für LLM-Training genutzt werden. Will genau wissen, welche Daten das System hat und diese jederzeit löschen können.                                                                                                                                                                                                                                                                                                                                                     |

### Persona 2: Markus – Senior Product Manager, Scale-up

| Attribut                     | Beschreibung                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Name**                     | Markus Brandt                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Rolle**                    | Senior Product Manager                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **Unternehmen**              | B2B-SaaS Scale-up, 80 Personen, Series-B                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **Typischer Arbeitstag**     | 08:00 Uhr Review der Jira-Updates und Notion-Roadmap. 09:00 Uhr Sprint Refinement (Zoom). 10:00–11:00 Uhr Stakeholder-Sync mit Head of Sales. 11:30 Uhr Schreiben einer PRD in Notion. 13:00 Uhr Design Review (Zoom). 14:00–15:30 Uhr Kundeninterview (Zoom, transkribiert). 16:00 Uhr Abstimmung mit Engineering-Lead. 17:00 Uhr Notizen konsolidieren, offene Punkte in Obsidian festhalten.                                                                                                                                                                                                                                                                    |
| **Top-3-Schmerzpunkte**      | 1. Er hat 6–8 Meetings pro Tag mit verschiedenen Stakeholdern. Vor jedem Meeting muss er sich manuell den Kontext zusammensuchen – was beim letzten Mal besprochen wurde, welche Blocker genannt wurden, welche Entscheidungen ausstehen. Das kostet ihn 30–45 Minuten am Tag. 2. Kundeninterviews liefern wertvolle Insights, aber die Transkripte landen in einem Zoom-Archiv und werden nach einer Woche nie wieder gelesen. Wiederkehrende Kundenbeschwerden werden erst spät als Muster erkannt. 3. Er führt Notizen in Obsidian, Entscheidungen in Notion und Meeting-Notizen in Zoom – aber es gibt kein System, das ihm sagt, welche Information wo liegt. |
| **Erwartungen an PWBS**      | Meeting-Vorbereitung in unter 2 Minuten statt 10. Suche über alle Quellen hinweg mit einer einzigen Frage. Die extrahierten Personen und Projekte zeigen ihm sofort, wer wo involviert ist.                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **Technische Affinität**     | Mittel-Hoch. Kennt APIs und Datenmodelle aus der täglichen PM-Arbeit. Nutzt Notion, Obsidian, Figma, versteht JSON. Kein Entwickler, aber technisch versiert genug, OAuth-Flows zu durchlaufen.                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Datenschutz-Sensibilität** | Hoch. Arbeitet mit Kunden-NDA-Material und internen Strategiedokumenten. Erwartet strikte Datentrennung, verschlüsselte Speicherung und die Möglichkeit, einzelne Quellen jederzeit zu trennen und deren Daten vollständig zu löschen.                                                                                                                                                                                                                                                                                                                                                                                                                             |

### Persona 3: Lena – Freiberufliche Technikberaterin

| Attribut                     | Beschreibung                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Name**                     | Lena Vogt                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Rolle**                    | Freiberufliche Technikberaterin (Cloud-Architektur & DevOps)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| **Unternehmen**              | Einzelunternehmerin, 3–4 parallele Kundenprojekte                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **Typischer Arbeitstag**     | 07:30 Uhr Kaffee, Obsidian-Notizen vom Vortag strukturieren. 09:00 Uhr Workshop bei Kunde A (Zoom). 11:00 Uhr Architekturdokumentation für Kunde B in Notion schreiben. 13:00 Uhr Lunchgespräch mit einem Kontakt (offline). 14:00–16:00 Uhr Code-Review und Architektur-Feedback für Kunde C. 17:00 Uhr Angebot für potenziellen Kunden D vorbereiten. Abends: Lessons Learned in Obsidian festhalten, Woche planen.                                                                                                                                                                                                                                                                                                        |
| **Top-3-Schmerzpunkte**      | 1. Sie arbeitet parallel für mehrere Kunden und muss ständig den Kontext wechseln. Bei jedem Switch verliert sie 15–20 Minuten, um sich wieder „reinzudenken" – sie sucht in Notion nach dem letzten Stand, scannt Zoom-Transkripte und liest ihre Obsidian-Notizen. 2. Wiederkehrende Probleme über Kundenprojekte hinweg werden nicht systematisch erkannt. Sie hat das Gefühl, dass sie ähnliche Architekturentscheidungen immer wieder neu begründen muss, obwohl sie das Wissen bereits hat – nur nicht sofort greifbar. 3. Kalendereinträge, Notion-Seiten und Obsidian-Notizen bilden drei separate Welten. Es gibt keinen Ort, an dem sie fragen kann: „Was weiß ich insgesamt über das Thema Kubernetes-Migration?" |
| **Erwartungen an PWBS**      | Ein einziger Ort, um über alle Kunden und Projekte hinweg zu suchen. Morgenbriefings, die ihr den Kontext für den Tag liefern, ohne dass sie vier Tools öffnen muss. Verknüpfungen zwischen Personen, Projekten und Themen, die über die Grenzen einzelner Quellen hinausgehen.                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **Technische Affinität**     | Sehr hoch. Cloud-Architektin, arbeitet täglich mit Terminals, Docker, IaC. Obsidian-Power-Userin mit eigenem Plugin-Setup. Erwartet eine saubere API und Export-Möglichkeiten.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **Datenschutz-Sensibilität** | Sehr hoch. Arbeitet unter NDA für mehrere Kunden. Informationen verschiedener Kunden dürfen niemals vermischt oder an Dritte gelangen. Erwartet vollständige Kontrolle über ihre Daten, EU-Hosting und transparente Dokumentation, welche Daten wohin fließen (insbesondere an LLM-Provider).                                                                                                                                                                                                                                                                                                                                                                                                                                |

---

## 4. User Stories & Acceptance Criteria

### Epic 1: Onboarding & Konnektor-Setup

**US-1.1:** Als Jana möchte ich mich mit E-Mail und Passwort registrieren, damit ich einen eigenen, geschützten Account erhalte.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich bin auf der Registrierungsseite, **When** ich eine gültige E-Mail, ein Passwort (≥ 12 Zeichen, mind. 1 Großbuchstabe, 1 Zahl) und einen Anzeigenamen eingebe und absende, **Then** wird mein Account erstellt, ich erhalte ein JWT-Token-Paar und werde zum Dashboard weitergeleitet.
  - **Given** ich gebe eine bereits registrierte E-Mail ein, **When** ich absende, **Then** erhalte ich eine generische Fehlermeldung „Registrierung fehlgeschlagen" (kein Hinweis, ob die E-Mail existiert).
  - **Given** mein Passwort erfüllt nicht die Komplexitätsanforderungen, **When** ich absende, **Then** werden die konkreten Anforderungen unter dem Passwortfeld angezeigt.

**US-1.2:** Als Jana möchte ich meinen Google Calendar über OAuth2 verbinden, damit meine Termine automatisch importiert werden.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich bin eingeloggt und auf der Konnektoren-Seite, **When** ich auf „Google Calendar verbinden" klicke, **Then** werde ich zum Google-OAuth-Consent-Screen weitergeleitet mit den Scopes `calendar.events.readonly`.
  - **Given** ich habe den Google-Consent erteilt, **When** ich zurückgeleitet werde, **Then** zeigt das System „Google Calendar verbunden" an und startet den initialen Sync im Hintergrund.
  - **Given** der initiale Sync läuft, **When** ich die Konnektoren-Seite betrachte, **Then** sehe ich einen Fortschrittsbalken mit der Anzahl importierter Ereignisse.
  - **Given** ich lehne den Google-Consent ab oder bricht den OAuth-Flow ab, **When** ich zurückgeleitet werde, **Then** sehe ich eine Fehlermeldung „Verbindung konnte nicht hergestellt werden" und kann es erneut versuchen.

**US-1.3:** Als Markus möchte ich mein Notion-Workspace über OAuth2 verbinden, damit meine Notion-Seiten automatisch indexiert werden.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich bin eingeloggt und auf der Konnektoren-Seite, **When** ich auf „Notion verbinden" klicke, **Then** werde ich zum Notion-OAuth-Flow weitergeleitet.
  - **Given** ich habe Notion-Zugriff erteilt, **When** der Callback verarbeitet wird, **Then** werden die für die Integration freigegebenen Seiten und Datenbanken als Sync-Scope angezeigt.
  - **Given** der initiale Sync abgeschlossen ist, **When** ich auf der Konnektoren-Seite bin, **Then** sehe ich die Anzahl importierter Seiten und den Zeitpunkt des letzten Syncs.

**US-1.4:** Als Lena möchte ich meinen Obsidian-Vault verbinden, indem ich den lokalen Pfad angebe, damit meine Markdown-Notizen indexiert werden.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich bin auf der Konnektoren-Seite, **When** ich auf „Obsidian Vault verbinden" klicke, **Then** kann ich einen lokalen Verzeichnispfad eingeben oder per Datei-Dialog auswählen.
  - **Given** ich habe einen gültigen Vault-Pfad angegeben, der Markdown-Dateien enthält, **When** ich bestätige, **Then** startet der Import und ich sehe die Anzahl gefundener `.md`-Dateien.
  - **Given** der Pfad existiert nicht oder enthält keine Markdown-Dateien, **When** ich bestätige, **Then** erhalte ich eine Fehlermeldung „Kein gültiger Obsidian-Vault gefunden" mit Hinweis auf das erwartete Format.

**US-1.5:** Als Markus möchte ich mein Zoom-Konto verbinden, damit meine Meeting-Transkripte automatisch importiert werden.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich bin auf der Konnektoren-Seite, **When** ich auf „Zoom verbinden" klicke, **Then** werde ich zum Zoom-OAuth-Flow weitergeleitet mit den erforderlichen Scopes für Transkript-Zugriff.
  - **Given** der Zoom-Consent wurde erteilt, **When** ein neues Meeting-Transkript verfügbar wird (Webhook `recording.completed`), **Then** wird es automatisch importiert und verarbeitet.
  - **Given** ein Transkript wurde importiert, **When** ich es in der Dokumentenübersicht suche, **Then** finde ich es mit Titel, Datum, Dauer und Teilnehmerliste.

**US-1.6:** Als Jana möchte ich den Import-Status aller verbundenen Quellen auf einen Blick sehen, damit ich weiß, ob mein Wissensmodell aktuell ist.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich habe mindestens eine Quelle verbunden, **When** ich die Konnektoren-Übersichtsseite öffne, **Then** sehe ich pro Konnektor: Status (aktiv/pausiert/Fehler), Anzahl importierter Dokumente, Zeitpunkt des letzten erfolgreichen Syncs.
  - **Given** ein Konnektor befindet sich im Fehlerzustand, **When** ich den Konnektor betrachte, **Then** sehe ich eine verständliche Fehlerbeschreibung und einen Button „Erneut verbinden".
  - **Given** ein Sync läuft aktuell, **When** ich die Seite betrachte, **Then** sehe ich einen animierten Indikator mit Fortschrittsanzeige.

---

### Epic 2: Semantische Suche

**US-2.1:** Als Lena möchte ich eine natürlichsprachliche Frage stellen, damit ich Informationen aus allen meinen Quellen in einem einzigen Suchergebnis finde.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich bin im Suchbereich und habe mindestens eine Quelle verbunden, **When** ich die Frage „Was wurde im letzten Meeting mit Kunde A zu Kubernetes besprochen?" eingebe und absende, **Then** erhalte ich innerhalb von 2 Sekunden (p95) eine Liste relevanter Ergebnisse, sortiert nach Relevanz.
  - **Given** die Suche liefert Ergebnisse, **When** ich ein Ergebnis betrachte, **Then** sehe ich einen Textausschnitt (Chunk), den Quellentyp (Zoom-Transkript, Notion-Seite etc.), das Dokumentdatum und einen Relevanz-Score.
  - **Given** die Suche liefert keine Ergebnisse, **When** die Ergebnisliste angezeigt wird, **Then** sehe ich eine Nachricht „Keine Ergebnisse gefunden" mit Vorschlägen zur Umformulierung oder Filteranpassung.

**US-2.2:** Als Markus möchte ich Suchergebnisse mit nachvollziehbarer Quellenangabe sehen, damit ich die Information verifizieren kann.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich erhalte Suchergebnisse, **When** ich ein Ergebnis betrachte, **Then** enthält jedes Ergebnis den Quelltyp, den Dokumenttitel, das Erstellungs-/Änderungsdatum und den exakten Textausschnitt, aus dem die Information stammt.
  - **Given** die Suche eine LLM-generierte Zusammenfassung anzeigt, **When** ich die Zusammenfassung lese, **Then** enthält jede Aussage eine klickbare Quellenreferenz `[Quelle: Dokumenttitel, Datum]`.

**US-2.3:** Als Lena möchte ich Suchergebnisse nach Person, Projekt oder Thema filtern, damit ich die Ergebnisse schnell eingrenzen kann.

- **Priorität:** Should
- **Acceptance Criteria:**
  - **Given** ich habe eine Suche durchgeführt, **When** ich den Filter „Person" öffne, **Then** sehe ich eine Liste der in den Ergebnissen erkannten Personen und kann eine oder mehrere auswählen.
  - **Given** ich habe den Filter „Person: Maria" aktiviert, **When** die Ergebnisse aktualisiert werden, **Then** zeigt die Liste nur noch Ergebnisse, in denen Maria als Entität erkannt wurde.
  - **Given** ich habe einen Filter aktiviert, **When** ich den Filter entferne, **Then** kehre ich zur ungefilterten Ergebnisliste zurück.

**US-2.4:** Als Jana möchte ich von einem Suchergebnis direkt zur Originalquelle gelangen, damit ich den vollständigen Kontext lesen kann.

- **Priorität:** Should
- **Acceptance Criteria:**
  - **Given** ich sehe ein Suchergebnis aus einer Notion-Seite, **When** ich auf „Original öffnen" klicke, **Then** wird die entsprechende Notion-Seite in einem neuen Tab geöffnet.
  - **Given** ich sehe ein Suchergebnis aus einem Zoom-Transkript, **When** ich auf „Original öffnen" klicke, **Then** wird die Zoom-Aufnahmeseite in einem neuen Tab geöffnet.
  - **Given** die Originalquelle ist nicht mehr verfügbar (gelöscht in der Quell-App), **When** ich auf „Original öffnen" klicke, **Then** sehe ich eine Meldung „Originalquelle nicht mehr verfügbar" und den im System gespeicherten Textausschnitt.

---

### Epic 3: Kontextbriefings

**US-3.1:** Als Jana möchte ich jeden Morgen ein automatisch generiertes Briefing abrufen, damit ich den Tag mit vollem Kontext starten kann.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich habe mindestens einen Kalender verbunden und Termine heute, **When** ich morgens das Dashboard öffne (oder das Briefing wurde automatisch um 06:30 Uhr generiert), **Then** sehe ich ein Morgenbriefing mit: Übersicht der heutigen Termine, Kontextinformationen pro Termin (Teilnehmer, letzter Stand, offene Punkte) und einer Zusammenfassung relevanter Entwicklungen der letzten 7 Tage.
  - **Given** das Morgenbriefing wurde generiert, **When** ich es lese, **Then** ist jede Faktische Aussage mit einer Quellenreferenz versehen.
  - **Given** ich habe heute keine Termine und keine relevanten neuen Dokumente, **When** das Briefing generiert wird, **Then** zeigt es eine Meldung „Keine Termine heute. Hier eine Zusammenfassung der letzten Tage:" mit den relevantesten Themen.

**US-3.2:** Als Markus möchte ich vor einem Meeting ein Vorbereitungsbriefing generieren, damit ich in unter 2 Minuten den relevanten Kontext habe.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich habe einen kommenden Kalendereintrag mit Teilnehmern, **When** ich auf „Meeting-Vorbereitung" klicke (oder das System generiert das Briefing 30 Minuten vorher automatisch), **Then** erhalte ich innerhalb von 10 Sekunden ein Briefing mit: Thema des Meetings, Teilnehmer mit History (letzte gemeinsame Meetings, gemeinsame Projekte), offene Punkte aus vorherigen Interaktionen und relevante Dokumente.
  - **Given** das System hat keine Informationen zu einem Teilnehmer, **When** das Briefing generiert wird, **Then** wird dieser Teilnehmer als „Neu im System – keine vorherigen Interaktionen gespeichert" gekennzeichnet, anstatt Informationen zu erfinden.

**US-3.3:** Als Lena möchte ich die Quellen eines Briefings nachvollziehen können, damit ich der Information vertrauen kann.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich lese ein Briefing, **When** ich eine Quellenreferenz anklicke, **Then** werde ich zum entsprechenden Dokument-Detail im PWBS navigiert und sehe den exakten Textausschnitt hervorgehoben.
  - **Given** ein Briefing wurde generiert, **When** ich den „Quellen"-Bereich am Ende des Briefings öffne, **Then** sehe ich eine vollständige Liste aller verwendeten Quellen mit Typ, Titel, Datum und Relevanz-Score.

**US-3.4:** Als Markus möchte ich Feedback zu einem Briefing geben können, damit das System langfristig relevantere Briefings generiert.

- **Priorität:** Could
- **Acceptance Criteria:**
  - **Given** ich lese ein Briefing, **When** ich am Ende des Briefings auf „Hilfreich" oder „Nicht hilfreich" klicke, **Then** wird mein Feedback gespeichert und mit dem Briefing verknüpft.
  - **Given** ich markiere ein Briefing als „Nicht hilfreich", **When** ich möchte, **Then** kann ich optional einen Freitext-Kommentar hinterlassen, der beschreibt, was gefehlt hat oder irrelevant war.

---

### Epic 4: Knowledge Explorer Basis

**US-4.1:** Als Lena möchte ich eine Übersicht der vom System erkannten Entitäten (Personen, Projekte, Themen) sehen, damit ich verstehe, was das System über mein Wissensuniversum weiß.

- **Priorität:** Should
- **Acceptance Criteria:**
  - **Given** das System hat Dokumente verarbeitet und Entitäten extrahiert, **When** ich den Knowledge Explorer öffne, **Then** sehe ich eine filterbare Liste von Entitäten, gruppiert nach Typ (Personen, Projekte, Themen), jeweils mit Namen, Typ, Häufigkeit der Erwähnung und dem Datum der letzten Erwähnung.
  - **Given** ich filtere nach dem Typ „Person", **When** die Liste aktualisiert wird, **Then** zeigt sie nur Personen-Entitäten, sortiert nach Häufigkeit der Erwähnung.

**US-4.2:** Als Jana möchte ich Verbindungen zwischen Entitäten visuell erkunden, damit ich Zusammenhänge zwischen Personen, Projekten und Themen entdecke.

- **Priorität:** Should
- **Acceptance Criteria:**
  - **Given** ich bin im Knowledge Explorer, **When** ich eine Entität (z. B. ein Projekt) auswähle, **Then** sehe ich eine Graphdarstellung mit der ausgewählten Entität im Zentrum und ihren direkten Verbindungen (beteiligte Personen, zugehörige Themen, verknüpfte Dokumente) bis zu einer Tiefe von 2.
  - **Given** der Graph wird angezeigt, **When** ich auf einen verbundenen Knoten klicke, **Then** wird dieser Knoten zum neuen Zentrum und der Graph aktualisiert sich.

**US-4.3:** Als Markus möchte ich eine Entitäts-Detailseite mit zugehörigen Dokumenten sehen, damit ich alle Informationen zu einer Person oder einem Projekt gebündelt habe.

- **Priorität:** Should
- **Acceptance Criteria:**
  - **Given** ich klicke auf eine Entität (z. B. Person „Maria S.") in der Entitätsliste oder im Graph, **When** die Detailseite lädt, **Then** sehe ich: den Entitätsnamen und -typ, eine Zeitleiste der Erwähnungen (wann, in welchem Dokument), verknüpfte andere Entitäten (Projekte, an denen Maria beteiligt ist; Themen, die mit ihr assoziiert sind) und eine Liste der zugehörigen Dokument-Chunks mit Quellenangabe.
  - **Given** ich bin auf der Detailseite, **When** ich einen Dokument-Chunk anklicke, **Then** werde ich zum Dokument-Detail mit hervorgehobenem Chunk navigiert.

---

### Epic 5: Datenschutz & Kontrolle

**US-5.1:** Als Lena möchte ich alle verbundenen Datenquellen einsehen und einzelne Quellen trennen können, damit ich volle Kontrolle über meine Daten behalte.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich bin auf der Einstellungsseite unter „Datenquellen", **When** die Seite lädt, **Then** sehe ich alle verbundenen Quellen mit Status, Anzahl importierter Dokumente und Verbindungsdatum.
  - **Given** ich möchte eine Quelle trennen, **When** ich auf „Trennen" klicke und die Sicherheitsabfrage „Alle importierten Daten dieser Quelle werden unwiderruflich gelöscht. Fortfahren?" bestätige, **Then** wird die OAuth-Verbindung widerrufen, alle Dokumente, Chunks, Embeddings und Graph-Knoten dieser Quelle kaskadierend gelöscht und der Konnektor-Status auf „getrennt" gesetzt.

**US-5.2:** Als Jana möchte ich alle meine Daten exportieren können, damit ich mein Recht auf Datenportabilität (DSGVO Art. 20) wahrnehmen kann.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich bin auf der Einstellungsseite unter „Datenschutz", **When** ich auf „Daten exportieren" klicke, **Then** wird ein Exportjob gestartet und ich erhalte eine Fortschrittsanzeige.
  - **Given** der Export ist abgeschlossen, **When** ich die Seite betrachte, **Then** kann ich eine ZIP-Datei herunterladen, die alle meine Daten in maschinenlesbarem Format (JSON + Markdown) enthält: Dokument-Metadaten, Chunk-Inhalte, extrahierte Entitäten, generierte Briefings und Audit-Log.
  - **Given** der Export ist sehr groß, **When** die Verarbeitung länger als 60 Sekunden dauert, **Then** erhalte ich eine Benachrichtigung per E-Mail, sobald der Download bereitsteht (Link gültig 24 Stunden).

**US-5.3:** Als Markus möchte ich meinen Account vollständig löschen können, damit mein Recht auf Löschung (DSGVO Art. 17) gewährleistet ist.

- **Priorität:** Must
- **Acceptance Criteria:**
  - **Given** ich bin auf der Einstellungsseite unter „Account", **When** ich auf „Account löschen" klicke, **Then** erhalte ich eine Warnung mit einer 30-Tage-Karenzfrist, in der ich die Löschung rückgängig machen kann.
  - **Given** ich bestätige die Account-Löschung, **When** die 30-Tage-Frist abgelaufen ist ohne Widerruf, **Then** werden alle meine Daten kaskadierend gelöscht: PostgreSQL (CASCADE auf user_id), Weaviate (Tenant gelöscht), Neo4j (alle Knoten mit meiner userId), Redis (Session-Flush). Die Löschung ist irreversibel.
  - **Given** ich habe die Löschung eingeleitet, **When** ich mich innerhalb der 30 Tage erneut einlogge, **Then** sehe ich einen Banner „Ihr Account ist zur Löschung am [Datum] vorgemerkt" mit der Option „Löschung abbrechen".

**US-5.4:** Als Lena möchte ich den Verschlüsselungsstatus meiner Daten einsehen können, damit ich sicher bin, dass meine vertraulichen Informationen geschützt sind.

- **Priorität:** Could
- **Acceptance Criteria:**
  - **Given** ich bin auf der Einstellungsseite unter „Sicherheit", **When** die Seite lädt, **Then** sehe ich: den Verschlüsselungsstatus pro Speicherschicht (PostgreSQL: verschlüsselt, Weaviate: verschlüsselt, Neo4j: verschlüsselt), ob meine OAuth-Tokens verschlüsselt gespeichert sind, den Datenstandort (EU – Frankfurt) und eine Information, dass meine Daten nicht für LLM-Training verwendet werden.

---

## 5. Funktionale Anforderungen

### Epic 1: Onboarding & Konnektor-Setup

| ID    | Anforderung                   | Beschreibung                                                                                                                                                                                | Priorität | Abhängigkeiten      |
| ----- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ------------------- |
| F-001 | Nutzer-Registrierung          | Registrierung mit E-Mail, Passwort (≥ 12 Zeichen, Komplexitätsanforderungen) und Anzeigename. Passwort-Hashing mit Argon2. Generierung eines nutzer-spezifischen Data Encryption Key (DEK). | Must      | –                   |
| F-002 | Login / JWT-Authentifizierung | Login mit E-Mail und Passwort. Ausgabe von Access-Token (RS256, 15 Min.) und Refresh-Token (opaque, 30 Tage, rotierend). Generische Fehlermeldung bei fehlgeschlagenem Login.               | Must      | F-001               |
| F-003 | Token-Refresh                 | Erneuerung des Access-Tokens über Refresh-Token. Bei jedem Refresh wird ein neues Refresh-Token ausgestellt und das alte invalidiert (Token Rotation).                                      | Must      | F-002               |
| F-004 | Google Calendar Connector     | OAuth2-Integration mit Google. Scopes: `calendar.events.readonly`. Initialer Full-Sync, danach inkrementeller Sync alle 15 Minuten (oder via Webhook). Normalisierung in UDF.               | Must      | F-001, F-002        |
| F-005 | Notion Connector              | OAuth2-Integration mit Notion. Polling alle 10 Minuten via `last_edited_time`-Cursor. Import von Pages und Databases. Normalisierung in UDF.                                                | Must      | F-001, F-002        |
| F-006 | Obsidian Vault Connector      | Lokaler Import über Vault-Pfad-Angabe. File-System-Watcher für Änderungen. Import von Markdown-Dateien inkl. Frontmatter und internen Links. Normalisierung in UDF.                         | Must      | F-001               |
| F-007 | Zoom Transcript Connector     | OAuth2-Integration mit Zoom Marketplace. Webhook-basiert (`recording.completed`). Import von Meeting-Transkripten mit Teilnehmerliste und Dauer. Normalisierung in UDF.                     | Must      | F-001, F-002        |
| F-008 | Konnektor-Statusübersicht     | Dashboard-Widget und dedizierte Seite, die pro Konnektor Status, Dokumentenanzahl, letzten Sync-Zeitpunkt und ggf. Fehlerbeschreibung anzeigt.                                              | Must      | F-004 – F-007       |
| F-009 | Manueller Sync-Trigger        | Button pro Konnektor, um einen sofortigen Sync auszulösen. Rate Limiting: maximal 1 manueller Sync pro Konnektor pro 5 Minuten.                                                             | Should    | F-004 – F-007       |
| F-010 | OAuth-Token-Rotation          | Automatische Erneuerung abgelaufener OAuth-Tokens der Konnektoren im Hintergrund. Verschlüsselte Speicherung der Refresh-Tokens mit User-DEK.                                               | Must      | F-004, F-005, F-007 |

### Epic 2: Semantische Suche

| ID    | Anforderung                       | Beschreibung                                                                                                                                                                                      | Priorität | Abhängigkeiten |
| ----- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | -------------- |
| F-011 | Natürlichsprachliche Suche        | Eingabefeld für Freitext-Fragen. Backend: Query-Embedding generieren, Hybrid-Suche (75 % semantisch, 25 % Keyword via BM25) in Weaviate mit Tenant-Isolation.                                     | Must      | F-004 – F-007  |
| F-012 | Ergebnisse mit Quellenangabe      | Jedes Suchergebnis enthält: Titel des Quelldokuments, Quelltyp (Icon), Datum, relevanten Textausschnitt (Chunk) und Relevanz-Score. Maximal 10 Ergebnisse pro Seite, paginierbar.                 | Must      | F-011          |
| F-013 | LLM-generierte Suchantwort        | Optional: LLM generiert eine zusammenfassende Antwort auf Basis der Top-K-Chunks. Jede Aussage mit `[Quelle: Titel, Datum]` referenziert. Confidence-Indikator (hoch/mittel/niedrig).             | Should    | F-011          |
| F-014 | Filter nach Entitätstyp           | Suchergebnisse filterbar nach erkannten Entitäten: Personen, Projekte, Themen. Multi-Select. Filter werden serverseitig auf die Weaviate-/Neo4j-Query angewendet.                                 | Should    | F-011, F-020   |
| F-015 | Filter nach Quelltyp und Zeitraum | Suchergebnisse filterbar nach Quelltyp (Google Calendar, Notion, Obsidian, Zoom) und Zeitraum (letzte 7/30/90 Tage, benutzerdefiniert).                                                           | Should    | F-011          |
| F-016 | Direktlink zur Originalquelle     | Jedes Suchergebnis enthält einen „Original öffnen"-Link, der direkt zur Quelle in der Ursprungs-App führt (Notion-Seite, Zoom-Aufnahme etc.). Fallback-Anzeige, wenn Quelle nicht mehr verfügbar. | Should    | F-011          |

### Epic 3: Kontextbriefings

| ID    | Anforderung                        | Beschreibung                                                                                                                                                                                                  | Priorität | Abhängigkeiten |
| ----- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | -------------- |
| F-017 | Morgenbriefing-Generierung         | Automatische Generierung täglich um 06:30 Uhr (Nutzer-Timezone). Inhalt: Tagesübersicht, Kontext pro Termin (Teilnehmer-History, offene Punkte), relevante Entwicklungen der letzten 7 Tage. Max. 800 Wörter. | Must      | F-004, F-011   |
| F-018 | Meeting-Vorbereitungsbriefing      | On-Demand abrufbar oder automatisch 30 Minuten vor Kalendereinträgen mit ≥ 2 Teilnehmern. Inhalt: Thema, Teilnehmer mit History, offene Punkte, relevante Dokumente. Max. 400 Wörter.                         | Must      | F-004, F-011   |
| F-019 | Quellenreferenzen in Briefings     | Jede Aussage in einem Briefing wird mit einer klickbaren Quellenreferenz versehen. Am Ende des Briefings: vollständige Quellenliste mit Typ, Titel, Datum, Relevanz-Score.                                    | Must      | F-017, F-018   |
| F-020 | Briefing-Feedback-Mechanismus      | Daumen-hoch/runter pro Briefing. Optionaler Freitext bei negativem Feedback. Feedback wird mit Briefing-ID und Nutzer-ID gespeichert für spätere Auswertung.                                                  | Could     | F-017, F-018   |
| F-021 | Briefing-Abruf via Dashboard       | Dashboard zeigt das aktuelle Morgenbriefing als Hauptinhalt an. Meeting-Briefings erscheinen als Karte im „Nächste Termine"-Bereich. Alle Briefings über eine Listenansicht paginiert abrufbar.               | Must      | F-017, F-018   |
| F-022 | Briefing-Caching und Regenerierung | Generierte Briefings werden in der Datenbank persistiert. Nutzer können ein Briefing manuell neu generieren. Ablaufdatum: Morgenbriefings nach 24h, Meeting-Briefings nach 48h.                               | Should    | F-017, F-018   |

### Epic 4: Knowledge Explorer Basis

| ID    | Anforderung          | Beschreibung                                                                                                                                                                                | Priorität | Abhängigkeiten |
| ----- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | -------------- |
| F-023 | Entitätenliste       | Seite mit paginierter, filterbarer Liste aller extrahierten Entitäten. Spalten: Name, Typ (Person/Projekt/Thema/Entscheidung), Häufigkeit, letzte Erwähnung. Sortierbar nach allen Spalten. | Should    | F-004 – F-007  |
| F-024 | Graphvisualisierung  | Interaktive Force-Directed-Graph-Darstellung (D3.js) mit einer ausgewählten Entität als Zentrum. Darstellungstiefe konfigurierbar (1–3), max. 50 Knoten. Knoten nach Typ farbcodiert.       | Should    | F-023          |
| F-025 | Entitäts-Detailseite | Detailansicht einer Entität mit: Name, Typ, Metadaten, Zeitleiste der Erwähnungen, verknüpften Entitäten und einer Liste zugehöriger Dokument-Chunks mit Quellenangabe und Datum.           | Should    | F-023          |

### Epic 5: Datenschutz & Kontrolle

| ID    | Anforderung                       | Beschreibung                                                                                                                                                                                 | Priorität | Abhängigkeiten |
| ----- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | -------------- |
| F-026 | Datenquellen einsehen und trennen | Einstellungsseite zeigt alle verbundenen Quellen. „Trennen"-Funktion widerruft OAuth-Token, löscht alle Daten dieser Quelle kaskadierend (PostgreSQL, Weaviate, Neo4j). Sicherheitsabfrage.  | Must      | F-004 – F-007  |
| F-027 | DSGVO-Datenexport                 | Export aller Nutzerdaten als ZIP (JSON + Markdown). Umfasst: Dokumente, Chunks, Entitäten, Briefings, Audit-Log. Asynchrone Verarbeitung. Download-Link gültig 24 Stunden.                   | Must      | F-001          |
| F-028 | Account-Löschung mit Karenzfrist  | Account-Deletion mit 30-Tage-Karenzfrist. In der Karenzzeit: eingeschränkter Zugriff, Banner mit Option „Löschung abbrechen". Nach Ablauf: kaskadierte Löschung aller Daten und Tenant.      | Must      | F-001          |
| F-029 | Verschlüsselungsstatus-Anzeige    | Sicherheitseinstellungsseite zeigt: Verschlüsselungsstatus pro Speicherschicht, OAuth-Token-Verschlüsselungsstatus, Datenstandort (Region), Nutzungsinformation zu LLM-Daten.                | Could     | –              |
| F-030 | Audit-Log für Nutzer              | Nutzer können ihre letzten 100 Audit-Log-Einträge einsehen: Login, Konnektor-Verbindungen, Daten-Importe, Briefing-Generierungen, Daten-Löschungen. Kein Export von Inhalten, nur Metadaten. | Should    | F-001          |
| F-031 | Consent-Management pro Quelle     | Jede Datenquelle erfordert explizite Einwilligung (OAuth-Consent + App-interne Bestätigung). Einwilligung jederzeit widerrufbar (= Quelle trennen + Daten löschen).                          | Must      | F-004 – F-007  |

---

## 6. Nicht-funktionale Anforderungen

### Performance

| ID     | Anforderung                                  | Zielwert            | Messmethode                                                   |
| ------ | -------------------------------------------- | ------------------- | ------------------------------------------------------------- |
| NF-001 | Semantische Suche (Antwortzeit)              | < 2 Sekunden (p95)  | Backend-Logging der Request-Duration, Prometheus-Metriken     |
| NF-002 | Briefing-Generierung                         | < 10 Sekunden (p95) | Zeitmessung von Trigger bis Persistierung im Briefing-Service |
| NF-003 | API-Endpunkte (allgemein)                    | < 500 ms (p95)      | ALB/API-Gateway-Metriken, Application Performance Monitoring  |
| NF-004 | Frontend Time-to-Interactive                 | < 3 Sekunden (p95)  | Lighthouse CI, Vercel Analytics                               |
| NF-005 | Datenquelle Initial Sync (bis 500 Dokumente) | < 5 Minuten         | Timer im Ingestion-Service pro Sync-Job                       |

### Verfügbarkeit

| ID     | Anforderung              | Zielwert             | Messmethode                                           |
| ------ | ------------------------ | -------------------- | ----------------------------------------------------- |
| NF-006 | System-Verfügbarkeit     | 99,5 % (monatlich)   | AWS CloudWatch, Uptime-Monitoring (z. B. BetterStack) |
| NF-007 | Geplante Wartungsfenster | Max. 2 Stunden/Monat | Wartungslogs, Ankündigungen an Nutzer                 |

### Skalierbarkeit

| ID     | Anforderung                   | Zielwert          | Messmethode                                                       |
| ------ | ----------------------------- | ----------------- | ----------------------------------------------------------------- |
| NF-008 | Gleichzeitige aktive Nutzer   | 20                | Load-Testing mit k6/Locust, Connection-Pool-Monitoring            |
| NF-009 | Dokumente pro Nutzer          | Bis 10.000        | Smoke-Tests mit synthetischen Daten, Performance-Regression-Tests |
| NF-010 | Embedding-Speicher pro Nutzer | Bis 50.000 Chunks | Weaviate-Tenant-Metriken                                          |

### Sicherheit

| ID     | Anforderung                 | Zielwert                                                                 | Messmethode                                                      |
| ------ | --------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| NF-011 | OWASP Top 10 Compliance     | Alle 10 Kategorien adressiert (siehe Security Instructions)              | Manuelles Security-Review, Dependency-Scanning (Dependabot/Snyk) |
| NF-012 | Verschlüsselung at Rest     | AES-256 für PostgreSQL, Volume Encryption für Weaviate und Neo4j         | Konfigurationsaudit der AWS-Infrastruktur                        |
| NF-013 | Verschlüsselung in Transit  | TLS 1.2+ für alle Verbindungen, TLS 1.3 für Client-facing                | SSL-Labs-Scan, Infra-Audit                                       |
| NF-014 | JWT Access-Token Expiry     | 15 Minuten                                                               | Unit-Test der Token-Generierung                                  |
| NF-015 | Rate Limiting (API)         | 100 Requests/Minute pro Nutzer (allgemein), 5/Minute für Login-Endpunkte | Redis-basierte Counter, Integrationstests                        |
| NF-016 | OAuth-Token-Verschlüsselung | Doppelt verschlüsselt (DB-Level + App-Level mit User-DEK via Fernet)     | Integrationstests, Code-Review                                   |

### Datenschutz

| ID     | Anforderung                    | Zielwert                                                            | Messmethode                                                          |
| ------ | ------------------------------ | ------------------------------------------------------------------- | -------------------------------------------------------------------- |
| NF-017 | DSGVO-Konformität              | Vollständig für Art. 5, 6, 15, 17, 20, 25, 32                       | Datenschutz-Audit, dokumentierte TOM                                 |
| NF-018 | EU-Datenresidenz               | Alle Nutzerdaten in AWS eu-central-1 (Frankfurt)                    | AWS-Konfigurationsaudit, Region-Constraints                          |
| NF-019 | Account-Löschung (vollständig) | Innerhalb von 30 Tagen nach Ablauf der Karenzfrist                  | Automated Cleanup-Job, Verifikationstest nach Löschung               |
| NF-020 | Keine LLM-Training-Nutzung     | Nutzerdaten werden nie für externes LLM-Training verwendet          | Vertragliche Vereinbarung mit LLM-Providern (AVV), API-Konfiguration |
| NF-021 | Mandanten-Isolation            | Kein Cross-User-Datenzugriff auf Datenbank-, Vektor- und Graphebene | Weaviate Multi-Tenancy, PostgreSQL-Row-Level-Filtering, Pentests     |

### Erklärbarkeit

| ID     | Anforderung                  | Zielwert                                                                 | Messmethode                                                     |
| ------ | ---------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------- |
| NF-022 | Quellenreferenzierung        | 100 % aller LLM-generierten Aussagen mit Quellenreferenz                 | Automated Assertion in Briefing-Pipeline + stichprobenartige QA |
| NF-023 | Halluzinations-Kennzeichnung | Aussagen ohne direkte Quellenableitung mit Confidence-Indikator versehen | LLM-Output-Parsing, QA-Reviews                                  |

### Usability

| ID     | Anforderung      | Zielwert                                                                     | Messmethode                                                        |
| ------ | ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| NF-024 | Time-to-Value    | ≤ 3 Tage ab Registrierung                                                    | Nutzer-Interviews, Event-Tracking (Zeitpunkt des ersten Briefings) |
| NF-025 | Onboarding-Dauer | ≤ 15 Minuten (Registrierung bis erste verbundene Quelle und erstes Briefing) | Event-basierte Zeitmessung                                         |
| NF-026 | Barrierefreiheit | WCAG 2.1 Level AA für Kernfunktionen                                         | Axe/Lighthouse Accessibility-Audit                                 |

---

## 7. UX-Anforderungen & User Flows

### User Flow 1: Erstmaliges Onboarding

**Ziel:** Neue Nutzerin registriert sich, verbindet eine Datenquelle und erhält ihr erstes Briefing.

1. **Registrierungsseite laden:** Nutzerin ruft `/register` auf. Die Seite enthält drei Felder: E-Mail, Passwort, Anzeigename.
2. **Registrierung absenden:** Nutzerin füllt die Felder aus und klickt „Account erstellen".
   - _Fehlerfall: Passwort zu schwach_ → Inline-Validierung zeigt fehlende Kriterien unter dem Passwortfeld an. Der Submit-Button bleibt deaktiviert.
   - _Fehlerfall: E-Mail bereits registriert_ → Generische Fehlermeldung „Registrierung fehlgeschlagen. Bitte versuche es erneut." (kein Leak, ob E-Mail existiert).
   - _Fehlerfall: Netzwerk-Timeout_ → Fehlermeldung „Verbindungsfehler. Bitte prüfe deine Internetverbindung und versuche es erneut."
3. **Willkommensdialog:** Nach erfolgreicher Registrierung wird die Nutzerin zum Dashboard weitergeleitet. Ein modaler Willkommensdialog erscheint: „Willkommen bei PWBS! Verbinde deine erste Datenquelle, um zu starten." Drei Optionen: Google Calendar, Notion, Obsidian Vault, Zoom. Button „Später" schließt den Dialog.
4. **Konnektor auswählen:** Nutzerin klickt auf „Google Calendar verbinden".
5. **OAuth-Flow:** Weiterleitung zum Google-Consent-Screen.
   - _Fehlerfall: Nutzerin bricht OAuth ab_ → Rückkehr zum Dashboard mit Meldung „Verbindung abgebrochen. Du kannst jederzeit eine Quelle unter Einstellungen → Datenquellen verbinden."
   - _Fehlerfall: OAuth-Fehler (z. B. ungültige Scopes)_ → Fehlermeldung mit Retry-Option und Hinweis auf den Support.
6. **Consent erteilt:** Nach erfolgreichem Consent wird die Nutzerin zurückgeleitet. Das Dashboard zeigt „Google Calendar verbunden ✓" und startet den initialen Sync. Fortschrittsbalken: „42 Termine importiert…"
7. **Initialer Sync abgeschlossen:** Die Fortschrittsanzeige verschwindet. Meldung: „Google Calendar vollständig synchronisiert. 156 Termine importiert." Ein Button erscheint: „Erstes Briefing generieren".
   - _Edge Case: Kalender enthält 0 Termine_ → Meldung: „Dein Google Calendar enthält keine Termine. Verbinde eine weitere Quelle, um dein Wissensmodell aufzubauen."
8. **Erstes Briefing:** Nutzerin klickt „Erstes Briefing generieren". Loading-Animation (max. 10 Sekunden). Das Briefing wird angezeigt mit Hinweis: „Dies ist dein erstes Briefing. Je mehr Quellen du verbindest, desto umfassender werden die Briefings."
   - _Fehlerfall: Briefing-Generierung schlägt fehl (LLM-Fehler)_ → Fehlermeldung: „Das Briefing konnte nicht generiert werden. Wir versuchen es automatisch erneut. Du kannst es auch manuell über den Button unten erneut auslösen."

---

### User Flow 2: Täglicher Nutzungsflow

**Ziel:** Nutzerin startet den Arbeitstag mit dem Morgenbriefing und nutzt die Suche.

1. **Login:** Nutzerin ruft die App auf. Wenn das JWT-Cookie noch gültig ist, wird sie direkt zum Dashboard weitergeleitet. Sonst: Login mit E-Mail und Passwort.
   - _Fehlerfall: Access-Token abgelaufen, Refresh-Token gültig_ → Automatischer Refresh im Hintergrund, keine Unterbrechung.
   - _Fehlerfall: Refresh-Token abgelaufen_ → Redirect zur Login-Seite mit Meldung „Deine Sitzung ist abgelaufen. Bitte melde dich erneut an."
2. **Dashboard:** Das Dashboard zeigt als Hauptinhalt das heutige Morgenbriefing (automatisch um 06:30 Uhr generiert). Darunter: „Nächste Termine"-Karten. Rechts: Konnektor-Status-Widget.
   - _Edge Case: Morgenbriefing noch nicht generiert (Nutzerin vor 06:30)_ → Hinweis: „Dein Morgenbriefing wird um 06:30 Uhr generiert. Du kannst es auch jetzt manuell auslösen." Button: „Briefing jetzt generieren".
   - _Edge Case: Keine Termine heute und keine neuen Dokumente_ → Briefing enthält stattdessen eine Zusammenfassung der Woche: „Keine Termine heute. Hier ein Überblick über die Themen der letzten 7 Tage."
3. **Morgenbriefing lesen:** Die Nutzerin liest das Briefing. Sie klickt auf eine Quellenreferenz → wird zum Dokument-Detail navigiert und sieht den relevanten Chunk hervorgehoben.
4. **Semantische Suche nutzen:** Die Nutzerin wechselt zur Suchseite. Sie gibt ein: „Was hat Maria letzte Woche zum Redesign gesagt?" Ergebnisse erscheinen in < 2 Sekunden.
   - _Edge Case: Keine Ergebnisse_ → „Keine Ergebnisse für deine Suche gefunden. Versuche eine allgemeinere Formulierung oder prüfe deine Filter."
5. **Ergebnisse erkunden:** Die Nutzerin klickt auf ein Suchergebnis. Sie sieht den Chunk mit hervorgehobenen Schlüsselbegriffen und die Quellenangabe. Sie klickt „Original öffnen" → die Notion-Seite öffnet sich in einem neuen Tab.
6. **Knowledge Explorer:** Die Nutzerin öffnet den Knowledge Explorer. Sie sieht die Entität „Maria" und klickt darauf. Die Graphdarstellung zeigt Marias Verbindungen: 3 Projekte, 5 zugehörige Meetings, 2 Themen. Sie klickt auf ein Projekt → die Detailseite zeigt alle verknüpften Dokumente.

---

### User Flow 3: Meeting-Vorbereitung

**Ziel:** Nutzerin bereitet sich auf ein Meeting in 30 Minuten vor.

1. **Trigger:** Die Nutzerin hat einen Kalendereintrag „Produkt-Sync mit Team Alpha" um 10:00 Uhr. Um 09:30 Uhr wird automatisch ein Meeting-Briefing generiert (wenn der Nutzer die automatische Generierung aktiviert hat), oder die Nutzerin klickt manuell auf den „Vorbereiten"-Button neben dem Termin auf dem Dashboard.
2. **Briefing wird generiert:** Loading-Animation. Das System:
   - Holt die Teilnehmer aus dem Kalenderterm (Maria S., Thomas K., Lena W.).
   - Fragt den Knowledge Graph nach vorherigen Interaktionen mit diesen Personen.
   - Sucht semantisch nach Dokumenten, die die Meeting-Themen betreffen.
   - Generiert ein strukturiertes Briefing (max. 400 Wörter).
   - _Fehlerfall: Kein LLM-Provider erreichbar_ → Fallback: Rohdaten anzeigen (letzte Meetings mit Teilnehmern, relevante Dokumente) ohne LLM-Zusammenfassung, mit Hinweis „Zusammenfassung konnte nicht generiert werden. Hier die relevanten Quellen."
3. **Briefing anzeigen:** Das Meeting-Briefing enthält:
   - Thema und geplante Dauer
   - Pro Teilnehmer: Letzte gemeinsame Meetings, gemeinsame Projekte, offene Punkte
   - Relevante Dokumente der letzten 14 Tage
   - Alle Aussagen mit Quellenreferenzen
   - _Edge Case: Ein Teilnehmer ist dem System unbekannt_ → „Thomas K. – Neu im System. Keine vorherigen Interaktionen gespeichert."
   - _Edge Case: Kein Kontext verfügbar (Meeting-Titel ist nur „Call")_ → „Für dieses Meeting liegen keine spezifischen Kontextinformationen vor. Hier die aktuellen Interaktionen mit den Teilnehmern."
4. **Quellen prüfen:** Die Nutzerin klickt auf eine Quellenreferenz. Sie wird zum Dokument-Detail navigiert und sieht den relevanten Chunk hervorgehoben. Sie kann über einen Deeplink das Original in der Quell-App öffnen.

---

### User Flow 4: Datenlöschung / Account-Kündigung (DSGVO-Flow)

**Ziel:** Nutzerin möchte ihren Account und alle Daten vollständig löschen.

1. **Einstellungen öffnen:** Die Nutzerin navigiert zu Einstellungen → Account → „Account löschen".
2. **Information und Warnung:** Es erscheint ein Vollbild-Dialog mit:
   - Erklärung: „Wenn du deinen Account löschst, werden nach einer 30-tägigen Karenzfrist alle deine Daten unwiderruflich gelöscht. Dies umfasst: alle importierten Dokumente, extrahierte Entitäten, generierte Briefings, Verbindungen zu Datenquellen und dein Audit-Log."
   - Hinweis: „Du kannst vor der Löschung einen vollständigen Datenexport anfordern."
   - Checkbox: „Ich habe verstanden, dass dies nicht rückgängig gemacht werden kann."
   - Passwort-Feld zur Bestätigung
   - Button: „Account zur Löschung vormerken"
   - _Fehlerfall: Falsches Passwort_ → „Das eingegebene Passwort ist nicht korrekt."
3. **Bestätigung:** Die Nutzerin bestätigt. Der Account wird als „zur Löschung vorgemerkt" markiert. E-Mail-Bestätigung mit Löschdatum. Die Nutzerin wird ausgeloggt.
4. **Karenzfrist (30 Tage):**
   - Die Nutzerin kann sich weiterhin einloggen.
   - Ein permanenter Banner zeigt: „Dein Account wird am [Datum] gelöscht. [Löschung abbrechen]"
   - Alle Funktionen sind weiterhin nutzbar (Lesen, Suchen). Neue Daten-Imports werden nicht durchgeführt.
   - _Edge Case: Nutzerin klickt „Löschung abbrechen"_ → Account wird reaktiviert, Banner verschwindet, alle Konnektoren werden wieder aktiviert.
5. **Löschung nach Karenzfrist:** Am Stichtag führt der Cleanup-Job folgende Schritte durch:
   - PostgreSQL: DELETE CASCADE auf den User-Eintrag (entfernt alle Dokumente, Chunks, Entitäten, Briefings, Connections, Audit-Log).
   - Weaviate: Tenant des Nutzers wird vollständig gelöscht.
   - Neo4j: Alle Knoten und Kanten mit der userId werden gelöscht.
   - Redis: Sessions und Rate-Limit-Daten werden geflusht.
   - AWS S3: Eventuelle Export-Dateien werden gelöscht.
   - _Fehlerfall: Löschung in einer Datenbank schlägt fehl_ → Job wird als „fehlgeschlagen" markiert, automatischer Retry nach 1 Stunde. Nach 3 Fehlversuchen: Alert an Operations. Nutzer-Daten werden als „Löschung ausstehend" markiert.
6. **Bestätigungs-E-Mail:** Nach vollständiger Löschung erhält die ehemalige Nutzerin eine Bestätigungs-E-Mail: „Dein PWBS-Account und alle zugehörigen Daten wurden gelöscht."

---

## 8. API-Spezifikation (Übersicht)

### Auth

| Methode | Pfad                    | Beschreibung                        | Auth    | Request Body                      | Response                                     | Fehler-Codes  |
| ------- | ----------------------- | ----------------------------------- | ------- | --------------------------------- | -------------------------------------------- | ------------- |
| POST    | `/api/v1/auth/register` | Neuen Nutzer registrieren           | Keine   | `{email, password, display_name}` | `{user_id, access_token, refresh_token}`     | 400, 409, 422 |
| POST    | `/api/v1/auth/login`    | Login                               | Keine   | `{email, password}`               | `{access_token, refresh_token, expires_in}`  | 400, 401      |
| POST    | `/api/v1/auth/refresh`  | Access-Token erneuern               | Refresh | `{refresh_token}`                 | `{access_token, refresh_token, expires_in}`  | 401           |
| POST    | `/api/v1/auth/logout`   | Logout (Refresh-Token invalidieren) | JWT     | `{refresh_token}`                 | `{message: "logged_out"}`                    | 401           |
| GET     | `/api/v1/auth/me`       | Aktuelles Nutzerprofil              | JWT     | –                                 | `{user_id, email, display_name, created_at}` | 401           |

### Connectors

| Methode | Pfad                                 | Beschreibung                         | Auth | Request Body    | Response                                                         | Fehler-Codes  |
| ------- | ------------------------------------ | ------------------------------------ | ---- | --------------- | ---------------------------------------------------------------- | ------------- |
| GET     | `/api/v1/connectors/`                | Verfügbare Konnektor-Typen auflisten | JWT  | –               | `{connectors: [{type, name, description, auth_method, status}]}` | 401           |
| GET     | `/api/v1/connectors/status`          | Status aller verbundenen Quellen     | JWT  | –               | `{connections: [{type, status, doc_count, last_sync, error?}]}`  | 401           |
| GET     | `/api/v1/connectors/{type}/auth-url` | OAuth2-Auth-URL generieren           | JWT  | –               | `{auth_url, state}`                                              | 401, 404      |
| POST    | `/api/v1/connectors/{type}/callback` | OAuth2-Callback verarbeiten          | JWT  | `{code, state}` | `{connection_id, status, initial_sync_started}`                  | 400, 401, 409 |
| POST    | `/api/v1/connectors/{type}/config`   | Obsidian-Vault-Pfad konfigurieren    | JWT  | `{vault_path}`  | `{connection_id, status, file_count}`                            | 400, 401, 422 |
| DELETE  | `/api/v1/connectors/{type}`          | Verbindung trennen + Daten löschen   | JWT  | –               | `{message, deleted_doc_count}`                                   | 401, 404      |
| POST    | `/api/v1/connectors/{type}/sync`     | Manuellen Sync auslösen              | JWT  | –               | `{sync_id, status: "started"}`                                   | 401, 404, 429 |

### Search

| Methode | Pfad              | Beschreibung               | Auth | Request Body                                                                        | Response                                                                                                        | Fehler-Codes  |
| ------- | ----------------- | -------------------------- | ---- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------- |
| POST    | `/api/v1/search/` | Semantische + Hybrid-Suche | JWT  | `{query, filters?: {source_types?, date_from?, date_to?, entity_ids?}, limit?: 10}` | `{results: [{chunk_id, doc_title, source_type, date, content, score, entities}], answer?, sources, confidence}` | 400, 401, 422 |

### Briefings

| Methode | Pfad                              | Beschreibung                    | Auth | Request Body                                                 | Response                                                                                                   | Fehler-Codes  |
| ------- | --------------------------------- | ------------------------------- | ---- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- | ------------- |
| GET     | `/api/v1/briefings/`              | Briefings auflisten (paginiert) | JWT  | Query: `?type=morning\|meeting_prep&limit=10&offset=0`       | `{briefings: [{id, type, title, generated_at, expires_at}], total, has_more}`                              | 401           |
| GET     | `/api/v1/briefings/latest`        | Letztes Briefing pro Typ        | JWT  | Query: `?type=morning`                                       | `{briefing: {id, type, title, content, source_chunks, source_entities, generated_at}}`                     | 401, 404      |
| GET     | `/api/v1/briefings/{id}`          | Einzelnes Briefing mit Quellen  | JWT  | –                                                            | `{id, type, title, content, sources: [{chunk_id, doc_title, source_type, date, relevance}], generated_at}` | 401, 403, 404 |
| POST    | `/api/v1/briefings/generate`      | Briefing manuell auslösen       | JWT  | `{type: "morning"\|"meeting_prep", context?: {meeting_id?}}` | `{briefing_id, status: "generating"}`                                                                      | 400, 401, 429 |
| POST    | `/api/v1/briefings/{id}/feedback` | Feedback zu Briefing abgeben    | JWT  | `{rating: "positive"\|"negative", comment?}`                 | `{message: "feedback_saved"}`                                                                              | 400, 401, 404 |
| DELETE  | `/api/v1/briefings/{id}`          | Briefing löschen                | JWT  | –                                                            | `{message: "deleted"}`                                                                                     | 401, 403, 404 |

### Knowledge

| Methode | Pfad                                        | Beschreibung                    | Auth | Request Body / Query                                                       | Response                                                                                                  | Fehler-Codes  |
| ------- | ------------------------------------------- | ------------------------------- | ---- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------- |
| GET     | `/api/v1/knowledge/entities`                | Entitäten auflisten (gefiltert) | JWT  | Query: `?type=person\|project\|topic&sort=mention_count&limit=50&offset=0` | `{entities: [{id, type, name, mention_count, last_seen}], total}`                                         | 401           |
| GET     | `/api/v1/knowledge/entities/{id}`           | Entität mit Verbindungen        | JWT  | –                                                                          | `{id, type, name, metadata, first_seen, last_seen, mention_count, related: [{id, type, name, relation}]}` | 401, 403, 404 |
| GET     | `/api/v1/knowledge/entities/{id}/related`   | Verwandte Entitäten             | JWT  | Query: `?depth=2&limit=20`                                                 | `{entities: [{id, type, name, relation, weight}]}`                                                        | 401, 403, 404 |
| GET     | `/api/v1/knowledge/entities/{id}/documents` | Dokumente zu einer Entität      | JWT  | Query: `?limit=20&offset=0`                                                | `{documents: [{doc_id, title, source_type, date, chunk_preview}], total}`                                 | 401, 403, 404 |
| GET     | `/api/v1/knowledge/graph`                   | Subgraph für Visualisierung     | JWT  | Query: `?center={entity_id}&depth=2&limit=50`                              | `{nodes: [{id, type, name, size}], edges: [{source, target, relation, weight}]}`                          | 401, 404      |

### Documents

| Methode | Pfad                     | Beschreibung                    | Auth | Request Body / Query                           | Response                                                                                           | Fehler-Codes  |
| ------- | ------------------------ | ------------------------------- | ---- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------- |
| GET     | `/api/v1/documents/`     | Dokumente auflisten (paginiert) | JWT  | Query: `?source_type=notion&limit=20&offset=0` | `{documents: [{id, title, source_type, source_id, chunk_count, created_at, updated_at}], total}`   | 401           |
| GET     | `/api/v1/documents/{id}` | Dokument-Metadaten + Chunks     | JWT  | –                                              | `{id, title, source_type, metadata, chunks: [{id, index, content_preview, entities}], created_at}` | 401, 403, 404 |
| DELETE  | `/api/v1/documents/{id}` | Dokument löschen (kaskadiert)   | JWT  | –                                              | `{message: "deleted", deleted_chunks}`                                                             | 401, 403, 404 |

### User

| Methode | Pfad                                   | Beschreibung                      | Auth | Request Body                                      | Response                                                                         | Fehler-Codes  |
| ------- | -------------------------------------- | --------------------------------- | ---- | ------------------------------------------------- | -------------------------------------------------------------------------------- | ------------- |
| GET     | `/api/v1/user/settings`                | Nutzereinstellungen abrufen       | JWT  | –                                                 | `{timezone, briefing_auto_generate, language, notification_prefs}`               | 401           |
| PATCH   | `/api/v1/user/settings`                | Nutzereinstellungen aktualisieren | JWT  | `{timezone?, briefing_auto_generate?, language?}` | `{updated_settings}`                                                             | 400, 401, 422 |
| POST    | `/api/v1/user/export`                  | DSGVO-Datenexport anfordern       | JWT  | –                                                 | `{export_id, status: "processing", estimated_completion}`                        | 401, 429      |
| GET     | `/api/v1/user/export/{id}`             | Export-Status prüfen              | JWT  | –                                                 | `{export_id, status, download_url?, expires_at?}`                                | 401, 404      |
| DELETE  | `/api/v1/user/account`                 | Account-Löschung einleiten        | JWT  | `{password, confirmation: "DELETE"}`              | `{deletion_scheduled_at, cancellation_deadline}`                                 | 400, 401, 403 |
| POST    | `/api/v1/user/account/cancel-deletion` | Account-Löschung abbrechen        | JWT  | –                                                 | `{message: "deletion_cancelled"}`                                                | 401, 404, 409 |
| GET     | `/api/v1/user/audit-log`               | Audit-Log einsehen                | JWT  | Query: `?limit=100&offset=0`                      | `{entries: [{id, action, resource_type, resource_id, created_at}], total}`       | 401           |
| GET     | `/api/v1/user/security`                | Verschlüsselungsstatus            | JWT  | –                                                 | `{encryption: {postgres, weaviate, neo4j}, data_region, llm_data_usage: "none"}` | 401           |

---

## 9. Datenmodell-Übersicht

### User (Nutzer)

- **id:** Eindeutige Kennung des Nutzers (UUID).
- **email:** E-Mail-Adresse für Login und Kommunikation. Eindeutig im System.
- **display_name:** Anzeigename im Frontend.
- **password_hash:** Argon2-gehashtes Passwort. Wird nie im Klartext gespeichert.
- **encryption_key_enc:** Nutzer-spezifischer Data Encryption Key (DEK), verschlüsselt mit dem Master Key (KEK). Dient zur Verschlüsselung aller sensiblen Nutzerdaten.
- **created_at / updated_at:** Erstellungs- und Änderungszeitpunkt.

**Beziehungen:** Ein User besitzt beliebig viele Connections, Documents, Entities und Briefings. Alle Daten sind durch CASCADE-Löschung an den User gebunden.

---

### Connection (Verbundene Datenquelle)

- **id:** Eindeutige Kennung der Verbindung (UUID).
- **user_id:** Fremdschlüssel zum Nutzer. Jede Verbindung gehört genau einem Nutzer.
- **source_type:** Typ der Datenquelle (GOOGLE_CALENDAR, NOTION, OBSIDIAN, ZOOM).
- **status:** Aktueller Status der Verbindung (active, paused, error, revoked).
- **credentials_enc:** Verschlüsselte OAuth-Tokens (Access + Refresh Token), verschlüsselt mit dem User-DEK via Fernet.
- **watermark:** Zeitpunkt des letzten erfolgreichen Syncs. Dient als Cursor für inkrementelle Abfragen.
- **config:** Quellenspezifische Konfiguration (z. B. Obsidian-Vault-Pfad, Notion-Workspace-ID) als JSON.
- **created_at / updated_at:** Erstellungs- und Änderungszeitpunkt.

**Beziehungen:** Gehört zu genau einem User. Eine Connection erzeugt beliebig viele Documents. Pro User ist jeder source_type einmalig.

---

### Document (Importiertes Dokument)

- **id:** Eindeutige Kennung des Dokuments (UUID).
- **user_id:** Fremdschlüssel zum Nutzer. Mandanten-Isolation.
- **source_type:** Herkunft des Dokuments (gleiche Werte wie Connection.source_type).
- **source_id:** Originale ID des Dokuments im Quellsystem (z. B. Notion-Page-ID, Google-Event-ID). Dient zur Deduplizierung und Verlinkung.
- **title:** Titel des Dokuments.
- **content_hash:** SHA-256-Hash des Rohinhalts. Ermöglicht idempotente Re-Imports: Wenn der Hash gleich bleibt, wird nicht erneut verarbeitet.
- **language:** Sprache des Inhalts (ISO 639-1).
- **chunk_count:** Anzahl der erzeugten Chunks.
- **processing_status:** Verarbeitungsstatus (pending, processing, done, error).
- **created_at / updated_at:** Zeitpunkte.

**Beziehungen:** Gehört zu genau einem User. Enthält beliebig viele Chunks. Wird durch beliebig viele Entities referenziert. Eindeutig identifiziert durch (user_id, source_type, source_id).

---

### Chunk (Textausschnitt für Embedding)

- **id:** Eindeutige Kennung des Chunks (UUID).
- **document_id:** Fremdschlüssel zum Dokument.
- **user_id:** Fremdschlüssel zum Nutzer (denormalisiert für schnelle Queries).
- **chunk_index:** Reihenfolge des Chunks innerhalb des Dokuments.
- **token_count:** Anzahl der Tokens im Chunk (für Token-Budget-Kalkulationen).
- **weaviate_id:** Referenz zum Vektor in der Weaviate-Datenbank. Bindeglied zwischen relationalem Speicher und Vektordatenbank.
- **content_preview:** Erste 200 Zeichen des Chunks (für Admin-Zwecke und Vorschau in Suchergebnissen).
- **created_at:** Erstellungszeitpunkt.

**Beziehungen:** Gehört zu genau einem Document. Kann von beliebig vielen EntityMentions referenziert werden. Hat genau einen Vektor in Weaviate. Kann in Briefings als Quelle referenziert werden.

---

### Entity (Extrahierte Entität)

- **id:** Eindeutige Kennung der Entität (UUID).
- **user_id:** Fremdschlüssel zum Nutzer.
- **entity_type:** Typ der Entität (PERSON, PROJECT, TOPIC, DECISION).
- **name:** Anzeigename der Entität.
- **normalized_name:** Normalisierter Name (lowercase, trimmed) zur Deduplizierung.
- **metadata:** Zusätzliche Informationen als JSON (z. B. Rolle einer Person, Status eines Projekts).
- **first_seen / last_seen:** Zeitpunkte der ersten und letzten Erwähnung.
- **mention_count:** Gesamtanzahl der Erwähnungen über alle Chunks.
- **neo4j_node_id:** Referenz zum entsprechenden Knoten im Neo4j Knowledge Graph.

**Beziehungen:** Gehört zu genau einem User. Wird über EntityMentions mit Chunks verknüpft. Hat einen korrespondierenden Knoten in Neo4j mit Kanten zu anderen Entitäten. Eindeutig pro (user_id, entity_type, normalized_name).

---

### EntityMention (Verknüpfung Entität ↔ Chunk)

- **entity_id:** Fremdschlüssel zur Entität.
- **chunk_id:** Fremdschlüssel zum Chunk.
- **confidence:** Konfidenzwert der Extraktion (0.0–1.0). Regelbasierte Extraktion = 1.0, LLM-basiert = variabel.
- **extraction_method:** Methode der Extraktion (rule, llm).

**Beziehungen:** Verbindet genau eine Entity mit genau einem Chunk (M:N-Beziehung). Zusammengesetzter Primärschlüssel (entity_id, chunk_id).

---

### Briefing (Generiertes Kontextbriefing)

- **id:** Eindeutige Kennung des Briefings (UUID).
- **user_id:** Fremdschlüssel zum Nutzer.
- **briefing_type:** Typ des Briefings (MORNING, MEETING_PREP).
- **title:** Titel (z. B. „Morgenbriefing – 18. März 2026").
- **content:** Generierter Inhalt im Markdown-Format mit eingebetteten Quellenreferenzen.
- **source_chunks:** Array von Chunk-UUIDs, die als Kontext für die Generierung verwendet wurden. Ermöglicht Nachvollziehbarkeit.
- **source_entities:** Array von Entity-UUIDs, die im Briefing referenziert werden.
- **trigger_context:** JSON mit Informationen zum Auslöser (z. B. Meeting-ID bei Meeting-Briefings, Zeitplan-Info bei Morgenbriefings).
- **generated_at:** Zeitpunkt der Generierung.
- **expires_at:** Ablaufdatum. Morgenbriefings: 24h, Meeting-Briefings: 48h.

**Beziehungen:** Gehört zu genau einem User. Referenziert beliebig viele Chunks (als Quellen) und Entities.

---

### AuditLogEntry (Audit-Protokolleintrag)

- **id:** Fortlaufende, automatisch inkrementierte ID.
- **user_id:** Fremdschlüssel zum Nutzer. NULL nach Account-Deletion (Referenz wird auf SET NULL gesetzt; der Eintrag bleibt aus Compliance-Gründen bis zum Ende der Retention-Dauer bestehen).
- **action:** Aktion, die protokolliert wird (z. B. user.registered, connection.created, data.ingested, briefing.generated, search.executed, user.deleted).
- **resource_type:** Typ der betroffenen Ressource (document, connection, briefing, entity).
- **resource_id:** UUID der betroffenen Ressource.
- **metadata:** Zusätzliche Metadaten als JSON (keine PII, keine Inhalte – nur IDs, Zählwerte, Fehlercodes).
- **ip_address:** IP-Adresse des Aufrufs.
- **created_at:** Zeitpunkt.

**Beziehungen:** Referenziert optional einen User. Append-only (kein UPDATE/DELETE, außer bei Retention-Bereinigung oder Account-Deletion).

---

## 10. Metriken & Erfolgskriterien

### North Star Metric

**Wöchentlich aktive Briefing-Nutzer (WAB):** Anzahl der Nutzer, die in einer Kalenderwoche mindestens ein Briefing (Morgen- oder Meeting-Briefing) aufgerufen haben.

**Begründung:** Diese Metrik bildet den Kernwert des Produkts ab. Wer regelmäßig Briefings abruft, hat das System in seinen Workflow integriert und erlebt den primären Nutzen – kontextbezogene Vorbereitung auf den Tag und auf Meetings. Die Metrik korreliert stark mit Retention: Wer Briefings nutzt, bleibt; wer aufhört, churnt.

---

### Engagement-Metriken

| Metrik                                     | Zielwert (MVP-Ende)    | Messmethode                                                         | Systembereich      |
| ------------------------------------------ | ---------------------- | ------------------------------------------------------------------- | ------------------ |
| DAU/MAU-Ratio                              | ≥ 40 %                 | Login-Events / eindeutige Nutzer pro Monat (Analytics)              | API Layer (Auth)   |
| Briefings abgerufen / Nutzer / Woche       | ≥ 3                    | Aggregation der GET /briefings/{id} und GET /briefings/latest Calls | Briefing Engine    |
| Suchanfragen / aktiver Nutzer / Woche      | ≥ 2                    | Aggregation der POST /search/ Calls pro Nutzer                      | Search Service     |
| Durchschn. verbundene Konnektoren / Nutzer | ≥ 2                    | COUNT(DISTINCT source_type) pro User in connections-Tabelle         | Connector Registry |
| Knowledge Explorer Sessions / Woche        | ≥ 1 pro aktivem Nutzer | Page-View-Tracking auf /knowledge/-Routen                           | Frontend Analytics |

### Quality-Metriken

| Metrik                  | Zielwert (MVP-Ende) | Messmethode                                                                  | Systembereich       |
| ----------------------- | ------------------- | ---------------------------------------------------------------------------- | ------------------- |
| Briefing-Relevanz-Score | ≥ 70 % „hilfreich"  | Positives Feedback / (positiv + negativ) aus Briefing-Feedback-Funktion      | Briefing Engine     |
| False-Positive-Rate NER | ≤ 15 %              | Stichprobenartige manuelle QA (50 Entitäten/Woche gegen Quelldokumente)      | Processing Pipeline |
| Halluzinations-Vorfälle | 0 pro Woche         | Nutzer-Reports + automatische Quellen-Validierung im Briefing-Postprocessing | LLM Orchestration   |
| Suchrelevanz (nDCG@10)  | ≥ 0,6               | Golden-Set-Evaluation mit 50 manuell bewerteten Queries                      | Search Service      |

### Retention-Metriken

| Metrik        | Zielwert (MVP-Ende) | Messmethode                                                        | Systembereich |
| ------------- | ------------------- | ------------------------------------------------------------------ | ------------- |
| D1-Retention  | ≥ 80 %              | Anteil der Nutzer, die am Tag nach Registrierung erneut aktiv sind | Analytics     |
| D7-Retention  | ≥ 65 %              | Anteil einmal wöchentlich aktiver Nutzer                           | Analytics     |
| D14-Retention | ≥ 60 %              | Anteil nach zwei Wochen aktiver Nutzer                             | Analytics     |
| D30-Retention | ≥ 50 %              | Anteil nach 30 Tagen aktiver Nutzer                                | Analytics     |

### Onboarding-Metriken

| Metrik                     | Zielwert (MVP-Ende)      | Messmethode                                                                                                 | Systembereich  |
| -------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------- | -------------- |
| Time-to-First-Briefing     | ≤ 20 Minuten             | Zeit zwischen user.registered und erstem briefing.generated Event                                           | Audit-Log      |
| Onboarding-Completion-Rate | ≥ 80 %                   | Anteil der Nutzer, die innerhalb von 24h ≥ 1 Konnektor + ≥ 1 Briefing erreichen                             | Event-Tracking |
| Dropout-Punkt              | Identifiziert und < 20 % | Funnel-Analyse: Registrierung → Erster Konnektor → Erster Sync → Erstes Briefing. Dropout-Rate pro Schritt. | Analytics      |

---

## 11. Annahmen, Risiken & Mitigationen

| ID    | Typ     | Beschreibung                                                                                                                                          | Wahrscheinlichkeit | Impact | Mitigation                                                                                                                                                                              |
| ----- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AR-01 | Annahme | Kalender + Notizen + Meeting-Transkripte decken genug Kontext ab, um nützliche Briefings zu generieren (ohne Gmail und Slack).                        | –                  | –      | Validierung durch Early-Adopter-Feedback in den ersten 4 Wochen. Pivot-Kriterium: Wenn < 50 % der Nutzer Briefings als „hilfreich" bewerten, zusätzliche Quellen priorisieren.          |
| AR-02 | Annahme | Early Adopters sind bereit, dem System Zugriff auf persönliche Datenquellen (Kalender, Notizen, Transkripte) zu gewähren.                             | –                  | –      | Transparente Datenschutzkommunikation beim Onboarding. DSGVO-Konformität und EU-Hosting als Vertrauensanker.                                                                            |
| AR-03 | Annahme | text-embedding-3-small (OpenAI) liefert ausreichende Qualität für die semantische Suche über deutschsprachige und gemischt deutsch/englische Inhalte. | –                  | –      | A/B-Test gegen text-embedding-3-large in den ersten Wochen. Golden-Set mit 50 Queries erstellen und nDCG messen.                                                                        |
| AR-04 | Risiko  | LLM-Halluzinationen erzeugen falsche Verknüpfungen oder erfundene Kontextinformationen in Briefings, was zu Vertrauensverlust führt.                  | M                  | H      | Grounded Generation (nur RAG-basiert), Quellenvalidierung im Postprocessing, Confidence-Scoring. Fallback auf Rohdaten bei niedrigem Confidence.                                        |
| AR-05 | Risiko  | Onboarding-Aufwand ist zu hoch: OAuth-Flows sind für nicht-technische Nutzer zu komplex oder die initiale Sync-Dauer zu lang.                         | M                  | H      | Guided Onboarding mit Schritt-für-Schritt-Wizard. Fortschrittsanzeigen während des Syncs. Ziel: Erster Konnektor in < 5 Minuten.                                                        |
| AR-06 | Risiko  | Heterogene Datenformate (insb. Obsidian-Markdown mit Plugins, Notion-Blocks mit Embeds) führen zu unzuverlässiger Normalisierung und NER.             | H                  | M      | Robustes Parsing mit Fallbacks. Obsidian: Unterstützung für Standard-Markdown + Frontmatter, Plugin-spezifische Syntax wird als Plaintext behandelt.                                    |
| AR-07 | Risiko  | API-Rate-Limits externer Dienste (Google, Notion, Zoom, OpenAI) beschränken die Sync-Frequenz oder Briefing-Generierung bei wachsender Nutzerzahl.    | M                  | M      | Token-Budget-Management, Batch-APIs nutzen, Zeitversetzung bei Morgenbriefing-Generierung (±15 Min Jitter), lokale Embedding-Modelle als Fallback.                                      |
| AR-08 | Risiko  | Datenschutzverletzung oder Sicherheitslücke führt zu Verlust des Nutzervertrauens.                                                                    | L                  | H      | Envelope Encryption, Tenant-Isolation, kein PII in Logs, OWASP-Top-10-Review, regelmäßige Dependency-Updates, Security-Review vor Go-Live.                                              |
| AR-09 | Risiko  | Kosten für LLM-API-Calls und Embedding-Generierung überschreiten das Budget bei steigender Nutzung.                                                   | M                  | M      | Token-Budget pro Nutzer/Tag (Max. 100 LLM-Extraction-Calls). Caching häufiger Queries. Günstigere Modelle (Claude Haiku) für NER. Monitoring der Kosten pro Nutzer.                     |
| AR-10 | Risiko  | Notion- oder Zoom-API-Änderungen brechen den Konnektor ohne Vorwarnung.                                                                               | M                  | M      | Adapter-Pattern mit klarem Interface. Integrationstests gegen echte APIs (täglicher CI-Job). Monitoring der API-Verfügbarkeit. Fehler-Alerting pro Konnektor.                           |
| AR-11 | Annahme | 10–20 Early Adopters lassen sich innerhalb von 4 Wochen rekrutieren und sind bereit, das System regelmäßig zu nutzen und Feedback zu geben.           | –                  | –      | Persönliche Ansprache aus bestehendem Netzwerk. Wöchentliche Feedback-Sessions. Kein Commitment > 15 Min/Woche für Feedback erforderlich.                                               |
| AR-12 | Risiko  | Neo4j Knowledge Graph liefert bei geringer Datenmenge (wenige Wochen) keinen spürbaren Mehrwert gegenüber reiner Vektor⁠suche.                        | M                  | L      | Knowledge Explorer als „Growing Feature" positionieren. Nutzern kommunizieren, dass der Graph mit der Zeit wertvoller wird. Fallback: Briefings funktionieren auch nur mit Vektorsuche. |

---

## 12. Abhängigkeiten & externe Dienste

| Anbieter               | Zweck                                                           | SLA                                | Kostenschätzung (MVP, monatlich)                      | Fallback                                                                    | DSGVO-Relevanz                                                                                                                                          |
| ---------------------- | --------------------------------------------------------------- | ---------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AWS (eu-central-1)** | Hosting: ECS Fargate, RDS PostgreSQL, EBS, ALB, ElastiCache, S3 | 99,99 % (EC2), 99,95 % (RDS)       | 200–400 € (t3-Instanzen, minimale Konfiguration)      | Multi-AZ für RDS. Kein Multi-Region im MVP.                                 | AVV mit AWS vorhanden. Datenresidenz Frankfurt. AWS ist DSGVO-konform.                                                                                  |
| **Vercel**             | Frontend-Hosting (Next.js), Edge Functions                      | 99,99 %                            | 0–20 € (Pro-Plan)                                     | Statisches Fallback-Hosting auf S3 + CloudFront                             | AVV mit Vercel erforderlich. Edge-Funktionen laufen in EU-Region. Kein PII im Frontend-Cache.                                                           |
| **OpenAI**             | Embedding-Generierung (text-embedding-3-small)                  | 99,5 % (documented target)         | 15–30 € (geschätzt bei 20 Nutzern, ~2M Tokens/Monat)  | Lokales Modell all-MiniLM-L6-v2 via Sentence Transformers                   | AVV/DPA mit OpenAI erforderlich. API-Daten werden laut OpenAI-Policy nicht für Training verwendet (Enterprise/API). DSGVO-kritisch: Daten verlassen EU. |
| **Anthropic (Claude)** | LLM für Briefing-Generierung, NER, Suchantworten                | 99,5 % (documented target)         | 50–100 € (geschätzt bei 20 Nutzern, ~5M Tokens/Monat) | GPT-4 (OpenAI) als Fallback-Provider. Cached Response als Notfall-Fallback. | AVV/DPA mit Anthropic erforderlich. Daten verlassen EU. Kein Training mit API-Daten laut Anthropic-Policy.                                              |
| **OpenAI (GPT-4)**     | LLM-Fallback bei Claude-Ausfall                                 | 99,5 %                             | 0–50 € (nur bei Fallback-Nutzung)                     | Fehlermeldung mit Rohdaten-Anzeige statt LLM-Zusammenfassung                | Siehe OpenAI oben. Nur aktiviert, wenn Claude nicht erreichbar.                                                                                         |
| **Google (OAuth/API)** | Google Calendar Connector                                       | 99,9 % (Google Workspace SLA)      | 0 € (kostenlose API-Nutzung im Rahmen der Quotas)     | Polling-Fallback bei Webhook-Ausfall. Cache der letzten bekannten Termine.  | OAuth2-Consent deckt Scope ab. Nur Kalender-Events werden gelesen (kein Gmail). Google als Auftragsverarbeiter.                                         |
| **Notion (OAuth/API)** | Notion Connector                                                | 99,9 % (Notion API SLA)            | 0 € (kostenlose API-Nutzung)                          | Letzte bekannte Daten aus DB. Retry bei API-Fehlern.                        | OAuth2-Consent. Notion als Auftragsverarbeiter. Daten werden von Notion-Servern gelesen (US-basiert).                                                   |
| **Zoom (OAuth/API)**   | Zoom Transcript Connector                                       | 99,9 % (Zoom Meeting SLA)          | 0 € (kostenlose API im Rahmen der App)                | Manuelle Transkript-Upload-Option als Fallback.                             | OAuth2-Consent. Zoom als Auftragsverarbeiter. Transkripte werden von Zoom-Servern gelesen.                                                              |
| **Weaviate**           | Vektordatenbank (self-hosted auf AWS EC2)                       | Abhängig von eigener Infrastruktur | Inkludiert in AWS-Kosten (t3.xlarge, ~120 €/Monat)    | Nur semantische Suche betroffen. Keyword-Suche via PostgreSQL als Fallback. | Self-hosted, keine externe Datenübertragung. DSGVO-unkritisch.                                                                                          |
| **Neo4j**              | Knowledge Graph (self-hosted auf AWS EC2)                       | Abhängig von eigener Infrastruktur | Inkludiert in AWS-Kosten (t3.large, ~80 €/Monat)      | Knowledge Explorer degradiert. Briefings verwenden nur Vektorsuche.         | Self-hosted, keine externe Datenübertragung. DSGVO-unkritisch.                                                                                          |

---

## 13. Offene Fragen

| Nr.   | Fragestellung                                                                                                                                           | Auswirkung bei falscher Annahme                                                                                                                     | Entscheidungsverantwortlicher  | Deadline-Empfehlung |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ | ------------------- |
| OQ-01 | Reicht text-embedding-3-small für deutschsprachige und gemischt DE/EN-Inhalte, oder brauchen wir text-embedding-3-large bzw. ein multilinguales Modell? | Schlechte Suchrelevanz bei deutschen Texten → Nutzer vertrauen der Suche nicht → niedrige Adoption                                                  | Technical Lead                 | Monat 4, Woche 2    |
| OQ-02 | Wird der Obsidian-Connector über einen lokalen Agent (Desktop-Dienst) oder über einen Upload-Mechanismus realisiert?                                    | Ohne Agent: Kein automatischer Sync bei Dateiänderungen. Nutzer müssten manuell re-importieren → hoher Friction, niedrige Nutzung                   | Technical Lead                 | Monat 4, Woche 1    |
| OQ-03 | Wie gehen wir mit Meeting-Transkripten um, die keine AI-basierte Transkription haben (z. B. Zoom Basic ohne Transcript)?                                | Feature ist für Nutzer ohne Zoom-Pro-Abo nicht nutzbar → eingeschränkte Zielgruppe                                                                  | Product Owner                  | Monat 4, Woche 3    |
| OQ-04 | Soll die Meeting-Briefing-Generierung standardmäßig automatisch (30 Min vorher) oder nur manuell on-demand geschehen?                                   | Automatisch könnte unnötige LLM-Kosten erzeugen (Briefings für Meetings, die keinen Kontext brauchen). Manuell könnte vergessen werden.             | Product Owner + UX Lead        | Monat 5             |
| OQ-05 | Welche Strategie für die Deduplizierung von Entitäten: Nur Name-Matching (normalisiert) oder auch LLM-basiertes Entity Resolution?                      | Rein regelbasiert: Hohe Duplikat-Rate (z. B. „Maria Schneider" vs. „Maria S." als zwei Entitäten). LLM-basiert: Höhere Kosten.                      | Technical Lead                 | Monat 5             |
| OQ-06 | Müssen wir eine eigene AVV (Auftragsverarbeitungsvereinbarung) mit jedem LLM-Provider abschließen, oder reichen deren Standard-DPAs?                    | Ohne AVV: DSGVO-Verstoß möglich → rechtliches Risiko, ggf. Bußgeld, Vertrauensverlust bei datenschutzsensiblen Early Adopters                       | Datenschutzbeauftragter        | Monat 4, Woche 1    |
| OQ-07 | Wie gehen wir mit Rate-Limits der Notion-API um, wenn ein Nutzer ein sehr großes Workspace (>1000 Seiten) hat?                                          | Initialer Sync dauert Stunden statt Minuten → schlechte Onboarding-Erfahrung → Dropout                                                              | Technical Lead                 | Monat 5             |
| OQ-08 | Soll der Knowledge Explorer im MVP eine vollwertige Graphvisualisierung (D3.js) enthalten, oder reicht eine vereinfachte Listenansicht?                 | Vollwertig: Höherer Entwicklungsaufwand. Vereinfacht: Weniger beeindruckend, aber schneller lieferbar. Risiko: Nutzer sehen keinen Mehrwert im MVP. | Product Owner + UX Lead        | Monat 5, Woche 2    |
| OQ-09 | Werden Briefings per WebSocket live gepusht oder reicht ein Polling-Intervall (z. B. alle 60 Sekunden)?                                                 | WebSocket: Echtzeitgefühl, aber höhere Infrastruktur-Komplexität. Polling: Einfacher, aber bis zu 60s Verzögerung.                                  | Technical Lead                 | Monat 5             |
| OQ-10 | Wie behandeln wir Quellen, die der Nutzer in der Ursprungsapp gelöscht hat, deren Chunks aber noch im PWBS-Index liegen?                                | Verwaiste Chunks verfälschen Suchergebnisse und Briefings. Ohne Bereinigung: Qualitätsverlust über Zeit.                                            | Product Owner + Technical Lead | Monat 6             |
| OQ-11 | Sollen Nutzer in der MVP-Phase die Briefing-Generierungszeit (06:30 Uhr) konfigurieren können?                                                          | Nicht konfigurierbar: Nutzer in anderen Zeitzonen oder mit anderem Tagesrhythmus erhalten irrelevante Briefings.                                    | UX Lead                        | Monat 5             |

---

## 14. Glossar

| Begriff             | Definition                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **UDF**             | Unified Document Format. Das gemeinsame Datenformat, in das alle Konnektoren ihre Rohdaten normalisieren. Enthält Felder wie id, owner_id, source_type, source_id, content, metadata, created_at, expires_at, etc. Dient als einheitliche Schnittstelle zwischen Ingestion und Processing.                                                                                                                          |
| **Chunk**           | Ein Textausschnitt eines Dokuments, der eigenständig eingebettet und durchsuchbar ist. Typische Größe: 128–512 Tokens mit 32–64 Tokens Überlappung zum vorherigen Chunk. Chunks sind die kleinste durchsuchbare Einheit in der Vektordatenbank.                                                                                                                                                                     |
| **Embedding**       | Ein numerischer Vektor (z. B. 1536 Dimensionen bei text-embedding-3-small), der die semantische Bedeutung eines Textausschnitts repräsentiert. Ermöglicht die Suche nach inhaltlich ähnlichen Texten statt nach exakten Schlüsselwörtern.                                                                                                                                                                           |
| **Briefing**        | Ein automatisch generiertes, kontextbezogenes Textdokument, das dem Nutzer relevante Informationen aufbereitet präsentiert. Im MVP: Morgenbriefing (tägliche Übersicht) und Meeting-Briefing (Vorbereitung auf einen spezifischen Termin). Jedes Briefing enthält Quellenreferenzen.                                                                                                                                |
| **Entity**          | Ein aus Dokumenten extrahiertes semantisches Objekt: eine Person, ein Projekt, ein Thema oder eine Entscheidung. Entitäten werden im Knowledge Graph als Knoten verwaltet und ermöglichen die Verknüpfung von Informationen über Dokumentgrenzen hinweg.                                                                                                                                                            |
| **Connector**       | Eine Softwarekomponente, die eine externe Datenquelle (Google Calendar, Notion, Obsidian, Zoom) über deren API anbindet, authentifiziert, inkrementell abfragt und die Rohdaten ins UDF normalisiert. Jeder Konnektor implementiert das BaseConnector-Interface.                                                                                                                                                    |
| **Knowledge Graph** | Eine Graphdatenbank (Neo4j), in der extrahierte Entitäten als Knoten und ihre Beziehungen (z. B. „Person arbeitet an Projekt", „Thema wurde in Meeting diskutiert") als Kanten gespeichert werden. Ermöglicht Kontextabfragen, die über reine Textsuche hinausgehen.                                                                                                                                                |
| **NER**             | Named Entity Recognition. Der Prozess der automatischen Identifikation und Klassifikation von benannten Objekten (Personen, Projekte, Themen, Entscheidungen) in unstrukturiertem Text. Im PWBS zweistufig: regelbasiert (E-Mail-Adressen, @-Mentions) und LLM-basiert (Freitext-Analyse).                                                                                                                          |
| **Konnektor**       | Synonym für Connector (deutsche Schreibweise). Siehe Connector.                                                                                                                                                                                                                                                                                                                                                     |
| **Early Adopter**   | Ein Erstnutzer, der das System in einer frühen Entwicklungsphase (MVP) intensiv testet, regelmäßig Feedback gibt und eine höhere Fehlertoleranz mitbringt. Im PWBS: 10–20 Personen aus der Zielgruppe (Gründer, PMs, Berater).                                                                                                                                                                                      |
| **DSGVO**           | Datenschutz-Grundverordnung. Europäische Verordnung (EU 2016/679) zum Schutz personenbezogener Daten. Im PWBS relevant für: Einwilligungsmanagement (Art. 6), Auskunftsrecht (Art. 15), Recht auf Löschung (Art. 17), Datenportabilität (Art. 20), Privacy by Design (Art. 25), Auftragsverarbeitung (Art. 28).                                                                                                     |
| **Time-to-Value**   | Die Zeitspanne von der Registrierung bis zu dem Moment, in dem ein Nutzer erstmals den konkreten Mehrwert des Produkts erlebt (im PWBS: das erste relevante Briefing). Zielwert: ≤ 3 Tage.                                                                                                                                                                                                                          |
| **Idempotenz**      | Die Eigenschaft einer Operation, bei mehrfacher Ausführung mit denselben Eingaben immer dasselbe Ergebnis zu liefern, ohne unerwünschte Seiteneffekte (z. B. keine Duplikate). Im PWBS kritisch für Ingestion (Upsert statt Insert) und Processing (gleicher Chunk → gleiches Embedding).                                                                                                                           |
| **RAG**             | Retrieval-Augmented Generation. Ein Verfahren, bei dem ein LLM nicht nur auf sein Vorwissen zurückgreift, sondern zunächst relevante Dokumente aus einer externen Wissensbasis abruft (Retrieval) und diese als Kontext in die Generierung einbezieht. Im PWBS: Alle Briefings und Suchantworten basieren auf RAG – das LLM generiert ausschließlich auf Basis der abgerufenen Chunks, nicht aus eigenem Vorwissen. |
