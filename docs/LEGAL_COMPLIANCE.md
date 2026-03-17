# Rechtliche Compliance-Checkliste: PWBS – EU-Launch

**Version:** 1.0
**Datum:** 17. März 2026
**Status:** Prüfentwurf – zur Abstimmung mit Datenschutzanwalt
**Scope:** Phase 2 – MVP, Closed Beta (10–20 Nutzer), EU-Betrieb
**Basisdokumente:** [docs/dsgvo-erstkonzept.md](dsgvo-erstkonzept.md), [legal/tom.md](../legal/tom.md), [legal/security-audit.md](../legal/security-audit.md), [docs/encryption-strategy.md](encryption-strategy.md), [ARCHITECTURE.md](../ARCHITECTURE.md)

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Regulatorisches Inventar](#2-regulatorisches-inventar)
3. [DSGVO-Compliance-Matrix](#3-dsgvo-compliance-matrix)
4. [Consent-Architektur](#4-consent-architektur)
5. [Pflicht-Rechtstexte – Status-Checklist](#5-pflicht-rechtstexte--status-checklist)
6. [EU AI Act Relevanz](#6-eu-ai-act-relevanz)
7. [Drittanbieter-Datenflüsse](#7-drittanbieter-datenflüsse)
8. [Security-Compliance-Integration](#8-security-compliance-integration)
9. [Offene Punkte & Handlungsbedarf](#9-offene-punkte--handlungsbedarf)

---

## 1. Executive Summary

Das PWBS befindet sich in Phase 2 (MVP) und plant eine Closed Beta mit 10–20 Nutzern in der EU. Das System verarbeitet hochsensible persönliche Wissensarbeiterdaten aus vier Quellen (Google Calendar, Notion, Zoom, Obsidian), generiert daraus über LLM-APIs (Anthropic Claude, OpenAI GPT-4) Kontextbriefings und speichert abgeleitete Daten in PostgreSQL, Weaviate und optional Neo4j. Deployment: AWS eu-central-1 (Backend), Vercel (Frontend).

### Ampel-Bewertung

| Bereich                            | Status                         | Bewertung                                                                                                                         |
| ---------------------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| **Technische DSGVO-Maßnahmen**     | 🟢 Fertig                      | Envelope Encryption, Tenant-Isolation (`owner_id`), `expires_at`, kaskadierte Löschung, TLS 1.3 – alles architektonisch verankert |
| **AVVs mit Dienstleistern**        | 🟢 Fertig                      | AVV-Entwürfe für AWS, Anthropic, OpenAI, Vercel vorhanden; Klärungsbedarf bei EU-Datenresidenz der LLM-Provider                   |
| **Technische Sicherheit (OWASP)**  | 🟡 Weitgehend fertig           | 0 kritische Findings; 2 hohe Findings offen (Dependency-Scanning, Audit-Trail); CSP-Header fehlt                                  |
| **Datenschutzerklärung**           | 🔴 Fehlt                       | Kein Art.-13/14-konformer Text vorhanden – **Launch-Blocker**                                                                     |
| **Impressum**                      | 🔴 Fehlt                       | DDG § 5 nicht erfüllt – **Launch-Blocker**                                                                                        |
| **AGB**                            | 🔴 Fehlen                      | Keine Nutzungsbedingungen – **Launch-Blocker**                                                                                    |
| **Cookie-/Tracking-Hinweis**       | 🟡 Teilweise                   | Vercel Analytics deaktiviert; formaler TDDDG-Hinweis fehlt, wenn Analytics aktiviert wird                                         |
| **EU AI Act Transparenz**          | 🟡 Konzeptionell               | LLM-generierte Inhalte tragen Quellenreferenzen; formale Kennzeichnung als KI-generiert fehlt                                     |
| **DSFA**                           | 🟡 Vorabeinschätzung vorhanden | Formale DSFA gemäß Art. 35 DSGVO noch nicht durchgeführt – vor Open Beta erforderlich                                             |
| **VVT (Verarbeitungsverzeichnis)** | 🔴 Fehlt                       | Art. 30 DSGVO – formales Verzeichnis noch nicht erstellt                                                                          |

**Gesamtbewertung:** Die technische Basis ist solide (Verschlüsselung, Isolation, Löschkonzepte). Was fehlt, sind die **rechtlichen Pflichtdokumente** (Datenschutzerklärung, Impressum, AGB) und die **formale DSFA**. Ohne diese Dokumente ist auch eine Closed Beta in der EU rechtlich nicht tragfähig.

---

## 2. Regulatorisches Inventar

### 2.1 DSGVO (EU) 2016/679 – Datenschutz-Grundverordnung

**Relevanz:** Hoch – Kernanwendungsbereich

Das PWBS verarbeitet personenbezogene Daten von EU-Bürgern (Nutzer und in Dokumenten genannte Dritte). Die DSGVO ist vollumfänglich anwendbar.

**Betroffene Verarbeitungen:**

- Erhebung und Speicherung von Kalendereinträgen, Notizen, Transkripten (Art. 4 Nr. 2 DSGVO)
- Profiling durch Knowledge-Graph-Aufbau und Musteranalyse (Art. 4 Nr. 4 DSGVO – ⚖️ Juristische Prüfung empfohlen: Ob die Wissensvernetzung als Profiling einzustufen ist)
- Übermittlung von Dokumenten-Chunks an LLM-Provider in den USA (Art. 44 ff. DSGVO – Drittlandtransfer)
- Automatisierte Entscheidungsfindung: nicht anwendbar, da Briefings informativ sind und keine rechtsverbindlichen Entscheidungen treffen (Art. 22 DSGVO)

**Besonderheit Drittdaten:** Kalendereinträge enthalten E-Mail-Adressen von Meeting-Teilnehmern; Zoom-Transkripte enthalten Äußerungen Dritter. Dies sind personenbezogene Daten Dritter, die ohne deren direkte Einwilligung verarbeitet werden. ⚖️ Juristische Prüfung empfohlen: Ob Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse des Nutzers an der Kontextaufbereitung seiner eigenen Meetings) hier als Rechtsgrundlage tragfähig ist, oder ob eine Informationspflicht gegenüber Dritten besteht (Art. 14 DSGVO).

### 2.2 DDG – Digitale-Dienste-Gesetz

**Relevanz:** Mittel – Impressumspflicht

Das PWBS ist ein digitaler Dienst im Sinne des DDG (vormals TMG). Es besteht eine **Impressumspflicht nach § 5 DDG**.

**Anwendbar:**

- § 5 DDG: Impressumspflicht mit Name/Firma, Anschrift, E-Mail, ggf. Handelsregister, USt-IdNr.
- § 6 DDG: Informationspflichten bei kommerzieller Kommunikation (relevant, sobald Marketing-E-Mails versendet werden)

**Nicht anwendbar:**

- §§ 7–10 DDG (Haftungsprivilegien für Hosting-Provider): Das PWBS ist kein Hosting-Dienstleister im DDG-Sinne, da es nutzereigene Daten verarbeitet, nicht fremde Inhalte hostet.

### 2.3 TDDDG – Telekommunikation-Digitale-Dienste-Datenschutz-Gesetz

**Relevanz:** Niedrig bis Mittel – Cookie-/Tracking-Consent

Das TDDDG (seit 14.05.2024 in Kraft, ersetzt TTDSG) regelt den Zugriff auf Endgeräte und die Verarbeitung von Telekommunikations-Nutzungsdaten.

**Anwendbar:**

- § 25 TDDDG: Einwilligung für Cookies und vergleichbare Technologien, die nicht „unbedingt erforderlich" sind. Falls Vercel Analytics, Sentry oder andere Tracking-Tools aktiviert werden, ist ein Opt-in-Banner erforderlich.
- Technisch notwendige Cookies/Tokens (JWT im `localStorage`, Session-Cookies): Kein Consent erforderlich (§ 25 Abs. 2 Nr. 2 TDDDG).

**Nicht anwendbar:**

- §§ 1–24 TDDDG (Telekommunikationsregulierung): Das PWBS erbringt keine Telekommunikationsdienste.

**Aktueller Stand:** Vercel Analytics ist standardmäßig deaktiviert (dokumentiert in AVV-Vercel Abschnitt 10.1). Solange kein nicht-essentielles Tracking aktiviert wird, besteht keine Cookie-Banner-Pflicht – lediglich ein Hinweis auf technisch notwendige Cookies in der Datenschutzerklärung.

### 2.4 EU AI Act (EU) 2024/1689

**Relevanz:** Mittel – Transparenzpflichten ab August 2026

Der EU AI Act trat am 1. August 2024 in Kraft. Die Bestimmungen treten gestaffelt in Kraft:

- **Ab 2. Februar 2025:** Verbotene KI-Praktiken (Art. 5) – für PWBS nicht relevant
- **Ab 2. August 2025:** Pflichten für General Purpose AI (GPAI) Modelle – betrifft Anthropic/OpenAI als Provider, nicht PWBS als Deployer
- **Ab 2. August 2026:** Transparenzpflichten für KI-Systeme mit limitiertem Risiko (Art. 50) – betrifft PWBS direkt

**Klassifizierung des PWBS:**

| AI-Act-Kategorie                          | Anwendbar? | Begründung                                                                                                                               |
| ----------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Verbotenes KI-System (Art. 5)             | Nein       | Kein Social Scoring, keine biometrische Überwachung, keine Manipulation                                                                  |
| Hochrisiko-KI-System (Anhang III)         | Nein       | PWBS fällt nicht unter die in Anhang III aufgeführten Bereiche (Beschäftigung, Bildung, kritische Infrastruktur, Strafverfolgung)        |
| KI-System mit begrenztem Risiko (Art. 50) | **Ja**     | PWBS generiert LLM-basierte Textinhalte (Briefings, Suchantworten). Art. 50 Abs. 4 verpflichtet zur Kennzeichnung KI-generierter Inhalte |
| GPAI-Modell-Anbieter (Art. 51 ff.)        | Nein       | PWBS nutzt GPAI-Modelle, bietet aber selbst kein Modell an (Deployer, kein Provider)                                                     |

Detaillierte Analyse in [Abschnitt 6](#6-eu-ai-act-relevanz).

---

## 3. DSGVO-Compliance-Matrix

Die folgende Matrix baut auf den 7 Datenverarbeitungskategorien aus [docs/dsgvo-erstkonzept.md](dsgvo-erstkonzept.md) auf und ergänzt fehlende Aspekte.

### 3.1 Kalendereinträge (Google Calendar)

| Aspekt                 | Detail                                                                                                                                                                                                                                                                                                                                    |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Datentyp**           | Terminbetreff, Beschreibung, Teilnehmer-E-Mails, Ort, Zeitraum                                                                                                                                                                                                                                                                            |
| **Verarbeitungszweck** | Meeting-Briefings, Kontextsuche, Tagesplanung                                                                                                                                                                                                                                                                                             |
| **Rechtsgrundlage**    | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung via OAuth-Consent) für die Daten des Nutzers; für E-Mail-Adressen Dritter (Meeting-Teilnehmer): Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse). ⚖️ Juristische Prüfung empfohlen: Tragfähigkeit des berechtigten Interesses für Drittdaten                                                  |
| **Speicherdauer**      | 365 Tage nach Event-Datum                                                                                                                                                                                                                                                                                                                 |
| **Löschkonzept**       | `expires_at` wird bei Ingestion auf Event-Datum + 365 Tage gesetzt. `cleanup_expired`-Job (täglich 03:00) löscht abgelaufene Einträge. Kaskadierende Löschung: PostgreSQL (CASCADE DELETE) → Weaviate (Tenant-Objekte) → Neo4j (Knoten mit `owner_id`)                                                                                    |
| **Betroffenenrechte**  | **Auskunft (Art. 15):** Export via `POST /api/v1/admin/export` (JSON). **Löschung (Art. 17):** Einzelquelle via Konnektor-Trennung; vollständig via `DELETE /api/v1/admin/account` (30 Tage Soft-Delete). **Portabilität (Art. 20):** JSON+Markdown-Export. **Widerspruch (Art. 21):** Konnektor-Trennung löscht alle Daten dieser Quelle |

### 3.2 Notizen (Notion / Obsidian)

| Aspekt                 | Detail                                                                                                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Datentyp**           | Freitext (Markdown/Rich Text), Metadaten, interne Links, Frontmatter                                                                                                                                  |
| **Verarbeitungszweck** | Wissensvernetzung, semantische Suche, Briefing-Kontext                                                                                                                                                |
| **Rechtsgrundlage**    | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) – die Indexierung und semantische Suche über Notizen ist die vertraglich zugesicherte Kernfunktion                                                     |
| **Speicherdauer**      | 730 Tage nach letzter Aktualisierung                                                                                                                                                                  |
| **Löschkonzept**       | Identisch zu 3.1. Obsidian-Vault-Trennung löscht alle importierten Dateien; Notion-Trennung löscht alle Notion-Seiten. Re-Sync nach Löschung in Quell-App: Hash-Vergleich erkennt gelöschte Dokumente |
| **Betroffenenrechte**  | Identisch zu 3.1. Besonderheit: Nutzer kontrolliert Inhalt vollständig – Freitext kann beliebige PII enthalten. Keine Inhaltsfilterung durch PWBS                                                     |

### 3.3 Transkripte (Zoom)

| Aspekt                 | Detail                                                                                                                                                                                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Datentyp**           | Gesprächsinhalte, Sprechernamen, Meeting-Metadaten, Teilnehmerliste, Dauer                                                                                                                                                                                         |
| **Verarbeitungszweck** | Meeting-Nachbereitung, Entscheidungsextraktion, Wissenserhalt                                                                                                                                                                                                      |
| **Rechtsgrundlage**    | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung via OAuth-Consent) für Nutzerdaten. Für Äußerungen Dritter: ⚖️ Juristische Prüfung empfohlen: Tragfähigkeit von Art. 6 Abs. 1 lit. f (berechtigtes Interesse) oder Erfordernis der Einwilligung aller Gesprächsteilnehmer |
| **Speicherdauer**      | 365 Tage nach Meeting-Datum                                                                                                                                                                                                                                        |
| **Löschkonzept**       | Identisch zu 3.1. Transkript-Chunks werden kaskadiert gelöscht                                                                                                                                                                                                     |
| **Betroffenenrechte**  | Identisch zu 3.1. Besonderheit: Dritte (Meeting-Teilnehmer) haben ebenfalls Betroffenenrechte bezüglich ihrer Äußerungen – Prozess für Drittanfragen muss definiert werden                                                                                         |

### 3.4 Embeddings (abgeleitete Vektordaten)

| Aspekt                 | Detail                                                                                                                                                                                                                                                                                               |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Datentyp**           | Numerische Vektoren (1536 Dimensionen bei `text-embedding-3-small`), Chunk-Metadaten                                                                                                                                                                                                                 |
| **Verarbeitungszweck** | Semantische Suche, Ähnlichkeitserkennung                                                                                                                                                                                                                                                             |
| **Rechtsgrundlage**    | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung, technisch notwendig für Kernfunktion). ⚖️ Juristische Prüfung empfohlen: Ob Embedding-Vektoren als personenbezogene Daten einzustufen sind (theoretische Rückschließbarkeit auf Quellinhalte). Konservative Empfehlung: Als personenbezogen behandeln |
| **Speicherdauer**      | Identisch zum Quelldokument (kaskadierte Löschung)                                                                                                                                                                                                                                                   |
| **Löschkonzept**       | Weaviate-Objekte werden bei Quelldokument-Löschung kaskadiert entfernt (Tenant-Isolation). Bei Account-Löschung: kompletter Weaviate-Tenant wird gelöscht                                                                                                                                            |
| **Betroffenenrechte**  | Über Quelldokument-Rechte abgedeckt. Embedding-Löschung erfolgt automatisch bei Quelllöschung                                                                                                                                                                                                        |

### 3.5 LLM-generierte Inhalte (Briefings, Suchantworten)

| Aspekt                 | Detail                                                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Datentyp**           | Strukturierte Briefings (Markdown), Suchantwort-Zusammenfassungen mit Quellenreferenzen                             |
| **Verarbeitungszweck** | Kontextuelle Aufbereitung (Morning-, Meeting-, Weekly-Briefings), Antwortgenerierung                                |
| **Rechtsgrundlage**    | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung – Briefings sind die Kerndienstleistung)                              |
| **Speicherdauer**      | Briefings: 90 Tage nach Erstellung. Suchantworten: nicht persistiert (transient)                                    |
| **Löschkonzept**       | `expires_at` = Erstellung + 90 Tage. Cleanup-Job löscht abgelaufene Briefings. Bei Account-Löschung: CASCADE DELETE |
| **Betroffenenrechte**  | Export umfasst Briefings (Art. 15/20). Löschung über Account- oder Einzellöschung                                   |

### 3.6 Knowledge-Graph-Daten (Neo4j)

| Aspekt                 | Detail                                                                                                                                                                                                      |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Datentyp**           | Entitäten (Personen, Projekte, Entscheidungen, Themen), Relationen (MENTIONED_IN, DECIDED_IN, RELATED_TO)                                                                                                   |
| **Verarbeitungszweck** | Beziehungsanalyse, Kontextanreicherung, Mustererkennung                                                                                                                                                     |
| **Rechtsgrundlage**    | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung). ⚖️ Juristische Prüfung empfohlen: Ob die Erstellung von Beziehungsgraphen über persönliche Kontakte als Profiling gemäß Art. 4 Nr. 4 DSGVO einzustufen ist  |
| **Speicherdauer**      | Identisch zum Quelldokument (kaskadierte Löschung via `owner_id`)                                                                                                                                           |
| **Löschkonzept**       | Alle Graph-Operationen nutzen MERGE (Idempotenz). Löschung: `MATCH (n {owner_id: $id}) DETACH DELETE n`. Neo4j ist im MVP optional – bei Nichtverfügbarkeit gibt `NullGraphService` leere Ergebnisse zurück |
| **Betroffenenrechte**  | Export umfasst Entitäten und Relationen (JSON). Löschung über Account-Löschung oder Quelltrennung                                                                                                           |

### 3.7 Authentifizierungs- und Session-Daten

| Aspekt                 | Detail                                                                                                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Datentyp**           | E-Mail, Anzeigename, Passwort-Hash (Argon2id), JWT-Tokens, OAuth-Access/Refresh-Tokens                                                                                   |
| **Verarbeitungszweck** | Authentifizierung, Autorisierung, Konnektor-Anbindung                                                                                                                    |
| **Rechtsgrundlage**    | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung – Registrierung und Login sind für die Nutzung erforderlich)                                                               |
| **Speicherdauer**      | Access Token: 15 Min. Refresh Token: 30 Tage (Rotation bei Nutzung). OAuth-Tokens: bis Widerruf. Account-Daten: bis Löschung + 30 Tage Karenzzeit                        |
| **Löschkonzept**       | Token-Revocation bei Logout/Widerruf. Account-Löschung: 30 Tage Soft-Delete, danach irreversibel. DEK-Löschung macht alle verschlüsselten Daten kryptographisch unlesbar |
| **Betroffenenrechte**  | Auskunft: Kontodaten und Verbindungsstatus im Export. Löschung: `DELETE /api/v1/admin/account`. Berichtigung: Anzeigename/E-Mail änderbar über UI                        |

