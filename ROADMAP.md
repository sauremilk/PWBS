# Roadmap: Persönliches Wissens-Betriebssystem

Das persönliche Wissens-Betriebssystem ist eine kognitive Infrastruktur, die fragmentiertes Wissen aus digitalen Quellen zusammenführt, semantisch versteht und in handlungsfähige Klarheit übersetzt. Die Entwicklung folgt einem iterativen Ansatz: von der Problemvalidierung über einen fokussierten MVP bis hin zu einer skalierbaren Plattform – mit konsequentem Nutzerfeedback in jeder Phase.

---

## Phase 1: Discovery & Problemvalidierung (Monate 1–3)

**Ziel der Phase**
Sicherstellen, dass das identifizierte Problem – kognitive Fragmentierung bei Wissensarbeitern – real, dringend und zahlungsbereit ist. Gleichzeitig technische Machbarkeit der Kernidee (semantische Verknüpfung heterogener Quellen) nachweisen.

**Kern-Deliverables**
- 15–20 strukturierte Probleminterviews mit Gründern, Produktmanagern, Entwicklern und Beratern
- Auswertung der Interviews: Priorisierte Schmerzpunkte, Zahlungsbereitschaft, bestehende Workarounds
- Technischer Proof-of-Concept: Kalendereinträge + Obsidian-/Notion-Notizen einlesen, Embeddings erzeugen, einfache semantische Suche demonstrieren
- Architektur-Entscheidungsdokument: Cloud vs. On-Premise, LLM-Provider (Claude API / GPT-4 / lokale Modelle via Ollama), Graph-Datenbank (Neo4j / TigerGraph), Vector-DB (Weaviate)
- Initiales Datenschutz- und DSGVO-Konzept (rechtliche Erstberatung, Verschlüsselungsstrategie)

**Messbare Erfolgsindikatoren**
- ≥ 10 Interviews bestätigen Kontextverlust und Fragmentierung als Top-3-Problem
- ≥ 5 Personen signalisieren Bereitschaft, einen frühen Prototyp intensiv zu testen
- Proof-of-Concept liefert relevante Suchergebnisse über ≥ 2 Datenquellen hinweg

**Annahmen & Risiken**
- **Annahme:** Wissensarbeiter empfinden das Problem als akut genug, um ein neues System zu adoptieren
- **Risiko:** Interviewpartner bestätigen das Problem, aber bestehende Workarounds (Notion, Obsidian, manuelle Routinen) werden als „gut genug" empfunden
- **Risiko:** Technische Machbarkeit der zuverlässigen Entitätsextraktion (Personen, Projekte, Entscheidungen) über heterogene Quellen wird unterschätzt

---

## Phase 2: MVP & Early Adopters (Monate 4–9)

**Ziel der Phase**
Einen funktionsfähigen Prototyp ausliefern, der für 10–20 Early Adopters echten Mehrwert erzeugt. Fokus auf den Kernnutzen: automatische Kontextbriefings und semantische Suche über persönliche Wissensquellen.

**Kern-Deliverables**
- **Universelle Datenerfassung (Stufe 1):** Integrationen für Google Calendar / Outlook-Kalender, Notion, Obsidian, Zoom-/Teams-Meeting-Transkripte
- **Semantisches Wissensmodell (Basis):** Embedding-basierte Indexierung aller erfassten Inhalte; automatische Extraktion von Personen, Projekten und Schlüsselthemen; Speicherung in Graph-Datenbank
- **Kontextbriefings:** Tägliches Morgenbriefing (anstehende Termine, relevanter Kontext, offene Themen); automatische Meeting-Vorbereitung (letzter Stand, offene Punkte, beteiligte Personen)
- **Semantische Suche:** Natürlichsprachliche Suche über alle integrierten Quellen mit Quellenangabe
- **Erklärbarkeit (Basis):** Jede Aussage des Systems mit Quellenverweis; klare Trennung zwischen Fakten und Interpretationen
- **Frontend:** Web-Applikation (Next.js/React), einfaches Dashboard mit Briefing-Ansicht und Suchfunktion
- **Backend:** Python/FastAPI, PostgreSQL + Weaviate, LLM-Anbindung (Claude API oder GPT-4)
- **Datenschutz:** Ende-zu-Ende-Verschlüsselung für alle Nutzerdaten, kein Training externer Modelle mit Nutzerdaten
- **Hosting:** Vercel (Frontend) + AWS (Backend, Datenbanken)

**Messbare Erfolgsindikatoren**
- 10–20 aktive Early Adopters (Gründer, Entwickler, Produktmanager)
- Time-to-Value: Nutzer erleben innerhalb von 3 Tagen messbaren Mehrwert
- ≥ 60 % der Early Adopters nutzen das System nach 14 Tagen noch regelmäßig
- Qualitatives Feedback bestätigt, dass Briefings im Arbeitsalltag tatsächlich genutzt werden

