# DSGVO-Erstkonzept: Persoenliches Wissens-Betriebssystem (PWBS)

**Version:** 1.0
**Datum:** 13. Maerz 2026
**Status:** Entwurf - Erstkonzept vor rechtlicher Pruefung
**Naechster Schritt:** Rechtliche Erstberatung beauftragen (siehe Abschnitt 7)

---

## 1. Zusammenfassung

Das PWBS verarbeitet personenbezogene Daten aus heterogenen Quellen (Kalender, Notizen, Transkripte) eines einzelnen Nutzers, um kontextuelle Briefings und semantische Suche bereitzustellen. Dieses Dokument bildet die relevanten DSGVO-Artikel auf die PWBS-Funktionen ab und identifiziert offene rechtliche Fragen.

**Kernprinzip:** DSGVO by Design - Verschluesselung, Datenminimierung und Loeschbarkeit sind keine Features, sondern Grundstruktur.

---

## 2. DSGVO-Artikel-Mapping auf PWBS-Funktionen

### Art. 5 - Grundsaetze der Verarbeitung

| Grundsatz | PWBS-Umsetzung | Status |
|-----------|---------------|--------|
| **Rechtmaessigkeit (Abs. 1a)** | Verarbeitung auf Basis von Einwilligung (Art. 6 Abs. 1a) oder Vertragserfuellung (Art. 6 Abs. 1b). Pro Datenquelle explizite OAuth-Einwilligung. | Konzept |
| **Zweckbindung (Abs. 1b)** | Nutzerdaten ausschliesslich fuer persoenliche Briefings und Suche des jeweiligen Nutzers. Kein Cross-User-Lernen, kein Training externer Modelle. | Architektur |
| **Datenminimierung (Abs. 1c)** | E-Mail-Body wird nach Chunk-Erstellung nicht im Klartext vorgehalten (nur Chunks + Embeddings). Nur fuer Kernfunktion benoetigte Daten. | Konzept |
| **Richtigkeit (Abs. 1d)** | Cursor-basierte Sync haelt Daten aktuell. Quellsystem ist Single Source of Truth. | Architektur |
| **Speicherbegrenzung (Abs. 1e)** | Jedes Datum hat `expires_at`. Automatische Loeschung abgelaufener Daten via `cleanup_expired`-Job (taeglich 03:00). | Architektur |
| **Integritaet/Vertraulichkeit (Abs. 1f)** | Envelope Encryption (KEK/DEK, AES-256-GCM). TLS 1.3 fuer Transit. Tenant-Isolation in allen Storage-Schichten. | Architektur |

### Art. 6 - Rechtmaessigkeit der Verarbeitung

| Rechtsgrundlage | Anwendungsfall im PWBS |
|----------------|----------------------|
| **Art. 6 Abs. 1a - Einwilligung** | OAuth-Consent bei Verbindung jeder Datenquelle (Google Calendar, Notion, Zoom, Slack). Jederzeit widerrufbar. Widerruf loescht alle Daten dieser Quelle. |
| **Art. 6 Abs. 1b - Vertragserfuellung** | Kernverarbeitung: Ingestion, Embedding-Generierung, Briefing-Erstellung, Suche. Notwendig fuer die vertraglich zugesicherte Dienstleistung. |
| **Art. 6 Abs. 1f - Berechtigtes Interesse** | Audit-Logging, Sicherheitsmonitoring, Fehleranalyse (ohne PII in Logs). |

### Art. 15 - Auskunftsrecht

| Anforderung | PWBS-Umsetzung |
|-------------|---------------|
| Auskunft ueber verarbeitete Daten | `POST /api/v1/admin/export` - generiert vollstaendiges JSON-Exportpaket aller Nutzerdaten |
| Kategorien personenbezogener Daten | Export umfasst: Dokumente, Chunks, Entities, Briefings, Audit-Log, Connection-Metadaten |
| Empfaenger der Daten | Dokumentiert in Datenschutzerklaerung: AWS (Hosting), OpenAI/Anthropic (LLM-Processing), Vercel (Frontend) |
| Speicherdauer | Pro Kategorie definiert (siehe Abschnitt 3) |

### Art. 17 - Recht auf Loeschung

| Anforderung | PWBS-Umsetzung |
|-------------|---------------|
| Loeschung aller personenbezogenen Daten | `DELETE /api/v1/admin/account` - kaskadierte Loeschung |
| PostgreSQL | `CASCADE DELETE` auf alle Tabellen mit `owner_id` FK |
| Weaviate | Tenant-Loeschung (alle Vektoren/Objekte des Nutzers) |
| Neo4j | Loeschung aller Knoten und Kanten mit `owner_id` |
| Redis | Session-Flush fuer den Nutzer |
| Karenzzeit | 30 Tage reversibel (Soft-Delete), danach irreversibel |
| Einzelne Quelle | Widerruf einer Verbindung loescht nur Daten dieser Quelle |