### 3.8 Audit- und Telemetriedaten

| Aspekt                 | Detail                                                                                                                                                               |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Datentyp**           | User-IDs, Aktionstypen (Login, Export, Löschung, Konnektor-Anbindung), Zeitstempel, Request-IDs, HTTP-Status                                                         |
| **Verarbeitungszweck** | Sicherheitsmonitoring, Fehleranalyse, Compliance-Nachweis                                                                                                            |
| **Rechtsgrundlage**    | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an Sicherheit und Betriebsstabilität). Kein PII in Logs (Policy in [legal/tom.md](../legal/tom.md), Abschnitt 10) |
| **Speicherdauer**      | Audit-Log: 2 Jahre (Compliance-Nachweis). Application-Logs: 90 Tage                                                                                                  |
| **Löschkonzept**       | Automatische Rotation. Audit-Log enthält nur User-IDs – bei Account-Löschung wird User-ID pseudonymisiert, Log-Einträge bleiben für Compliance bestehen              |
| **Betroffenenrechte**  | Auskunft: Audit-Log im Export enthalten. Löschung: Pseudonymisierung statt Löschung (berechtigtes Interesse an Nachvollziehbarkeit überwiegt)                        |

---

## 4. Consent-Architektur

### 4.1 Rechtsgrundlagen-Zuordnung: Einwilligung vs. Vertragserfüllung

