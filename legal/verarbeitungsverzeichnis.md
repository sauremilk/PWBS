# Verzeichnis von Verarbeitungstätigkeiten (Art. 30 DSGVO)

**Verantwortlicher:** PWBS – Persönliches Wissens-Betriebssystem
**Version:** 1.0
**Datum:** 14. März 2026
**Datenschutzbeauftragter:** [Name des DSB einsetzen]
**Nächste Überprüfung:** 14. September 2026

---

## VT-001: Nutzer-Authentifizierung und Account-Verwaltung

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | Registrierung, Anmeldung und Verwaltung von Nutzerkonten |
| **Zweck** | Authentifizierung und Autorisierung der Nutzer, Bereitstellung des Dienstes |
| **Rechtsgrundlage** | Art. 6 Abs. 1b DSGVO (Vertragserfüllung) |
| **Kategorien betroffener Personen** | Registrierte Nutzer des PWBS |
| **Kategorien personenbezogener Daten** | E-Mail-Adresse, Name, Passwort-Hash (Argon2id), JWT-Tokens |
| **Empfänger** | Keine Weitergabe an Dritte |
| **Drittlandtransfer** | Nein (AWS eu-central-1) |
| **Speicherdauer** | Bis zur Kontolöschung + 30 Tage Karenzzeit |
| **Technische Maßnahmen** | RS256-JWT, Argon2id-Hashing, Rate Limiting, Audit-Logging |
| **System** | PostgreSQL (users-Tabelle), Redis (Sessions) |

---

## VT-002: Kalenderanbindung (Google Calendar)

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | Import und Verarbeitung von Kalendereinträgen via Google Calendar API |
| **Zweck** | Kontextuelle Meeting-Briefings, Tagesplanung, Wissensvernetzung |
| **Rechtsgrundlage** | Art. 6 Abs. 1a DSGVO (Einwilligung via OAuth-Consent) |
| **Kategorien betroffener Personen** | PWBS-Nutzer, Meeting-Teilnehmer (Dritte) |
| **Kategorien personenbezogener Daten** | Terminbetreff, Beschreibung, Teilnehmer-E-Mails, Ort, Zeitraum |
| **Empfänger** | AWS (Hosting), Anthropic/OpenAI (LLM-Verarbeitung für Briefings) |
| **Drittlandtransfer** | Ja – LLM-API-Aufrufe an Anthropic (US) / OpenAI (US). Abgesichert über AVV + SCCs |
| **Speicherdauer** | 365 Tage nach Event-Datum, dann automatische Löschung |
| **Technische Maßnahmen** | OAuth2-Consent, Cursor-basierter Sync, owner_id-Isolation, Encryption at Rest |
| **System** | PostgreSQL (documents), Weaviate (Embeddings), Neo4j (Entitäten) |

---

## VT-003: Notizen-Integration (Notion / Obsidian)

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | Import und Verarbeitung von Notizen aus Notion und Obsidian |
| **Zweck** | Wissensvernetzung, semantische Suche, Briefing-Generierung |
| **Rechtsgrundlage** | Art. 6 Abs. 1b DSGVO (Vertragserfüllung) |
| **Kategorien betroffener Personen** | PWBS-Nutzer |
| **Kategorien personenbezogener Daten** | Freitext-Notizen (potenziell beliebige PII), Metadaten |
| **Empfänger** | AWS (Hosting), Anthropic/OpenAI (LLM-Verarbeitung) |
| **Drittlandtransfer** | Ja – LLM-API-Aufrufe an Anthropic/OpenAI (US). Abgesichert über AVV + SCCs |
| **Speicherdauer** | 730 Tage nach letzter Aktualisierung |
| **Technische Maßnahmen** | OAuth2 (Notion) / lokaler Dateizugriff (Obsidian), owner_id-Isolation |
| **System** | PostgreSQL (documents, chunks), Weaviate, Neo4j |

---