### Art. 20 - Recht auf Datenportabilitaet

| Anforderung | PWBS-Umsetzung |
|-------------|---------------|
| Maschinenlesbares Format | Export als JSON + Markdown |
| Umfang | Alle Rohquellen, extrahierte Entitaeten, generierte Briefings |
| Uebertragbarkeit | Download-Link nach asynchroner Erstellung |

### Art. 25 - Datenschutz durch Technikgestaltung (Privacy by Design)

| Massnahme | Umsetzung |
|-----------|-----------|
| Tenant-Isolation | Jede DB-Query enthaelt `WHERE owner_id = :user_id`. Keine shared Embedding-Spaces. Keine globalen Indizes ueber Nutzergrenzen. |
| Default-Datenschutz | Neue Verbindungen sind inaktiv bis OAuth-Consent erteilt. Minimale Datenerhebung als Standard. |
| `owner_id` auf jedem Datum | Pflichtfeld auf: `UnifiedDocument`, `Chunk`, `Entity`, `Briefing`, `Connection`, `AuditLog` |
| `expires_at` auf jedem Datum | Standardwert abhaengig von Kategorie (siehe Abschnitt 3). Automatische Loeschung. |

### Art. 32 - Sicherheit der Verarbeitung

| Massnahme | Umsetzung |
|-----------|-----------|
| Verschluesselung at rest | Envelope Encryption: KEK (AWS KMS) wraps DEK (pro Nutzer, AES-256-GCM). PostgreSQL-Spalten, OAuth-Tokens einzeln verschluesselt. |
| Verschluesselung in transit | TLS 1.3 fuer alle externen Verbindungen. mTLS zwischen Services (Phase 3). |
| Zugriffskontrolle | JWT-basierte Auth (RS256, 15min Access Token). Rate Limiting auf allen oeffentlichen Endpunkten. |
| Belastbarkeit | Health Checks, Monitoring (Prometheus/Grafana), strukturiertes Logging ohne PII. |
| Wiederherstellbarkeit | Verschluesselte Backups (PostgreSQL, Weaviate, Neo4j). RPO < 1h, RTO < 4h. |
| Regelmaessige Pruefung | Audit-Log (unveraenderlich), automatisierte DSGVO-Compliance-Tests in CI/CD. |

---

## 3. Datenverarbeitungskategorien und Rechtsgrundlagen

### 3.1 Kalendereintraege (Google Calendar)

| Attribut | Wert |
|----------|------|
| **Datenquelle** | Google Calendar API (OAuth2) |
| **Personenbezogene Daten** | Terminbetreff, Beschreibung, Teilnehmer-E-Mails, Ort, Zeitraum |
| **Rechtsgrundlage** | Art. 6 Abs. 1a (Einwilligung via OAuth-Consent) |
| **Verarbeitungszweck** | Meeting-Briefings, Kontextsuche, Tagesplanung |
| **Speicherdauer** | 365 Tage nach Event-Datum, danach automatische Loeschung |
| **Besonderheiten** | Teilnehmer-E-Mails Dritter - kritisch, siehe offene Fragen |

### 3.2 Notizen (Obsidian / Notion)

| Attribut | Wert |
|----------|------|
| **Datenquelle** | Obsidian (lokaler Dateizugriff), Notion API (OAuth2) |
| **Personenbezogene Daten** | Freitext mit potenziell beliebigen PII |
| **Rechtsgrundlage** | Art. 6 Abs. 1b (Vertragserfuellung) |
| **Verarbeitungszweck** | Wissensvernetzung, semantische Suche, Briefings |
| **Speicherdauer** | 730 Tage nach letzter Aktualisierung |
| **Besonderheiten** | Nutzer kontrolliert Inhalt vollstaendig. Keine Filterung des Inhalts. |

### 3.3 Transkripte (Zoom)

| Attribut | Wert |
|----------|------|
| **Datenquelle** | Zoom API (OAuth2) |
| **Personenbezogene Daten** | Gespraechsinhalte, Sprechernamen, Meeting-Metadaten |
| **Rechtsgrundlage** | Art. 6 Abs. 1a (Einwilligung via OAuth-Consent) |
| **Verarbeitungszweck** | Meeting-Nachbereitung, Entscheidungsextraktion, Wissenserhalt |
| **Speicherdauer** | 365 Tage nach Meeting-Datum |
| **Besonderheiten** | Enthaelt Aeusserungen Dritter - Einwilligung aller Teilnehmer erforderlich? (siehe offene Fragen) |