| Verarbeitungszweck                             | Rechtsgrundlage                                                                | Begründung                                                                                                                                                                                                                                                                                                          |
| ---------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Konnektor-Anbindung (Google Calendar, Zoom)    | **Art. 6 Abs. 1 lit. a – Einwilligung**                                        | OAuth-Consent-Flow als explizite, informierte Einwilligung. Jeder Konnektor = separate Einwilligung. Jederzeit widerrufbar.                                                                                                                                                                                         |
| Konnektor-Anbindung (Notion)                   | **Art. 6 Abs. 1 lit. a – Einwilligung**                                        | OAuth-Consent-Flow. Nutzer wählt, welche Seiten/Datenbanken geteilt werden.                                                                                                                                                                                                                                         |
| Konnektor-Anbindung (Obsidian Vault)           | **Art. 6 Abs. 1 lit. b – Vertragserfüllung**                                   | Lokaler Dateizugriff durch explizite Pfadangabe. Kein OAuth, aber bewusste Nutzeraktion. ⚖️ Juristische Prüfung empfohlen: Ob die Pfadangabe als konkludente Einwilligung genügt oder ein separater Consent-Dialog erforderlich ist                                                                                 |
| Ingestion, Chunking, Embedding-Generierung     | **Art. 6 Abs. 1 lit. b – Vertragserfüllung**                                   | Technisch notwendig für die vertraglich zugesicherte Dienstleistung (semantische Suche, Briefings)                                                                                                                                                                                                                  |
| Briefing-Generierung (via LLM-API)             | **Art. 6 Abs. 1 lit. b – Vertragserfüllung**                                   | Kernfunktion des Produkts. Nutzer erwartet bei Registrierung, dass Briefings generiert werden                                                                                                                                                                                                                       |
| Weitergabe an LLM-Provider (Anthropic, OpenAI) | **Art. 6 Abs. 1 lit. b – Vertragserfüllung** + **separater Hinweis empfohlen** | Die LLM-Verarbeitung ist technisch integraler Bestandteil der Dienstleistung. Dennoch sollte die Datenschutzerklärung explizit auf die Datenübermittlung an Drittanbieter hinweisen. ⚖️ Juristische Prüfung empfohlen: Ob eine separate Einwilligung für den Drittlandtransfer an OpenAI/Anthropic erforderlich ist |
| Knowledge-Graph-Aufbau                         | **Art. 6 Abs. 1 lit. b – Vertragserfüllung**                                   | Bestandteil der Wissensvernetzung als Kernfunktion                                                                                                                                                                                                                                                                  |
| Audit-Logging, Sicherheitsmonitoring           | **Art. 6 Abs. 1 lit. f – Berechtigtes Interesse**                              | Betriebssicherheit und Compliance-Nachweis. Kein PII in Logs                                                                                                                                                                                                                                                        |
| Analytics/Tracking (falls aktiviert)           | **Art. 6 Abs. 1 lit. a – Einwilligung**                                        | Opt-in-Pflicht unter TDDDG § 25. Aktuell deaktiviert                                                                                                                                                                                                                                                                |