## VT-004: Messaging-Integration (Slack)

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | Import und Verarbeitung von Slack-Nachrichten und Channel-Historien |
| **Zweck** | Wissensvernetzung, Kontextsuche, Briefing-Generierung |
| **Rechtsgrundlage** | Art. 6 Abs. 1a DSGVO (Einwilligung via OAuth-Consent) |
| **Kategorien betroffener Personen** | PWBS-Nutzer, Slack-Channel-Teilnehmer (Dritte) |
| **Kategorien personenbezogener Daten** | Nachrichteninhalte, Benutzernamen, Channel-Metadaten, Timestamps |
| **Empfänger** | AWS (Hosting), Anthropic/OpenAI (LLM-Verarbeitung) |
| **Drittlandtransfer** | Ja – LLM-API-Aufrufe an Anthropic/OpenAI (US). Abgesichert über AVV + SCCs |
| **Speicherdauer** | 365 Tage nach Nachrichtendatum |
| **Technische Maßnahmen** | OAuth2 V2, HMAC-SHA256-Signaturvalidierung, owner_id-Isolation |
| **System** | PostgreSQL (documents, chunks), Weaviate, Neo4j |

---

## VT-005: E-Mail-Integration (Gmail)

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | Import und Verarbeitung von E-Mails via Gmail API |
| **Zweck** | Wissensvernetzung, Kontextsuche |
| **Rechtsgrundlage** | Art. 6 Abs. 1a DSGVO (Einwilligung via OAuth-Consent) |
| **Kategorien betroffener Personen** | PWBS-Nutzer, E-Mail-Korrespondenzpartner (Dritte) |
| **Kategorien personenbezogener Daten** | E-Mail-Betreff, Body, Absender/Empfänger, Zeitstempel |
| **Empfänger** | AWS (Hosting), Anthropic/OpenAI (LLM-Verarbeitung) |
| **Drittlandtransfer** | Ja – LLM-API-Aufrufe an Anthropic/OpenAI (US). Abgesichert über AVV + SCCs |
| **Speicherdauer** | 365 Tage nach E-Mail-Datum |
| **Technische Maßnahmen** | OAuth2, historyId-basierter Cursor, Pub/Sub-Webhook-Validierung |
| **System** | PostgreSQL (documents, chunks), Weaviate, Neo4j |

---

## VT-006: Meeting-Transkripte (Zoom)

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | Import und Verarbeitung von Zoom-Meeting-Transkripten |
| **Zweck** | Meeting-Nachbereitung, Entscheidungsextraktion, Wissenserhalt |
| **Rechtsgrundlage** | Art. 6 Abs. 1a DSGVO (Einwilligung via OAuth-Consent) |
| **Kategorien betroffener Personen** | PWBS-Nutzer, Meeting-Teilnehmer (Dritte) |
| **Kategorien personenbezogener Daten** | Gesprächsinhalte, Sprechernamen, Meeting-Metadaten |
| **Empfänger** | AWS (Hosting), Anthropic/OpenAI (LLM-Verarbeitung) |
| **Drittlandtransfer** | Ja – LLM-API-Aufrufe an Anthropic/OpenAI (US). Abgesichert über AVV + SCCs |
| **Speicherdauer** | 365 Tage nach Meeting-Datum |
| **Technische Maßnahmen** | OAuth2, Cursor-basierter Sync, owner_id-Isolation |
| **System** | PostgreSQL (documents, chunks), Weaviate, Neo4j |

---