### 3.4 Embeddings (abgeleitete Daten)

| Attribut | Wert |
|----------|------|
| **Datenquelle** | Generiert aus allen Quelldokumenten via OpenAI API |
| **Personenbezogene Daten** | Vektoren sind mathematische Repraesentationen, die theoretisch Rueckschluesse erlauben |
| **Rechtsgrundlage** | Art. 6 Abs. 1b (Vertragserfuellung, technisch notwendig) |
| **Verarbeitungszweck** | Semantische Suche, Aehnlichkeitserkennung |
| **Speicherdauer** | Identisch zum Quelldokument (kaskadierte Loeschung) |
| **Besonderheiten** | An OpenAI API uebertragen zur Generierung - AVV erforderlich. Keine Speicherung bei OpenAI (Zero Data Retention Policy). |

### 3.5 LLM-generierte Inhalte (Briefings, Suchantworten)

| Attribut | Wert |
|----------|------|
| **Datenquelle** | Claude API (Anthropic) / GPT-4 (OpenAI) |
| **Personenbezogene Daten** | Zusammenfassungen die PII aus Quelldokumenten enthalten koennen |
| **Rechtsgrundlage** | Art. 6 Abs. 1b (Vertragserfuellung) |
| **Verarbeitungszweck** | Kontextuelle Briefings, Antwortgenerierung |
| **Speicherdauer** | 90 Tage nach Erstellung (Briefings), Suchantworten werden nicht persistiert |
| **Besonderheiten** | Nutzerkontext wird als Prompt-Bestandteil an LLM-API gesendet. AVV mit Anthropic und OpenAI zwingend. Kein Training mit Nutzerdaten (API Terms bestaetigen). |

### 3.6 Knowledge Graph (Entitaeten, Relationen)

| Attribut | Wert |
|----------|------|
| **Datenquelle** | Extrahiert aus Dokumenten via NER-Pipeline |
| **Personenbezogene Daten** | Personennamen, Projektbezeichnungen, Entscheidungen |
| **Rechtsgrundlage** | Art. 6 Abs. 1b (Vertragserfuellung) |
| **Verarbeitungszweck** | Beziehungsanalyse, Kontextanreicherung, Mustererkennung |
| **Speicherdauer** | Identisch zum Quelldokument (kaskadierte Loeschung via owner_id) |
| **Besonderheiten** | Alle Graph-Queries mit `WHERE n.owner_id = $owner_id`. MERGE statt CREATE (Idempotenz). |

### 3.7 Authentifizierungs- und Verbindungsdaten

| Attribut | Wert |
|----------|------|
| **Datenquelle** | OAuth2-Flows, JWT-System |
| **Personenbezogene Daten** | E-Mail, Name, OAuth-Tokens, Refresh-Tokens |
| **Rechtsgrundlage** | Art. 6 Abs. 1b (Vertragserfuellung) |
| **Verarbeitungszweck** | Authentifizierung, Datenquellen-Anbindung |
| **Speicherdauer** | Access Token: 15min, Refresh Token: 30 Tage, OAuth-Tokens: bis Widerruf |
| **Besonderheiten** | Tokens mit AES-256-GCM verschluesselt in DB. Automatische Rotation. |

---

## 4. Auftragsverarbeitungsvertraege (AVVs)

### 4.1 Erforderliche AVVs

| Dienstleister | Dienst | Datentypen | Status | Prioritaet |
|--------------|--------|-----------|--------|-----------|
| **Amazon Web Services (AWS)** | Hosting (EC2/ECS, RDS, S3) | Alle Nutzerdaten (verschluesselt) | AVV erforderlich | Kritisch |
| **OpenAI** | Embedding-Generierung (text-embedding-3-small), GPT-4 Fallback | Dokumentinhalte (Chunks), Suchqueries | AVV erforderlich | Kritisch |
| **Anthropic** | LLM-Processing (Claude API), primaerer LLM-Provider | Dokumentkontext, Briefing-Prompts | AVV erforderlich | Kritisch |
| **Vercel** | Frontend-Hosting, Edge Functions | Keine Nutzerdaten im Backend-Sinne, aber Browser-Metadaten | AVV erforderlich | Hoch |

### 4.2 AVV-Anforderungen pro Dienstleister

#### AWS