### 4.2 Granularität der Consent-Optionen

Dem Nutzer müssen folgende **separate** Einwilligungsoptionen angeboten werden:

1. **Pro Konnektor:** Jeder Konnektor wird über einen eigenen OAuth-Flow oder expliziten Aktivierungsdialog verbunden. Die Einwilligung für Google Calendar ist unabhängig von der Einwilligung für Notion.
2. **LLM-Verarbeitung:** In der Datenschutzerklärung muss transparent dargestellt werden, dass Dokumenten-Chunks an Anthropic (Claude) und OpenAI (Embeddings, Fallback) übermittelt werden. Empfehlung: Bei Registrierung einen expliziten Hinweis mit Bestätigung einbauen (kein separater Consent-Flow, aber informiertes Opt-in).
3. **Analytics/Tracking:** Falls Vercel Analytics oder vergleichbare Tools aktiviert werden: separates Cookie-Banner mit Opt-in (TDDDG § 25).

**Empfehlung:** Kein Bundled Consent. Die Konnektor-Anbindung darf nicht Voraussetzung für die Registrierung sein (Koppelungsverbot, Art. 7 Abs. 4 DSGVO).

### 4.3 Widerruf und Folgen

| Widerruf                     | Technische Folge                                                                                                                                                                                                   |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Einzelner Konnektor getrennt | Alle Daten dieser Quelle werden gelöscht (PostgreSQL CASCADE, Weaviate-Objekte, Neo4j-Knoten). OAuth-Tokens werden widerrufen und gelöscht. Andere Konnektoren bleiben aktiv                                       |
| Account-Löschung             | Komplette Datenlöschung nach 30 Tagen Karenzzeit. DEK-Löschung macht alle verschlüsselten Daten kryptographisch unlesbar. Alle Sessions invalidiert                                                                |
| LLM-Verarbeitung abgelehnt   | ⚖️ Zu klären: Da die LLM-Verarbeitung Kernfunktion ist, könnte der Dienst ohne sie nicht erbracht werden. Keine Briefing-Generierung möglich. Empfehlung: In AGB als essenzielle Funktionsvoraussetzung definieren |

### 4.4 Consent-Dokumentation

Jede Einwilligung muss dokumentiert werden (Art. 7 Abs. 1 DSGVO):

- **Zeitpunkt** des Consents (Timestamp)
- **Umfang** (welcher Konnektor, welche Scopes)
- **Version** der Datenschutzerklärung zum Zeitpunkt des Consents
- **Widerrufe** (Timestamp, Umfang)

Empfehlung: `ConnectorConsent`-Tabelle (bereits im Datenmodell als `connector_consents` vorhanden) um Consent-Version und DSE-Version ergänzen.

---

## 5. Pflicht-Rechtstexte – Status-Checklist