## VT-007: Embedding-Generierung

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | Generierung semantischer Vektoren (Embeddings) aus Dokumenten-Chunks |
| **Zweck** | Semantische Suche, Ähnlichkeitserkennung, Briefing-Kontextfindung |
| **Rechtsgrundlage** | Art. 6 Abs. 1b DSGVO (Vertragserfüllung, technisch notwendig) |
| **Kategorien betroffener Personen** | PWBS-Nutzer |
| **Kategorien personenbezogener Daten** | Text-Chunks (enthalten potenziell PII aus Quelldokumenten) |
| **Empfänger** | OpenAI (Embedding-API), AWS (Weaviate-Speicherung) |
| **Drittlandtransfer** | Ja – OpenAI API (US). Zero Data Retention bestätigt. AVV + SCCs |
| **Speicherdauer** | Identisch zum Quelldokument (kaskadierte Löschung) |
| **Technische Maßnahmen** | Batch-Verarbeitung, owner_id-Isolation in Weaviate, Fallback auf lokale Modelle |
| **System** | Weaviate (Vektorspeicher) |

---

## VT-008: Briefing-Generierung (LLM)

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | Generierung kontextueller Briefings via LLM (Morning, Meeting, Weekly) |
| **Zweck** | Persönliche Wissensaufbereitung, Entscheidungsunterstützung |
| **Rechtsgrundlage** | Art. 6 Abs. 1b DSGVO (Vertragserfüllung) |
| **Kategorien betroffener Personen** | PWBS-Nutzer |
| **Kategorien personenbezogener Daten** | Dokumentkontext (Chunks), Kalendereinträge, Entitäten als Prompt-Bestandteile |
| **Empfänger** | Anthropic (primär), OpenAI (Fallback) |
| **Drittlandtransfer** | Ja – LLM-APIs (US). Zero Data Retention. AVV + SCCs |
| **Speicherdauer** | Morning: 24h, Meeting: 48h, Weekly: 7 Tage |
| **Technische Maßnahmen** | Quellenreferenzen in jedem Briefing, Grounding-Validierung, owner_id-Isolation |
| **System** | PostgreSQL (briefings), LLM-APIs |

---

## VT-009: Knowledge Graph (Entitäts-/Beziehungsextraktion)

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | NER-Extraktion und Beziehungsmodellierung in Neo4j |
| **Zweck** | Beziehungsanalyse, Kontextanreicherung, Mustererkennung |
| **Rechtsgrundlage** | Art. 6 Abs. 1b DSGVO (Vertragserfüllung) |
| **Kategorien betroffener Personen** | PWBS-Nutzer, in Dokumenten genannte Personen (Dritte) |
| **Kategorien personenbezogener Daten** | Personennamen, Projektbezeichnungen, Entscheidungen, Beziehungen |
| **Empfänger** | Keine Weitergabe (lokale Neo4j-Instanz auf AWS) |
| **Drittlandtransfer** | Nein |
| **Speicherdauer** | Identisch zum Quelldokument (kaskadierte Löschung via owner_id) |
| **Technische Maßnahmen** | owner_id-Filter auf allen Cypher-Queries, MERGE statt CREATE |
| **System** | Neo4j (Knowledge Graph) |

---

## VT-010: Audit-Logging und Sicherheitsmonitoring

| Feld | Beschreibung |
|------|-------------|
| **Verarbeitungstätigkeit** | Protokollierung datenschutzrelevanter Aktionen |
| **Zweck** | Nachvollziehbarkeit, Sicherheitsmonitoring, Compliance-Nachweis |
| **Rechtsgrundlage** | Art. 6 Abs. 1f DSGVO (berechtigtes Interesse) |
| **Kategorien betroffener Personen** | PWBS-Nutzer |
| **Kategorien personenbezogener Daten** | user_id, Aktionstyp, Ressource-IDs (keine Inhalte), IP-Adressen, Zeitstempel |
| **Empfänger** | Keine Weitergabe |
| **Drittlandtransfer** | Nein |
| **Speicherdauer** | 365 Tage (gesetzliche Aufbewahrungspflicht) |
| **Technische Maßnahmen** | Unveränderlicher audit_log (append-only), keine PII in Log-Inhalten |
| **System** | PostgreSQL (audit_log) |

---

## Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 14.03.2026 | Erstversion mit 10 Verarbeitungstätigkeiten (TASK-147) |