- Standard-AVV (Data Processing Agreement) abschliessen
- Region: `eu-central-1` (Frankfurt) fuer alle Services
- KMS fuer Master-Key-Verwaltung
- Keine automatische Datenweitergabe an Sub-Processors ausserhalb EU
- Backup-Verschluesselung mit separatem Key

#### OpenAI

- API Terms of Use pruefen: Bestaetigung Zero Data Retention
- Klaeren: Werden API-Inputs fuer Modell-Training verwendet? (Stand Maerz 2026: Nein bei API-Nutzung, aber vertragliche Absicherung noetig)
- DPA (Data Processing Agreement) unterzeichnen
- Klaeren: Datenverarbeitung in welcher Region? (ggf. EU-Endpoint verfuegbar?)

#### Anthropic

- API Terms of Use pruefen: Datenspeicherung und -nutzung
- DPA unterzeichnen
- Klaeren: EU-Datenresidenz verfuegbar?
- Safety-Evaluations und Prompt-Logging: Welche Daten werden wie lange gespeichert?

#### Vercel

- DPA abschliessen
- Klaeren: Wo werden Edge Functions ausgefuehrt? (EU-Region erzwingen)
- Keine sensiblen Nutzerdaten im Frontend rendern, die Vercel sehen koennte
- Analytics/Monitoring-Daten: Welche werden erhoben?

### 4.3 Datenresidenz-Anforderungen

| Anforderung | Umsetzung |
|-------------|-----------|
| Primaere Haltung | EU (AWS eu-central-1, Frankfurt) |
| LLM-API-Aufrufe | Pruefen ob EU-Endpoints bei OpenAI/Anthropic verfuegbar. Falls nicht: Risikobewertung und ggf. Standardvertragsklauseln. |
| CDN/Edge | Vercel EU-Region erzwingen |
| Backups | Ausschliesslich in EU-Region (S3 eu-central-1) |

---

## 5. Technische Datenschutzmassnahmen (Privacy by Design)

### 5.1 Datenmodell-Pflichten

Jede persistierte Datenstruktur im PWBS **muss** enthalten:

```python
class AnyPWBSModel(BaseModel):
    owner_id: UUID          # FK auf users.id, CASCADE DELETE
    expires_at: datetime | None  # Automatische Loeschung nach Ablauf
    created_at: datetime
    updated_at: datetime
```

### 5.2 Query-Isolation

```python
# PFLICHT: Jede Datenbankabfrage filtert nach owner_id
# KORREKT:
SELECT * FROM documents WHERE owner_id = :user_id AND ...

# VERBOTEN:
SELECT * FROM documents WHERE ...  # ohne owner_id
```

### 5.3 Logging-Hygiene

- **Erlaubt:** Request-IDs, HTTP-Status, Latenzen, Fehlercodes
- **Verboten:** Dokumentinhalte, Embeddings, Metadaten-Werte, E-Mail-Adressen, OAuth-Tokens
- **Format:** Strukturiertes JSON-Logging

### 5.4 Automatische Datenbereinigung

```
SchedulerAgent Job: cleanup_expired
Cron: 0 3 * * * (taeglich 03:00 Uhr)
Aktion: Loescht alle Datensaetze mit expires_at < NOW()
Umfang: UnifiedDocument, Chunk, Entity, Briefing
Kaskade: Weaviate-Vektoren, Neo4j-Knoten werden mitgeloescht
```

---

## 6. Datenschutzfolgenabschaetzung (DSFA) - Vorabeinschaetzung

### 6.1 Kriterien fuer DSFA-Pflicht (Art. 35)

| Kriterium | Zutrifft? | Begruendung |
|-----------|-----------|-------------|
| Systematische Bewertung persoenlicher Aspekte | Ja | Knowledge Graph analysiert Verhaltensmuster, Entscheidungsmuster, Beziehungen |
| Umfangreiche Verarbeitung besonderer Kategorien | Potenziell | Transkripte koennten Gesundheitsdaten oder politische Meinungen enthalten |
| Systematische Ueberwachung oeffentlich zugaenglicher Bereiche | Nein | Nur private Daten des Nutzers |
| Neue Technologien | Ja | LLM-basierte Analyse persoenlicher Daten, Embedding-basierte Profilbildung |

**Einschaetzung:** Eine DSFA ist wahrscheinlich erforderlich aufgrund der systematischen Analyse persoenlicher Daten mittels KI/LLM-Technologie und der Erstellung von Wissensverknuepfungen.

### 6.2 Risikobewertung