| Rechtstext                                  | Status     | Fundort                                                     | Handlungsbedarf                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------------- | ---------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Impressum (DDG § 5)**                     | ❌ Fehlt   | —                                                           | Impressum erstellen mit: Name/Firma, ladungsfähige Anschrift, E-Mail, Telefon, ggf. Handelsregister, USt-IdNr. Im Frontend unter `/impressum` verlinken. **Blocker für Launch.**                                                                                                                                                      |
| **Datenschutzerklärung (DSGVO Art. 13/14)** | ❌ Fehlt   | —                                                           | Vollständige DSE erstellen mit: Verantwortlicher, DPO (falls vorhanden), Verarbeitungszwecke pro Datentyp, Rechtsgrundlagen, Speicherdauern, Empfänger (AWS, Anthropic, OpenAI, Vercel), Betroffenenrechte, Beschwerderecht bei Aufsichtsbehörde, Drittlandtransfer-Garantien. Basis: Matrix aus Abschnitt 3. **Blocker für Launch.** |
| **AGB (Allgemeine Geschäftsbedingungen)**   | ❌ Fehlen  | —                                                           | Nutzungsbedingungen erstellen: Leistungsbeschreibung, Nutzungsrecht, Haftungsbeschränkung, Verfügbarkeit (kein SLA für Beta), Kündigung, anwendbares Recht (deutsches Recht), Gerichtsstand. **Blocker für Launch.**                                                                                                                  |
| **Cookie-/Tracking-Hinweis (TDDDG § 25)**   | ⚠️ Bedingt | —                                                           | Aktuell nicht erforderlich, da Vercel Analytics deaktiviert. Sobald nicht-essentielles Tracking aktiviert wird: Opt-in-Banner implementieren. Cookie-Hinweis in DSE aufnehmen (technisch notwendige Cookies wie JWT).                                                                                                                 |
| **AVV – AWS**                               | ✅ Entwurf | [legal/avv/avv-aws.md](../legal/avv/avv-aws.md)             | Entwurf vorhanden. Muss noch unterzeichnet und mit AWS-Standard-DPA abgeglichen werden. Klärung: Ob AWS-Standard-DPA (online akzeptierbar) ausreicht.                                                                                                                                                                                 |
| **AVV – Anthropic**                         | ✅ Entwurf | [legal/avv/avv-anthropic.md](../legal/avv/avv-anthropic.md) | Entwurf vorhanden. Offene Punkte: EU-Datenresidenz, Safety-Logging-Dauer, Opt-Out für Prompt-Logging. DPA von Anthropic unterzeichnen.                                                                                                                                                                                                |
| **AVV – OpenAI**                            | ✅ Entwurf | [legal/avv/avv-openai.md](../legal/avv/avv-openai.md)       | Entwurf vorhanden. Offene Punkte: EU-Endpoint-Verfügbarkeit, Content-Filter-Log-Speicherung. OpenAI DPA unterzeichnen.                                                                                                                                                                                                                |
| **AVV – Vercel**                            | ✅ Entwurf | [legal/avv/avv-vercel.md](../legal/avv/avv-vercel.md)       | Entwurf vorhanden. Vercel DPA online akzeptieren. Edge-Functions auf EU-Region beschränken.                                                                                                                                                                                                                                           |
| **DPA-Template (für Enterprise)**           | ❌ Fehlt   | —                                                           | Für Enterprise-Anfragen ein eigenes DPA-Template erstellen, das PWBS als Auftragsverarbeiter positioniert. Nicht launch-kritisch für Closed Beta.                                                                                                                                                                                     |
| **VVT (Art. 30 DSGVO)**                     | ❌ Fehlt   | —                                                           | Verzeichnis von Verarbeitungstätigkeiten erstellen. Basis: Matrix aus Abschnitt 3. Pflicht, sobald die Verarbeitung nicht nur gelegentlich erfolgt (was bei regelmäßiger Sync-Verarbeitung der Fall ist).                                                                                                                             |

---

## 6. EU AI Act Relevanz

### 6.1 Klassifizierung

Das PWBS fällt unter die Kategorie **KI-System mit begrenztem Risiko (Limited Risk)** gemäß Art. 50 EU AI Act:

- Es nutzt GPAI-Modelle (Claude, GPT-4), um Textinhalte zu generieren (Briefings, Suchantworten)
- Die generierten Inhalte könnten als authentisch wahrgenommen werden (Risiko: Nutzer behandelt LLM-generierte Zusammenfassungen als Fakten)
- Es ist **kein** Hochrisiko-System nach Anhang III, da es keine Entscheidungen in den dort genannten Bereichen trifft

### 6.2 Pflichten nach Art. 50 (ab 2. August 2026)

| Pflicht                                                  | Anwendbar? | Umsetzung im PWBS                                                                                                               | Status                                                                                                             |
| -------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Art. 50 Abs. 4: Kennzeichnung KI-generierter Inhalte** | Ja         | Briefings und Suchantworten müssen als KI-generiert erkennbar sein                                                              | ⚠️ Teilweise: Quellenreferenzen vorhanden, aber keine explizite Kennzeichnung „Dieser Text wurde mit KI generiert" |
| **Art. 50 Abs. 2: Kennzeichnung bei Deepfakes**          | Nein       | PWBS generiert keine Bild-/Audio-/Video-Inhalte                                                                                 | —                                                                                                                  |
| **Art. 52 (alt)/Art. 50: Hinweis auf KI-Interaktion**    | Nein       | Nutzer interagiert nicht mit einem Chatbot, der sich als Mensch ausgibt. PWBS ist explizit als automatisiertes System erkennbar | —                                                                                                                  |

### 6.3 Empfohlene Maßnahmen

Auch wenn die vollen Art.-50-Pflichten erst ab August 2026 greifen, sind folgende Maßnahmen jetzt schon sinnvoll:

1. **KI-Kennzeichnung in Briefings:** Jedes generierte Briefing sollte einen sichtbaren Hinweis tragen, z. B.:

   > „Dieses Briefing wurde automatisch mit KI-Unterstützung erstellt. Alle Aussagen basieren auf den angegebenen Quellen. Bitte verifizieren Sie wichtige Informationen."

2. **Quellenreferenzen stärken:** Bereits implementiert – jede faktische Aussage in Briefings trägt eine klickbare Quellenreferenz. Dies erfüllt die Erklärbarkeitsanforderung.

3. **Dokumentation der KI-Nutzung:** In der Datenschutzerklärung und ggf. in den AGB dokumentieren:
   - Welche KI-Modelle eingesetzt werden (Claude, GPT-4)
   - Zu welchem Zweck (Briefing-Generierung, Embedding, NER)
   - Dass keine automatisierten Entscheidungen im Sinne von Art. 22 DSGVO getroffen werden
   - Dass die Modellausgaben auf vom Nutzer bereitgestellten Daten basieren (RAG, kein LLM-Vorwissen)

4. **Halluzinations-Mitigation dokumentieren:** LLM-Temperatur 0.3, Grounding-Validierung, „Kein Ergebnis"-Fallback statt Erfindung – diese Maßnahmen sollten in einer internen AI-Governance-Dokumentation festgehalten werden.

---

## 7. Drittanbieter-Datenflüsse

### 7.1 Inventar

