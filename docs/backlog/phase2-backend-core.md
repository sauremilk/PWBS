# PWBS – Backlog Teil 2: Konnektoren, Processing, LLM & Briefing

---

## Konnektoren – Basisinfrastruktur

#### TASK-041: BaseConnector ABC mit fetch/normalize/get_cursor Interface implementieren

| Feld             | Wert                                                       |
| ---------------- | ---------------------------------------------------------- |
| **Priorität**    | P0                                                         |
| **Bereich**      | Backend                                                    |
| **Aufwand**      | M                                                          |
| **Status**       | 🔴 Offen                                                   |
| **Quelle**       | D1 Abschnitt 3.1 (BaseConnector-Interface), D4 F-004–F-007 |
| **Abhängig von** | Pydantic-Modelle (Agent 1)                                 |
| **Blockiert**    | TASK-045, TASK-049, TASK-053, TASK-057                     |

**Beschreibung:** Abstrakte Basisklasse `BaseConnector` im Modul `pwbs/connectors/base.py` implementieren. Definiert das Interface mit den Methoden `authenticate()`, `fetch_incremental(watermark)`, `normalize(raw) → UnifiedDocument` und `source_type()`. Enthält gemeinsame Logik für Exponential Backoff bei Rate-Limit-Fehlern (429, 503) und partielle Batch-Verarbeitung (max. 100 Dokumente pro Run).

**Acceptance Criteria:**

- [ ] `BaseConnector` ist eine abstrakte Klasse mit `@abstractmethod` für `authenticate`, `fetch_incremental`, `normalize` und `source_type`
- [ ] Gemeinsame Retry-Logik mit Exponential Backoff (3 Retries: 1 min → 5 min → 25 min) ist in der Basisklasse implementiert
- [ ] Partielle Erfolge werden unterstützt – ein fehlgeschlagenes Dokument bricht nicht den gesamten Batch ab
- [ ] Vollständige Type Annotations, keine `Any`-Typen

**Technische Hinweise:** Das `BaseConnector`-Interface folgt exakt dem Schema aus D1 Abschnitt 3.1. Alle Konnektoren erben von dieser Klasse. Die max. Batch-Größe von 100 Dokumenten pro Run ist als Klassenkonstante konfigurierbar.

---

#### TASK-042: ConnectorRegistry mit Registrierung, Lookup und Health-Check implementieren

| Feld             | Wert                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                        |
| **Bereich**      | Backend                                                                   |
| **Aufwand**      | S                                                                         |
| **Status**       | 🔴 Offen                                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (Connector Registry), D1 Abschnitt 2.1 (Ingestion Layer) |
| **Abhängig von** | TASK-041                                                                  |
| **Blockiert**    | TASK-045, TASK-049, TASK-053, TASK-057                                    |

**Beschreibung:** `ConnectorRegistry` im Modul `pwbs/connectors/registry.py` implementieren. Sie verwaltet alle registrierten Konnektoren, ermöglicht Lookup nach `SourceType`, und bietet einen Health-Check-Mechanismus, der den Status jedes registrierten Konnektors abfragt (active, paused, error, revoked).

**Acceptance Criteria:**

- [ ] Konnektoren können per `register(connector_class)` registriert und per `get(source_type)` abgefragt werden
- [ ] `health_check()` gibt pro registriertem Konnektor den Status zurück (active/paused/error/revoked)
- [ ] Doppelte Registrierung desselben `SourceType` wirft einen `ConnectorError`
- [ ] Liste aller verfügbaren Konnektoren abrufbar

**Technische Hinweise:** Im MVP läuft die Registry in-process. Die Statuswerte korrespondieren mit der `connections`-Tabelle aus D1 Abschnitt 3.3.1.

---

#### TASK-043: OAuth Token Manager mit verschlüsselter Persistierung implementieren

| Feld             | Wert                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                        |
| **Bereich**      | Backend                                                                   |
| **Aufwand**      | M                                                                         |
| **Status**       | 🔴 Offen                                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (OAuth-Flow), D4 F-010 (OAuth-Token-Rotation), D4 NF-016 |
| **Abhängig von** | DB-Schema (Agent 1)                                                       |
| **Blockiert**    | TASK-045, TASK-049, TASK-057                                              |

**Beschreibung:** `OAuthTokenManager` im Modul `pwbs/connectors/oauth.py` implementieren. Verantwortlich für die verschlüsselte Speicherung von OAuth-Tokens (Access + Refresh) in der `connections`-Tabelle, automatische Token-Rotation bei Ablauf und Refresh-Token-Erneuerung. Tokens werden doppelt verschlüsselt: DB-Level + App-Level mit User-DEK via Fernet.

**Acceptance Criteria:**

- [ ] Tokens werden mit User-DEK via Fernet verschlüsselt in der `credentials_enc`-Spalte gespeichert
- [ ] Automatischer Refresh bei abgelaufenem Access-Token vor jedem API-Call
- [ ] Bei Refresh wird ein neues Refresh-Token ausgestellt und das alte invalidiert (Token Rotation)
- [ ] Bei fehlgeschlagenem Refresh wird der Konnektor-Status auf `error` gesetzt
- [ ] Keine Secrets im Klartext in Logs oder Fehlermeldungen

**Technische Hinweise:** Doppelte Verschlüsselung gemäß D4 NF-016: DB-Encryption + App-Level Fernet mit user-spezifischem DEK. Der DEK wird über den `encryption_key_enc` aus der `users`-Tabelle (D1 Abschnitt 3.3.1) abgeleitet.

---

#### TASK-044: UnifiedDocument-Normalizer-Basislogik und Content-Hashing implementieren

| Feld             | Wert                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                        |
| **Bereich**      | Backend                                                                   |
| **Aufwand**      | S                                                                         |
| **Status**       | 🔴 Offen                                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (Unified Document Format), D1 Abschnitt 1.2 (Idempotenz) |
| **Abhängig von** | Pydantic-Modelle (Agent 1), TASK-041                                      |
| **Blockiert**    | TASK-046, TASK-050, TASK-054, TASK-058                                    |

**Beschreibung:** Gemeinsame Normalizer-Logik implementieren, die von allen Konnektoren genutzt wird: SHA-256 Content-Hashing für Deduplizierung (`raw_hash`/`content_hash`), Sprach-Erkennung (`language`), Participants-Extraktion und Metadaten-Validierung. Idempotenz-Prüfung: Dokumente mit identischem `content_hash` werden nicht erneut verarbeitet.

**Acceptance Criteria:**

- [ ] SHA-256-Hash wird aus dem normalisierten Content berechnet und als `content_hash` gespeichert
- [ ] Duplikaterkennung: Existierender `content_hash` für gleichen `user_id + source_type + source_id` verhindert Neuverarbeitung
- [ ] Spracherkennung liefert ISO 639-1 Code (de, en)
- [ ] Metadaten-Schema-Validierung via Pydantic

**Technische Hinweise:** Das UDF-Schema folgt exakt D1 Abschnitt 3.1. Die Deduplizierung nutzt den UNIQUE-Constraint `(user_id, source_type, source_id)` aus dem DB-Schema (D1 Abschnitt 3.3.1).

---

## Konnektoren – Google Calendar

#### TASK-045: Google Calendar OAuth2-Flow implementieren

| Feld             | Wert                                                                             |
| ---------------- | -------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                               |
| **Bereich**      | Backend                                                                          |
| **Aufwand**      | M                                                                                |
| **Status**       | 🔴 Offen                                                                         |
| **Quelle**       | D1 Abschnitt 3.1 (OAuth-Flow-Diagramm, Konnektoren-Tabelle), D4 US-1.2, D4 F-004 |
| **Abhängig von** | TASK-041, TASK-042, TASK-043                                                     |
| **Blockiert**    | TASK-046                                                                         |

**Beschreibung:** Google Calendar Konnektor (`pwbs/connectors/google_calendar.py`) mit vollständigem OAuth2-Flow implementieren. Scope: `calendar.events.readonly`. Auth-URL-Generierung, Callback-Verarbeitung (Code → Token-Exchange), verschlüsselte Token-Speicherung via `OAuthTokenManager`. Bei abgelehntem Consent oder abgebrochenem Flow wird ein aussagekräftiger Fehler zurückgegeben.

**Acceptance Criteria:**

- [ ] OAuth2-Auth-URL wird mit Scope `calendar.events.readonly` generiert
- [ ] Callback verarbeitet den Authorization Code und tauscht ihn gegen Access+Refresh Token
- [ ] Tokens werden verschlüsselt in der `connections`-Tabelle persistiert
- [ ] Fehlgeschlagener oder abgebrochener OAuth-Flow wird sauber behandelt (kein hängender Zustand)
- [ ] Connection-Status wird auf `active` gesetzt nach erfolgreichem Flow

**Technische Hinweise:** Flow folgt dem OAuth-Sequenzdiagramm aus D1 Abschnitt 3.1. Google API Client Library verwenden. Redirect-URI muss konfigurierbar sein.

---

#### TASK-046: Google Calendar Sync-Logik mit Webhook + Polling-Fallback implementieren

