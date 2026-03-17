# Go-to-Market-Plan: PWBS – Persönliches Wissens-Betriebssystem

**Version:** 1.0
**Datum:** 17. März 2026
**Status:** Aktiv
**Basisdokumente:** [vision-wissens-os.md](../vision-wissens-os.md), [ROADMAP.md](../ROADMAP.md), [PRD-SPEC.md](../PRD-SPEC.md), [ADR-014](adr/014-beta-launch-strategie.md), [community-setup.md](public-beta/community-setup.md), [LEGAL_COMPLIANCE.md](LEGAL_COMPLIANCE.md)

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Ideal Customer Profile (ICP)](#2-ideal-customer-profile-icp)
3. [Value Proposition & Positionierung](#3-value-proposition--positionierung)
4. [Pricing-Hypothese](#4-pricing-hypothese)
5. [Distributionskanäle](#5-distributionskanäle)
6. [Beta-Strategie](#6-beta-strategie)
7. [90-Tage-Timeline](#7-90-tage-timeline)
8. [Erfolgskennzahlen (KPIs)](#8-erfolgskennzahlen-kpis)
9. [Content- & Kommunikationsstrategie](#9-content---kommunikationsstrategie)
10. [Risiken & Mitigationen](#10-risiken--mitigationen)

---

## 1. Executive Summary

Das PWBS ist eine kognitive Infrastruktur, die fragmentiertes Wissen aus Google Calendar, Notion, Zoom und Obsidian zusammenführt, semantisch verknüpft und als automatische Kontextbriefings aufbereitet. Es richtet sich an deutschsprachige Wissensarbeiter mit hoher Kontextlast – Gründer, Produktmanager und Berater –, die täglich 30–45 Minuten mit manuellem Kontextwechsel zwischen ihren Tools verlieren. Der Launch erfolgt im März/April 2026 als Closed Beta mit 10–20 handverlesenen Design Partners, gefolgt von einer koordinierten Öffnung über PKM-Communities, ProductHunt und LinkedIn (Hybrid-Strategie gemäß ADR-014). Das Produkt ist im MVP kostenlos nutzbar; die DSGVO-Konformität mit EU-Datenresidenz (AWS Frankfurt) ist ein zentrales Differenzierungsmerkmal gegenüber US-amerikanischen Alternativen. Die technische Basis steht (Phase 2 abgeschlossen), drei rechtliche Pflichtdokumente (Datenschutzerklärung, Impressum, AGB) müssen vor dem Launch erstellt werden.

**Zentrale Hypothese:** Wissensarbeiter, die ≥ 3 der 4 unterstützten Datenquellen aktiv nutzen, werden das Morgenbriefing mindestens dreimal pro Woche abrufen und die semantische Suche der manuellen Suche in Einzelquellen vorziehen – messbar an ≥ 60 % 14-Tage-Retention und ≥ 3 Briefing-Abrufen pro Nutzer pro Woche (Produkthypothese aus PRD-SPEC.md).

---

## 2. Ideal Customer Profile (ICP)

### Primär-ICP für Closed Beta: Lena – Die multikontextuelle Power-Userin

Von den drei PRD-Personas (Jana/Gründerin, Markus/PM, Lena/Beraterin) ist **Lena Vogt** der ideale erste Nutzer. Begründung:

1. **Maximale Konnektorabdeckung:** Lena nutzt aktiv alle vier Kern-Konnektoren – Google Calendar für Kundentermine, Notion für Projektdokumentation, Zoom für Workshops, Obsidian für persönliche Wissensbasis. Jana und Markus nutzen typischerweise nur 2–3.
2. **Höchster Schmerzpunkt:** Mit 3–4 parallelen Kundenprojekten verliert Lena bei jedem Kontextwechsel 15–20 Minuten. Ihr Pain ist quantifizierbar und täglich spürbar – nicht nur an Meeting-intensiven Tagen.
3. **Technische Affinität:** Als Cloud-Architektin ist Lena Obsidian-Power-Userin, versteht APIs und kann qualifiziertes Feedback zu technischen Aspekten geben. Sie toleriert Beta-Rauheit.
4. **Community-Multiplikator:** Freiberufliche Berater sind in PKM-Communities (Obsidian Discord, r/PKMS) aktiv und teilen Tools, die ihren Workflow verbessern.
5. **DSGVO-Sensibilität als Feature-Tester:** Lena arbeitet unter NDA für mehrere Kunden. Mandantentrennung und Datenschutz sind für sie keine abstrakte Anforderung, sondern tägliche Notwendigkeit.

### Demographisches Profil

| Attribut              | Beschreibung                                                                                                           |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Berufsrolle**       | Freiberufliche Berater, Solo-Gründer, Senior PMs – Rollen mit hoher Eigenverantwortung und vielen parallelen Kontexten |
| **Unternehmensgröße** | 1–10 Personen (Einzelunternehmer, Micro-Startups, kleine Beratungen)                                                   |
| **Erfahrungslevel**   | 5+ Jahre Berufserfahrung, etablierte Workflows, bewusste Tool-Auswahl                                                  |
| **Geographie**        | DACH-Region (Deutschland, Österreich, Schweiz)                                                                         |
| **Alter**             | 28–45 Jahre                                                                                                            |

### Psychographisches Profil

| Attribut                         | Beschreibung                                                                                                              |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Kernschmerzpunkt**             | Kognitive Fragmentierung: Wissen ist über 4+ Tools verteilt, der richtige Kontext fehlt im entscheidenden Moment          |
| **Informations-Overload-Muster** | 6–10 Meetings pro Woche, 50+ Notion-Seiten, wachsender Obsidian-Vault, ungelesene Transkripte                             |
| **Bestehende Tool-Landschaft**   | Google Workspace + Notion + Obsidian + Zoom (Kern-Stack). Dazu oft: Todoist/Things, Figma, Miro, Slack                    |
| **Workaround heute**             | Manuelles Zusammensuchen vor Meetings (20–30 Min/Tag), Obsidian als „Second Brain" mit wachsendem aber ungenutztem Archiv |
| **Adoptionsbereitschaft**        | Hoch für Tools, die messbaren Zeitgewinn liefern. Niedrig für Tools, die weitere manuelle Pflege erfordern                |

### Technisches Profil

| Konnektor       | Nutzung durch ICP                                          |
| --------------- | ---------------------------------------------------------- |
| Google Calendar | ✅ Primärer Kalender für alle beruflichen Termine          |
| Notion          | ✅ Projektdokumentation, Kunden-Wikis, Meeting-Notes       |
| Obsidian        | ✅ Persönliche Wissensbasis, Zettelkasten, Lessons Learned |
| Zoom            | ✅ Kundenmeetings, Workshops (Transkription aktiv)         |

### Anti-Persona: Wer ist NICHT die Zielgruppe im MVP

- **Enterprise-Teams (50+ Personen):** Brauchen RBAC, SSO, Admin-Dashboard – alles deferred in Phase 4+.
- **Reine Obsidian-Nutzer ohne Cloud-Tools:** Ohne Calendar und Zoom fehlt die Datenbasis für nützliche Briefings. PWBS braucht mindestens 2 Datenquellen.
- **„Tool-Touristen":** Personen, die jede neue Produktivitäts-App testen, aber keine davon in ihren Workflow integrieren. Erkennung: weniger als 50 Dokumente in verbundenen Quellen.
- **Datenschutz-Maximalisten ohne Cloud-Bereitschaft:** Wer prinzipiell keine Daten an einen externen Dienst geben will (auch nicht EU-gehostet), für den ist die Cloud-Architektur ein Dealbreaker. Self-Hosting kommt erst in Phase 4.
- **Nutzer ohne Kalenderdaten:** Das Morgenbriefing – der zentrale Value Moment – basiert auf Kalendereinträgen. Ohne verbundenen Kalender ist der Sofort-Nutzen stark eingeschränkt.

---

## 3. Value Proposition & Positionierung

### Kernversprechen

> **Dein Arbeitswissen – automatisch vernetzt, im richtigen Moment verfügbar.**

### Positioning Statement (nach Geoffrey Moore)

> **Für** Wissensarbeiter mit 4+ digitalen Quellen und hoher Meeting-Dichte **ist PWBS** die kognitive Infrastruktur, **die** Kalender, Notizen, Transkripte und Wissensdatenbanken automatisch zusammenführt und als kontextbezogene Tagesbriefings aufbereitet, **weil** es als einziges System proaktiv den richtigen Kontext zur richtigen Zeit liefert – DSGVO-konform, mit nachvollziehbaren Quellen, ohne auf manuelle Pflege angewiesen zu sein.

### Abgrenzungsmatrix

| Kriterium                    | PWBS                                                                                                             | Notion                                                           | Obsidian                                                          | Mem.ai                                                                | Reflect                                              |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------- |
| **Datenquellen-Integration** | 4 Quellen automatisch zusammengeführt (Calendar, Notion, Obsidian, Zoom)                                         | Nur eigene Datenbank; externe Quellen erfordern manuellen Import | Nur lokaler Vault; Integrationen über Community-Plugins (manuell) | Google-Ökosystem (Gmail, Calendar); keine Notion/Obsidian-Integration | Nur eigene Notizen; kein Import aus externen Quellen |
| **Automatische Briefings**   | ✅ Morgen-, Meeting- und Wochenbriefings mit Kontextanreicherung                                                 | ❌ Kein Briefing-System                                          | ❌ Keine automatische Aufbereitung                                | ⚠️ Tägliche Zusammenfassungen, aber nur aus eigenen Notizen           | ❌ Keine automatische Aufbereitung                   |
| **Knowledge Graph**          | ✅ Automatische Entitätserkennung (Personen, Projekte, Entscheidungen) mit Beziehungsanalyse                     | ❌ Nur manuelle Verknüpfungen via Relations                      | ⚠️ Manueller Graph über Backlinks und Graph-View                  | ⚠️ Automatische Verknüpfungen, aber ohne Graphdarstellung             | ⚠️ Backlinks, aber kein semantischer Graph           |
| **DSGVO-Konformität**        | ✅ EU-Hosting (AWS Frankfurt), Envelope Encryption, Mandantentrennung, Löschkonzepte, keine LLM-Trainingsnutzung | ⚠️ US-Hosting, Standard-DPA                                      | ✅ Lokale Daten (aber kein Cloud-Feature)                         | ❌ US-Hosting, unklare Datennutzungspolicies                          | ⚠️ Teilweise EU-Hosting, limitierte Transparenz      |
| **Offline-Fähigkeit**        | ⚠️ Obsidian-Vault lokal, Web-App cloud-basiert                                                                   | ⚠️ Nur mit manueller Offline-Funktion                            | ✅ Vollständig lokal                                              | ❌ Cloud-only                                                         | ⚠️ Limitiert                                         |
| **Erklärbarkeit**            | ✅ Jede Briefing-Aussage mit klickbarer Quellenreferenz, Confidence-Scoring                                      | ❌ Nicht anwendbar (kein KI-generierter Content)                 | ❌ Nicht anwendbar                                                | ⚠️ Quellenangaben vorhanden, aber nicht immer nachvollziehbar         | ❌ Nicht anwendbar                                   |

---

## 4. Pricing-Hypothese

### Phase 2 (MVP / Closed Beta): Free for Early Adopters

Keine monetäre Hürde. Die Closed Beta validiert Product-Market-Fit, nicht Zahlungsbereitschaft. Nutzer erhalten vollständigen Zugang zu allen MVP-Funktionen ohne zeitliche Begrenzung der Beta-Phase.

### Phase 3 (geplant, Monate 10–15): Tier-Struktur-Hypothese

| Tier           | Preis (Hypothese) | Inkludiert                                                                         | Zielgruppe                          |
| -------------- | ----------------- | ---------------------------------------------------------------------------------- | ----------------------------------- |
| **Free**       | 0 €               | 1 Konnektor, 3 Briefings/Woche, 100 Suchanfragen/Monat                             | Evaluierung, leichte Nutzung        |
| **Pro**        | 19–29 €/Monat     | Alle 4+ Konnektoren, unbegrenzte Briefings, Prioritäts-Support, Knowledge Explorer | Einzelnutzer mit intensiver Nutzung |
| **Enterprise** | Auf Anfrage       | Self-Hosting, SSO, SLA, dedizierter Support, DPA                                   | Beratungshäuser, Scale-ups          |

**Anmerkung:** Diese Werte sind Hypothesen. Die reine Kostendeckung (LLM-API-Costs, Hosting) liegt bei geschätzt 3–5 € pro aktivem Nutzer pro Monat (Annahme: ~50 LLM-Calls/Tag pro Nutzer).

### Pricing-Kommunikation auf der Landing Page

Empfohlener Text für den Pricing-Abschnitt der Landing Page:

> **Aktuell: Kostenlos für Early Adopters**
>
> PWBS befindet sich in der Beta-Phase. Alle Funktionen sind kostenfrei nutzbar – ohne Kreditkarte, ohne Ablaufdatum. Wir suchen Wissensarbeiter, die uns helfen, das Produkt zu formen. Im Gegenzug erhältst du frühen Zugang und direkten Einfluss auf die Roadmap.
>
> _Langfristig wird es einen kostenlosen Basis-Zugang und einen Pro-Plan geben. Alle Beta-Nutzer erhalten einen dauerhaften Vorteil._

### Zeitpunkt der Pricing-Validierung

- **Methode:** Willingness-to-Pay-Interviews mit den 10 aktivsten Beta-Nutzern nach 8 Wochen aktiver Nutzung. Van-Westendorp-Methode (4 Preisfragen). Ergänzend: Fake-Door-Test auf der Landing Page („Pro-Plan ab 19 €" mit CTA → Waitlist statt Checkout).
- **Zeitpunkt:** Woche 10–12 nach Beta-Start (frühestens nach Erreichen von 50+ aktiven Nutzern).
- **Entscheidungskriterium:** Pricing wird erst eingeführt, wenn ≥ 30 % der aktiven Nutzer Zahlungsbereitschaft signalisieren (Roadmap-Zielwert Phase 3).

---

## 5. Distributionskanäle

Die folgenden Schätzungen bauen auf den Conversion-Daten aus ADR-014 auf und konkretisieren die Taktiken pro Kanal.

### 5.1 Obsidian-Community (Discord, Forum, Plugin Store)

| Attribut                 | Detail                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Taktik**               | Authentische Präsenz im Obsidian-Discord (#plugins, #workflow-share): Eigenes Setup teilen, auf Fragen zu PKM-Workflows antworten, PWBS als Lösung für die häufig diskutierte Frage „Wie verknüpfe ich Obsidian mit meinem Kalender?" positionieren. Obsidian-Plugin im Community Store veröffentlichen (Vault-Sync-Funktion als Standalone-Wert). Beitrag im Obsidian-Forum mit Use-Case-Beschreibung. |
| **Erwartete Conversion** | 5.000 Reach → 80–175 Signups → 30–70 aktive Nutzer (ADR-014: PKM-Communities gesamt)                                                                                                                                                                                                                                                                                                                    |
| **Aufwand**              | Medium (5–8h/Woche Community-Engagement + Plugin-Veröffentlichung)                                                                                                                                                                                                                                                                                                                                      |
| **Timing**               | Ab Woche 2 (Community-Phase), Plugin-Store ab Woche 3                                                                                                                                                                                                                                                                                                                                                   |

### 5.2 PKM-Subreddits (r/ObsidianMD, r/PKMS, r/productivity)

| Attribut                 | Detail                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Taktik**               | Kein direktes Marketing – Reddit-Kultur verlangt Authentizität. Stattdessen: Problem-Posts mit echtem Mehrwert („Wie ich meine Meeting-Vorbereitung von 30 auf 2 Minuten verkürzt habe" – mit PWBS als eine Komponente im Workflow). Auf relevante Fragen antworten. Show-and-Tell-Posts in r/ObsidianMD mit Screenshots des Briefing-Dashboards. AMA nach dem ProductHunt-Launch. |
| **Erwartete Conversion** | Inkludiert in PKM-Communities-Schätzung oben. Reddit-spezifisch: 3–5 % Signup-Rate bei relevanten Posts (Annahme basierend auf vergleichbaren Indie-SaaS-Launches).                                                                                                                                                                                                                |
| **Aufwand**              | Medium (3–5h/Woche, Karmaaufbau über 2–3 Wochen vor erstem PWBS-Bezug)                                                                                                                                                                                                                                                                                                             |
| **Timing**               | Ab Woche 2 (subtil), expliziter ab Woche 5 (Launch)                                                                                                                                                                                                                                                                                                                                |

### 5.3 LinkedIn (Personal Brand, Thought Leadership)

| Attribut                 | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Taktik**               | Wöchentliche Posts (deutsch) über das Problem der kognitiven Fragmentierung – ohne sofortigen Produktbezug. Themen: „Wie sieht dein erster Arbeitsmorgen aus?", „Was passiert in den 30 Minuten vor deinem wichtigsten Meeting?", Building-in-Public-Updates (Learnings aus der Beta). Persönliches Profil als Founder, nicht als Unternehmensseite. Direkte Vernetzung mit Zielgruppen-Profilen (Berater, PMs, Gründer in der DACH-Region). |
| **Erwartete Conversion** | 5.000 Reach → 50–100 Signups → 20–40 aktive Nutzer (ADR-014)                                                                                                                                                                                                                                                                                                                                                                                 |
| **Aufwand**              | Medium (3–4h/Woche Content-Erstellung + Engagement)                                                                                                                                                                                                                                                                                                                                                                                          |
| **Timing**               | Ab Woche 1 (Fundament), kontinuierlich                                                                                                                                                                                                                                                                                                                                                                                                       |

### 5.4 Product Hunt

| Attribut                 | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Taktik**               | Koordinierter Launch an einem Dienstag oder Mittwoch (höchste Aktivität). Vorbereitung: Hochwertiges Thumbnail, 60-Sekunden-Demo-GIF, deutsch+englische Beschreibung. Hunter mit Follower-Basis in der PKM/Productivity-Nische rekrutieren (offener Punkt aus ADR-014 – Empfehlung: über Obsidian-Community oder Indie-Hacker-Netzwerk finden). Community vorab informieren und um Upvotes bitten (nicht explizit – sondern durch genuines Interesse). |
| **Erwartete Conversion** | 3.500–12.500 Reach → 70–250 Signups → 28–100 aktive Nutzer (ADR-014: PH+HN gesamt, 50 % PH-Anteil als Annahme)                                                                                                                                                                                                                                                                                                                                         |
| **Aufwand**              | High (einmaliger Spike: 15–20h Vorbereitung)                                                                                                                                                                                                                                                                                                                                                                                                           |
| **Timing**               | Woche 5 (Launch-Event, koordiniert mit HN)                                                                                                                                                                                                                                                                                                                                                                                                             |

### 5.5 Hacker News (Show HN)

| Attribut                 | Detail                                                                                                                                                                                                                                                                                                                                 |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Taktik**               | „Show HN"-Post am selben Tag wie ProductHunt (oder 1 Tag versetzt falls PH-Momentum ausreicht). Technischer Fokus: Architektur (RAG + Knowledge Graph), DSGVO-Design, Erklärbarkeit als Differenzierungsmerkmal. Englischsprachig. Keine Marketing-Sprache – HN bestraft das. Erster Kommentar: Founder-Story mit technischen Details. |
| **Erwartete Conversion** | 3.500–12.500 Reach → 70–250 Signups → 27–100 aktive Nutzer (ADR-014: PH+HN gesamt, 50 % HN-Anteil als Annahme)                                                                                                                                                                                                                         |
| **Aufwand**              | Medium (5–8h Vorbereitung + aktives Antworten am Launch-Tag)                                                                                                                                                                                                                                                                           |
| **Timing**               | Woche 5 (koordiniert mit ProductHunt)                                                                                                                                                                                                                                                                                                  |

### 5.6 Direkte Outreach (Design Partners)

| Attribut                 | Detail                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Taktik**               | 10 handverlesene Design Partners aus dem eigenen Netzwerk und der PKM-Community. Auswahlkriterien: Nutzt ≥ 3 der 4 Konnektoren, hat ≥ 6 Meetings/Woche, ist bereit zu 1-on-1-Onboarding (30 Min) und wöchentlichem Feedback (15 Min). Persönliche Einladung per E-Mail oder DM. 1-on-1-Onboarding mit Screen-Share. Wöchentliches 15-Min-Feedback-Call in den ersten 4 Wochen. |
| **Erwartete Conversion** | 10 eingeladen → 10 Signups → 8–10 aktive Nutzer (ADR-014)                                                                                                                                                                                                                                                                                                                      |
| **Aufwand**              | High (10–15h/Woche in den ersten 2 Wochen, danach 3–5h/Woche)                                                                                                                                                                                                                                                                                                                  |
| **Timing**               | Woche 2–4 (vor dem öffentlichen Launch)                                                                                                                                                                                                                                                                                                                                        |

### 5.7 Referral-Mechanismus

| Attribut                 | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Taktik**               | UUID-basierte Invite-Codes (DSGVO-konform, nicht mit E-Mail verknüpft – ADR-014). Aktivierung nach 7 Tagen aktiver Nutzung (verhindert Spam und stellt sicher, dass nur zufriedene Nutzer einladen). Max. 20 Invites pro Nutzer, Codes mit 7-Tage-Ablauf (ADR-014: Referral-Abuse-Schutz). Incentive: Kein monetärer Anreiz im MVP. Stattdessen: „Hilf uns, PWBS mit den richtigen Leuten zu testen" – Zugehörigkeitsgefühl statt Belohnung. |
| **Erwartete Conversion** | 30–80 Signups → 15–40 aktive Nutzer (ADR-014)                                                                                                                                                                                                                                                                                                                                                                                                |
| **Aufwand**              | Low (Mechanismus bereits architektonisch vorbereitet, Referral-Route existiert)                                                                                                                                                                                                                                                                                                                                                              |
| **Timing**               | Ab Woche 4 (nach Aktivierung durch Design Partners)                                                                                                                                                                                                                                                                                                                                                                                          |

### 5.8 PWBS-Discord (eigener Community-Server)

| Attribut                 | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Taktik**               | Community-Server nach der in community-setup.md definierten Struktur einrichten. Einladungslinks mit Ablaufdatum (nicht öffentlich). Channels: #ankündigungen, #allgemein, #bug-reports, #feature-requests, #feedback-beta, #show-and-tell (siehe community-setup.md). Bot-Integrationen für automatische Release-Notes und Welcome-Messages. Ziel: 200 Discord-Mitglieder vor dem öffentlichen Launch (ADR-014). Wöchentliches Community-Event (Donnerstag 17:00, Voice-Channel): 15-Min-Update + offene Fragen. |
| **Erwartete Conversion** | Kein direkter Akquisitionskanal, sondern Retention- und Feedback-Instrument. Indirekter Effekt: Zufriedene Community-Mitglieder werden zu Referral-Quellen.                                                                                                                                                                                                                                                                                                                                                       |
| **Aufwand**              | Medium (Setup: 5h einmalig, danach 3–5h/Woche Moderation und Events)                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **Timing**               | Setup in Woche 2, aktiv ab Woche 3                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

### Kanal-Priorisierung

| Priorität | Kanal                              | Begründung                                                             |
| --------- | ---------------------------------- | ---------------------------------------------------------------------- |
| 1         | Design Partners (Direkte Outreach) | Höchste Feedback-Qualität, validiert Hypothese vor öffentlichem Launch |
| 2         | Obsidian-Community                 | Höchste Zielgruppen-Überlappung, nachhaltige Präsenz                   |
| 3         | ProductHunt + Hacker News          | Sichtbarkeits-Spike, Validierung außerhalb der Nische                  |
| 4         | LinkedIn                           | Building-in-Public, langfristiger Brand-Aufbau                         |
| 5         | Reddit                             | Ergänzend, authentizitätsgetrieben                                     |
| 6         | Referral                           | Organisches Wachstum ab Woche 4                                        |
| 7         | PWBS-Discord                       | Retention-fokussiert                                                   |

---

## 6. Beta-Strategie

### Phase A: Closed Beta (Invite-Only)

| Attribut                       | Detail                                                                                                                                                                                                                                                            |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ziel-Nutzerzahl**            | 10–20 aktive Nutzer                                                                                                                                                                                                                                               |
| **Dauer**                      | 4 Wochen (Woche 2–5)                                                                                                                                                                                                                                              |
| **Einladungsmechanismus**      | Manuelle Auswahl aus Waitlist + Direkteinladungen. Kein First-Come-First-Serve. Begründung: In der Closed Beta ist Feedback-Qualität wichtiger als Quantität. Die Auswahl sichert, dass alle Nutzer dem ICP entsprechen und bereit sind, aktiv Feedback zu geben. |
| **Entry-Kriterien für Nutzer** | (1) Nutzt mindestens 2 der 4 Konnektoren aktiv im Arbeitsalltag, (2) hat ≥ 4 Meetings pro Woche, (3) ist bereit zum 1-on-1-Onboarding (30 Min) und wöchentlichem kurzem Feedback, (4) arbeitet in der DACH-Region (DSGVO-Kontext)                                 |
| **Onboarding**                 | Persönliches 1-on-1 per Zoom (30 Min): Account-Setup, Konnektor-Verbindung, erstes Briefing gemeinsam durchgehen. Ziel: Time-to-First-Briefing < 20 Minuten (PRD-SPEC NF-024).                                                                                    |
| **Feedback-Rhythmus**          | Wöchentlich: 15-Min-Feedback-Call oder strukturierter Fragebogen (5 Fragen). Täglich: Briefing-Feedback via Daumen-hoch/runter im Produkt (US-3.4).                                                                                                               |

**Exit-Kriterien für Closed Beta (alle müssen erfüllt sein):**

1. ≥ 8 von 10 Design Partners nutzen PWBS nach 14 Tagen noch regelmäßig (D14-Retention ≥ 80 % in dieser Kohorte)
2. Durchschnittlich ≥ 2 Konnektoren pro Nutzer verbunden
3. Briefing-Relevanz-Score ≥ 60 % positives Feedback (PRD-SPEC: Ziel 70 %, Closed-Beta-Schwelle 60 %)
4. Keine kritischen Bugs offen (P0/P1)
5. Rechtliche Pflichtdokumente veröffentlicht: Datenschutzerklärung, Impressum, AGB (LEGAL_COMPLIANCE.md: Launch-Blocker)
6. Time-to-First-Briefing ≤ 20 Minuten für 80 % der Nutzer

### Phase B: Open Beta (Self-Serve mit Waitlist)

| Attribut              | Detail                                                                                                                                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Zeitpunkt**         | Nach Erfüllung aller Exit-Kriterien von Phase A (frühestens Woche 6)                                                                                                                                          |
| **Wachstumsziel**     | 100–500 aktive Nutzer innerhalb von 8 Wochen (ADR-014: Gesamt-Conversion 163–430)                                                                                                                             |
| **Zugang**            | Waitlist mit automatischer Freischaltung in Wellen (50 Nutzer pro Welle, wöchentlich). Feature-Flag `beta_registration_open` steuert den Cutoff bei Überlast (ADR-014).                                       |
| **Support-Kapazität** | Discord-Community als primärer Support-Kanal (#hilfe-und-support). FAQ-Seite. Kein 1-on-1-Onboarding mehr – stattdessen Self-Serve mit Onboarding-Wizard im Produkt. Ziel: < 24h Antwortzeit auf Bug-Reports. |

**Voraussetzungen vor Öffnung:**

1. Alle Exit-Kriterien Phase A erfüllt
2. Load-Test auf 500 VUs bestanden (ADR-014)
3. Error-Monitoring (Sentry) konfiguriert (GTM-Readiness-Checklist)
4. Onboarding-Wizard im Frontend implementiert (Self-Serve ohne 1-on-1)
5. Discord-Community-Server aktiv mit Moderationsregeln (community-setup.md)
6. DSGVO-konforme Analytics aktiv (Plausible/Fathom – ADR-014)

### Phase C: General Availability (GA)

| Attribut       | Detail                                                                                                                                                                                                    |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Zeitpunkt**  | Frühestens Monat 10 der Roadmap (Phase 3), nach Erreichen stabiler Retention über alle Kohorten                                                                                                           |
| **Kriterien**  | D30-Retention > 50 % über mindestens 3 aufeinanderfolgende Kohorten. ≥ 30 % der aktiven Nutzer signalisieren Zahlungsbereitschaft. NPS > 40. Keine wiederkehrenden Stabilitätsprobleme (Uptime > 99,5 %). |
| **Änderungen** | Pricing wird aktiviert (Free/Pro/Enterprise). SLA für Pro-Kunden (99,5 % Uptime). Formaler Support-Kanal (E-Mail) zusätzlich zu Discord. Phase-3-Konnektoren (Gmail, Slack) werden freigeschaltet.        |

---

## 7. 90-Tage-Timeline

Ausgangspunkt: 17. März 2026.

### Woche 1–2 (17.–30. März): Fundament

| Meilenstein                 | Was wird geliefert                                                                                           | Was wird gemessen                        | Abhängigkeiten                                     |
| --------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------- | -------------------------------------------------- |
| Rechtliche Pflichtdokumente | Datenschutzerklärung, Impressum, AGB erstellt und auf Landing Page veröffentlicht                            | Dokumente live: ja/nein                  | Juristische Prüfung (extern oder Template-basiert) |
| Analytics einrichten        | Plausible/Fathom auf Landing Page und App integriert (DSGVO-konform, kein Cookie-Banner nötig)               | Analytics-Events feuern: ja/nein         | –                                                  |
| Landing Page optimieren     | Demo-Video (90 Sek) oder animiertes GIF eingebettet, Pricing-Abschnitt „Free for Early Adopters" hinzugefügt | Waitlist-Signups/Woche (Baseline messen) | Demo-Video-Produktion                              |
| LinkedIn-Start              | 2 Posts veröffentlicht (Problem-fokussiert, kein Produkt-Pitch)                                              | Impressions, Kommentare                  | –                                                  |
| Design-Partner-Auswahl      | 10 Design Partners identifiziert und persönlich eingeladen                                                   | 10 Zusagen                               | Eigenes Netzwerk, Waitlist-Analyse                 |

### Woche 3–4 (31. März – 13. April): Closed Beta Start

| Meilenstein                     | Was wird geliefert                                                                    | Was wird gemessen                                | Abhängigkeiten                   |
| ------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------ | -------------------------------- |
| Closed Beta Go-Live             | Erste 10 Design Partners ongeboardet (1-on-1 Zoom)                                    | Time-to-First-Briefing pro Nutzer                | Rechtsdokumente live (Woche 1–2) |
| Discord-Server live             | Community-Server eingerichtet nach community-setup.md, Moderationsregeln aktiv        | Mitglieder (Ziel: 20 zum Start)                  | –                                |
| Obsidian-Community-Präsenz      | Erste Beiträge in Obsidian-Discord und Forum                                          | Reaktionen, DMs, Waitlist-Signups aus Community  | –                                |
| Feedback-Zyklus 1               | Erste wöchentliche Feedback-Calls mit Design Partners abgeschlossen                   | Briefing-Relevanz-Score, qualitative Pain Points | Design Partners aktiv            |
| Obsidian-Plugin veröffentlichen | Plugin im Obsidian Community Store einreichen (Review-Prozess kann 1–2 Wochen dauern) | Plugin-Review-Status                             | Plugin-Code finalisiert          |

### Monat 2 (14. April – 11. Mai): Iteration & Launch-Vorbereitung

| Meilenstein            | Was wird geliefert                                                                   | Was wird gemessen                                                       | Abhängigkeiten            |
| ---------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- | ------------------------- |
| Closed-Beta-Iteration  | 2 weitere Feedback-Zyklen, kritische UX-Fixes basierend auf Design-Partner-Feedback  | D14-Retention der Design Partners, verbesserter Briefing-Relevanz-Score | Kontinuierliches Feedback |
| Onboarding-Wizard      | Self-Serve-Onboarding im Frontend (kein 1-on-1 mehr nötig für Open Beta)             | Onboarding-Completion-Rate in Staging-Tests                             | Frontend-Entwicklung      |
| Load-Test              | k6-Test auf 500 VUs bestanden, Connection-Pool und Redis-Cache verifiziert (ADR-014) | Latenz unter Last, Fehlerraten                                          | DevOps                    |
| Launch-Material        | ProductHunt-Profil vorbereitet, Show-HN-Entwurf geschrieben, Hunter kontaktiert      | Material fertig: ja/nein                                                | Demo-Video aus Woche 1–2  |
| Reddit-Präsenz         | 3–4 authentische Beiträge in r/ObsidianMD, r/PKMS (Problem-Posts, kein Marketing)    | Karma, Engagement, Waitlist-Signups                                     | Account-Karmaaufbau       |
| Closed-Beta Exit-Check | Alle 6 Exit-Kriterien evaluiert                                                      | Jedes Kriterium erfüllt: ja/nein                                        | Alle obigen Meilensteine  |

### Monat 3 (12. Mai – 15. Juni): Launch & Open Beta

| Meilenstein                    | Was wird geliefert                                                                                               | Was wird gemessen                                          | Abhängigkeiten                              |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------- |
| Koordinierter Launch (Woche 9) | ProductHunt + Show HN am selben Tag/Woche, LinkedIn-Announcement, Community-Mobilisierung                        | PH-Rank, HN-Points, Signups am Launch-Tag                  | Launch-Material, Exit-Kriterien erfüllt     |
| Open Beta aktiviert            | Waitlist-Wellen (50/Woche), Feature-Flag `beta_registration_open` aktiv                                          | Wöchentliche Signups, Conversion Waitlist → Aktiver Nutzer | Load-Test bestanden, Onboarding-Wizard live |
| Content-Pipeline gestartet     | 2 Blog-Posts veröffentlicht (deutsch): „Was ist ein Wissens-OS?" + „Wie PWBS Meeting-Vorbereitung automatisiert" | Blog-Traffic, Backlinks, Waitlist-Signups                  | –                                           |
| Community-Wachstum             | Wöchentliche Community-Events (Donnerstag 17:00), Discord wächst auf 100+ Mitglieder                             | Discord-Mitglieder, Event-Teilnahme, Bug-Reports/Woche     | Discord-Server aktiv                        |
| Referral aktiviert             | Referral-Mechanismus für Nutzer mit ≥ 7 Tagen aktiver Nutzung freigeschaltet                                     | Referral-Signups/Woche                                     | 7-Tage-Aktivitäts-Trigger                   |
| Monat-3-Review                 | Gesamtbewertung: KPI-Dashboard, Retention-Kohorten, qualitatives Feedback                                        | Alle 5 Launch-KPIs (Abschnitt 8)                           | Alle obigen Daten                           |

---

## 8. Erfolgskennzahlen (KPIs)

### Top-5 Launch-KPIs

| #   | KPI                                    | Definition                                                                                                                        | Zielwert Closed Beta        | Zielwert Open Beta                  | Datenquelle                                 |
| --- | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | ----------------------------------- | ------------------------------------------- |
| 1   | **Waitlist-to-Signup Conversion Rate** | Anteil der Waitlist-Einträge, die sich nach Einladung registrieren und ≥ 1 Konnektor verbinden                                    | ≥ 80 % (manuell eingeladen) | ≥ 40 % (Self-Serve)                 | Waitlist-DB + Registrierungs-Events         |
| 2   | **Time-to-First-Briefing**             | Zeitspanne zwischen Registrierung (`user.registered`) und erstem generierten Briefing (`briefing.generated`)                      | ≤ 20 Minuten (PRD-SPEC)     | ≤ 30 Minuten (Annahme: ohne 1-on-1) | Audit-Log (Event-Timestamps)                |
| 3   | **7-Day Retention Rate**               | Anteil der Nutzer, die 7 Tage nach Registrierung mindestens eine Aktion durchführen (Briefing abrufen, Suche, Knowledge Explorer) | ≥ 80 %                      | ≥ 65 % (PRD-SPEC D7-Retention)      | Analytics (Login/Activity-Events)           |
| 4   | **Connector Completion Rate**          | Anteil der registrierten Nutzer, die ≥ 1 Konnektor innerhalb von 24h verbinden                                                    | ≥ 90 % (1-on-1 Onboarding)  | ≥ 70 % (Self-Serve)                 | `connections`-Tabelle (COUNT pro User)      |
| 5   | **Weekly Active Briefing Views**       | Durchschnittliche Anzahl der Briefing-Abrufe pro aktivem Nutzer pro Woche (North Star Metric aus PRD-SPEC)                        | ≥ 3 (PRD-SPEC)              | ≥ 3 (PRD-SPEC)                      | Prometheus-Metriken (GET /briefings/ Calls) |

### Ergänzende Metriken (Tracking, kein hartes Ziel)

| Metrik                            | Beschreibung                                          | Datenquelle                   |
| --------------------------------- | ----------------------------------------------------- | ----------------------------- |
| Briefing-Relevanz-Score           | Positives Feedback / (positiv + negativ) pro Briefing | Briefing-Feedback-Tabelle     |
| Durchschn. verbundene Konnektoren | COUNT(DISTINCT source_type) pro Nutzer                | `connections`-Tabelle         |
| Suchanfragen / Nutzer / Woche     | Nutzungsintensität der semantischen Suche             | Prometheus (POST /search/)    |
| NPS                               | Net Promoter Score (monatliche Umfrage)               | Umfrage-Tool oder Discord-Bot |
| D30-Retention                     | 30-Tage-Retention über Kohorten                       | Analytics                     |

---

## 9. Content- & Kommunikationsstrategie

### Vor dem Launch (Woche 1–4)

| Inhalt                     | Format                                                                               | Sprache                 | Zweck                                               | Timing                 |
| -------------------------- | ------------------------------------------------------------------------------------ | ----------------------- | --------------------------------------------------- | ---------------------- |
| Demo-Video                 | 90-Sek-Screencast: Registrierung → Konnektor → Erstes Briefing                       | Deutsch (Untertitel EN) | Landing Page, ProductHunt, Social Sharing           | Woche 1–2              |
| „Problem-Artikel" LinkedIn | 3–4 Posts, je 200–300 Wörter                                                         | Deutsch                 | Problembewusstsein, Personal Brand, Audience-Aufbau | Woche 1–4, wöchentlich |
| Obsidian-Forum-Post        | Use-Case-Beitrag: „Mein Workflow – Obsidian + Kalender + Zoom automatisch verknüpft" | Englisch                | Community-Vertrauen, Waitlist-Conversions           | Woche 3                |

### Zum Launch (Woche 5)

| Inhalt                | Format                                                                                    | Sprache  | Zweck                                    | Timing     |
| --------------------- | ----------------------------------------------------------------------------------------- | -------- | ---------------------------------------- | ---------- |
| ProductHunt-Listing   | Titel, Tagline, 5 Screenshots, Demo-GIF, Beschreibung                                     | Englisch | Sichtbarkeit, Signups                    | Launch-Tag |
| Show HN Post          | Technischer Erfahrungsbericht (800–1200 Wörter): Architektur, RAG, Knowledge Graph, DSGVO | Englisch | HN-Community, technische Glaubwürdigkeit | Launch-Tag |
| LinkedIn-Announcement | Launch-Post mit persönlicher Geschichte                                                   | Deutsch  | DACH-Netzwerk aktivieren                 | Launch-Tag |
| Discord-Announcement  | @everyone: Open Beta live, was ist neu, wie beitreten                                     | Deutsch  | Community-Aktivierung                    | Launch-Tag |

### Nach dem Launch (Woche 6–12)

| Inhalt                 | Format                                                                          | Sprache | Zweck                               | Timing      |
| ---------------------- | ------------------------------------------------------------------------------- | ------- | ----------------------------------- | ----------- |
| Blog-Post 1            | „Was ist ein Wissens-Betriebssystem?" (1500 Wörter)                             | Deutsch | SEO, Kategorie-Definition           | Woche 6     |
| Blog-Post 2            | „Wie PWBS Meeting-Vorbereitung automatisiert" (1200 Wörter, mit Screenshots)    | Deutsch | Use-Case-spezifisch, Social Sharing | Woche 8     |
| Blog-Post 3            | „DSGVO und KI: Warum dein zweites Gehirn in der EU liegen sollte" (1000 Wörter) | Deutsch | DSGVO als Positionierung, SEO       | Woche 10    |
| Community-Event-Recaps | Kurzzusammenfassungen der wöchentlichen Discord-Events                          | Deutsch | LinkedIn-Content, Vertrauen         | Wöchentlich |

### Tonalität und Sprache

| Kontext                          | Sprache                          | Tonalität                                                                                                                          |
| -------------------------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Landing Page, Blog, LinkedIn     | **Deutsch**                      | Klar, direkt, ohne Marketing-Floskeln. Technisch zugänglich, aber nicht vereinfachend. Respektiert die Intelligenz der Zielgruppe. |
| ProductHunt, Hacker News, GitHub | **Englisch**                     | Sachlich-technisch. Architekturentscheidungen begründen, nicht verkaufen.                                                          |
| Discord-Community                | **Deutsch** (Englisch toleriert) | Kollegial, offen, hilfsbereit. Feedback wird als Geschenk behandelt.                                                               |
| Technische Dokumentation         | **Englisch**                     | Präzise, standardkonform, Code-nah.                                                                                                |

### Messaging-Framework: 3 Kernbotschaften

| Kontext                                                  | Kernbotschaft                                                                                                                                               | Verwendung                                                                     |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **Problem-Kommunikation** (LinkedIn, Blog, Landing)      | „Du verlierst jeden Tag 30 Minuten damit, vor Meetings den Kontext zusammenzusuchen. PWBS macht das automatisch."                                           | Für Erstberührung: Problem greifbar machen, bevor die Lösung präsentiert wird. |
| **Differenzierung** (ProductHunt, HN, Vergleichs-Seiten) | „Das einzige Wissens-System, das deine Quellen nicht nur speichert, sondern versteht – mit Quellenbelegen, EU-Hosting und ohne Black-Box-Empfehlungen."     | Für informierte Prospects, die bereits Alternativen kennen (Notion, Mem.ai).   |
| **Trust** (DSGVO-sensible Nutzer, Berater, Enterprise)   | „Deine Daten bleiben in der EU, werden nie für KI-Training genutzt und sind jederzeit vollständig löschbar. Jede Aussage des Systems zeigt dir die Quelle." | Für Nutzer, die Datenschutz als Entscheidungskriterium gewichten.              |

---

## 10. Risiken & Mitigationen

| #   | Risiko                                                                                                                                                                                                | Eintrittswahrscheinlichkeit | Auswirkung | Mitigation                                                                                                                                                                                                                                                                                                                                                             |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Onboarding-Friction:** Nutzer brechen den OAuth-Flow ab oder verstehen nicht, wie sie von der Registrierung zum ersten Briefing kommen. Dropout zwischen Registrierung und erstem Konnektor > 30 %. | Hoch                        | Hoch       | Onboarding-Wizard mit Schritt-für-Schritt-Anleitung (PRD-SPEC: US-1.1). In Closed Beta: 1-on-1-Onboarding identifiziert exakte Reibungspunkte. Fortschrittsanzeige während des Syncs. Ziel: Erster Konnektor in < 5 Minuten (AR-05 in PRD-SPEC).                                                                                                                       |
| 2   | **Niedrige Retention:** Nutzer testen PWBS, finden Briefings nicht relevant genug und kehren nicht zurück. D14-Retention < 40 %.                                                                      | Mittel                      | Hoch       | Briefing-Qualität ist das Produkt. Feedback-Mechanismus (US-3.4) liefert Signale zur Verbesserung. Pivot-Kriterium: Wenn < 50 % der Nutzer Briefings als „hilfreich" bewerten, zusätzliche Datenquellen priorisieren oder Briefing-Algorithmus überarbeiten (AR-01 in PRD-SPEC). Wöchentliche Qualitäts-Reviews der generierten Briefings durch das Team.              |
| 3   | **Rechtliche Lücken:** Launch ohne Datenschutzerklärung, Impressum oder AGB. Abmahnung durch Wettbewerber oder Nutzerbeschwerde bei Datenschutzbehörde.                                               | Mittel                      | Sehr hoch  | Klarer Blocker in der Timeline: Woche 1–2 sind den Rechtsdokumenten gewidmet. Keine Nutzer-Einladung vor Veröffentlichung aller drei Dokumente (LEGAL_COMPLIANCE.md: Launch-Blocker). AVV-Entwürfe für AWS, Anthropic, OpenAI, Vercel bereits vorhanden – finalisieren.                                                                                                |
| 4   | **Technische Instabilität:** LLM-Halluzinationen in Briefings, langsame Sync-Zeiten, Downtime während des Launch-Spikes.                                                                              | Mittel                      | Hoch       | Grounded Generation: Briefings nur RAG-basiert, Quellenvalidierung im Postprocessing, Confidence-Scoring (AR-04 in PRD-SPEC). Load-Test auf 500 VUs vor Launch (ADR-014). Sentry für Error-Monitoring. Feature-Flag `beta_registration_open` als Notbremse bei Überlast.                                                                                               |
| 5   | **Wettbewerber-Launch:** Mem.ai, Notion AI oder ein neuer Player launcht ein ähnliches Feature (Cross-Source-Briefings) während der PWBS-Beta.                                                        | Niedrig                     | Mittel     | DSGVO-Konformität und EU-Hosting sind kurzfristig schwer kopierbar und für die DACH-Zielgruppe ein harter Differenzierungsfaktor. Erklärbarkeit (Quellenreferenzen) ist architektonisch verankert, nicht nachträglich aufgesetzt. Community-Lock-in durch Design-Partner-Beziehungen und Discord-Engagement. Schnellere Iteration durch Nutzernähe in der Closed Beta. |