| Anbieter           | Dienst                                                                                              | Welche Daten fließen                                                                                                           | Serverstandort                                           | AVV-Status                        | Datenschutzniveau                                                                                                               | Anmerkung                                                                                                                                       |
| ------------------ | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Anthropic**      | Claude API (Messages)                                                                               | Dokumenten-Chunks (max. 512 Token) als Prompt-Kontext, Briefing-Prompts mit strukturierten Kontextdaten, extrahierte Entitäten | USA (Hauptsitz). EU-Endpoint: ⚠️ ungeklärt               | ✅ AVV-Entwurf vorhanden          | EU-US Data Privacy Framework (DPF) + SCCs empfohlen. Zero Data Retention Policy (API Terms). Kein Modelltraining mit API-Daten. | Offener Punkt: Dauer der Safety-Evaluation-Logs. `owner_id` wird NICHT in Prompts übermittelt. Chunks auf 512 Token begrenzt (Datenminimierung) |
| **OpenAI**         | Embeddings API (`text-embedding-3-small`), GPT-4 Fallback                                           | Dokumenten-Chunks (128–512 Token), Suchqueries                                                                                 | USA (Microsoft Azure Hosting). EU-Endpoint: ⚠️ ungeklärt | ✅ AVV-Entwurf vorhanden          | EU-US DPF + SCCs empfohlen. Zero Data Retention Policy (API Terms). Kein Modelltraining.                                        | Offener Punkt: Content-Filter-Log-Speicherung. `owner_id` wird NICHT übermittelt. Fallback auf lokale Sentence Transformers möglich             |
| **AWS**            | ECS Fargate (Compute), RDS PostgreSQL (DB), ElastiCache Redis (Cache), S3 (Backup), KMS (Schlüssel) | Alle Nutzerdaten (verschlüsselt at rest, TLS in transit)                                                                       | **EU: eu-central-1 (Frankfurt)**                         | ✅ AVV-Entwurf vorhanden          | ✅ Angemessen: EU-Datenresidenz, ISO 27001, SOC 2 Type II, C5-Testat. Customer Managed Keys (KMS)                               | Keine Datenübermittlung in Drittländer. AWS GDPR DPA online akzeptierbar                                                                        |
| **Vercel**         | Frontend-Hosting (Next.js), Edge Functions                                                          | Browser-Metadaten (IP, User-Agent). Keine Backend-Nutzerdaten. API-Calls gehen direkt Client→Backend                           | Edge Network (weltweit), steuerbar auf EU                | ✅ AVV-Entwurf vorhanden          | ✅ Angemessen bei EU-Region-Lock: SOC 2. Keine sensiblen Daten im Frontend                                                      | Edge Functions auf EU beschränken. Vercel Analytics deaktiviert. Keine Secrets in Vercel-Umgebung                                               |
| **Sentry**         | Error Tracking                                                                                      | Stack-Traces, Request-IDs, HTTP-Metadaten. **Keine PII** (Policy: nur IDs und Metadaten in Logs)                               | EU-Datenresidenz wählbar (Sentry EU)                     | ⚠️ Noch kein AVV                  | ⚠️ Zu klären: Sentry DPA abschließen, EU-Region wählen                                                                          | Falls Sentry aktiviert wird: DPA erforderlich. PII-Scrubbing konfigurieren. Kein User-Content in Error-Berichten                                |
| **Weaviate Cloud** | Vektor-Datenbank (falls nicht Self-Hosted)                                                          | Embedding-Vektoren, Chunk-Metadaten (source_id, title, owner_id)                                                               | ⚠️ Abhängig von Einrichtung                              | ⚠️ Nur bei Cloud-Nutzung relevant | ⚠️ Bei Self-Hosted: kein Drittanbieter. Bei Cloud: AVV erforderlich                                                             | Aktuelle Architektur: Self-Hosted auf AWS (EC2). Kein externer Weaviate-Cloud-Dienst. Bei Wechsel zu Cloud: AVV zwingend                        |

### 7.2 Bewertung Drittlandtransfer

**Anthropic und OpenAI (USA):** Beide Anbieter verarbeiten Daten in den USA. Seit dem Angemessenheitsbeschluss der EU-Kommission zum EU-US Data Privacy Framework (DPF, Juli 2023) ist ein Datentransfer an DPF-zertifizierte Unternehmen grundsätzlich möglich. Empfehlung:

1. Prüfen, ob Anthropic und OpenAI DPF-zertifiziert sind
2. Zusätzlich SCCs (Standardvertragsklauseln) gemäß Art. 46 Abs. 2 lit. c DSGVO vereinbaren
3. Transfer Impact Assessment (TIA) dokumentieren
4. Technische Zusatzmaßnahmen: Datenminimierung (max. 512 Token Chunks), keine `owner_id` in Prompts, Zero Data Retention

**AWS (EU):** Kein Drittlandtransfer, da alle Services in eu-central-1 (Frankfurt) betrieben werden. Angemessenes Datenschutzniveau sichergestellt.

**Vercel (konfigurierbar):** Edge Functions auf EU beschränken. CDN-Caching ohne nutzerspezifische Daten. Bei korrekt konfiguriertem Region-Lock: kein problematischer Drittlandtransfer.

---

## 8. Security-Compliance-Integration

### 8.1 Offene Security-Findings mit rechtlicher Relevanz

Die folgende Tabelle referenziert die Findings aus [legal/security-audit.md](../legal/security-audit.md) und bewertet deren rechtliche Relevanz aus DSGVO-Sicht.