| Feld             | Wert                                                                     |
| ---------------- | ------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                       |
| **Bereich**      | Backend                                                                  |
| **Aufwand**      | L                                                                        |
| **Status**       | 🔴 Offen                                                                 |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle: Webhook + Polling 15 min), D4 F-004 |
| **Abhängig von** | TASK-045, TASK-044                                                       |
| **Blockiert**    | TASK-047                                                                 |

**Beschreibung:** Sync-Logik für den Google Calendar Konnektor implementieren. Primär: Webhook-basierte Push Notifications von der Google Calendar API. Fallback: Polling alle 15 Minuten via `fetch_incremental(watermark)`. Initialer Full-Sync aller Kalendereinträge beim ersten Verbinden. Inkrementeller Sync basierend auf `syncToken`/`updatedMin` als Watermark. Cursor wird nach jedem erfolgreichen Batch persistiert.

**Acceptance Criteria:**

- [ ] Initialer Full-Sync importiert alle Kalendereinträge (paginiert)
- [ ] Inkrementeller Sync nutzt `syncToken` oder `updatedMin` als Watermark
- [ ] Webhook-Empfang für Google Calendar Push Notifications implementiert
- [ ] Polling-Fallback alle 15 Minuten greift automatisch, wenn Webhook nicht verfügbar
- [ ] Watermark wird nach jedem erfolgreichen Batch in der `connections`-Tabelle persistiert

**Technische Hinweise:** Google Calendar API nutzt `syncToken` für inkrementelle Sync. Webhook erfordert einen öffentlichen Endpunkt; im lokalen Dev-Modus wird nur Polling verwendet. Batch-Größe max. 100 Events.

---

#### TASK-047: Google Calendar Normalizer (Events → UnifiedDocument) implementieren

| Feld             | Wert                                                                        |
| ---------------- | --------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                          |
| **Bereich**      | Backend                                                                     |
| **Aufwand**      | M                                                                           |
| **Status**       | 🔴 Offen                                                                    |
| **Quelle**       | D1 Abschnitt 3.1 (Datentypen: Events, Teilnehmer, Beschreibungen), D4 F-004 |
| **Abhängig von** | TASK-046, TASK-044                                                          |
| **Blockiert**    | –                                                                           |

**Beschreibung:** Normalizer für Google Calendar Events, der Rohdaten ins UnifiedDocument Format konvertiert. Extrahiert: Event-Titel, Beschreibung, Teilnehmer (E-Mail + Name), Start-/Endzeit, Wiederholungsregeln, Ort. Teilnehmer werden in das `participants`-Feld und in source-spezifische `metadata` geschrieben. Ganztägige Events und wiederkehrende Events werden korrekt behandelt.

**Acceptance Criteria:**

- [ ] Events werden in UnifiedDocument normalisiert mit Titel, Content (Beschreibung), Participants und Metadaten
- [ ] Teilnehmer werden als `list[str]` (E-Mail oder Name) in das `participants`-Feld extrahiert
- [ ] Ganztägige Events, wiederkehrende Events und Events ohne Beschreibung werden korrekt verarbeitet
- [ ] `source_type` ist `GOOGLE_CALENDAR`, `source_id` ist die Google Event-ID
- [ ] Content-Hash wird berechnet für Deduplizierung

**Technische Hinweise:** Metadaten enthalten mindestens: `start_time`, `end_time`, `location`, `is_recurring`, `attendee_count`. Das Format folgt dem UDF aus D1 Abschnitt 3.1.

---

## Konnektoren – Notion

#### TASK-048: Notion OAuth2-Flow implementieren

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P0                                                        |
| **Bereich**      | Backend                                                   |
| **Aufwand**      | M                                                         |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle), D4 US-1.3, D4 F-005 |
| **Abhängig von** | TASK-041, TASK-042, TASK-043                              |
| **Blockiert**    | TASK-049                                                  |

**Beschreibung:** Notion Integration Konnektor (`pwbs/connectors/notion.py`) mit OAuth2-Flow implementieren. Nutzt die Notion Public Integration OAuth. Callback verarbeitet den Authorization Code, tauscht ihn gegen Access Token (Notion verwendet kein Refresh-Token-Paar, sondern einen dauerhaften Access Token) und speichert diesen verschlüsselt. Nach erfolgreichem Consent werden die freigegebenen Seiten und Datenbanken als Sync-Scope angezeigt.

**Acceptance Criteria:**

- [ ] OAuth2-Auth-URL wird für Notion Public Integration generiert
- [ ] Callback tauscht Authorization Code gegen Access Token
- [ ] Token wird verschlüsselt in der `connections`-Tabelle persistiert
- [ ] Freigegebene Seiten/Datenbanken werden nach Verbindung aufgelistet
- [ ] Connection-Status wird auf `active` gesetzt

**Technische Hinweise:** Notion OAuth unterscheidet sich von Google: Es gibt keinen Refresh-Token. Der Access Token bleibt gültig, bis der Nutzer die Integration widerruft. Notion API Client nutzen.

---

#### TASK-049: Notion Polling-Sync mit last_edited_time-Cursor implementieren

| Feld             | Wert                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                      |
| **Bereich**      | Backend                                                                                 |
| **Aufwand**      | M                                                                                       |
| **Status**       | 🔴 Offen                                                                                |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle: Polling 10 min, last_edited_time-Cursor), D4 F-005 |
| **Abhängig von** | TASK-048, TASK-044                                                                      |
| **Blockiert**    | TASK-050                                                                                |

**Beschreibung:** Polling-basierte Sync-Logik für den Notion Konnektor. Polling-Intervall: alle 10 Minuten. Verwendet `last_edited_time` als Cursor/Watermark für inkrementelle Syncs. Initialer Full-Sync beim ersten Verbinden holt alle freigegebenen Seiten und Datenbanken. Paginierung über Notion API `start_cursor`.

**Acceptance Criteria:**

- [ ] Initialer Full-Sync importiert alle freigegebenen Seiten und Datenbanken (paginiert)
- [ ] Inkrementeller Sync nutzt `last_edited_time` als Watermark und holt nur geänderte Seiten
- [ ] Polling-Intervall beträgt 10 Minuten
- [ ] Cursor/Watermark wird nach jedem erfolgreichen Batch persistiert
- [ ] Gelöschte Notion-Seiten werden erkannt und im System als gelöscht markiert

**Technische Hinweise:** Notion API `POST /search` mit `filter.timestamp = last_edited_time` und `sort.direction = ascending`. Paginierung über `start_cursor` und `has_more`.

---

#### TASK-050: Notion Normalizer (Pages, Databases, Blöcke → UnifiedDocument) implementieren

| Feld             | Wert                                                              |
| ---------------- | ----------------------------------------------------------------- |
| **Priorität**    | P0                                                                |
| **Bereich**      | Backend                                                           |
| **Aufwand**      | L                                                                 |
| **Status**       | 🔴 Offen                                                          |
| **Quelle**       | D1 Abschnitt 3.1 (Datentypen: Pages, Databases, Blöcke), D4 F-005 |
| **Abhängig von** | TASK-049, TASK-044                                                |
| **Blockiert**    | –                                                                 |

**Beschreibung:** Normalizer für Notion-Inhalte, der Pages, Database-Einträge und deren Blöcke ins UnifiedDocument Format konvertiert. Notion-Blöcke (Paragraphs, Headings, Lists, Code, Toggle, Callout etc.) werden rekursiv aufgelöst und in Plaintext/Markdown konvertiert. Page-Properties (Titel, Tags, Daten) werden als Metadaten extrahiert. Verschachtelte Blöcke (Children) werden rekursiv verarbeitet.

**Acceptance Criteria:**

- [ ] Notion Pages werden mit Titel, extrahiertem Textinhalt aus allen Blöcken und Properties normalisiert
- [ ] Block-Typen (paragraph, heading_1/2/3, bulleted_list_item, numbered_list_item, code, toggle, callout) werden in Markdown konvertiert
- [ ] Verschachtelte Blöcke (children) werden rekursiv aufgelöst
- [ ] Database-Einträge werden als individuelle UnifiedDocuments normalisiert
- [ ] Notion-interne Links (@-Mentions, Page-Links) werden als Metadaten extrahiert

**Technische Hinweise:** Notion API `GET /blocks/{block_id}/children` für rekursive Block-Auflösung. Tiefe der Rekursion auf max. 5 Ebenen begrenzen. `content_type` ist `MARKDOWN`.

---

## Konnektoren – Obsidian

#### TASK-051: Obsidian Vault File-System-Watcher implementieren

| Feld             | Wert                                                                                        |
| ---------------- | ------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                          |
| **Bereich**      | Backend                                                                                     |
| **Aufwand**      | M                                                                                           |
| **Status**       | 🔴 Offen                                                                                    |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle: File-System-Watcher via watchdog), D4 US-1.4, D4 F-006 |
| **Abhängig von** | TASK-041, TASK-042                                                                          |
| **Blockiert**    | TASK-052                                                                                    |

**Beschreibung:** Obsidian Vault Konnektor (`pwbs/connectors/obsidian.py`) mit File-System-Watcher via `watchdog`-Library implementieren. Kein OAuth erforderlich – der Nutzer gibt einen lokalen Vault-Pfad an. Initialer Full-Scan aller `.md`-Dateien im Vault. Danach überwacht der Watcher Datei-Änderungen (create, modify, delete) und triggert inkrementelle Verarbeitung. Pfad-Validierung: Prüfung ob der Pfad existiert und Markdown-Dateien enthält.