| Risiko | Eintrittswahrscheinlichkeit | Schwere | Massnahme |
|--------|---------------------------|---------|-----------|
| Unbefugter Zugriff auf Nutzerdaten | Mittel | Hoch | Envelope Encryption, JWT-Auth, Rate Limiting |
| Daten-Leak durch LLM-Provider | Niedrig | Hoch | AVVs, Zero Data Retention, kein Modell-Training |
| Unvollstaendige Loeschung | Mittel | Mittel | Kaskadierte Loeschung testen, Audit-Log |
| Re-Identifikation aus Embeddings | Niedrig | Mittel | Tenant-Isolation, keine shared Embedding-Spaces |
| Unberechtigte Cross-User-Suche | Niedrig | Hoch | owner_id-Filter in jeder Query, Integration-Tests |

---

## 7. Offene rechtliche Fragen

Die folgenden Fragen muessen mit einem Datenschutzanwalt geklaert werden:

### Hohe Prioritaet

1. **Drittdaten in Kalendern und Transkripten:** Wenn ein Nutzer Kalendereintraege importiert, die E-Mail-Adressen anderer Personen enthalten, oder Zoom-Transkripte mit Aeusserungen Dritter - welche Einwilligung ist erforderlich? Reicht die Einwilligung des PWBS-Nutzers oder muessen Dritte informiert werden?

2. **LLM-Datenverarbeitung:** Ist die Uebertragung von Nutzerkontext an LLM-APIs (Claude, GPT-4) durch Art. 6 Abs. 1b abgedeckt, oder braucht es eine separate Einwilligung? Wie sind die aktuellen Standardvertragsklauseln bei OpenAI und Anthropic zu bewerten?

3. **Embedding-Vektoren als personenbezogene Daten:** Sind Embedding-Vektoren, die aus personenbezogenen Texten erzeugt wurden, selbst als personenbezogene Daten einzustufen? Das haette Auswirkungen auf Loeschpflichten und Verschluesselungsanforderungen fuer den Vektor-Store.

4. **DSFA-Pflicht:** Ist eine formale Datenschutzfolgenabschaetzung erforderlich? Unsere Vorabeinschaetzung (Abschnitt 6) deutet darauf hin.

### Mittlere Prioritaet

5. **EU-Datenresidenz bei LLM-Calls:** Falls OpenAI/Anthropic keine EU-Endpoints anbieten, reichen Standardvertragsklauseln fuer den Datentransfer in die USA? Status nach Schrems-II-Nachfolger?

6. **Speicherdauer-Defaults:** Sind die vorgeschlagenen Speicherdauern (90 Tage Briefings, 365 Tage Kalender, 730 Tage Notizen) angemessen oder muessen sie kuerzere Fristen haben?

7. **Auftragsverarbeitung vs. gemeinsame Verantwortlichkeit:** Ist das Verhaeltnis zu OpenAI/Anthropic korrekt als Auftragsverarbeitung klassifiziert, oder liegt ggf. eine gemeinsame Verantwortlichkeit vor?

### Niedrige Prioritaet

8. **Datenschutzerklaerung:** Welche Informationspflichten bestehen (Art. 13/14)? Template fuer Datenschutzerklaerung erstellen lassen.

9. **Verzeichnis von Verarbeitungstaetigkeiten:** Formales VVT gemaess Art. 30 erstellen.

10. **Datenschutzbeauftragter:** Ab welchem Nutzungsumfang ist ein DSB erforderlich?

---

## 8. Naechste Schritte

| # | Aktion | Prioritaet | Verantwortlich |
|---|--------|-----------|----------------|
| 1 | Rechtliche Erstberatung mit Datenschutzanwalt | Kritisch | Projektleitung |
| 2 | AVV mit AWS abschliessen | Kritisch | Projektleitung |
| 3 | DPA mit OpenAI und Anthropic pruefen/abschliessen | Kritisch | Projektleitung |
| 4 | DPA mit Vercel abschliessen | Hoch | Projektleitung |
| 5 | Formale DSFA durchfuehren (falls bestaetigt) | Hoch | +Datenschutzanwalt |
| 6 | Verschluesselungsstrategie detaillieren (TASK-004) | Hoch | ORCH-A |
| 7 | Datenschutzerklaerung erstellen | Mittel | +Datenschutzanwalt |
| 8 | VVT erstellen | Mittel | Projektleitung |

---

## Referenzen

- ARCHITECTURE.md, Abschnitt 5 (Datenschutz & Sicherheit)
- PRD-SPEC.md, NF-017 bis NF-021 (Datenschutz-Anforderungen)
- EU-DSGVO (Verordnung 2016/679)
- Schrems-II-Folgeregulierung (EU-US Data Privacy Framework)