**Annahmen & Risiken**
- **Annahme:** Kalender + Notizen + Meeting-Transkripte decken genug Kontext ab, um nützliche Briefings zu erzeugen
- **Annahme:** Nutzer sind bereit, dem System Zugriff auf persönliche Datenquellen zu gewähren
- **Risiko:** LLM-Halluzinationen erzeugen falsche Verknüpfungen oder erfundene Kontextinformationen – Vertrauensverlust
- **Risiko:** Onboarding-Aufwand (Datenquellen anbinden, System kennenlernen) ist zu hoch → lange Time-to-Value
- **Risiko:** Heterogene Datenformate führen zu unzuverlässiger Entitätsextraktion

---

## Phase 3: Private Beta & Produktreife (Monate 10–15)

**Ziel der Phase**
Das Produkt von einem Prototyp zu einem robusten, zahlungswürdigen Dienst weiterentwickeln. Die Datenbasis durch weitere Integrationen verbreitern und mit Entscheidungsunterstützung den Kernwert deutlich vertiefen.

**Kern-Deliverables**
- **Erweiterte Datenerfassung:** Gmail, Outlook-Mail, Slack, Google Docs
- **Semantisches Wissensmodell (erweitert):** Automatische Erkennung von Zielen, Entscheidungen, Risiken, offenen Fragen und Hypothesen; Verknüpfung über Zeit und Kontext hinweg; Mustererkennung (wiederkehrende Themen, sich ändernde Annahmen)
- **Entscheidungsunterstützung:** Strukturierung offener Entscheidungen mit Pro/Contra, Annahmen und Abhängigkeiten; Sichtbarmachung relevanter früherer Erkenntnisse bei neuen Entscheidungen; Nachverfolgung: Was wurde entschieden, warum, und was ist daraus geworden?
- **Aktive Erinnerung:** Hinweise auf vergessene Themen, überfällige Follow-ups, wiederkehrende Probleme; proaktive Fragen („Thema X wurde vor drei Monaten bearbeitet – ist das noch relevant?")
- **Projektbriefings:** Übersicht pro Projekt: Status, Entscheidungshistorie, offene Punkte
- **Persönliches Lernmodell:** System lernt individuelle Arbeitsmuster, Prioritäten und Denkgewohnheiten
- **UX-Verbesserungen:** Desktop-App (Tauri oder Electron); Integrationen in bestehende Tools (Notion-Sidebar, Slack-Bot, Browser-Extension als Prototyp)
- **Pricing-Modell:** Einführung eines Bezahlmodells (Zielkorridor: 20–50 €/Monat), A/B-Tests verschiedener Preispunkte

**Messbare Erfolgsindikatoren**
- 100–500 aktive Beta-Nutzer
- Retention: > 60 % nach 30 Tagen
- Depth of Use: Nutzer interagieren täglich mit Briefings, Kontextanzeigen oder Entscheidungshilfen
- Willingness to Pay: > 30 % der Beta-Nutzer konvertieren zu zahlenden Kunden
- NPS > 50

**Annahmen & Risiken**
- **Annahme:** Die Erweiterung um Mail und Slack liefert signifikant bessere Kontextqualität
- **Annahme:** Entscheidungsunterstützung ist ein Feature, für das Nutzer bereit sind zu zahlen
- **Risiko:** Datenschutzbedenken bei Mail-/Slack-Integration bremsen Adoption
- **Risiko:** Aktive Erinnerungen werden als aufdringlich empfunden statt als hilfreich
- **Risiko:** Pricing-Widerstand: Nutzer erwarten kostenlosen Zugang in der Beta-Phase

---

## Phase 4: Launch & Skalierung (Monate 16–21)

**Ziel der Phase**
Öffentlicher Launch mit klarer Positionierung als kognitive Infrastruktur. Product-Market-Fit validieren, Nutzerbasis signifikant skalieren und erste B2B-Angebote pilotieren.

**Kern-Deliverables**
- **Public Beta** mit gezieltem Marketing-Push (Content-Marketing, Community-Building, Partnerschaften mit Produktivitäts-Communities)
- **Team-Features (Basis):** Gemeinsames Wissensmodell für kleine Teams (3–10 Personen); Onboarding-Unterstützung: Neue Teammitglieder erhalten automatisch relevanten Projektkontext; Wissensübergabe bei Rollenwechseln
- **Self-Hosting-Option:** On-Premise-Variante für datenschutzsensible Nutzer und Enterprise-Kunden
- **Skalierung der Infrastruktur:** Modulare Architektur: Datenquellen nach Bedarf aktivierbar; Performance-Optimierung für wachsende Nutzerzahlen und Datenmengen
- **Vertrauens- und Compliance-Paket:** Unabhängiges Sicherheitsaudit; DSGVO-Dokumentation und Zertifizierung; Transparenzbericht zur Datennutzung
- **Erste B2B-Piloten** mit Beratungshäusern oder Tech-Startups

**Messbare Erfolgsindikatoren**
- 1.000–5.000 aktive Nutzer
- Stabile Retention > 60 % nach 30 Tagen über alle Kohorten
- ≥ 3 zahlende B2B-Pilotkunden
- Positiver Unit-Economics-Trend (CAC/LTV)

**Annahmen & Risiken**
- **Annahme:** Content-Marketing und Community-Effekte reichen aus, um ohne großes Werbebudget zu wachsen
- **Annahme:** Team-Features erzeugen zusätzlichen Mehrwert und rechtfertigen höhere Preispunkte
- **Risiko:** Go-to-Market-Herausforderung: Der Nutzen ist vor der Nutzung schwer zu demonstrieren
- **Risiko:** Self-Hosting-Option bindet erhebliche Engineering-Kapazität
- **Risiko:** Sicherheitslücken oder Datenschutzvorfälle in der Wachstumsphase wären existenzbedrohend

---

## Phase 5: Plattform & Vertikalisierung (Monate 22–36)

**Ziel der Phase**
Vom Einzelprodukt zur Plattform evolvieren. Drittanbieter-Integrationen ermöglichen, vertikale Spezialisierungen anbieten und den Lock-in-Effekt des personalisierten Langzeitgedächtnisses als strategischen Vorteil ausbauen.

**Kern-Deliverables**
- **API für Drittanbieter:** Offene API, über die externe Tools das Wissensmodell lesen und anreichern können; Marketplace-Ansatz für Community-Integrationen
- **Mobile Apps:** iOS- und Android-Applikationen für unterwegs (Schnellnotizen, Spracherfassung, Briefings)
- **Erweiterte Team-Kollaboration:** Rollenbasierte Zugriffssteuerung; gemeinsame Entscheidungshistorie und Wissensübergabe auf Organisationsebene
- **Vertikale Spezialisierungen:** Angepasste Workflows und Wissensmodelle für spezifische Zielgruppen: Forscher (Literaturnachweise, Hypothesen-Tracking), Berater (Kundenprojekte, Lessons Learned), Entwickler (Architekturentscheidungen, technische Schulden)
- **Erweiterte Zielgruppen:** Selbstständige, Juristen, Ärzte, Pädagogen, Journalisten; Unterstützung bei komplexen Lebensübergängen (Jobwechsel, Selbstständigkeit)
- **Langzeit-Intelligenz:** Erkennung von Mustern über Monate und Jahre; Nachverfolgung, welche Annahmen sich als falsch herausgestellt haben; proaktive Hinweise auf strategische Veränderungen

**Messbare Erfolgsindikatoren**
- 10.000+ aktive Nutzer
- Substanzieller, wachsender Umsatz (MRR)
- ≥ 5 aktive Drittanbieter-Integrationen über die API
- Messbare Nutzung vertikaler Features in ≥ 2 Spezialisierungen
- Durchschnittliche Nutzungsdauer > 12 Monate (Langzeitgedächtnis-Effekt)

**Annahmen & Risiken**
- **Annahme:** Der Lock-in durch persönliches Langzeitgedächtnis macht das Produkt mit zunehmender Nutzungsdauer unverzichtbar
- **Annahme:** Vertikale Spezialisierungen erzeugen genug Differenzierung gegenüber generischen Lösungen
- **Risiko:** Große Tech-Unternehmen (Google, Microsoft, Apple) integrieren ähnliche Funktionen in bestehende Ökosysteme
- **Risiko:** Plattform-Komplexität übersteigt die Kapazitäten eines kleinen Teams
- **Risiko:** Unterschiedliche vertikale Anforderungen fragmentieren die Entwicklungskapazität

---

## Risiken & Annahmen pro Phase – Überblick

| Phase | Kritischstes Risiko | Wichtigste Annahme |
|-------|---------------------|--------------------|
| **1 – Discovery** | Problem wird als „nice to have" statt als dringend wahrgenommen | Kognitive Fragmentierung ist ein echtes, zahlungsbereites Problem |
| **2 – MVP** | LLM-Halluzinationen zerstören Vertrauen in das System | Kalender + Notizen + Transkripte genügen für nützliche Briefings |
| **3 – Private Beta** | Datenschutzbedenken bei Mail-/Slack-Integration | Entscheidungsunterstützung ist der entscheidende Zahlungstreiber |
| **4 – Launch** | Nutzen ist vor Nutzung schwer zu demonstrieren (hohe Erklärungslast) | Community-getriebenes Wachstum funktioniert ohne großes Werbebudget |
| **5 – Plattform** | Große Tech-Unternehmen kopieren den Ansatz | Lock-in durch Langzeitgedächtnis schützt vor Abwanderung |

---

**Lesehinweis:** Diese Roadmap ist als strategischer Rahmen für ein Team von 2–5 Personen gedacht. Die Phasengrenzen sind fließend; die angegebenen Zeiträume dienen der Orientierung. Priorisierung innerhalb der Phasen sollte auf Basis laufender Nutzerfeedbacks und validierter Annahmen erfolgen.