**Acceptance Criteria:**

- [ ] Nutzer kann einen lokalen Vault-Pfad konfigurieren
- [ ] Pfad-Validierung: Existenz prüfen, mindestens eine `.md`-Datei vorhanden
- [ ] Initialer Full-Scan importiert alle `.md`-Dateien rekursiv
- [ ] File-System-Watcher erkennt create, modify und delete von `.md`-Dateien
- [ ] Gelöschte Dateien werden im System als gelöscht markiert

**Technische Hinweise:** `watchdog`-Library für plattformübergreifendes File-System-Monitoring. `.obsidian/`-Ordner und andere Konfigurationsverzeichnisse vom Scan ausschließen. Watcher läuft als Background-Task im FastAPI-Prozess.

---

#### TASK-052: Obsidian Markdown-Parser mit Frontmatter- und Link-Extraktion implementieren

| Feld             | Wert                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                    |
| **Bereich**      | Backend                                                                               |
| **Aufwand**      | M                                                                                     |
| **Status**       | 🔴 Offen                                                                              |
| **Quelle**       | D1 Abschnitt 3.1 (Datentypen: Markdown-Dateien, Frontmatter, interne Links), D4 F-006 |
| **Abhängig von** | TASK-051, TASK-044                                                                    |
| **Blockiert**    | –                                                                                     |

**Beschreibung:** Markdown-Parser für Obsidian-Dateien, der YAML-Frontmatter, Wikilinks (`[[...]]`), Tags (`#tag`), und Standard-Markdown-Strukturen extrahiert. Frontmatter-Felder (titel, tags, aliases, date) werden als Metadaten in das UnifiedDocument übernommen. Interne Links werden als Beziehungen in den Metadaten gespeichert (für spätere Graph-Verknüpfung). Content wird als Markdown normalisiert.

**Acceptance Criteria:**

- [ ] YAML-Frontmatter wird geparst und als `metadata`-Dict extrahiert
- [ ] Wikilinks `[[Page Name]]` und `[[Page Name|Display Text]]` werden erkannt und in Metadaten gespeichert
- [ ] Tags `#tag` und verschachtelte Tags `#parent/child` werden extrahiert
- [ ] `source_type` ist `OBSIDIAN`, `source_id` ist der relative Dateipfad im Vault
- [ ] Content wird als Markdown normalisiert, Frontmatter wird nicht in den Content aufgenommen

**Technische Hinweise:** `python-frontmatter`-Library für Frontmatter-Parsing. Regex für Wikilink-Extraktion: `\[\[([^\]]+)\]\]`. Content-Type ist `MARKDOWN`.

---

## Konnektoren – Zoom-Transkripte

#### TASK-053: Zoom OAuth2-Flow implementieren

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P0                                                        |
| **Bereich**      | Backend                                                   |
| **Aufwand**      | M                                                         |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle), D4 US-1.5, D4 F-007 |
| **Abhängig von** | TASK-041, TASK-042, TASK-043                              |
| **Blockiert**    | TASK-054                                                  |

**Beschreibung:** Zoom Konnektor (`pwbs/connectors/zoom.py`) mit OAuth2-Flow für den Zoom Marketplace implementieren. Scopes für Transkript-Zugriff (`cloud_recording:read`, `meeting:read`). Callback verarbeitet Authorization Code, tauscht gegen Access+Refresh Token und persistiert verschlüsselt.

**Acceptance Criteria:**

- [ ] OAuth2-Auth-URL wird mit Transkript-relevanten Scopes generiert
- [ ] Callback verarbeitet Authorization Code und tauscht gegen Access+Refresh Token
- [ ] Tokens werden verschlüsselt via `OAuthTokenManager` gespeichert
- [ ] Connection-Status wird auf `active` gesetzt
- [ ] Fehlerzustände (abgebrochener Consent, ungültiger Code) werden sauber behandelt

**Technische Hinweise:** Zoom OAuth2 nutzt Server-to-Server oder User-Level OAuth. Für MVP wird User-Level OAuth verwendet. Token-Rotation via Refresh-Token.

---

#### TASK-054: Zoom Webhook-Receiver für Recording-completed-Events implementieren

| Feld             | Wert                                                                        |
| ---------------- | --------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                          |
| **Bereich**      | Backend                                                                     |
| **Aufwand**      | M                                                                           |
| **Status**       | 🔴 Offen                                                                    |
| **Quelle**       | D1 Abschnitt 3.1 (Konnektor-Tabelle: Webhook recording.completed), D4 F-007 |
| **Abhängig von** | TASK-053, TASK-044                                                          |
| **Blockiert**    | TASK-055                                                                    |

**Beschreibung:** Webhook-Endpunkt für Zoom `recording.completed`-Events implementieren. Verarbeitet eingehende Webhook-Payloads, validiert die Zoom-Signatur (Webhook Verification Token), ruft die Transkript-Datei über die Zoom API ab und stößt die Normalisierung an. Idempotenz: Doppelte Webhook-Events (gleiche `recording_id`) werden erkannt und ignoriert.

**Acceptance Criteria:**

- [ ] Webhook-Endpunkt empfängt `recording.completed`-Events
- [ ] Zoom-Signatur wird gegen den Verification Token validiert (Replay-Schutz)
- [ ] Transkript wird über die Zoom Cloud Recording API abgerufen
- [ ] Doppelte Events (gleiche `recording_id`) werden idempotent verarbeitet
- [ ] Webhook-Payload wird mit Pydantic validiert

**Technische Hinweise:** Zoom Webhooks senden einen `event`-Typ und `payload` mit `recording_files`. Nur Dateien vom Typ `TRANSCRIPT` verarbeiten. Zoom erfordert URL-Validation Challenge bei Webhook-Setup.

---

#### TASK-055: Zoom Normalizer (Transkripte, Teilnehmer, Dauer → UnifiedDocument) implementieren

| Feld             | Wert                                                                            |
| ---------------- | ------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                              |
| **Bereich**      | Backend                                                                         |
| **Aufwand**      | M                                                                               |
| **Status**       | 🔴 Offen                                                                        |
| **Quelle**       | D1 Abschnitt 3.1 (Datentypen: Meeting-Transkripte, Teilnehmer, Dauer), D4 F-007 |
| **Abhängig von** | TASK-054, TASK-044                                                              |
| **Blockiert**    | –                                                                               |

**Beschreibung:** Normalizer für Zoom-Transkripte, der Meeting-Aufnahmen ins UnifiedDocument Format konvertiert. Extrahiert: Transkript-Text, Teilnehmerliste (Name + E-Mail), Meeting-Titel, Dauer, Start-/Endzeit. VTT-Format wird in Plaintext konvertiert, Sprecherzuordnung wird soweit vorhanden beibehalten.

**Acceptance Criteria:**

- [ ] Zoom-Transkripte (VTT/TXT-Format) werden in Plaintext konvertiert
- [ ] Teilnehmer werden als `participants`-Liste extrahiert (Name und E-Mail)
- [ ] Meeting-Titel, Dauer, Start-/Endzeit werden als Metadaten gespeichert
- [ ] `source_type` ist `ZOOM`, `source_id` ist die Zoom Meeting-UUID
- [ ] Sprecherzuordnung wird beibehalten, wenn im Transkript vorhanden

**Technische Hinweise:** Zoom liefert Transkripte im VTT-Format. Timestamps im VTT können für spätere Chunk-Referenzierung als Metadaten extrahiert werden. Metadaten enthalten: `duration_minutes`, `start_time`, `end_time`, `participant_count`.

---

## Processing Pipeline – Chunking

#### TASK-056: Chunking Service mit semantischem Splitting implementieren

| Feld             | Wert                                                                          |
| ---------------- | ----------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                            |
| **Bereich**      | Backend                                                                       |
| **Aufwand**      | L                                                                             |
| **Status**       | 🔴 Offen                                                                      |
| **Quelle**       | D1 Abschnitt 3.2 (ChunkingConfig, Pipeline-Stufen), AGENTS.md ProcessingAgent |
| **Abhängig von** | Pydantic-Modelle (Agent 1)                                                    |
| **Blockiert**    | TASK-060                                                                      |

**Beschreibung:** Chunking Service (`pwbs/processing/chunking.py`) implementieren mit drei Strategien: `semantic` (Standard), `paragraph` und `fixed`. Semantisches Splitting teilt an Satzgrenzen auf und erhält semantisch zusammenhängende Abschnitte. Konfiguration: max. 512 Tokens, 64 Token Overlap (D1), Strategie wählbar. Paragraph-Splitting als Fallback für strukturierte Dokumente (Notion, Obsidian). Fixed-Splitting für unstrukturierten Langtext.

**Acceptance Criteria:**

- [ ] Drei Chunking-Strategien implementiert: `semantic`, `paragraph`, `fixed`
- [ ] Semantic Splitting teilt an Satzgrenzen, max. 512 Tokens pro Chunk
- [ ] Token-Overlap von 64 Tokens zwischen aufeinanderfolgenden Chunks
- [ ] Paragraph-Splitting nutzt Markdown-Absätze als natürliche Grenzen
- [ ] Leere oder zu kurze Dokumente (< 32 Tokens) ergeben genau einen Chunk