| Finding                                                          | Schweregrad (Security) | Rechtliche Relevanz                                                                                                                                                                                          | Auswirkung auf Launch          | Maßnahme                                                                                                                    |
| ---------------------------------------------------------------- | :--------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| **A05-F01: Keine automatische Dependency-Vulnerability-Prüfung** |          Hoch          | **Hoch** – Art. 32 DSGVO fordert „Verfahren zur regelmäßigen Überprüfung" der Sicherheit. Fehlende CVE-Scans sind ein dokumentierter GAP                                                                     | Vor Closed Beta schließen      | `pip-audit` / `safety` in CI integrieren, `npm audit` für Frontend. Dependabot/Renovate aktivieren                          |
| **A09-F01: Audit-Trail unvollständig**                           |          Hoch          | **Hoch** – Art. 5 Abs. 2 DSGVO (Rechenschaftspflicht) erfordert Nachweisbarkeit aller datenschutzrelevanten Aktionen. Ohne Audit-Trail sind Löschungen, Exporte und Consent-Änderungen nicht nachvollziehbar | Vor Closed Beta schließen      | Audit-Log-Service implementieren, der Datenlöschung, Konnektor-Anbindung/-Trennung, Datenexport, Login/Logout protokolliert |
| **A02-F01: Dev-Fallback auf HS256**                              |         Mittel         | **Mittel** – In Produktion unsicher. Art. 32 DSGVO – Integrität der Authentifizierung                                                                                                                        | Vor Closed Beta: Startup-Check | Startup-Check: Bei `PWBS_ENV=production` ohne RSA-Keys Start verweigern                                                     |
| **A03-F01: CSP-Header fehlt**                                    |         Mittel         | **Mittel** – XSS-Schutz. Art. 32 DSGVO – Schutz der Integrität und Vertraulichkeit                                                                                                                           | Vor Closed Beta empfohlen      | `Content-Security-Policy` in `SecurityHeadersMiddleware` ergänzen                                                           |
| **A06-F01: Kein automatisierter CVE-Scanner**                    |         Mittel         | Identisch mit A05-F01                                                                                                                                                                                        | Siehe A05-F01                  | Siehe A05-F01                                                                                                               |
| **A08-F01: Keine Docker-Image-Signierung**                       |         Mittel         | **Niedrig** für Closed Beta – relevant für Produktionsumgebung (Integrität der Deployment-Pipeline)                                                                                                          | Vor Open Beta                  | Docker Content Trust oder Cosign evaluieren                                                                                 |
| **A05-F02: CORS `allow_methods=["*"]`**                          |        Niedrig         | **Niedrig** – Theoretisches Attack-Surface, aber Backend-Auth schützt Endpoints                                                                                                                              | Vor Open Beta                  | Auf tatsächlich genutzte Methoden/Header einschränken                                                                       |
| **A10-F01: SSRF-Schutz nur als Richtlinie**                      |        Niedrig         | **Niedrig** für MVP (keine benutzerdefinierte URL-Eingabe aktuell)                                                                                                                                           | Vor Open Beta                  | URL-Validierungsfunktion für HTTP-Clients zentralisieren                                                                    |

### 8.2 Bereits implementierte Maßnahmen (Referenz: legal/tom.md)

Die in [legal/tom.md](../legal/tom.md) dokumentierten 10 TOM-Kategorien decken die Anforderungen von Art. 32 DSGVO weitgehend ab:

- ✅ **Zutrittskontrolle:** AWS-Rechenzentrum ISO 27001, Entwickler-Festplattenverschlüsselung
- ✅ **Zugangskontrolle:** JWT RS256, Token-Rotation, Argon2id, Rate Limiting
- ✅ **Zugriffskontrolle:** `owner_id`-Isolation, Weaviate-Tenants, Neo4j-Filter
- ✅ **Weitergabekontrolle:** TLS 1.3, HSTS, Security-Headers, Webhook-HMAC
- ✅ **Eingabekontrolle:** Pydantic-Validierung, parametrisierte Queries, Audit-Log (konzipiert)
- ✅ **Auftragskontrolle:** AVVs mit AWS, Anthropic, OpenAI, Vercel (Entwürfe vorhanden)
- ✅ **Verfügbarkeitskontrolle:** Backups RPO < 1h / RTO < 4h, Multi-AZ, Health Checks
- ✅ **Trennungskontrolle:** `owner_id` als Pflichtfeld, getrennte DB-Umgebungen
- ✅ **Verschlüsselung:** Envelope Encryption (KEK/DEK), Volume Encryption, TLS
- ✅ **Organisatorisch:** PII-freie Logs, Secrets-Management, Code-Review mit DSGVO-Checkliste

**GAPs in TOM:**

- MFA: Geplant für Phase 4
- DSGVO-Schulungen: Geplant, aber nicht durchgeführt
- DSFA für LLM-Verarbeitung: Dokumentiert, aber nicht formal durchgeführt

---

## 9. Offene Punkte & Handlungsbedarf

### 🔴 Blocker (vor Closed Beta)

| #   | Beschreibung                                                                                                                                                                                                                    | Komplexität | Abhängigkeit                                                               |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------- |
| B-1 | **Datenschutzerklärung erstellen** (Art. 13/14 DSGVO). Muss alle 8 Datenverarbeitungskategorien (Abschnitt 3), Drittanbieter (Abschnitt 7), Speicherdauern, Betroffenenrechte und Beschwerderecht bei Aufsichtsbehörde umfassen | M           | Empfehlung: Mit Datenschutzanwalt erstellen. Basis: Matrix aus Abschnitt 3 |
| B-2 | **Impressum erstellen** (DDG § 5). Vollständige Anbieterkennzeichnung im Frontend unter `/impressum`                                                                                                                            | S           | Keine technische Abhängigkeit                                              |
| B-3 | **AGB / Nutzungsbedingungen erstellen**. Leistungsbeschreibung, Haftungsausschluss für Beta-Phase, Nutzungsrechte, Kündigung, anwendbares Recht                                                                                 | M           | Empfehlung: Mit Anwalt für IT-Recht erstellen                              |
| B-4 | **AVVs formalisieren und unterzeichnen**. AWS-DPA online akzeptieren, Anthropic-DPA und OpenAI-DPA unterzeichnen, Vercel-DPA akzeptieren                                                                                        | S           | Abhängig von Provider-Prozessen                                            |
| B-5 | **Audit-Trail implementieren** (Finding A09-F01). Datenschutzrelevante Aktionen unveränderlich protokollieren: Consent-Erteilung/-Widerruf, Datenexport, Account-Löschung, Konnektor-Anbindung/-Trennung                        | M           | Backend-Entwicklung                                                        |
| B-6 | **Dependency-Vulnerability-Scanning** (Finding A05-F01). `pip-audit` und `npm audit` in CI integrieren                                                                                                                          | S           | CI/CD-Pipeline                                                             |
| B-7 | **Produktions-Startup-Check für RSA-Keys** (Finding A02-F01). Bei `PWBS_ENV=production` ohne RSA-Keys den Start verweigern, um HS256-Fallback zu verhindern                                                                     | S           | Backend-Entwicklung                                                        |
| B-8 | **CSP-Header implementieren** (Finding A03-F01). `Content-Security-Policy` in `SecurityHeadersMiddleware`                                                                                                                       | S           | Backend-Entwicklung                                                        |

### 🟡 Wichtig (vor Open Beta)

