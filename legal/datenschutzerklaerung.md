# Datenschutzerklärung  PWBS (Persönliches Wissens-Betriebssystem)

**Stand:** 17. März 2026
**Verantwortlicher:** [Name/Firma eintragen]
**Status:** Entwurf  anwaltliche Prüfung empfohlen

> **Hinweis:** Die vollständige, formatierte Version ist im Frontend unter /datenschutz einsehbar.
> Diese Datei dient als Quelldokument für Audits und Versionierung.

---

## 1. Verantwortlicher

[Name und Anschrift des Verantwortlichen eintragen]
E-Mail: kontakt@pwbs.app

---

## 2. Übersicht der Verarbeitung

PWBS verarbeitet persönliche Wissensdaten aus externen Quellen, um kontextbezogene Briefings zu erstellen. Die Verarbeitung erfolgt ausschließlich im Interesse und im Auftrag des Nutzers.

---

## 3. Datenverarbeitungskategorien (gemäß LEGAL_COMPLIANCE §3)

### 3.1 Kalendereinträge (Google Calendar)
- **Datentyp:** Terminbetreff, Beschreibung, Teilnehmer-E-Mails, Ort, Zeitraum
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a DSGVO (Einwilligung via OAuth-Consent)
- **Speicherdauer:** 365 Tage nach Event-Datum
- **Löschung:** Automatisch via `expires_at` + `cleanup_expired`-Job

### 3.2 Notizen (Notion / Obsidian)
- **Datentyp:** Seitentitel, Textinhalte, Metadaten, Tags
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)
- **Speicherdauer:** Solange Konnektor aktiv, max. 365 Tage nach letzter Änderung
- **Löschung:** Bei Konnektor-Trennung oder Account-Löschung

### 3.3 Transkripte (Zoom)
- **Datentyp:** Meeting-Transkripte, Aufnahme-Metadaten
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)
- **Speicherdauer:** 365 Tage nach Meeting-Datum
- **Löschung:** Automatisch via `expires_at`

### 3.4 Embeddings (abgeleitete Vektordaten)
- **Datentyp:** Mathematische Repräsentationen der Inhalte (nicht rückrechenbar)
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a DSGVO (abgeleitet aus Einwilligung zur Quelldatenverarbeitung)
- **Speicherdauer:** Gekoppelt an Quelldokument
- **Löschung:** Kaskadierend bei Quelldokument-Löschung

### 3.5 LLM-generierte Inhalte (Briefings, Suchantworten)
- **Datentyp:** Generierte Briefings, Suchantworten mit Quellenreferenzen
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a DSGVO
- **Speicherdauer:** 90 Tage (konfigurierbar)
- **Besonderheit:** Inputs werden NICHT für LLM-Training verwendet

### 3.6 Knowledge-Graph-Daten (Neo4j)
- **Datentyp:** Extrahierte Entitäten (Personen, Projekte, Entscheidungen) und deren Beziehungen
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a DSGVO
- **Speicherdauer:** Gekoppelt an Quelldokument
- **Löschung:** Kaskadierend mit `owner_id`-Filter

### 3.7 Authentifizierungs- und Session-Daten
- **Datentyp:** E-Mail, Passwort-Hash, JWT-Tokens, OAuth-Tokens (verschlüsselt)
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung)
- **Speicherdauer:** Solange Account aktiv; 30 Tage Soft-Delete nach Löschanfrage
- **Sicherheit:** RS256 JWT-Signatur, AES-256-GCM Token-Verschlüsselung

### 3.8 Audit- und Telemetriedaten
- **Datentyp:** Zugriffslogs, Fehlerprotokolle, Performance-Metriken
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an Sicherheit und Betrieb)
- **Speicherdauer:** 90 Tage
- **Besonderheit:** Pseudonymisierte User-IDs in Sentry (SHA-256 Prefix)

---

## 4. Drittanbieter und Auftragsverarbeiter

| Anbieter  | Zweck                         | Standort     | AVV-Status |
|-----------|-------------------------------|-------------|------------|
| AWS       | Hosting, Datenbanken          | EU (Frankfurt) | Abgeschlossen (DPA) |
| Anthropic | LLM-Verarbeitung (Claude)     | USA (SCCs)  | Abgeschlossen |
| OpenAI    | Fallback-LLM, Embeddings      | USA (SCCs)  | Abgeschlossen |
| Vercel    | Frontend-Hosting              | EU          | Abgeschlossen (DPA) |

Alle US-Anbieter: Angemessenheitsbeschluss bzw. EU-Standardvertragsklauseln (SCCs) gemäß Art. 46 Abs. 2 lit. c DSGVO.

**Datenminimierung bei LLM-Aufrufen:** Es wird nur der für die Anfrage notwendige Kontext übermittelt. Kein Training auf Nutzerdaten.

---

## 5. Betroffenenrechte

Sie haben folgende Rechte bezüglich Ihrer personenbezogenen Daten:

- **Auskunft (Art. 15 DSGVO):** Datenexport via `POST /api/v1/admin/export` (JSON-Format)
- **Berichtigung (Art. 16 DSGVO):** Über Kontoeinstellungen
- **Löschung (Art. 17 DSGVO):** Einzelquellen via Konnektor-Trennung; vollständig via `DELETE /api/v1/admin/account` (30 Tage Soft-Delete, dann kaskadierte Löschung)
- **Einschränkung (Art. 18 DSGVO):** Via Konnektor-Deaktivierung
- **Datenübertragbarkeit (Art. 20 DSGVO):** JSON-Export aller Daten
- **Widerspruch (Art. 21 DSGVO):** Gegen Verarbeitung auf Basis berechtigter Interessen
- **Widerruf der Einwilligung (Art. 7 Abs. 3 DSGVO):** Jederzeit durch Konnektor-Trennung oder Account-Löschung

---

## 6. Technische und organisatorische Maßnahmen (Art. 32 DSGVO)

- Verschlüsselung: TLS 1.2+ (Transport), AES-256-GCM (OAuth-Tokens at rest)
- Zugriffskontrolle: `owner_id`-Filter auf allen Queries (Mandantenisolation)
- Authentifizierung: RS256 JWT mit 15-Min-Access / 30-Tage-Refresh Token-Rotation
- Monitoring: Strukturiertes Logging (JSON), Sentry Error-Tracking mit PII-Scrubbing
- Löschkonzept: `expires_at`-basierte automatische Löschung, CASCADE DELETE

---

## 7. Cookies und Tracking

PWBS verwendet im Standardbetrieb **keine Cookies** für Tracking-Zwecke. Ausschließlich technisch notwendige Session-Daten werden verwendet. Bei Aktivierung von Analytics (PostHog) wird ein Consent-Banner eingeblendet.

---

## 8. Beschwerderecht

Sie haben das Recht, sich bei einer Datenschutz-Aufsichtsbehörde zu beschweren (Art. 77 DSGVO). Die zuständige Aufsichtsbehörde richtet sich nach Ihrem Wohnort bzw. dem Sitz des Verantwortlichen.

---

## Änderungshistorie

| Datum       | Änderung                    |
|-------------|----------------------------|
| 2026-03-17  | Erstfassung (Closed Beta)  |