**Technische Hinweise:** ChunkingConfig aus D1 Abschnitt 3.2: `max_tokens=512`, `overlap_tokens=64`, `strategy="semantic"`. Token-Zählung via `tiktoken` (OpenAI Tokenizer) für Konsistenz mit dem Embedding-Modell.

---

#### TASK-057: Chunking-Strategie-Auswahl nach Dokumenttyp implementieren

| Feld             | Wert                                                 |
| ---------------- | ---------------------------------------------------- |
| **Priorität**    | P1                                                   |
| **Bereich**      | Backend                                              |
| **Aufwand**      | S                                                    |
| **Status**       | 🔴 Offen                                             |
| **Quelle**       | D1 Abschnitt 3.2 (Chunking-Strategie je Dokumenttyp) |
| **Abhängig von** | TASK-056                                             |
| **Blockiert**    | –                                                    |

**Beschreibung:** Automatische Strategieauswahl basierend auf `source_type` und `content_type` des UnifiedDocuments. Obsidian und Notion-Dokumente (`MARKDOWN`) verwenden `paragraph`-Splitting, Zoom-Transkripte `semantic`-Splitting, Kalender-Events `fixed`-Splitting. Überschreibbar per Konfiguration.

**Acceptance Criteria:**

- [ ] Strategie wird automatisch anhand von `source_type` und `content_type` gewählt
- [ ] Mapping ist konfigurierbar (nicht hardcoded)
- [ ] Fallback auf `semantic` wenn kein spezifisches Mapping existiert
- [ ] Strategie wird im Chunk-Modell als Metadatum gespeichert

**Technische Hinweise:** Default-Mapping: `OBSIDIAN` → `paragraph`, `NOTION` → `paragraph`, `ZOOM` → `semantic`, `GOOGLE_CALENDAR` → `fixed`.

---

## Processing Pipeline – Embedding-Generierung

#### TASK-058: OpenAI text-embedding-3-small Integration implementieren

| Feld             | Wert                                                                              |
| ---------------- | --------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                |
| **Bereich**      | Backend                                                                           |
| **Aufwand**      | M                                                                                 |
| **Status**       | 🔴 Offen                                                                          |
| **Quelle**       | D1 Abschnitt 3.2 (Embedding-Tabelle: text-embedding-3-small, 1536 Dim.), D4 F-011 |
| **Abhängig von** | TASK-056, Pydantic-Modelle (Agent 1)                                              |
| **Blockiert**    | TASK-059, TASK-068                                                                |

**Beschreibung:** Embedding-Generator (`pwbs/processing/embedding.py`) implementieren, der Chunks über die OpenAI `text-embedding-3-small`-API in 1536-dimensionale Vektoren konvertiert. Batch-Verarbeitung: max. 64 Chunks pro API-Call. Fehlerbehandlung bei API-Ausfall (Timeout, Rate-Limit) mit Retry-Logik. Das Embedding-Modell ist via Konfiguration austauschbar.

**Acceptance Criteria:**

- [ ] Chunks werden in Batches von max. 64 an die OpenAI Embedding API gesendet
- [ ] Ergebnis: 1536-dimensionale Float-Vektoren pro Chunk
- [ ] Retry-Logik bei API-Fehlern (429, 500, Timeout) mit Exponential Backoff (3 Retries)
- [ ] Modellname ist konfigurierbar (nicht hardcoded)
- [ ] Token-Count pro Batch wird geprüft (OpenAI-Limit: 8191 Tokens pro Input)

**Technische Hinweise:** OpenAI API via `openai`-Library. Batch-Endpoint: `client.embeddings.create(model=..., input=[...])`. Im MVP wird ausschließlich `text-embedding-3-small` verwendet; lokale Modelle (Sentence Transformers) erst ab Phase 3.

---

#### TASK-059: Weaviate-Upsert für Embeddings mit Idempotenz implementieren

| Feld             | Wert                                                                           |
| ---------------- | ------------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                             |
| **Bereich**      | Backend                                                                        |
| **Aufwand**      | M                                                                              |
| **Status**       | 🔴 Offen                                                                       |
| **Quelle**       | D1 Abschnitt 3.3.2 (Weaviate Collection Schema), D1 Abschnitt 1.2 (Idempotenz) |
| **Abhängig von** | TASK-058, DB-Schema (Agent 1)                                                  |
| **Blockiert**    | TASK-068                                                                       |

**Beschreibung:** Weaviate-Storage-Schicht (`pwbs/storage/weaviate.py`) implementieren, die generierte Embeddings idempotent in die `DocumentChunk`-Collection schreibt. Upsert-Logik: Existierender Vektor für gleiche `chunkId` + `userId` wird überschrieben. Multi-Tenancy: Jeder Nutzer ist ein eigener Weaviate-Tenant. Referenz zwischen Weaviate-ID und PostgreSQL `chunks.weaviate_id` wird aktualisiert.

**Acceptance Criteria:**

- [ ] Embeddings werden in die Weaviate `DocumentChunk`-Collection geschrieben
- [ ] Upsert: Existierender Vektor für gleiche `chunkId` wird überschrieben (Idempotenz)
- [ ] Multi-Tenancy: Tenant entspricht der `userId`, kein Cross-User-Zugriff möglich
- [ ] `weaviate_id` wird in der PostgreSQL `chunks`-Tabelle gespeichert
- [ ] Properties `chunkId`, `userId`, `sourceType`, `content`, `title`, `createdAt`, `language` werden gesetzt

**Technische Hinweise:** Weaviate Collection-Schema aus D1 Abschnitt 3.3.2 verwenden. `vectorizer: none` (Vektoren werden extern generiert). HNSW-Index mit `efConstruction=128`, `maxConnections=16`.

---

#### TASK-060: Fehlerbehandlung und Retry-Logik für Embedding-Pipeline implementieren

| Feld             | Wert                                        |
| ---------------- | ------------------------------------------- |
| **Priorität**    | P1                                          |
| **Bereich**      | Backend                                     |
| **Aufwand**      | S                                           |
| **Status**       | 🔴 Offen                                    |
| **Quelle**       | D1 Abschnitt 3.2, AGENTS.md ProcessingAgent |
| **Abhängig von** | TASK-058, TASK-059                          |
| **Blockiert**    | –                                           |

**Beschreibung:** Fehlerbehandlung für die Embedding-Pipeline: Bei OpenAI API-Ausfall werden fehlgeschlagene Batches in eine Retry-Queue geschrieben. Exponential Backoff (1 min → 5 min → 25 min). Dokuemnt-Status in PostgreSQL wird auf `error` gesetzt bei dauerhaftem Fehler (nach 3 Retries). Partielle Erfolge werden gespeichert – wenn 60 von 64 Chunks im Batch erfolgreich sind, werden die 60 persistiert.

**Acceptance Criteria:**

- [ ] Fehlgeschlagene Batches werden mit Exponential Backoff (3 Retries) wiederholt
- [ ] `processing_status` in der `documents`-Tabelle wird auf `error` gesetzt nach 3 Fehlversuchen
- [ ] Partielle Batch-Erfolge werden gespeichert (nicht alles verwerfen bei Teilerfolg)
- [ ] Fehlermeldung wird in den Audit-Log geschrieben

**Technische Hinweise:** Im MVP läuft Retry als Background-Task in FastAPI. Ab Phase 3 über Celery + Redis Queue.

---

## Processing Pipeline – NER & Entitätsextraktion

#### TASK-061: Regelbasierte Entitätsextraktion implementieren

| Feld             | Wert                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                                         |
| **Bereich**      | Backend                                                                                    |
| **Aufwand**      | M                                                                                          |
| **Status**       | 🔴 Offen                                                                                   |
| **Quelle**       | D1 Abschnitt 3.2 (NER regelbasiert: E-Mail, @-Mentions, Kalender-Teilnehmer, Notion-Links) |
| **Abhängig von** | TASK-056, DB-Schema (Agent 1)                                                              |
| **Blockiert**    | TASK-063                                                                                   |

**Beschreibung:** Regelbasierte Entitätsextraktion (`pwbs/processing/ner.py`) als erste Stufe der NER-Pipeline. Erkennt: E-Mail-Adressen → Person-Entities, @-Mentions → Person-Entities, Kalender-Teilnehmer (aus Metadaten) → Person-Entities, Notion-Verlinkungen (aus Metadaten) → diverse Entities. Konfidenz-Score ist 1.0 für regelbasierte Extraktion. Ergebnisse werden in die `entities`- und `entity_mentions`-Tabellen geschrieben.

**Acceptance Criteria:**

- [ ] E-Mail-Adressen werden als Person-Entities mit `extraction_method='rule'` extrahiert
- [ ] @-Mentions (aus Content) werden als Person-Entities extrahiert
- [ ] Kalender-Teilnehmer (aus `participants`-Feld) werden als Person-Entities extrahiert
- [ ] Notion-Links (aus Metadaten) werden als Entities extrahiert
- [ ] Entity-Deduplizierung über `normalized_name` (lowercase, Whitespace-Normalisierung)