| #    | Beschreibung                                                                                                                                                                                                                                                                                             | Komplexität | Abhängigkeit                              |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------- |
| W-1  | **Formale DSFA durchführen** (Art. 35 DSGVO). Die Vorabeinschätzung in [docs/dsgvo-erstkonzept.md](dsgvo-erstkonzept.md#6-datenschutzfolgenabschaetzung-dsfa---vorabeinschaetzung) bestätigt die Notwendigkeit. Fokus: LLM-Verarbeitung, Knowledge-Graph als Profilbildung, Embedding-Rückschließbarkeit | L           | Datenschutzanwalt + interne Dokumentation |
| W-2  | **VVT erstellen** (Art. 30 DSGVO). Formales Verzeichnis aller Verarbeitungstätigkeiten. Basis: Matrix aus Abschnitt 3, aber im vorgeschriebenen Format                                                                                                                                                   | M           | Keine technische Abhängigkeit             |
| W-3  | **Drittdaten-Strategie klären**. Rechtliche Bewertung: Wie mit E-Mail-Adressen von Meeting-Teilnehmern und Äußerungen Dritter in Zoom-Transkripten umgehen? Optionen: (a) Art. 6 Abs. 1 lit. f, (b) Benachrichtigungspflicht Art. 14, (c) Ausnahme nach Art. 14 Abs. 5                                   | M           | ⚖️ Juristische Prüfung erforderlich       |
| W-4  | **EU-Datenresidenz bei LLM-Providern klären**. Prüfen, ob Anthropic und OpenAI EU-Endpoints anbieten. Falls nicht: SCCs vereinbaren, TIA dokumentieren                                                                                                                                                   | M           | Abhängig von Provider-Angeboten           |
| W-5  | **KI-Kennzeichnung implementieren** (Art. 50 EU AI Act, ab August 2026). Briefings als KI-generiert kennzeichnen                                                                                                                                                                                         | S           | Frontend + Backend                        |
| W-6  | **Consent-Dokumentation erweitern**. `ConnectorConsent`-Tabelle um DSE-Version und Consent-Timestamp erweitern                                                                                                                                                                                           | S           | Backend-Entwicklung + Migration           |
| W-7  | **Docker-Image-Signierung einführen** (Finding A08-F01)                                                                                                                                                                                                                                                  | M           | DevOps/CI                                 |
| W-8  | **CORS-Einschränkung** (Finding A05-F02). `allow_methods` und `allow_headers` auf tatsächlich genutzte Werte beschränken                                                                                                                                                                                 | S           | Backend-Konfiguration                     |
| W-9  | **Sentry-AVV abschließen** (falls Sentry aktiviert wird). DPA, EU-Region, PII-Scrubbing konfigurieren                                                                                                                                                                                                    | S           | Sentry-Einrichtung                        |
| W-10 | **Prozess für Betroffenenanfragen Dritter definieren**. Wie geht PWBS mit Art.-15/17-Anfragen von Personen um, die in Transkripten/Kalendereinträgen eines Nutzers genannt werden?                                                                                                                       | M           | ⚖️ Juristische Prüfung erforderlich       |

### 🟢 Wünschenswert (vor General Availability)

| #   | Beschreibung                                                                                                                                                                  | Komplexität | Abhängigkeit             |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------ |
| G-1 | **DPA-Template für Enterprise** erstellen. PWBS als Auftragsverarbeiter für Unternehmenskunden positionieren                                                                  | L           | Anwalt für IT-Recht      |
| G-2 | **Datenschutzbeauftragten benennen** (prüfen, ob Pflicht ab 20 Mitarbeitern oder bei Kerntätigkeit der umfangreichen Verarbeitung besonderer Kategorien)                      | S           | ⚖️ Juristische Prüfung   |
| G-3 | **MFA implementieren** (aktuell Phase 4 geplant). Erhöht Kontoschutzniveau gemäß Art. 32 DSGVO                                                                                | M           | Backend + Frontend       |
| G-4 | **SSRF-Schutz zentralisieren** (Finding A10-F01). URL-Validierungsfunktion für alle externen HTTP-Clients                                                                     | S           | Backend-Security         |
| G-5 | **Jährliche DSGVO-Schulung durchführen** (in TOM als geplant markiert). Für alle Entwickler mit Zugriff auf Produktionsdaten                                                  | S           | Organisatorisch          |
| G-6 | **Externe Sicherheitsauditierung** beauftragen. Penetration-Test durch unabhängigen Auditor                                                                                   | L           | Budget + Beauftragung    |
| G-7 | **ISO 27001-Zertifizierung evaluieren**. Best Practice für B2B-Kunden. Langfristiges Ziel                                                                                     | L           | Organisatorisch + Budget |
| G-8 | **Embedding-Vektoren rechtlich bewerten lassen**. Abschließende Klärung, ob Embeddings als personenbezogene Daten gelten. Auswirkung auf Verschlüsselungs- und Löschpflichten | M           | ⚖️ Juristische Prüfung   |

---

## Anhang: Referenzen auf Quelldokumente

| Dokument                                                    | Relevanz                                                                                                |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| [docs/dsgvo-erstkonzept.md](dsgvo-erstkonzept.md)           | DSGVO-Artikel-Mapping, 7 Datenverarbeitungskategorien, offene rechtliche Fragen, DSFA-Vorabeinschätzung |
| [docs/encryption-strategy.md](encryption-strategy.md)       | 3-Stufen-Schlüsselhierarchie (CMK→KEK→DEK), akzeptierte Risiken bei Weaviate/Neo4j, Key-Rotation        |
| [legal/tom.md](../legal/tom.md)                             | 10 TOM-Kategorien, Umsetzungsstatus aller technischen und organisatorischen Maßnahmen                   |
| [legal/security-audit.md](../legal/security-audit.md)       | OWASP Top 10 Assessment, 9 Findings (0 kritisch, 2 hoch, 4 mittel, 3 niedrig)                           |
| [legal/avv/avv-aws.md](../legal/avv/avv-aws.md)             | AVV-Entwurf AWS: EU-Datenresidenz, KMS, Löschfristen                                                    |
| [legal/avv/avv-anthropic.md](../legal/avv/avv-anthropic.md) | AVV-Entwurf Anthropic: Zero Data Retention, Safety-Logging, Datenminimierung                            |
| [legal/avv/avv-openai.md](../legal/avv/avv-openai.md)       | AVV-Entwurf OpenAI: Zero Data Retention, Embedding-Verarbeitung, Content-Filter                         |
| [legal/avv/avv-vercel.md](../legal/avv/avv-vercel.md)       | AVV-Entwurf Vercel: EU-Region-Lock, minimaler Datenumfang, Analytics deaktiviert                        |
| [ARCHITECTURE.md](../ARCHITECTURE.md)                       | System-Topologie, Deployment (AWS eu-central-1 + Vercel), Datenflüsse, OAuth-Flows                      |
| [PRD-SPEC.md](../PRD-SPEC.md)                               | MVP-Features, User Personas, Datenschutz-Sensibilität der Zielgruppe                                    |

---

**⚖️ Haftungsausschluss:** Dieses Dokument stellt keine Rechtsberatung dar. Es wurde auf Basis der technischen Dokumentation und öffentlich verfügbarer Rechtsquellen erstellt. Vor Produktiv-Einsatz wird eine Prüfung durch einen auf EU-Datenschutzrecht spezialisierten Anwalt dringend empfohlen. Markierungen mit „⚖️ Juristische Prüfung empfohlen" kennzeichnen Punkte, die ohne rechtsverbindliche Bewertung nicht abschließend beurteilt werden können.