**Technische Hinweise:** `confidence=1.0` für regelbasierte Ergebnisse. `UNIQUE(user_id, entity_type, normalized_name)` in der `entities`-Tabelle nutzen für Upsert (Idempotenz). Regex für E-Mail: RFC 5322-konform.

---

#### TASK-062: LLM-basierte Entitätsextraktion mit Structured Output implementieren

| Feld             | Wert                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                                |
| **Bereich**      | LLM                                                                                               |
| **Aufwand**      | L                                                                                                 |
| **Status**       | 🔴 Offen                                                                                          |
| **Quelle**       | D1 Abschnitt 3.2 (ENTITY_EXTRACTION_PROMPT, LLM-basierte Stufe), D1 Abschnitt 3.4 (Token-Budgets) |
| **Abhängig von** | TASK-061, TASK-065                                                                                |
| **Blockiert**    | TASK-063                                                                                          |

**Beschreibung:** LLM-basierte Entitätsextraktion als zweite Stufe der NER-Pipeline. Nutzt den `ENTITY_EXTRACTION_PROMPT` aus D1 mit Structured Output (JSON-Schema) via Claude API (Modell: `claude-haiku` für Kosteneffizienz). Extrahiert: Personen, Projekte, Themen, Entscheidungen, offene Fragen, Termine. Wird nur für Chunks ausgeführt, die die regelbasierte Stufe nicht vollständig abdeckt. Kostenkontrolle: Max. 100 LLM-Extraction-Calls pro Nutzer/Tag.

**Acceptance Criteria:**

- [ ] Structured Output via Claude API (JSON-Schema-Validierung der Antwort)
- [ ] Extrahiert: Personen (Name, Rolle, Kontext), Projekte (Name, Status), Themen, Entscheidungen, offene Fragen, Termine
- [ ] Kostenkontrolle: Max. 100 LLM-Extraction-Calls pro Nutzer/Tag (Counter in Redis/PostgreSQL)
- [ ] Confidence-Score wird pro extrahierter Entity berechnet (nur > 0.75 wird in Graph aufgenommen)
- [ ] LLM-Output wird gegen JSON-Schema validiert, fehlerhafte Antworten werden verworfen und geloggt

**Technische Hinweise:** Token-Budget aus D1: context_tokens=2000, output_tokens=1000, Modell: `claude-haiku`. `extraction_method='llm'` in `entity_mentions`. Prompt-Template liegt in `pwbs/prompts/entity_extraction.md`.

---

#### TASK-063: Entity-Deduplizierung über normalized_name implementieren

| Feld             | Wert                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                       |
| **Bereich**      | Backend                                                                                  |
| **Aufwand**      | M                                                                                        |
| **Status**       | 🔴 Offen                                                                                 |
| **Quelle**       | D1 Abschnitt 3.3.1 (entities-Tabelle: UNIQUE normalized_name), AGENTS.md ProcessingAgent |
| **Abhängig von** | TASK-061, TASK-062                                                                       |
| **Blockiert**    | TASK-064                                                                                 |

**Beschreibung:** Entity-Deduplizierungslogik implementieren, die sicherstellt, dass gleiche Entitäten nicht doppelt existieren. Normalisierung: Lowercase, Whitespace-Trimming, Umlaute normalisieren. Fuzzy-Matching für ähnliche Namen (z.B. „Thomas K." und „Thomas Klein") mit konfigurierbarem Threshold. Merge-Logik: Bei erkanntem Duplikat werden `mention_count`, `last_seen` und `metadata` zusammengeführt.

**Acceptance Criteria:**

- [ ] `normalized_name` wird berechnet: lowercase, whitespace-trimmed, Umlaute normalisiert
- [ ] UPSERT-Logik: Existierender Entity mit gleichem `(user_id, entity_type, normalized_name)` wird aktualisiert statt dupliziert
- [ ] `mention_count` wird inkrementiert, `last_seen` wird aktualisiert
- [ ] Fuzzy-Matching für Kurz-/Langformen implementiert (konfigurierbar, Standard-Threshold: 0.85)

**Technische Hinweise:** PostgreSQL UPSERT via `ON CONFLICT (user_id, entity_type, normalized_name) DO UPDATE`. Fuzzy-Matching zunächst nur für `entity_type=PERSON` via Levenshtein-Distanz.

---

## Processing Pipeline – Graph Builder

#### TASK-064: Neo4j Graph Builder mit MERGE-basierter Idempotenz implementieren

| Feld             | Wert                                                                                          |
| ---------------- | --------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                            |
| **Bereich**      | Backend                                                                                       |
| **Aufwand**      | L                                                                                             |
| **Status**       | 🔴 Offen                                                                                      |
| **Quelle**       | D1 Abschnitt 3.3.3 (Neo4j Schema, Knotentypen, Kantentypen), D1 Abschnitt 3.2 (Graph Builder) |
| **Abhängig von** | TASK-063, DB-Schema (Agent 1)                                                                 |
| **Blockiert**    | TASK-069                                                                                      |

**Beschreibung:** Graph Builder (`pwbs/graph/builder.py`) implementieren, der extrahierte Entities als Knoten und deren Beziehungen als Kanten in Neo4j schreibt. Idempotenz via `MERGE` statt `CREATE`. Knotentypen: Person, Project, Topic, Decision, Meeting, Document. Kantentypen gemäß D1 Schema. Alle Knoten und Queries enthalten `userId` als Pflichtattribut für Mandanten-Isolation.

**Acceptance Criteria:**

- [ ] Knoten werden per `MERGE` erstellt/aktualisiert (kein Duplikat bei erneutem Processing)
- [ ] Alle 6 Knotentypen (Person, Project, Topic, Decision, Meeting, Document) werden unterstützt
- [ ] Alle Kantentypen aus D1 werden erzeugt (PARTICIPATED_IN, WORKS_ON, MENTIONED_IN, etc.)
- [ ] Jeder Cypher-Query enthält `WHERE n.userId = $userId` (Mandanten-Isolation)
- [ ] `neo4j_node_id` wird in der PostgreSQL `entities`-Tabelle als Referenz gespeichert

**Technische Hinweise:** Neo4j-Schema aus D1 Abschnitt 3.3.3. `neo4j`-Python-Driver verwenden. Alle Queries parametrisiert (kein String-Concatenation für Cypher). Batch-Writes: max. 50 Knoten pro Transaction.

---

#### TASK-065: Kantengewichtung und Co-Occurrence-basierte Kantenableitung implementieren

| Feld             | Wert                                                                                |
| ---------------- | ----------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                  |
| **Bereich**      | Backend                                                                             |
| **Aufwand**      | M                                                                                   |
| **Status**       | 🔴 Offen                                                                            |
| **Quelle**       | D1 Abschnitt 3.3.3 (Kantengewichtung: weight-Property, Co-Occurrence, Decay-Faktor) |
| **Abhängig von** | TASK-064                                                                            |
| **Blockiert**    | –                                                                                   |

**Beschreibung:** Kantengewichtung für alle Neo4j-Kanten implementieren. `weight`-Property (Float, 0.0–1.0) basierend auf Häufigkeit der Co-Occurrence und zeitlichem Abstand (Decay-Faktor). Abgeleitete Kanten: `KNOWS`-Beziehung zwischen Personen, die häufig in gleichen Meetings/Dokumenten vorkommen. `RELATED_TO`-Beziehung zwischen Topics mit hoher Co-Occurrence.

**Acceptance Criteria:**

- [ ] Alle Kanten tragen eine `weight`-Property (Float, 0.0–1.0)
- [ ] Gewicht steigt mit Häufigkeit der Co-Occurrence
- [ ] Gewicht sinkt mit zeitlichem Abstand (exponentieller Decay-Faktor)
- [ ] `KNOWS`-Kante zwischen Personen wird automatisch abgeleitet bei Co-Occurrence in ≥ 2 Dokumenten
- [ ] `RELATED_TO`-Kante zwischen Topics bei Co-Occurrence in ≥ 3 Chunks

**Technische Hinweise:** Decay-Formel: `weight = base_weight * exp(-decay_rate * days_since_last_occurrence)`. Kantenableitung läuft als Post-Processing-Schritt nach dem initialen Graph-Build.

---

## LLM Gateway

#### TASK-066: LLM Gateway Service mit Provider-Abstraktion implementieren

| Feld             | Wert                                                                            |
| ---------------- | ------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                              |
| **Bereich**      | LLM                                                                             |
| **Aufwand**      | L                                                                               |
| **Status**       | 🔴 Offen                                                                        |
| **Quelle**       | D1 Abschnitt 3.4 (LLM Orchestration Service, Provider Router, Fallback-Kaskade) |
| **Abhängig von** | Pydantic-Modelle (Agent 1)                                                      |
| **Blockiert**    | TASK-062, TASK-067, TASK-068, TASK-073, TASK-076                                |

**Beschreibung:** LLM Gateway (`pwbs/core/llm_gateway.py`) als Abstraktion über Claude API (primär) und GPT-4 (Fallback) implementieren. Provider Router wählt den Provider basierend auf `model_preference` im PromptTemplate. Fallback-Kaskade: Claude → GPT-4 → Cached Response → Fehlermeldung mit Rohdaten. Request Pipeline: Prompt Assembly → Token Budget Check → Provider Selection → API Call mit Retry → Response Validation → Source Attribution → Confidence Scoring → Cost Logging.

**Acceptance Criteria:**

- [ ] Claude API (primär) und GPT-4 (Fallback) als Provider implementiert
- [ ] Provider Router selektiert automatisch anhand von `model_preference` und Verfügbarkeit
- [ ] Fallback-Kaskade: Claude → GPT-4 → Cached Response → strukturierte Fehlermeldung
- [ ] Retry-Logik mit Exponential Backoff (3 Retries) bei transienten Fehlern (429, 500, Timeout)
- [ ] Cost & Latency Logging pro Aufruf (Modell, Token-Count Input/Output, Dauer, Kosten)

**Technische Hinweise:** Architektur aus D1 Abschnitt 3.4. `anthropic`-Library für Claude, `openai`-Library für GPT-4. Keine Secrets im Code – API-Keys über Umgebungsvariablen.

---

#### TASK-067: Prompt-Management mit versionierten Templates implementieren

| Feld             | Wert                                                                                   |
| ---------------- | -------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                     |
| **Bereich**      | LLM                                                                                    |
| **Aufwand**      | M                                                                                      |
| **Status**       | 🔴 Offen                                                                               |
| **Quelle**       | D1 Abschnitt 3.4 (Prompt Registry, PromptTemplate Dataclass), AGENTS.md (Prompt-Files) |
| **Abhängig von** | TASK-066                                                                               |
| **Blockiert**    | TASK-073, TASK-076                                                                     |

**Beschreibung:** Prompt Registry (`pwbs/prompts/`) implementieren. Prompts werden als versionierte Template-Dateien gespeichert und über eine Registry geladen. `PromptTemplate`-Dataclass mit: `id`, `template` (Jinja2), `model_preference`, `max_output_tokens`, `temperature`, `system_prompt`, `required_context`, `version`. Template-Variablen werden beim Assembly gegen den bereitgestellten Kontext aufgelöst.

**Acceptance Criteria:**

- [ ] `PromptTemplate`-Dataclass mit allen Feldern aus D1 implementiert
- [ ] Prompt Registry lädt Templates aus `pwbs/prompts/`-Verzeichnis
- [ ] Jinja2-basiertes Template-Rendering mit Kontextvariablen
- [ ] Versionierung: Mehrere Versionen eines Prompts können koexistieren, die neueste wird per Default geladen
- [ ] `required_context`-Prüfung: Fehlende Kontextvariablen werfen einen aussagekräftigen Fehler

**Technische Hinweise:** Prompts als `.md` oder `.j2`-Dateien in `pwbs/prompts/`. Benennung: `{use_case}.v{version}.j2` (z.B. `briefing_morning.v1.j2`). Jinja2-Template-Engine mit Auto-Escaping.

---

#### TASK-068: Structured Output mit JSON-Schema-Validierung implementieren

| Feld             | Wert                                                                                            |
| ---------------- | ----------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                              |
| **Bereich**      | LLM                                                                                             |
| **Aufwand**      | M                                                                                               |
| **Status**       | 🔴 Offen                                                                                        |
| **Quelle**       | D1 Abschnitt 3.4 (Response Validation), D1 Abschnitt 3.2 (ENTITY_EXTRACTION_PROMPT JSON-Schema) |
| **Abhängig von** | TASK-066                                                                                        |
| **Blockiert**    | TASK-062                                                                                        |

**Beschreibung:** Structured Output Layer im LLM Gateway implementieren, der LLM-Antworten gegen ein vorgegebenes JSON-Schema validiert. Nutzt Claude's native JSON-Mode / Tool-Use für strukturierte Ausgaben. Fallback: Regex-basiertes JSON-Extraktion aus Freitext-Antworten. Validierung via Pydantic-Modelle. Ungültige Antworten werden geloggt und ein Retry mit angepasstem Prompt ausgelöst.

**Acceptance Criteria:**

- [ ] LLM-Antworten werden gegen ein Pydantic-Schema validiert
- [ ] Claude's JSON-Mode / Tool-Use wird für strukturierte Ausgaben genutzt
- [ ] Fallback: Regex-basierte JSON-Extraktion bei Freitext-Antworten
- [ ] Ungültige Antworten lösen einen Retry aus (max. 1 Retry mit expliziterem Format-Prompt)
- [ ] Validierungsfehler werden mit dem Rohdaten-Response geloggt

**Technische Hinweise:** Claude API unterstützt `tool_use` für strukturierte Outputs. JSON-Schema-Definition als Pydantic-Modelle, die mit `model_json_schema()` exportiert werden.

---

#### TASK-069: Halluzinations-Mitigation mit Quellenreferenz-Pflicht implementieren

| Feld             | Wert                                                                                                  |
| ---------------- | ----------------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                                    |
| **Bereich**      | LLM                                                                                                   |
| **Aufwand**      | M                                                                                                     |
| **Status**       | 🔴 Offen                                                                                              |
| **Quelle**       | D1 Abschnitt 3.4 (Halluzinations-Mitigation, Grounded Generation), D3 Erklärbarkeit, D4 NF-022/NF-023 |
| **Abhängig von** | TASK-066, TASK-067                                                                                    |
| **Blockiert**    | TASK-076, TASK-077                                                                                    |

**Beschreibung:** Halluzinations-Mitigationsschicht im LLM Gateway implementieren. Jeder LLM-Call enthält die Instruktion „Antworte ausschließlich basierend auf den bereitgestellten Quellen." Jede generierte Aussage wird mit `[Quelle: {document_title}, {date}]` annotiert. Confidence Scoring: Aussagen ohne direkte Quellenableitung erhalten einen `low`-Confidence-Indikator. Fakten/Interpretation-Trennung in der Prompt-Struktur.

**Acceptance Criteria:**

- [ ] System-Prompt enthält explizite Grounding-Instruktion für alle LLM-Calls
- [ ] Generierte Aussagen enthalten `[Quelle: Titel, Datum]`-Annotationen
- [ ] Confidence Scoring: `high` (direkte Quelle), `medium` (abgeleitet), `low` (keine direkte Quelle)
- [ ] Aussagen mit `low` Confidence werden im Output gekennzeichnet
- [ ] Prompt-Struktur erzwingt Abschnitte: Fakten, Zusammenhänge, Empfehlungen

**Technische Hinweise:** Grounding-Pattern aus D1 Abschnitt 3.4. Quellenreferenzen werden im Post-Processing gegen die tatsächlich bereitgestellten Chunks validiert. Invalide Referenzen werden entfernt.

---

#### TASK-070: Rate Limiting und Kostenkontrolle pro Nutzer im LLM Gateway implementieren

| Feld             | Wert                                                                                               |
| ---------------- | -------------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                                 |
| **Bereich**      | LLM                                                                                                |
| **Aufwand**      | M                                                                                                  |
| **Status**       | 🔴 Offen                                                                                           |
| **Quelle**       | D1 Abschnitt 3.2 (100 LLM-Extraction-Calls/Nutzer/Tag), D1 Abschnitt 3.4 (Token-Budget-Management) |
| **Abhängig von** | TASK-066                                                                                           |
| **Blockiert**    | –                                                                                                  |

**Beschreibung:** Per-User Rate Limiting und Kostenkontrolle im LLM Gateway implementieren. Token-Budget-Limits pro Use-Case (aus D1 `TOKEN_BUDGETS`): `briefing.morning` (context: 8000, output: 2000), `search.answer` (context: 6000, output: 1500), `entity.extraction` (context: 2000, output: 1000). Täglicher Kostencap pro Nutzer. LLM-Extraction-Calls: max. 100 pro Nutzer/Tag. Counter in PostgreSQL oder Redis.

**Acceptance Criteria:**

- [ ] Token-Budget-Limits pro Use-Case werden vor jedem LLM-Call geprüft
- [ ] Tägliches Limit: Max. 100 LLM-Extraction-Calls pro Nutzer/Tag
- [ ] Bei Überschreitung wird ein `PWBSError` mit klarer Fehlermeldung geworfen (kein stiller Fehler)
- [ ] Verbrauchszähler werden täglich zurückgesetzt
- [ ] Cost Logging: Jeder LLM-Call wird mit geschätzten Kosten (Token-basiert) geloggt

**Technische Hinweise:** Token-Budgets aus D1 Abschnitt 3.4 `TOKEN_BUDGETS`-Dict. Counter-Implementierung im MVP über PostgreSQL; ab Phase 3 Redis.

---

#### TASK-071: LLM Gateway Retry-Logik mit Exponential Backoff implementieren

| Feld             | Wert                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------ |
| **Priorität**    | P1                                                                                         |
| **Bereich**      | LLM                                                                                        |
| **Aufwand**      | S                                                                                          |
| **Status**       | 🔴 Offen                                                                                   |
| **Quelle**       | D1 Abschnitt 3.4 (Fallback-Kaskade, Retry), AGENTS.md SchedulerAgent (Exponential Backoff) |
| **Abhängig von** | TASK-066                                                                                   |
| **Blockiert**    | –                                                                                          |

**Beschreibung:** Retry-Logik für den LLM Gateway implementieren. Bei transienten Fehlern (HTTP 429 Rate Limit, 500 Server Error, Timeout) wird mit Exponential Backoff wiederholt (1 min → 5 min → 25 min, max. 3 Retries). Bei permanenten Fehlern (401, 403) wird sofort auf den Fallback-Provider gewechselt. Idempotenz: Gleicher Request darf keine doppelten Nebenwirkungen erzeugen.

**Acceptance Criteria:**

- [ ] Exponential Backoff: 1 min → 5 min → 25 min bei transienten Fehlern
- [ ] Max. 3 Retries pro Provider, danach Wechsel zum Fallback-Provider
- [ ] Permanente Fehler (401, 403) lösen sofortigen Provider-Wechsel aus
- [ ] Alle Retries und Provider-Wechsel werden geloggt
- [ ] Timeout pro LLM-Call ist konfigurierbar (Default: 30 Sekunden)

**Technische Hinweise:** Retry-Intervalle aus AGENTS.md SchedulerAgent. `tenacity`-Library oder eigene Retry-Implementierung. Jitter hinzufügen um Thundering Herd zu vermeiden.

---

## Semantische Suche – Service-Kern

#### TASK-072: Weaviate Nearest-Neighbor-Suche (Semantic Mode) implementieren

| Feld             | Wert                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                      |
| **Bereich**      | Backend                                                                                 |
| **Aufwand**      | M                                                                                       |
| **Status**       | 🔴 Offen                                                                                |
| **Quelle**       | D1 Abschnitt 3.3.2 (Suchstrategie: Hybrid, alpha=0.75), D4 F-011, AGENTS.md SearchAgent |
| **Abhängig von** | TASK-059, TASK-058                                                                      |
| **Blockiert**    | TASK-074                                                                                |

**Beschreibung:** Semantischen Such-Service (`pwbs/search/service.py`) implementieren mit Weaviate Nearest-Neighbor-Suche. Query-Embedding wird über den gleichen Embedding-Service (TASK-058) generiert. Suche in der `DocumentChunk`-Collection des jeweiligen Nutzer-Tenants. Konfigurierbare Parameter: `top_k` (Default: 10, Max: 50), `alpha` (Default: 0.75 für semantisch-gewichtete Hybrid-Suche).

**Acceptance Criteria:**

- [ ] Query wird in Embedding konvertiert und gegen Weaviate Nearest-Neighbor gesucht
- [ ] Suche ist isoliert auf den Nutzer-Tenant (`userId`-Filter)
- [ ] `top_k` ist konfigurierbar (Default: 10, Max: 50)
- [ ] Ergebnisse enthalten: `chunkId`, `content`, `title`, `sourceType`, `createdAt`, `score`
- [ ] Leerer Query oder Query ohne Ergebnisse gibt leere Liste zurück (kein Fehler)

**Technische Hinweise:** Weaviate `nearVector`-Query mit dem generierten Query-Embedding. `alpha=0.75` für Standard-Suche, `alpha=0.3` für exakte Terme (Projektnamen, Personennamen) gemäß D1 Abschnitt 3.3.2.

---

#### TASK-073: PostgreSQL tsvector Keyword-Suche implementieren

| Feld             | Wert                                                                                                |
| ---------------- | --------------------------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                                  |
| **Bereich**      | Backend                                                                                             |
| **Aufwand**      | M                                                                                                   |
| **Status**       | 🔴 Offen                                                                                            |
| **Quelle**       | D1 Abschnitt 3.3.2 (BM25 Keyword-Suche), D4 F-011 (Hybrid-Suche 25% Keyword), AGENTS.md SearchAgent |
| **Abhängig von** | DB-Schema (Agent 1)                                                                                 |
| **Blockiert**    | TASK-074                                                                                            |

**Beschreibung:** Keyword-Suche über PostgreSQL `tsvector`/`tsquery` implementieren. Volltextindex auf `chunks.content_preview` und `documents.title`. Ranking via `ts_rank_cd`. Unterstützt deutsche und englische Stemming-Konfiguration. Owner-Filter: Jede Query enthält `WHERE user_id = $user_id`.

**Acceptance Criteria:**

- [ ] `tsvector`-Index auf relevanten Spalten erstellt (Content, Titel)
- [ ] `tsquery`-Suche mit Stemming (Deutsch + Englisch konfigurierbar)
- [ ] Ranking via `ts_rank_cd` für Ergebnissortierung
- [ ] `user_id`-Filter als Pflichtparameter bei jeder Query
- [ ] Ergebnisse enthalten: `chunk_id`, `document_id`, `content_preview`, `score`

**Technische Hinweise:** PostgreSQL Full-Text-Search mit `to_tsvector('german', content)` und `to_tsquery('german', query)`. GIN-Index für Performance. Bei mehrsprachigen Dokumenten: Sprachangabe aus `language`-Feld nutzen.

---

#### TASK-074: Hybrid-Suche mit RRF-Fusion implementieren

| Feld             | Wert                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                                               |
| **Bereich**      | Backend                                                                                          |
| **Aufwand**      | M                                                                                                |
| **Status**       | 🔴 Offen                                                                                         |
| **Quelle**       | D1 Abschnitt 3.3.2 (Hybrid-Suche), D4 F-011 (75% semantisch, 25% Keyword), AGENTS.md SearchAgent |
| **Abhängig von** | TASK-072, TASK-073                                                                               |
| **Blockiert**    | TASK-075                                                                                         |

**Beschreibung:** Reciprocal Rank Fusion (RRF) implementieren, die Ergebnisse aus Weaviate (semantisch) und PostgreSQL (Keyword) kombiniert. RRF-Formel: `score = Σ 1/(k + rank_i)` mit k=60. Gewichtung: 75% semantisch, 25% Keyword (konfigurierbar). Deduplizierung: Chunks, die in beiden Ergebnislisten vorkommen, werden zusammengeführt.

**Acceptance Criteria:**

- [ ] RRF-Fusion kombiniert Ergebnisse aus Weaviate und PostgreSQL
- [ ] RRF-Formel mit k=60 korrekt implementiert
- [ ] Gewichtung konfigurierbar (Default: 0.75 semantisch, 0.25 Keyword)
- [ ] Deduplizierung: Gleiche Chunks werden zusammengeführt, nicht doppelt angezeigt
- [ ] `owner_id` als Pflicht-Filter bei allen Teilabfragen

**Technische Hinweise:** RRF ist ein rank-basiertes Fusionsverfahren, das keine Score-Normalisierung erfordert. Standard-Konstante k=60 aus der Originalpublikation. Ergebnisliste wird nach fusioniertem Score sortiert.

---

#### TASK-075: Suchergebnisse mit SourceRef anreichern

| Feld             | Wert                                                                             |
| ---------------- | -------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                               |
| **Bereich**      | Backend                                                                          |
| **Aufwand**      | S                                                                                |
| **Status**       | 🔴 Offen                                                                         |
| **Quelle**       | D4 F-012 (Ergebnisse mit Quellenangabe), D3 Erklärbarkeit, AGENTS.md SearchAgent |
| **Abhängig von** | TASK-074                                                                         |
| **Blockiert**    | –                                                                                |

**Beschreibung:** Suchergebnisse mit `SourceRef`-Objekten anreichern, die alle Informationen für die Quellenangabe im Frontend enthalten. Jedes Ergebnis enthält: Dokumenttitel, Quelltyp (Icon-Mapping), Erstellungs-/Änderungsdatum, relevanter Textausschnitt (Chunk-Content), Relevanz-Score, Original-URL (für „Original öffnen"-Link).

**Acceptance Criteria:**

- [ ] Jedes Suchergebnis enthält ein `SourceRef`-Objekt mit Titel, Quelltyp, Datum, Content-Ausschnitt, Score
- [ ] Original-URL wird aus den Metadaten rekonstruiert (Notion-URL, Google Calendar-Link etc.)
- [ ] Quelltyp wird für Frontend-Icon-Mapping bereitgestellt
- [ ] Ergebnisse sind nach fusioniertem RRF-Score sortiert

**Technische Hinweise:** `SourceRef` als Pydantic-Modell. Original-URL-Rekonstruktion: Notion → `https://notion.so/{page_id}`, Google Calendar → `https://calendar.google.com/event/{event_id}`, Zoom → Recording-URL aus Metadaten.

---

## Briefing Engine

#### TASK-076: Morgenbriefing Kontextassemblierung implementieren

| Feld             | Wert                                                                                                        |
| ---------------- | ----------------------------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                                          |
| **Bereich**      | Backend                                                                                                     |
| **Aufwand**      | L                                                                                                           |
| **Status**       | 🔴 Offen                                                                                                    |
| **Quelle**       | D1 Abschnitt 3.5 (Kontextassemblierung Morning Briefing, 8 Schritte), D2 Phase 2 Kontextbriefings, D4 F-017 |
| **Abhängig von** | TASK-046, TASK-072, TASK-064, TASK-066, TASK-067                                                            |
| **Blockiert**    | TASK-078                                                                                                    |

**Beschreibung:** Kontextassemblierung für das Morgenbriefing implementieren, die den 8-Schritte-Prozess aus D1 Abschnitt 3.5 umsetzt: (1) Kalender-Events heute abrufen, (2) Für jeden Termin: Teilnehmer → Neo4j-Abfrage (letzte Interaktionen, gemeinsame Projekte, offene Punkte), (3) Semantische Suche: relevante Dokumente der letzten 7 Tage, gefiltert nach Topics aus heutigen Terminen, (4) Offene Entscheidungen aus Neo4j (Status pending, nach Alter sortiert), (5) Kontext in Token-Budget prüfen und ggf. priorisieren/kürzen.

**Acceptance Criteria:**

- [ ] Kalender-Events des Tages werden abgerufen (aus Google Calendar Connector-Daten)
- [ ] Pro Termin: Neo4j-Abfrage für Teilnehmer-History, gemeinsame Projekte, offene Punkte
- [ ] Semantische Suche: Relevante Dokumente der letzten 7 Tage, gefiltert nach Termin-Topics
- [ ] Offene Entscheidungen (Status `pending`) werden aus Neo4j abgerufen
- [ ] Zusammengestellter Kontext wird auf Token-Budget (8000 Tokens) geprüft und ggf. priorisiert

**Technische Hinweise:** Cypher-Queries für Meeting-Vorbereitung aus D1 Abschnitt 3.3.3 verwenden. Token-Budget: 8000 Context-Tokens für `briefing.morning` (D1 Abschnitt 3.4). Kontext-Priorisierung: Heutige Termine > Offene Entscheidungen > Hintergrund-Dokumente.

---

#### TASK-077: Meeting-Vorbereitung Kontextassemblierung implementieren

| Feld             | Wert                                             |
| ---------------- | ------------------------------------------------ |
| **Priorität**    | P0                                               |
| **Bereich**      | Backend                                          |
| **Aufwand**      | L                                                |
| **Status**       | 🔴 Offen                                         |
| **Quelle**       | D1 Abschnitt 3.5, D4 US-3.2, D4 F-018            |
| **Abhängig von** | TASK-046, TASK-072, TASK-064, TASK-066, TASK-067 |
| **Blockiert**    | TASK-078                                         |

**Beschreibung:** Kontextassemblierung für Meeting-Vorbereitungsbriefings implementieren. Ausgelöst 30 Minuten vor Kalendereintrag mit ≥ 2 Teilnehmern (oder on-demand). Assembliert: Meeting-Thema, Teilnehmer mit History (letzte gemeinsame Meetings, gemeinsame Projekte via Neo4j), offene Punkte aus vorherigen Interaktionen, relevante Dokumente (via semantische Suche). Für unbekannte Teilnehmer: „Neu im System – keine vorherigen Interaktionen gespeichert" statt Halluzination.

**Acceptance Criteria:**

- [ ] Trigger: 30 Minuten vor Meeting mit ≥ 2 Teilnehmern oder on-demand
- [ ] Teilnehmer-History wird aus Neo4j abgerufen (letzte gemeinsame Meetings, Projekte)
- [ ] Offene Punkte aus vorherigen Interaktionen werden extrahiert
- [ ] Relevante Dokumente werden per semantischer Suche abgerufen
- [ ] Unbekannte Teilnehmer werden als „Neu im System" gekennzeichnet (keine Halluzination)

**Technische Hinweise:** Max. 400 Wörter Output (D4 F-018). Cypher-Query für Teilnehmer-History aus D1 Abschnitt 3.3.3. Token-Budget: Kontext auf max. 6000 Tokens begrenzen.

---

#### TASK-078: Briefing LLM-Call mit Prompt-Template und strukturiertem Output implementieren

| Feld             | Wert                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| **Priorität**    | P0                                                                                                           |
| **Bereich**      | LLM                                                                                                          |
| **Aufwand**      | M                                                                                                            |
| **Status**       | 🔴 Offen                                                                                                     |
| **Quelle**       | D1 Abschnitt 3.4 (Token-Budgets), D1 Abschnitt 3.5 (Briefing Engine, Output-Format), AGENTS.md BriefingAgent |
| **Abhängig von** | TASK-076, TASK-077, TASK-067, TASK-069                                                                       |
| **Blockiert**    | TASK-079                                                                                                     |

**Beschreibung:** LLM-Call für Briefing-Generierung via LLM Gateway implementieren. Assemblierter Kontext wird in das Prompt-Template eingesetzt (Morning oder Meeting Prep). LLM generiert strukturiertes Briefing im Markdown-Format gemäß D1 Output-Format. Temperatur: 0.3 für sachliche Inhalte. Quellenreferenzen werden im Output als `[Quelle: Titel, Datum]` annotiert.

**Acceptance Criteria:**

- [ ] Kontext wird in Jinja2 Prompt-Template eingesetzt und an LLM Gateway übergeben
- [ ] Temperatur: 0.3 (sachliche Inhalte)
- [ ] Output im Markdown-Format gemäß D1 Briefing-Outputformat
- [ ] Morgenbriefing: max. 800 Wörter, Meeting-Briefing: max. 400 Wörter
- [ ] Jede Aussage enthält `[Quelle: Titel, Datum]`-Annotation

**Technische Hinweise:** Prompt-Templates: `briefing_morning.v1.j2` und `briefing_meeting_prep.v1.j2`. Token-Budgets aus D1: Morning (context: 8000, output: 2000), Meeting Prep analog. Modell: `claude-sonnet-4-20250514`.

---

#### TASK-079: Quellenreferenz-Validierung in Briefings implementieren

| Feld             | Wert                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                      |
| **Bereich**      | Backend                                                                                 |
| **Aufwand**      | M                                                                                       |
| **Status**       | 🔴 Offen                                                                                |
| **Quelle**       | D1 Abschnitt 3.5 (Schritt 7: Quellenreferenzen validieren), D4 NF-022, D3 Erklärbarkeit |
| **Abhängig von** | TASK-078                                                                                |
| **Blockiert**    | TASK-080                                                                                |

**Beschreibung:** Post-Processing-Schritt nach der Briefing-Generierung: Quellenreferenzen im generierten Text werden gegen die tatsächlich bereitgestellten Chunks in der Datenbank validiert. Invalide Referenzen (die auf nicht existierende Dokumente verweisen oder vom LLM halluziniert wurden) werden entfernt oder mit einem Warnhinweis versehen. Quellenreferenzen werden in eine strukturierte `source_chunks`-Liste konvertiert.

**Acceptance Criteria:**

- [ ] Jede `[Quelle: Titel, Datum]`-Annotation wird gegen die tatsächlich bereitgestellten Source-Chunks validiert
- [ ] Invalide Referenzen werden entfernt und der Chunk als `low confidence` markiert
- [ ] Valide Referenzen werden als UUID-Liste in `source_chunks` des Briefing-Records gespeichert
- [ ] 100% der verbleibenden Aussagen haben eine validierte Quellenreferenz (D4 NF-022)

**Technische Hinweise:** Matching: Dokumenttitel + Datum gegen `documents`-Tabelle. Fuzzy-Matching bei leicht abweichenden Titeln (LLM kann Titel kürzen/paraphrasieren). Ergebnis wird in `briefings.source_chunks` und `briefings.source_entities` persistiert.

---

#### TASK-080: Briefing-Persistierung in PostgreSQL implementieren

| Feld             | Wert                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                    |
| **Bereich**      | Backend                                                                               |
| **Aufwand**      | S                                                                                     |
| **Status**       | 🔴 Offen                                                                              |
| **Quelle**       | D1 Abschnitt 3.3.1 (briefings-Tabelle), D4 F-022 (Briefing-Caching und Regenerierung) |
| **Abhängig von** | TASK-079, DB-Schema (Agent 1)                                                         |
| **Blockiert**    | –                                                                                     |

**Beschreibung:** Generierte Briefings in der `briefings`-Tabelle in PostgreSQL persistieren. Felder: `user_id`, `briefing_type` (MORNING, MEETING_PREP), `title`, `content` (Markdown), `source_chunks` (UUID-Array), `source_entities` (UUID-Array), `trigger_context` (JSONB), `generated_at`, `expires_at`. Ablaufdaten: Morgenbriefings nach 24h, Meeting-Briefings nach 48h. Nutzer kann Regenerierung auslösen.

**Acceptance Criteria:**

- [ ] Briefing wird vollständig in der `briefings`-Tabelle persistiert (alle Felder)
- [ ] `expires_at` wird gesetzt: Morgenbriefing +24h, Meeting-Briefing +48h
- [ ] `trigger_context` enthält den Auslöser (Kalender-Event-ID, Zeitplan)
- [ ] `source_chunks` und `source_entities` referenzieren die verwendeten Quellen
- [ ] Briefing-Query mit `user_id`-Filter (Mandanten-Isolation)

**Technische Hinweise:** Schema aus D1 Abschnitt 3.3.1 `briefings`-Tabelle. Index `idx_briefings_user_type` für effiziente Abfragen nach Typ und Datum.

---

## Statistik Teil 2

| Bereich                             | Anzahl |
| ----------------------------------- | ------ |
| Konnektoren (Basis + 4 Konnektoren) | 15     |
| Processing Pipeline                 | 10     |
| LLM Gateway                         | 6      |
| Suche-Service                       | 4      |
| Briefing Engine                     | 5      |
| **Gesamt**                          | **40** |

<!-- AGENT_2_LAST: TASK-080 -->
