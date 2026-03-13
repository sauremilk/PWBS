# PWBS – Backlog Teil 3: API, Frontend, Auth, DSGVO & QA

---

## Authentifizierung & User Management

#### TASK-081: JWT-Token-Generierung und -Validierung implementieren

| Feld             | Wert                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| **Priorität**    | P0                                                                   |
| **Bereich**      | Auth                                                                 |
| **Aufwand**      | M                                                                    |
| **Status**       | 🔴 Offen                                                             |
| **Quelle**       | D4 F-002, D1 API Layer (Authentifizierung), D4 NF-014                |
| **Abhängig von** | DB-Schema (Agent 1)                                                  |
| **Blockiert**    | TASK-086, TASK-087, TASK-088, TASK-089, TASK-090, TASK-091, TASK-092 |

**Beschreibung:** JWT-Service implementieren, der Access-Tokens (RS256, 15 Minuten Gültigkeit) und Refresh-Tokens (opaque, 30 Tage, in DB gespeichert) generiert und validiert. RSA-Schlüsselpaar-Management über Umgebungsvariablen. Refresh-Tokens sind revokierbar und werden bei jedem Refresh rotiert.

**Acceptance Criteria:**

- [ ] Access-Token wird mit RS256 signiert und enthält `user_id`, `exp`, `iat` Claims
- [ ] Access-Token-Laufzeit beträgt exakt 15 Minuten (konfigurierbar via Umgebungsvariable)
- [ ] Refresh-Token ist opaque (kein JWT), kryptografisch sicher generiert (`secrets.token_urlsafe()`), und wird in der Datenbank persistiert
- [ ] Token-Validierung prüft Signatur, Ablaufzeitpunkt und Revokationsstatus
- [ ] Abgelaufene oder revokierte Tokens werden mit HTTP 401 abgelehnt

**Technische Hinweise:** RS256 statt HS256 gemäß D1 Security Instructions. Private Key über `PWBS_JWT_PRIVATE_KEY` Umgebungsvariable laden, niemals im Code.

---

#### TASK-082: User-Registrierung mit Argon2-Hashing implementieren

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P0                                                        |
| **Bereich**      | Auth                                                      |
| **Aufwand**      | M                                                         |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D4 F-001, D4 US-1.1, D1 Abschnitt 3.3 (PostgreSQL-Schema) |
| **Abhängig von** | TASK-081, DB-Schema (Agent 1)                             |
| **Blockiert**    | TASK-086                                                  |

**Beschreibung:** Registrierungsservice implementieren, der E-Mail, Passwort (≥ 12 Zeichen, mind. 1 Großbuchstabe, 1 Zahl) und Anzeigename entgegennimmt. Passwort wird mit Argon2 gehasht. Bei Erstellung wird ein nutzer-spezifischer Data Encryption Key (DEK) generiert und mit dem Master Key (KEK) verschlüsselt gespeichert. Generische Fehlermeldung bei bereits registrierter E-Mail.

**Acceptance Criteria:**

- [ ] Passwort wird mit Argon2 gehasht und niemals im Klartext gespeichert
- [ ] Passwort-Validierung erzwingt ≥ 12 Zeichen, mind. 1 Großbuchstabe, 1 Zahl
- [ ] User-DEK wird bei Registrierung generiert und verschlüsselt (Fernet + KEK) in `encryption_key_enc` gespeichert
- [ ] Bei bereits registrierter E-Mail wird generische Fehlermeldung „Registrierung fehlgeschlagen" zurückgegeben (kein E-Mail-Leak)
- [ ] Nach erfolgreicher Registrierung wird ein JWT-Token-Paar (Access + Refresh) ausgegeben

**Technische Hinweise:** DEK-Generierung gemäß D1 Envelope-Encryption-Architektur. Pydantic-Validator für Passwort-Komplexität.

---

#### TASK-083: OAuth2-Login-Flow mit Google als Identity Provider implementieren

| Feld             | Wert                                                            |
| ---------------- | --------------------------------------------------------------- |
| **Priorität**    | P1                                                              |
| **Bereich**      | Auth                                                            |
| **Aufwand**      | L                                                               |
| **Status**       | 🔴 Offen                                                        |
| **Quelle**       | D1 API Layer (Authentifizierung), D1 Abschnitt 3.1 (OAuth-Flow) |
| **Abhängig von** | TASK-081, TASK-082, DB-Schema (Agent 1)                         |
| **Blockiert**    | TASK-086                                                        |

**Beschreibung:** OAuth2-Authorization-Code-Flow mit Google als Identity Provider für Social Login implementieren. Nutzer können sich alternativ zur E-Mail/Passwort-Registrierung über ihr Google-Konto anmelden. Bei erstmaligem Google-Login wird automatisch ein PWBS-Account erstellt. Bei erneutem Login wird der bestehende Account verknüpft.

**Acceptance Criteria:**

- [ ] OAuth2-Auth-URL wird mit korrektem `state`-Parameter (CSRF-Schutz) und OpenID-Connect-Scopes generiert
- [ ] Callback-Endpunkt tauscht Authorization-Code gegen ID-Token und verifiziert die Google-E-Mail
- [ ] Bei erstmaligem Login wird automatisch ein PWBS-Nutzer mit DEK erstellt
- [ ] Bei bestehendem Nutzer (gleiche E-Mail) wird der Account verknüpft und ein JWT-Paar ausgegeben
- [ ] `state`-Parameter wird gegen CSRF-Angriffe validiert

**Technische Hinweise:** Google OAuth2-Credentials über Umgebungsvariablen (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`). Callback-URL in Google Cloud Console konfigurieren.

---

#### TASK-084: Token-Refresh-Endpunkt mit Token-Rotation implementieren

| Feld             | Wert                                              |
| ---------------- | ------------------------------------------------- |
| **Priorität**    | P0                                                |
| **Bereich**      | Auth                                              |
| **Aufwand**      | S                                                 |
| **Status**       | 🔴 Offen                                          |
| **Quelle**       | D4 F-003, D4 Abschnitt 8 (Auth API), D1 API Layer |
| **Abhängig von** | TASK-081, DB-Schema (Agent 1)                     |
| **Blockiert**    | TASK-086                                          |

**Beschreibung:** Token-Refresh-Endpunkt implementieren, der bei Vorlage eines gültigen Refresh-Tokens ein neues Access-Token und ein neues Refresh-Token ausstellt. Das alte Refresh-Token wird dabei invalidiert (Token Rotation). Bei Verwendung eines bereits invalidierten Refresh-Tokens werden alle Tokens des Nutzers revokiert (Replay-Detection).

**Acceptance Criteria:**

- [ ] POST /api/v1/auth/refresh akzeptiert `{refresh_token}` und gibt neues Token-Paar zurück
- [ ] Altes Refresh-Token wird nach Verwendung sofort invalidiert
- [ ] Replay-Detection: Wiederverwendung eines invalidierten Refresh-Tokens revokiert alle aktiven Tokens des Nutzers
- [ ] HTTP 401 bei ungültigem oder abgelaufenem Refresh-Token
- [ ] Neues Refresh-Token hat erneut 30 Tage Gültigkeit

**Technische Hinweise:** Refresh-Token-Familie tracken, um Replay-Detection zu ermöglichen. Token-Revokation über DB-Flag oder Löschen des Token-Eintrags.

---

#### TASK-085: Rate-Limiting-Middleware auf allen öffentlichen Endpunkten implementieren

| Feld             | Wert                                                 |
| ---------------- | ---------------------------------------------------- |
| **Priorität**    | P0                                                   |
| **Bereich**      | Backend                                              |
| **Aufwand**      | M                                                    |
| **Status**       | 🔴 Offen                                             |
| **Quelle**       | D4 NF-015, D1 Middleware-Stack (RateLimitMiddleware) |
| **Abhängig von** | DB-Schema (Agent 1)                                  |
| **Blockiert**    | TASK-086, TASK-087, TASK-088, TASK-089               |

**Beschreibung:** Redis-basierte Rate-Limiting-Middleware implementieren. Allgemeines Limit: 100 Requests/Minute pro authentifiziertem Nutzer. Login-Endpunkte: 5 Versuche/Minute pro IP. Manueller Sync: max. 1 pro Konnektor pro 5 Minuten. Briefing-Generierung: Rate Limit gemäß D4 (429 bei Überschreitung).

**Acceptance Criteria:**

- [ ] 100 Requests/Minute pro Nutzer auf allgemeinen Endpunkten; HTTP 429 bei Überschreitung
- [ ] 5 Requests/Minute pro IP auf Login-Endpunkten (POST /auth/login, /auth/register)
- [ ] 1 manueller Sync pro Konnektor pro 5 Minuten (POST /connectors/{type}/sync)
- [ ] Rate-Limit-Header (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) in jeder Response
- [ ] Redis-Ausfall führt zu Fail-Open (Requests werden durchgelassen, nicht blockiert), mit Logging

**Technische Hinweise:** Redis-basiertes Sliding-Window oder Token-Bucket-Muster. Konfigurierbar über Umgebungsvariablen für verschiedene Endpunkt-Gruppen.

---

## API Layer

#### TASK-086: Auth-API-Endpunkte als FastAPI-Router implementieren

| Feld             | Wert                                                      |
| ---------------- | --------------------------------------------------------- |
| **Priorität**    | P0                                                        |
| **Bereich**      | Backend                                                   |
| **Aufwand**      | M                                                         |
| **Status**       | 🔴 Offen                                                  |
| **Quelle**       | D4 Abschnitt 8 (Auth API), D1 API Layer (Routenübersicht) |
| **Abhängig von** | TASK-081, TASK-082, TASK-083, TASK-084, TASK-085          |
| **Blockiert**    | TASK-096, TASK-117                                        |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/auth/` mit allen Auth-Endpunkten implementieren: POST /register (→ TASK-082), POST /login (E-Mail/Passwort → JWT-Paar), POST /refresh (→ TASK-084), POST /logout (Refresh-Token invalidieren), GET /me (Nutzerprofil). Request/Response-Modelle als Pydantic v2 Schemas definieren. Fehler-Codes gemäß D4 Abschnitt 8.

**Acceptance Criteria:**

- [ ] POST /register gibt `{user_id, access_token, refresh_token}` zurück; Fehler-Codes 400, 409, 422
- [ ] POST /login gibt `{access_token, refresh_token, expires_in}` zurück; generische Fehlermeldung bei ungültigen Credentials (401)
- [ ] POST /refresh gibt neues Token-Paar zurück; 401 bei ungültigem Token
- [ ] POST /logout invalidiert Refresh-Token; 401 bei fehlendem JWT
- [ ] GET /me gibt `{user_id, email, display_name, created_at}` zurück; 401 bei fehlendem JWT

**Technische Hinweise:** Pydantic v2 Response-Modelle mit `model_config = ConfigDict(...)`. OpenAPI-Tags für Swagger-Dokumentation. Response-Objekte vor Default-Parameter-Dependencies platzieren.

---

#### TASK-087: Connectors-API-Endpunkte implementieren

| Feld             | Wert                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                    |
| **Bereich**      | Backend                                                                               |
| **Aufwand**      | L                                                                                     |
| **Status**       | 🔴 Offen                                                                              |
| **Quelle**       | D4 Abschnitt 8 (Connectors API), D1 Abschnitt 3.1 (Connector-Architektur, OAuth-Flow) |
| **Abhängig von** | TASK-081, TASK-085, TASK-093, DB-Schema (Agent 1)                                     |
| **Blockiert**    | TASK-100                                                                              |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/connectors/` implementieren: GET / (verfügbare Konnektor-Typen), GET /status (Status aller verbundenen Quellen), GET /{type}/auth-url (OAuth2-URL generieren), POST /{type}/callback (OAuth2-Callback), POST /{type}/config (Obsidian-Vault-Pfad), DELETE /{type} (Verbindung trennen + Daten löschen), POST /{type}/sync (manueller Sync). Kaskadierte Löschung bei Disconnect gemäß D4 US-5.1.

**Acceptance Criteria:**

- [ ] GET /connectors/ listet alle verfügbaren Konnektor-Typen mit Name, Beschreibung und Auth-Methode
- [ ] GET /connectors/status gibt pro verbundener Quelle Status, Dokumentenanzahl, letzten Sync-Zeitpunkt und ggf. Fehler zurück
- [ ] POST /{type}/callback tauscht OAuth-Code gegen Token und startet initialen Sync (D1 OAuth-Flow)
- [ ] DELETE /{type} widerruft OAuth-Token und löscht alle Daten der Quelle kaskadierend (PostgreSQL, Weaviate, Neo4j)
- [ ] POST /{type}/sync beachtet Rate-Limit (max. 1/5 Min pro Konnektor); gibt 429 bei Überschreitung

**Technische Hinweise:** OAuth-Tokens verschlüsselt in `credentials_enc` speichern (Fernet + User-DEK). `owner_id`-Filter in jeder Query. UNIQUE-Constraint (user_id, source_type) beachten.

---

#### TASK-088: Search-API-Endpunkt implementieren

| Feld             | Wert                                                   |
| ---------------- | ------------------------------------------------------ |
| **Priorität**    | P1                                                     |
| **Bereich**      | Backend                                                |
| **Aufwand**      | M                                                      |
| **Status**       | 🔴 Offen                                               |
| **Quelle**       | D4 Abschnitt 8 (Search API), D4 F-011–F-016, D4 NF-001 |
| **Abhängig von** | TASK-081, TASK-093, Such-Service (Agent 2)             |
| **Blockiert**    | TASK-099                                               |

**Beschreibung:** FastAPI-Endpunkt POST `/api/v1/search/` implementieren, der den Such-Service (Agent 2) aufruft. Entgegennimmt: Query-String, optionale Filter (source_types, date_from, date_to, entity_ids) und Limit (max. 50). Gibt Ergebnisliste mit Chunk-ID, Dokumenttitel, Quelltyp, Datum, Content, Score und Entitäten zurück. Optional: LLM-generierte Antwort mit Quellenreferenzen und Confidence.

**Acceptance Criteria:**

- [ ] POST /search/ akzeptiert `{query, filters?, limit?}` und gibt Ergebnisse innerhalb < 2 Sekunden (p95) zurück
- [ ] Ergebnisliste enthält pro Eintrag: chunk_id, doc_title, source_type, date, content, score, entities
- [ ] Optionale LLM-Antwort (`answer`) mit klickbaren Quellenreferenzen und Confidence-Indikator
- [ ] `owner_id` wird aus JWT extrahiert und als Filter an den Such-Service übergeben (Mandanten-Isolation)
- [ ] Fehler-Codes: 400 (leere Query), 401 (kein JWT), 422 (ungültige Filter)

**Technische Hinweise:** Der Such-Service (Agent 2) wird direkt als Python-Interface aufgerufen (kein HTTP im MVP, gemäß D1 Modularer Monolith).

---

#### TASK-089: Briefings-API-Endpunkte implementieren

| Feld             | Wert                                                             |
| ---------------- | ---------------------------------------------------------------- |
| **Priorität**    | P1                                                               |
| **Bereich**      | Backend                                                          |
| **Aufwand**      | L                                                                |
| **Status**       | 🔴 Offen                                                         |
| **Quelle**       | D4 Abschnitt 8 (Briefings API), D4 F-017–F-022, D1 Abschnitt 3.5 |
| **Abhängig von** | TASK-081, TASK-093, Briefing Engine (Agent 2)                    |
| **Blockiert**    | TASK-097, TASK-098                                               |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/briefings/` implementieren: GET / (paginierte Liste), GET /latest (letztes Briefing pro Typ), GET /{id} (Einzelnes Briefing mit Quellen), POST /generate (Briefing manuell auslösen, ruft Briefing Engine auf), POST /{id}/feedback (Daumen hoch/runter + optionaler Kommentar), DELETE /{id} (Briefing löschen). Rate-Limit auf /generate.

**Acceptance Criteria:**

- [ ] GET /briefings/ gibt paginierte Liste mit `{briefings, total, has_more}` zurück; filterbar nach Typ (morning, meeting_prep)
- [ ] GET /briefings/{id} gibt vollständiges Briefing mit Quellenliste `{chunk_id, doc_title, source_type, date, relevance}` zurück
- [ ] POST /generate ruft die Briefing Engine (Agent 2) auf und gibt `{briefing_id, status: "generating"}` zurück; 429 bei Rate-Limit
- [ ] POST /{id}/feedback speichert Rating (`positive`/`negative`) und optionalen Kommentar mit Briefing-ID und User-ID
- [ ] Ownership-Check: 403 bei Zugriff auf fremde Briefings

**Technische Hinweise:** Briefing Engine wird im MVP direkt als Python-Modul aufgerufen (`await briefing_engine.generate(...)`). Briefings werden bei Generierung asynchron verarbeitet (FastAPI Background Task).

---

#### TASK-090: Knowledge-API-Endpunkte implementieren

| Feld             | Wert                                                               |
| ---------------- | ------------------------------------------------------------------ |
| **Priorität**    | P2                                                                 |
| **Bereich**      | Backend                                                            |
| **Aufwand**      | M                                                                  |
| **Status**       | 🔴 Offen                                                           |
| **Quelle**       | D4 Abschnitt 8 (Knowledge API), D4 F-023–F-025, D1 Abschnitt 3.3.3 |
| **Abhängig von** | TASK-081, TASK-093, DB-Schema (Agent 1)                            |
| **Blockiert**    | TASK-101                                                           |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/knowledge/` implementieren: GET /entities (paginierte, gefilterte Entitätenliste), GET /entities/{id} (Entität mit Verbindungen), GET /entities/{id}/related (verwandte Entitäten bis Tiefe 2), GET /entities/{id}/documents (Dokumente zu einer Entität), GET /graph (Subgraph für D3.js-Visualisierung).

**Acceptance Criteria:**

- [ ] GET /entities gibt paginierte Liste mit `{entities: [{id, type, name, mention_count, last_seen}], total}` zurück; filterbar nach Typ
- [ ] GET /entities/{id} gibt Entitäts-Detail mit verknüpften Entitäten zurück; 403 bei fremder Entität, 404 bei nicht gefunden
- [ ] GET /graph gibt `{nodes: [{id, type, name, size}], edges: [{source, target, relation, weight}]}` zurück; max. 50 Knoten
- [ ] Alle Queries enthalten `WHERE owner_id = $user_id` (Mandanten-Isolation)
- [ ] Neo4j-Abfragen verwenden parametrisierte Cypher-Queries (keine Injection)

**Technische Hinweise:** Graph-Abfragen gegen Neo4j mit `depth`-Parameter (max. 3). PostgreSQL für Entitätenliste (performanter als Graph-Traversal für Listen).

---

#### TASK-091: Documents-API-Endpunkte implementieren

| Feld             | Wert                                               |
| ---------------- | -------------------------------------------------- |
| **Priorität**    | P2                                                 |
| **Bereich**      | Backend                                            |
| **Aufwand**      | S                                                  |
| **Status**       | 🔴 Offen                                           |
| **Quelle**       | D4 Abschnitt 8 (Documents API), D1 Abschnitt 3.3.1 |
| **Abhängig von** | TASK-081, TASK-093, DB-Schema (Agent 1)            |
| **Blockiert**    | TASK-098                                           |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/documents/` implementieren: GET / (paginierte Dokumentenliste, filterbar nach source_type), GET /{id} (Dokument-Metadaten + Chunks mit Content-Preview und Entitäten), DELETE /{id} (kaskadierte Löschung von Chunks, Weaviate-Vektoren und Graph-Referenzen).

**Acceptance Criteria:**

- [ ] GET /documents/ gibt `{documents: [{id, title, source_type, source_id, chunk_count, created_at, updated_at}], total}` zurück
- [ ] GET /documents/{id} gibt Metadaten und Chunks `{id, index, content_preview, entities}` zurück; 403 bei fremdem Dokument
- [ ] DELETE /documents/{id} löscht Dokument kaskadierend aus PostgreSQL, Weaviate und Neo4j
- [ ] Alle Queries enthalten `owner_id`-Filter
- [ ] Fehler-Codes: 401, 403, 404 gemäß D4 Spezifikation

**Technische Hinweise:** Content-Preview in Chunks: Erste 200 Zeichen aus `content_preview`-Spalte. Kaskadierte Löschung in Weaviate über `weaviate_id`-Referenz.

---

#### TASK-092: User-API-Endpunkte implementieren

| Feld             | Wert                                                                  |
| ---------------- | --------------------------------------------------------------------- |
| **Priorität**    | P1                                                                    |
| **Bereich**      | Backend                                                               |
| **Aufwand**      | L                                                                     |
| **Status**       | 🔴 Offen                                                              |
| **Quelle**       | D4 Abschnitt 8 (User API), D4 F-027–F-030, D4 US-5.2, US-5.3, US-5.4  |
| **Abhängig von** | TASK-081, TASK-093, TASK-104, TASK-105, TASK-106, DB-Schema (Agent 1) |
| **Blockiert**    | TASK-102                                                              |

**Beschreibung:** FastAPI `APIRouter` für `/api/v1/user/` implementieren: GET /settings, PATCH /settings (Timezone, Briefing-Autostart, Sprache), POST /export (DSGVO-Export), GET /export/{id} (Export-Status), DELETE /account (Löschung einleiten), POST /account/cancel-deletion, GET /audit-log (letzte 100 Einträge), GET /security (Verschlüsselungsstatus).

**Acceptance Criteria:**

- [ ] PATCH /settings aktualisiert Nutzereinstellungen (timezone, briefing_auto_generate, language); 422 bei ungültigen Werten
- [ ] POST /export startet asynchronen Exportjob und gibt `{export_id, status: "processing"}` zurück; 429 bei laufendem Export
- [ ] DELETE /account erwartet `{password, confirmation: "DELETE"}` und leitet 30-Tage-Karenzfrist ein
- [ ] GET /audit-log gibt letzte 100 Einträge zurück (nur Metadaten, keine Inhalte, kein PII)
- [ ] GET /security gibt Verschlüsselungsstatus pro Speicherschicht, Datenstandort und LLM-Nutzungsinformation zurück

**Technische Hinweise:** Export-Endpunkt delegiert an TASK-104. Account-Löschung delegiert an TASK-105. Audit-Log filtert nach `owner_id`.

---

#### TASK-093: API-Middleware-Stack implementieren

| Feld             | Wert                                                       |
| ---------------- | ---------------------------------------------------------- |
| **Priorität**    | P0                                                         |
| **Bereich**      | Backend                                                    |
| **Aufwand**      | L                                                          |
| **Status**       | 🔴 Offen                                                   |
| **Quelle**       | D1 Middleware-Stack, D1 API Layer, D4 NF-011, NF-013       |
| **Abhängig von** | TASK-081, DB-Schema (Agent 1)                              |
| **Blockiert**    | TASK-087, TASK-088, TASK-089, TASK-090, TASK-091, TASK-092 |

**Beschreibung:** FastAPI-Middleware-Stack in korrekter Reihenfolge implementieren: (1) CORSMiddleware (explizite Allowlist, kein `*` in Produktion), (2) TrustedHostMiddleware, (3) RequestIDMiddleware (UUID pro Request für Tracing), (4) RateLimitMiddleware (→ TASK-085), (5) AuthMiddleware (JWT-Validierung, User-Kontext), (6) AuditMiddleware (schreibende Ops loggen). API-Versionierung `/api/v1/` aufsetzen. Globaler Error-Handler für `PWBSError` und `HTTPException`.

**Acceptance Criteria:**

- [ ] CORS auf explizite Frontend-Domain beschränkt; `credentials: true` aktiviert; kein Wildcard in Produktion
- [ ] Jeder Request erhält eine eindeutige Request-ID im `X-Request-ID` Header (für Tracing)
- [ ] Security-Header gesetzt: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`
- [ ] Globaler Error-Handler gibt strukturierte Fehler `{code, message, detail?}` zurück; keine Stack-Traces in Produktion
- [ ] API-Versionierung über URL-Prefix `/api/v1/`; SwaggerUI und ReDoc in Produktion deaktiviert

**Technische Hinweise:** Middleware-Reihenfolge kritisch: Außen → Innen gemäß D1. Debug-Endpoints über `PWBS_ENV` Umgebungsvariable steuern.

---

## Frontend

#### TASK-094: Next.js App-Router-Grundstruktur und Navigation aufsetzen

| Feld             | Wert                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| **Priorität**    | P0                                                                   |
| **Bereich**      | Frontend                                                             |
| **Aufwand**      | M                                                                    |
| **Status**       | 🔴 Offen                                                             |
| **Quelle**       | D1 Abschnitt 3.7 (Frontend App-Struktur), D2 Phase 2 (Web-Frontend)  |
| **Abhängig von** | –                                                                    |
| **Blockiert**    | TASK-096, TASK-097, TASK-098, TASK-099, TASK-100, TASK-101, TASK-102 |

**Beschreibung:** Next.js-Projekt mit App Router initialisieren. Route-Gruppen anlegen: `(auth)/` für Login/Register (ohne Sidebar), `(dashboard)/` für authentifizierte Seiten (mit Sidebar + Header). Root-Layout mit Provider-Setup (Auth, TanStack Query). Sidebar-Navigation mit Links zu Dashboard, Briefings, Suche, Knowledge Explorer, Konnektoren, Einstellungen. Server/Client-Boundary klar markieren.

**Acceptance Criteria:**

- [ ] Route-Gruppen `(auth)/` und `(dashboard)/` mit separaten Layouts implementiert
- [ ] Sidebar-Navigation mit allen Hauptrouten (Dashboard, Briefings, Suche, Knowledge, Konnektoren, Einstellungen)
- [ ] Root-Layout enthält TanStack Query Provider und Auth-Provider
- [ ] `"use client"` nur wo zwingend nötig; Server Components als Standard
- [ ] Tailwind CSS konfiguriert; TypeScript Strict Mode in `tsconfig.json` aktiviert

**Technische Hinweise:** Struktur gemäß D1 Abschnitt 3.7. Shadcn/ui als Basis-Komponentenbibliothek.

---

#### TASK-095: Typisierte API-Client-Abstraktion erstellen

| Feld             | Wert                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Priorität**    | P0                                                                                      |
| **Bereich**      | Frontend                                                                                |
| **Aufwand**      | M                                                                                       |
| **Status**       | 🔴 Offen                                                                                |
| **Quelle**       | D1 Abschnitt 3.7 (lib/api-client.ts), Copilot-Instructions (Code-Konventionen Frontend) |
| **Abhängig von** | TASK-094                                                                                |
| **Blockiert**    | TASK-096, TASK-097, TASK-098, TASK-099, TASK-100, TASK-101, TASK-102                    |

**Beschreibung:** Typisierte Fetch-Abstraktion in `/src/lib/api/` implementieren. Für jeden Endpunkt-Bereich (Auth, Connectors, Search, Briefings, Knowledge, Documents, User) eigene Funktionen mit vollständigen TypeScript-Typen. Automatische Token-Anhängung, 401-Handling mit Refresh-Redirect, Error-Parsing. Niemals direkte `fetch()`-Aufrufe in Komponenten.

**Acceptance Criteria:**

- [ ] API-Client in `/src/lib/api/` mit Funktionen für alle Endpunkte (auth, connectors, search, briefings, knowledge, documents, user)
- [ ] TypeScript-Typen für alle Request/Response-Objekte in `/src/types/api.ts`
- [ ] Automatische JWT-Anhängung im `Authorization`-Header bei authentifizierten Requests
- [ ] Automatischer Token-Refresh bei 401-Response; Redirect zu Login bei Refresh-Fehler
- [ ] Zentrale Error-Handling-Funktion, die Backend-Fehlerstruktur `{code, message}` parst

**Technische Hinweise:** Kein Axios – nativer Fetch mit Wrapper gemäß D1. TanStack Query Hooks in separaten Hook-Dateien (`/src/hooks/`), die den API-Client nutzen.

---

#### TASK-096: Login- und Registrierungsseiten implementieren

| Feld             | Wert                                                  |
| ---------------- | ----------------------------------------------------- |
| **Priorität**    | P0                                                    |
| **Bereich**      | Frontend                                              |
| **Aufwand**      | M                                                     |
| **Status**       | 🔴 Offen                                              |
| **Quelle**       | D4 US-1.1, D4 User Flow 1, D1 Abschnitt 3.7 ((auth)/) |
| **Abhängig von** | TASK-094, TASK-095, TASK-086, TASK-117                |
| **Blockiert**    | TASK-097                                              |

**Beschreibung:** Login-Seite (`/login`) und Registrierungsseite (`/register`) implementieren. Registrierung: E-Mail, Passwort (mit Inline-Validierung der Komplexitätsanforderungen), Anzeigename. Login: E-Mail, Passwort. Optionaler Google-Login-Button. Generische Fehlermeldungen (kein E-Mail-Leak). Nach erfolgreichem Login/Register: Redirect zum Dashboard. Willkommensdialog nach Erstregistrierung gemäß D4 User Flow 1.

**Acceptance Criteria:**

- [ ] Registrierung: Inline-Passwort-Validierung zeigt fehlende Kriterien (≥ 12 Zeichen, Großbuchstabe, Zahl) an
- [ ] Login: Generische Fehlermeldung „E-Mail oder Passwort falsch" bei fehlgeschlagenem Login
- [ ] Google-Login-Button leitet zum OAuth2-Flow weiter (TASK-083)
- [ ] Nach Erstregistrierung: Willkommensdialog mit Konnektor-Optionen gemäß D4 User Flow 1
- [ ] Netzwerk-Fehler: Fehlermeldung „Verbindungsfehler. Bitte prüfe deine Internetverbindung."

**Technische Hinweise:** Client Component (`"use client"`). JWT-Token nach Login im httpOnly-Cookie oder Auth-Context speichern.

---

#### TASK-097: Dashboard mit Briefing-Übersicht implementieren

| Feld             | Wert                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| **Priorität**    | P1                                                                   |
| **Bereich**      | Frontend                                                             |
| **Aufwand**      | L                                                                    |
| **Status**       | 🔴 Offen                                                             |
| **Quelle**       | D4 F-021, D4 User Flow 2, D1 Abschnitt 3.7 (Schlüssel-Interaktionen) |
| **Abhängig von** | TASK-094, TASK-095, TASK-089, Briefing Engine (Agent 2)              |
| **Blockiert**    | –                                                                    |

**Beschreibung:** Dashboard-Seite als Hauptansicht nach Login implementieren. Hauptinhalt: Aktuelles Morgenbriefing (GET /briefings/latest?type=morning). Darunter: „Nächste Termine"-Karten mit Meeting-Briefing-Buttons. Rechts/unten: Konnektor-Status-Widget (GET /connectors/status). „Briefing jetzt generieren"-Button wenn Morgenbriefing noch nicht verfügbar (vor 06:30 Uhr). TanStack Query für Daten-Fetching mit SWR-Pattern.

**Acceptance Criteria:**

- [ ] Dashboard zeigt aktuelles Morgenbriefing als Hauptinhalt; parallel Konnektor-Status-Widget
- [ ] „Nächste Termine"-Karten mit Meeting-Briefing-Buttons (verlinkt auf TASK-098)
- [ ] „Briefing jetzt generieren"-Button wenn kein aktuelles Briefing verfügbar (ruft POST /briefings/generate auf)
- [ ] Edge Case: Keine Termine/kein Briefing → „Keine Termine heute"-Hinweis gemäß D4 User Flow 2
- [ ] Stale-While-Revalidate mit 5 Minuten Stale-Time für Briefing-Daten

**Technische Hinweise:** Parallel-Fetching von Briefing und Konnektor-Status gemäß D1 Dashboard-Load-Sequenz. Server Component für initiales Laden, Client Components für interaktive Elemente.

---

#### TASK-098: Briefing-Detailansicht mit Quellenverweisen implementieren

| Feld             | Wert                                                  |
| ---------------- | ----------------------------------------------------- |
| **Priorität**    | P1                                                    |
| **Bereich**      | Frontend                                              |
| **Aufwand**      | M                                                     |
| **Status**       | 🔴 Offen                                              |
| **Quelle**       | D4 US-3.3, D4 F-019, D1 Abschnitt 3.5 (Output-Format) |
| **Abhängig von** | TASK-094, TASK-095, TASK-089, TASK-091                |
| **Blockiert**    | –                                                     |

**Beschreibung:** Briefing-Detailseite (`/briefings/[id]`) implementieren. Rendert Briefing-Markdown mit eingebetteten Quellenreferenzen als klickbare Links. Klick auf Quellenreferenz navigiert zum Dokument-Detail im PWBS mit hervorgehobenem Chunk. Am Ende: Vollständige Quellenliste mit Typ, Titel, Datum und Relevanz-Score. Feedback-Buttons (Daumen hoch/runter) gemäß D4 US-3.4.

**Acceptance Criteria:**

- [ ] Briefing-Markdown wird korrekt gerendert; Quellenreferenzen `[Quelle: Titel, Datum]` als klickbare Links
- [ ] Klick auf Quellenreferenz navigiert zu `/documents/{id}` mit hervorgehobenem Chunk
- [ ] Quellen-Bereich am Ende des Briefings listet alle verwendeten Quellen mit Typ-Icon, Titel, Datum, Relevanz
- [ ] Feedback-Buttons „Hilfreich" / „Nicht hilfreich" mit optionalem Freitext-Kommentar (POST /briefings/{id}/feedback)
- [ ] „Original öffnen"-Links für Quellen, die zur Ursprungs-App verlinken (Notion, Zoom etc.)

**Technische Hinweise:** Markdown-Rendering mit `react-markdown` oder `next-mdx-remote`. Custom Renderer für Quellenreferenz-Syntax.

---

#### TASK-099: Suchoberfläche mit Filtern implementieren

| Feld             | Wert                                                                   |
| ---------------- | ---------------------------------------------------------------------- |
| **Priorität**    | P1                                                                     |
| **Bereich**      | Frontend                                                               |
| **Aufwand**      | L                                                                      |
| **Status**       | 🔴 Offen                                                               |
| **Quelle**       | D4 US-2.1–US-2.4, D4 F-011–F-016, D1 Abschnitt 3.7 (Semantische Suche) |
| **Abhängig von** | TASK-094, TASK-095, TASK-088                                           |
| **Blockiert**    | –                                                                      |

**Beschreibung:** Suchseite (`/search`) implementieren. Suchfeld mit Debounce (300ms). Ergebnisliste mit Result-Cards: Textausschnitt (Chunk), Quelltyp-Icon, Dokumenttitel, Datum, Relevanz-Score. Filter-Sidebar: Person, Projekt, Thema (Multi-Select), Quelltyp, Zeitraum. Optional: LLM-generierte Zusammenfassung oberhalb der Ergebnisse. „Original öffnen"-Link pro Ergebnis. Empty State bei keinen Ergebnissen.

**Acceptance Criteria:**

- [ ] Suchfeld mit 300ms Debounce; Ergebnisse erscheinen innerhalb 2 Sekunden
- [ ] Result-Cards mit Chunk-Text, Quelltyp-Icon, Dokumenttitel, Datum und Relevanz-Score
- [ ] Filter nach Person/Projekt/Thema (Multi-Select), Quelltyp und Zeitraum; Filter in URL-State (searchParams)
- [ ] Empty State: „Keine Ergebnisse gefunden" mit Vorschlägen zur Umformulierung (D4 US-2.1)
- [ ] „Original öffnen"-Link pro Ergebnis; Fallback-Meldung wenn Quelle nicht mehr verfügbar (D4 US-2.4)

**Technische Hinweise:** Debounced Search Hook (`/src/hooks/use-search.ts`). Filter-State über URL-searchParams für Bookmarkability. LLM-Antwort als optionale Sektion oberhalb der Ergebnisliste.

---

#### TASK-100: Konnektor-Management-Seite implementieren

| Feld             | Wert                                                            |
| ---------------- | --------------------------------------------------------------- |
| **Priorität**    | P1                                                              |
| **Bereich**      | Frontend                                                        |
| **Aufwand**      | L                                                               |
| **Status**       | 🔴 Offen                                                        |
| **Quelle**       | D4 US-1.2–US-1.6, D4 F-008–F-009, D1 Abschnitt 3.1 (OAuth-Flow) |
| **Abhängig von** | TASK-094, TASK-095, TASK-087                                    |
| **Blockiert**    | –                                                               |

**Beschreibung:** Konnektor-Management-Seite (`/connectors`) implementieren. Übersicht aller verfügbaren Konnektoren (Google Calendar, Notion, Obsidian, Zoom) mit Connect-Buttons. Pro verbundenem Konnektor: Status (aktiv/pausiert/Fehler), Dokumentenanzahl, letzter Sync-Zeitpunkt, Sync-Fortschrittsanzeige. OAuth-Connect-Buttons starten OAuth-Flow. Obsidian: Pfad-Eingabe. Disconnect-Button mit Sicherheitsabfrage. Manueller Sync-Button.

**Acceptance Criteria:**

- [ ] Verfügbare Konnektoren werden als Karten angezeigt; verbundene Konnektoren zeigen Status, Doc-Count, letzten Sync
- [ ] OAuth-Connect-Button leitet zum Provider-OAuth-Screen weiter; nach Rückkehr Status „verbunden"
- [ ] Obsidian: Pfad-Eingabefeld mit Validierung; Fehlermeldung bei ungültigem Vault-Pfad (D4 US-1.4)
- [ ] Disconnect-Button mit Sicherheitsabfrage „Alle importierten Daten dieser Quelle werden unwiderruflich gelöscht" (D4 US-5.1)
- [ ] Animierter Sync-Indikator während laufendem Sync; Fortschrittsanzeige mit Anzahl importierter Dokumente

**Technische Hinweise:** OAuth-Redirect-Handling über Callback-Route. Konnektor-Status per Polling (TanStack Query Refetch-Interval) oder WebSocket.

---

#### TASK-101: Knowledge Explorer implementieren

| Feld             | Wert                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| **Priorität**    | P2                                                                   |
| **Bereich**      | Frontend                                                             |
| **Aufwand**      | XL                                                                   |
| **Status**       | 🔴 Offen                                                             |
| **Quelle**       | D4 US-4.1–US-4.3, D4 F-023–F-025, D1 Abschnitt 3.7 (Knowledge Graph) |
| **Abhängig von** | TASK-094, TASK-095, TASK-090                                         |
| **Blockiert**    | –                                                                    |

**Beschreibung:** Knowledge Explorer (`/knowledge`) implementieren. Entitätenliste: Paginiert, filterbar nach Typ (Personen/Projekte/Themen), sortierbar nach Name, Häufigkeit, letzter Erwähnung. Graphvisualisierung: D3.js Force-Directed Graph mit ausgewählter Entität als Zentrum, Tiefe 2, max. 50 Knoten, farbcodiert nach Typ. Entitäts-Detailansicht: Name, Typ, verknüpfte Entitäten, Zeitleiste der Erwähnungen, zugehörige Dokument-Chunks.

**Acceptance Criteria:**

- [ ] Entitätenliste: Filterbar nach Typ (Person, Project, Topic), sortierbar, paginiert (D4 US-4.1)
- [ ] Graphvisualisierung: Force-Directed Graph (D3.js) mit Entity-Zentrum, Tiefe 1–3, max. 50 Knoten, farbcodiert
- [ ] Klick auf Knoten im Graph: Knoten wird neues Zentrum, Graph aktualisiert sich (D4 US-4.2)
- [ ] Entitäts-Detailseite: Zeitleiste der Erwähnungen, verknüpfte Entitäten, Dokument-Chunks mit Quellenangabe (D4 US-4.3)
- [ ] Klick auf Dokument-Chunk navigiert zur Dokument-Detailansicht

**Technische Hinweise:** D3.js Force-Directed Graph als Client Component. Graph-Daten via GET /knowledge/graph. Entitätsliste als Server Component mit Client-Side-Filterung.

---

#### TASK-102: Profil- und Einstellungsseite implementieren

| Feld             | Wert                                             |
| ---------------- | ------------------------------------------------ |
| **Priorität**    | P2                                               |
| **Bereich**      | Frontend                                         |
| **Aufwand**      | M                                                |
| **Status**       | 🔴 Offen                                         |
| **Quelle**       | D4 US-5.1–US-5.4, D4 F-026–F-030, D4 User Flow 4 |
| **Abhängig von** | TASK-094, TASK-095, TASK-092, TASK-107           |
| **Blockiert**    | –                                                |

**Beschreibung:** Einstellungsseite (`/settings`) implementieren mit Tabs: Profil (Anzeigename, Timezone, Benachrichtigungen), Datenquellen (verbundene Quellen einsehen und trennen – verlinkt auf TASK-100), Datenschutz (Datenexport-Button, Account-Löschung), Sicherheit (Verschlüsselungsstatus → TASK-107). Account-Löschung gemäß D4 User Flow 4 mit Vollbild-Dialog, Passwort-Bestätigung und 30-Tage-Karenzzeit-Hinweis.

**Acceptance Criteria:**

- [ ] Tab „Profil": Anzeigename, Timezone, Briefing-Autostart, Sprache editierbar (PATCH /user/settings)
- [ ] Tab „Datenschutz": „Daten exportieren"-Button startet Exportjob; Fortschrittsanzeige; Download-Link nach Fertigstellung
- [ ] Tab „Account": „Account löschen"-Button öffnet Vollbild-Dialog mit Warnung, Checkbox und Passwort-Bestätigung (D4 User Flow 4)
- [ ] Karenzfrist-Banner: „Dein Account wird am [Datum] gelöscht. [Löschung abbrechen]" bei vorgemerkter Löschung (D4 US-5.3)
- [ ] Tab „Sicherheit": Verschlüsselungsstatus-Anzeige (→ TASK-107)

**Technische Hinweise:** Tabs als URL-basierter State (`/settings?tab=privacy`). Datenexport-Status per Polling auf GET /user/export/{id}.

---

#### TASK-103: Konsistente Loading-, Error- und Empty-States implementieren

| Feld             | Wert                                                  |
| ---------------- | ----------------------------------------------------- |
| **Priorität**    | P2                                                    |
| **Bereich**      | Frontend                                              |
| **Aufwand**      | M                                                     |
| **Status**       | 🔴 Offen                                              |
| **Quelle**       | D4 User Flows 1–4 (Fehlerfälle), D4 NF-004, D4 NF-026 |
| **Abhängig von** | TASK-094                                              |
| **Blockiert**    | –                                                     |

**Beschreibung:** Wiederverwendbare UI-Komponenten für Loading-, Error- und Empty-States erstellen, die in allen Views konsistent eingesetzt werden. Loading: Skeleton-Screens für Dashboard, Briefings, Suche; Spinner für Aktionen. Error: Fehlerkarten mit Fehlerbeschreibung und Retry-Button; Netzwerk-Fehler-Banner. Empty: Kontextbezogene Hinweise (z. B. „Verbinde deine erste Datenquelle" auf leerem Dashboard).

**Acceptance Criteria:**

- [ ] Skeleton-Screen-Komponenten für Dashboard, Briefing-Liste, Suchergebnisse und Entitätenliste
- [ ] Error-Boundary-Komponente mit Fehlerbeschreibung und Retry-Button; fängt unerwartete React-Errors
- [ ] Netzwerk-Fehler-Banner: „Verbindungsfehler. Bitte prüfe deine Internetverbindung." bei Timeout
- [ ] Empty-State-Komponenten mit kontextbezogenen CTA-Buttons (z. B. „Erste Quelle verbinden" auf leerem Dashboard)
- [ ] Frontend Time-to-Interactive < 3 Sekunden (p95) gemäß D4 NF-004

**Technische Hinweise:** Shadcn/ui Skeleton-Komponente als Basis. Next.js `loading.tsx` und `error.tsx` pro Route-Segment nutzen.

---

## Datenschutz & DSGVO

#### TASK-104: DSGVO-Datenexport-Endpunkt implementieren

| Feld             | Wert                                               |
| ---------------- | -------------------------------------------------- |
| **Priorität**    | P1                                                 |
| **Bereich**      | Backend                                            |
| **Aufwand**      | L                                                  |
| **Status**       | 🔴 Offen                                           |
| **Quelle**       | D4 F-027, D4 US-5.2, D4 NF-017 (DSGVO Art. 15, 20) |
| **Abhängig von** | TASK-081, DB-Schema (Agent 1)                      |
| **Blockiert**    | TASK-092                                           |

**Beschreibung:** Asynchronen DSGVO-Datenexport implementieren. Bei Anforderung (POST /user/export) wird ein Background-Job gestartet, der alle Nutzerdaten aus PostgreSQL, Weaviate und Neo4j sammelt und als ZIP-Datei (JSON + Markdown) bereitstellt: Dokument-Metadaten, Chunk-Inhalte, extrahierte Entitäten, generierte Briefings und Audit-Log. Download-Link gültig 24 Stunden. E-Mail-Benachrichtigung bei Verarbeitungszeit > 60 Sekunden.

**Acceptance Criteria:**

- [ ] POST /user/export startet asynchronen Exportjob; gibt `{export_id, status: "processing"}` zurück
- [ ] Exportierte ZIP enthält: Dokumente (JSON), Chunks (Markdown), Entitäten (JSON), Briefings (Markdown), Audit-Log (JSON)
- [ ] Download-Link (GET /user/export/{id}) ist 24 Stunden gültig; danach wird die Datei gelöscht
- [ ] E-Mail-Benachrichtigung bei Verarbeitungszeit > 60 Sekunden gemäß D4 US-5.2
- [ ] Rate Limit: 1 Export pro Nutzer gleichzeitig; 429 bei laufendem Export

**Technische Hinweise:** ZIP-Generierung als FastAPI Background Task. Datei temporär auf S3 speichern. Keine PII in exportierten Audit-Log-Metadaten.

---

#### TASK-105: Kaskadierte Account-Löschung implementieren

| Feld             | Wert                                           |
| ---------------- | ---------------------------------------------- |
| **Priorität**    | P1                                             |
| **Bereich**      | Backend                                        |
| **Aufwand**      | XL                                             |
| **Status**       | 🔴 Offen                                       |
| **Quelle**       | D4 F-028, D4 US-5.3, D4 User Flow 4, D4 NF-019 |
| **Abhängig von** | DB-Schema (Agent 1)                            |
| **Blockiert**    | TASK-092                                       |

**Beschreibung:** Vollständigen Account-Lösch-Workflow implementieren. Dreistufig: (1) Löschung vormerken (30-Tage-Karenzfrist), (2) Während Karenzfrist: eingeschränkter Zugriff, Löschung abbrechen möglich, (3) Nach Ablauf: kaskadierte Löschung über alle drei Datenbanken – PostgreSQL (DELETE CASCADE auf user_id), Weaviate (Tenant löschen), Neo4j (alle Knoten mit userId), Redis (Session-Flush), S3 (Export-Dateien). Cleanup-Job als Scheduler-Task.

**Acceptance Criteria:**

- [ ] DELETE /user/account setzt `deletion_scheduled_at` (now + 30 Tage); erfordert Passwort-Bestätigung
- [ ] Während Karenzfrist: Login möglich, Banner sichtbar, keine neuen Imports; POST /account/cancel-deletion hebt Vormerkung auf
- [ ] Cleanup-Job löscht nach Ablauf: PostgreSQL CASCADE, Weaviate-Tenant, Neo4j-Knoten, Redis-Sessions, S3-Exports
- [ ] Fehlerbehandlung: Job-Retry nach 1 Stunde bei Teillöschung; Alert nach 3 Fehlversuchen (D4 User Flow 4)
- [ ] Bestätigungs-E-Mail nach vollständiger Löschung; Audit-Log-Eintrag bleibt mit `user_id = NULL` (ON DELETE SET NULL)

**Technische Hinweise:** Cleanup-Job als Scheduler-Task (CRON `0 3 * * *` gemäß AGENTS.md). Reihenfolge: Weaviate → Neo4j → PostgreSQL (CASCADE). Bei Fehler: Idempotentes Retry.

---

#### TASK-106: Unveränderliches Audit-Log implementieren

| Feld             | Wert                                                        |
| ---------------- | ----------------------------------------------------------- |
| **Priorität**    | P1                                                          |
| **Bereich**      | Backend                                                     |
| **Aufwand**      | M                                                           |
| **Status**       | 🔴 Offen                                                    |
| **Quelle**       | D4 F-030, D1 Abschnitt 3.3.1 (audit_log-Tabelle), D4 NF-017 |
| **Abhängig von** | DB-Schema (Agent 1)                                         |
| **Blockiert**    | TASK-092, TASK-104                                          |

**Beschreibung:** Audit-Log-Service implementieren, der alle sicherheitsrelevanten Aktionen unveränderlich in der `audit_log`-Tabelle protokolliert. Geloggte Aktionen: `user.registered`, `user.login`, `user.login_failed`, `connection.created`, `connection.deleted`, `data.ingested`, `briefing.generated`, `search.executed`, `data.exported`, `user.deleted`. Append-only: Kein UPDATE/DELETE auf Audit-Log-Einträge. Keine PII in Metadaten.

**Acceptance Criteria:**

- [ ] Alle definierten Aktionen werden in `audit_log` mit user_id, action, resource_type, resource_id, ip_address, created_at gespeichert
- [ ] Append-only: Kein UPDATE/DELETE auf audit_log (außer bei Retention-Bereinigung)
- [ ] Metadaten enthalten keine PII (kein Content, keine E-Mail-Adressen – nur IDs, Zählwerte, Fehlercodes)
- [ ] Fehlgeschlagene Login-Versuche werden als Security-Event geloggt (D1 Security Instructions A09)
- [ ] GET /user/audit-log gibt die letzten 100 Einträge zurück; paginiert, gefiltert nach `owner_id`

**Technische Hinweise:** Audit-Middleware in TASK-093 ruft den Audit-Log-Service bei schreibenden Operationen auf. BIGSERIAL für ID (auto-increment, nicht UUIDs).

---

#### TASK-107: Verschlüsselungsstatus-Anzeige im Frontend implementieren

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P3                           |
| **Bereich**      | Frontend                     |
| **Aufwand**      | S                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D4 US-5.4, D4 F-029          |
| **Abhängig von** | TASK-094, TASK-095, TASK-092 |
| **Blockiert**    | –                            |

**Beschreibung:** Sicherheits-Tab auf der Einstellungsseite implementieren (GET /user/security). Anzeige: Verschlüsselungsstatus pro Speicherschicht (PostgreSQL, Weaviate, Neo4j – jeweils „verschlüsselt" mit Verschlüsselungstyp), OAuth-Token-Verschlüsselungsstatus, Datenstandort (EU – Frankfurt), Hinweis „Deine Daten werden nicht für LLM-Training verwendet".

**Acceptance Criteria:**

- [ ] Pro Speicherschicht wird der Verschlüsselungsstatus angezeigt (PostgreSQL: AES-256, Weaviate: Volume Encryption, Neo4j: Volume Encryption)
- [ ] OAuth-Token-Status: „Verschlüsselt mit nutzer-spezifischem Schlüssel (Fernet)"
- [ ] Datenstandort: „EU – Frankfurt (eu-central-1)"
- [ ] LLM-Nutzung: „Deine Daten werden nicht für externes LLM-Training verwendet"
- [ ] Informationen werden von GET /user/security geladen (keine Hardcoded-Werte im Frontend)

**Technische Hinweise:** Statische Informationen vom Backend bereitgestellt (konfiguriert über Umgebungsvariablen). Visuelle Darstellung mit Status-Badges (grüner Haken).

---

## Testing & QA

#### TASK-108: pytest-Setup mit DB-Fixtures aufsetzen

| Feld             | Wert                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                        |
| **Bereich**      | Testing                                                                   |
| **Aufwand**      | L                                                                         |
| **Status**       | 🔴 Offen                                                                  |
| **Quelle**       | D1 Backend Instructions (Tests), Copilot-Instructions (Code-Konventionen) |
| **Abhängig von** | DB-Schema (Agent 1)                                                       |
| **Blockiert**    | TASK-109, TASK-110                                                        |

**Beschreibung:** pytest-Infrastruktur mit Fixtures für alle drei Datenbanken aufsetzen. PostgreSQL: Testcontainers oder In-Memory SQLite-Fallback; Schema-Migration über Alembic. Weaviate: Testcontainer mit Multi-Tenancy. Neo4j: Testcontainer oder Mock-Layer. Redis: fakeredis. LLM: Mock-Responses via `pytest-mock` / `httpx.MockTransport`. `conftest.py` mit Session-scoped DB-Fixtures und Function-scoped Test-Fixtures. `asyncio_mode = "auto"` in pytest.ini.

**Acceptance Criteria:**

- [ ] `conftest.py` mit Session-scoped Fixtures für PostgreSQL, Weaviate, Neo4j, Redis
- [ ] Testcontainers für PostgreSQL, Weaviate und Neo4j (docker-basiert für Integrationstests)
- [ ] Mock-Fixtures für LLM-Calls (kein Netzwerkzugriff in Unit-Tests)
- [ ] `pytest.ini` mit `asyncio_mode = "auto"` und Marker-Definitionen (`unit`, `integration`, `e2e`)
- [ ] Test-Verzeichnisstruktur: `tests/unit/`, `tests/integration/`, `tests/e2e/`

**Technische Hinweise:** `pytest-asyncio`, `testcontainers-python`, `fakeredis` als Test-Dependencies. Alembic-Migrations im Test-Setup ausführen.

---

#### TASK-109: Backend-Unit-Tests mit 80% Abdeckung schreiben

| Feld             | Wert                                           |
| ---------------- | ---------------------------------------------- |
| **Priorität**    | P2                                             |
| **Bereich**      | Testing                                        |
| **Aufwand**      | XL                                             |
| **Status**       | 🔴 Offen                                       |
| **Quelle**       | D4 NF-011, Copilot-Instructions (Tests)        |
| **Abhängig von** | TASK-108, TASK-081–TASK-093, TASK-104–TASK-106 |
| **Blockiert**    | –                                              |

**Beschreibung:** Unit-Tests für alle Backend-Module schreiben: Auth-Service (JWT-Generierung, Passwort-Hashing, Token-Rotation), API-Router (Request/Response-Validierung, Fehler-Codes), Middleware (Rate-Limiting, CORS), DSGVO-Service (Export, Löschung), Audit-Log. Mindestabdeckung 80% über Coverage-Report. Kein Netzwerkzugriff – alle externen Dependencies gemockt.

**Acceptance Criteria:**

- [ ] Unit-Tests für Auth-Service: Token-Generierung, Token-Validierung, Passwort-Hashing, Replay-Detection
- [ ] Unit-Tests für alle API-Router: Valide/invalide Requests, korrekte Fehler-Codes, Ownership-Checks
- [ ] Unit-Tests für Middleware: Rate-Limiting (Limit erreicht/nicht erreicht), CORS-Header, Auth-Middleware
- [ ] Unit-Tests für DSGVO: Export-Generierung, Löschungs-Workflow, Audit-Log-Integrität
- [ ] Coverage-Report ≥ 80% (`pytest --cov=pwbs --cov-report=html`)

**Technische Hinweise:** `pytest-cov` für Coverage. Parametrisierte Tests für Randfälle (leere Listen, None-Werte, abgelaufene Tokens).

---

#### TASK-110: API-Integrationstests gegen Test-Datenbank implementieren

| Feld             | Wert                               |
| ---------------- | ---------------------------------- |
| **Priorität**    | P1                                 |
| **Bereich**      | Testing                            |
| **Aufwand**      | L                                  |
| **Status**       | 🔴 Offen                           |
| **Quelle**       | D4 NF-003, D1 Backend Instructions |
| **Abhängig von** | TASK-108, TASK-086–TASK-093        |
| **Blockiert**    | –                                  |

**Beschreibung:** Integrationstests für alle API-Endpunkte gegen echte Test-Datenbanken (Testcontainers). Tests prüfen den vollständigen Request-Response-Zyklus inkl. Authentifizierung, Datenbank-Operationen und Fehlerbehandlung. Testdaten-Fixtures simulieren realistische Szenarien (Nutzer mit Konnektoren, Dokumenten, Briefings).

**Acceptance Criteria:**

- [ ] Integrationstests für alle Auth-Endpunkte: Registrierung → Login → Refresh → Logout Lifecycle
- [ ] Integrationstests für Connectors: CRUD-Lifecycle inkl. OAuth-Callback-Simulation und kaskadierter Löschung
- [ ] Integrationstests für Search, Briefings, Knowledge, Documents: Korrekte Responses mit realistischen Testdaten
- [ ] Integrationstests für User-Endpunkte: Export-Workflow, Account-Löschung mit Karenzfrist
- [ ] Alle Tests verifizieren Mandanten-Isolation (kein Cross-User-Zugriff in Responses)

**Technische Hinweise:** `httpx.AsyncClient` mit `app=app` für In-Process-Testing. Testcontainers für PostgreSQL + Weaviate + Neo4j. Marker `@pytest.mark.integration`.

---

#### TASK-111: E2E-Tests für Kernflows implementieren

| Feld             | Wert                                   |
| ---------------- | -------------------------------------- |
| **Priorität**    | P2                                     |
| **Bereich**      | Testing                                |
| **Aufwand**      | L                                      |
| **Status**       | 🔴 Offen                               |
| **Quelle**       | D4 User Flows 1–4, D4 NF-025           |
| **Abhängig von** | TASK-096, TASK-097, TASK-100, TASK-102 |
| **Blockiert**    | –                                      |

**Beschreibung:** End-to-End-Tests mit Playwright für die Kern-User-Flows implementieren: (1) Onboarding-Flow: Registrierung → Konnektor verbinden → erstes Briefing (D4 User Flow 1), (2) Täglicher Nutzungsflow: Login → Dashboard → Briefing lesen → Suche nutzen (D4 User Flow 2), (3) DSGVO-Flow: Datenexport → Account-Löschung → Karenzfrist-Banner (D4 User Flow 4).

**Acceptance Criteria:**

- [ ] E2E-Test Onboarding: Registrierung → Willkommensdialog → Konnektor-Simulation → Briefing-Anzeige
- [ ] E2E-Test Täglicher Flow: Login → Dashboard mit Morgenbriefing → Suche durchführen → Ergebnisse prüfen
- [ ] E2E-Test DSGVO: Datenexport anfordern → Account-Löschung einleiten → Karenzfrist-Banner verifizieren → Löschung abbrechen
- [ ] Tests laufen gegen lokale Test-Umgebung (Docker Compose + Frontend Dev-Server)
- [ ] Onboarding-Dauer ≤ 15 Minuten verifiziert (D4 NF-025 – Zeitmessung im Test)

**Technische Hinweise:** Playwright mit TypeScript. Test-Fixtures für Nutzer-Erstellung und Mock-OAuth. CI-Integration über Docker Compose.

---

#### TASK-112: Load-Tests für 20 gleichzeitige Nutzer implementieren

| Feld             | Wert                        |
| ---------------- | --------------------------- |
| **Priorität**    | P2                          |
| **Bereich**      | Testing                     |
| **Aufwand**      | M                           |
| **Status**       | 🔴 Offen                    |
| **Quelle**       | D4 NF-008, D4 NF-001–NF-003 |
| **Abhängig von** | TASK-086–TASK-093           |
| **Blockiert**    | –                           |

**Beschreibung:** Load-Tests mit k6 oder Locust implementieren, die 20 gleichzeitige Nutzer simulieren. Szenarien: (1) Dashboard-Load (parallele Briefing + Connectors-Status Requests), (2) Suchanfragen (POST /search/), (3) Briefing-Generierung (POST /briefings/generate). Zielwerte: API-Endpunkte < 500ms (p95), Suche < 2s (p95), Briefing-Generierung < 10s (p95).

**Acceptance Criteria:**

- [ ] 20 gleichzeitige Nutzer werden simuliert (D4 NF-008)
- [ ] API-Endpunkte (allgemein) antworten in < 500ms (p95)
- [ ] Semantische Suche antwortet in < 2 Sekunden (p95) unter Last
- [ ] Briefing-Generierung < 10 Sekunden (p95) unter Last
- [ ] Keine Fehler-Rate > 1% unter Normallast; Connection-Pool-Limits werden nicht überschritten

**Technische Hinweise:** k6 bevorzugt (JavaScript-basiert, leichtgewichtig). Test-Skripte in `tests/load/`. Ergebnisse als JSON-Report für CI-Integration.

---

## Monitoring & Observability

#### TASK-113: Structured JSON-Logging implementieren

| Feld             | Wert                                                                                |
| ---------------- | ----------------------------------------------------------------------------------- |
| **Priorität**    | P1                                                                                  |
| **Bereich**      | Backend                                                                             |
| **Aufwand**      | M                                                                                   |
| **Status**       | 🔴 Offen                                                                            |
| **Quelle**       | D1 Middleware-Stack (RequestIDMiddleware), D4 NF-001 (Messmethode: Backend-Logging) |
| **Abhängig von** | TASK-093                                                                            |
| **Blockiert**    | TASK-115                                                                            |

**Beschreibung:** Structured JSON-Logging für alle Backend-Operationen implementieren. Jeder Log-Eintrag enthält: Timestamp, Level, Request-ID (aus Middleware), User-ID (falls authentifiziert), Modul, Message, Dauer (für Performance-Tracking). Keine PII in Logs (kein Content, keine Embeddings, keine Metadaten-Werte). Log-Level konfigurierbar über Umgebungsvariable.

**Acceptance Criteria:**

- [ ] Alle Log-Einträge im JSON-Format mit Feldern: timestamp, level, request_id, user_id, module, message, duration_ms
- [ ] Keine PII in Logs (getestet: kein `content`, kein `email`, keine `metadata`-Werte)
- [ ] Log-Level konfigurierbar via `PWBS_LOG_LEVEL` Umgebungsvariable (DEBUG, INFO, WARNING, ERROR)
- [ ] Request-ID aus TASK-093 (RequestIDMiddleware) wird in jedem Log-Eintrag mitgeführt
- [ ] Request-Dauer wird für alle API-Calls geloggt (Basis für Performance-Metriken)

**Technische Hinweise:** `structlog` oder `python-json-logger` als Logging-Bibliothek. Konfiguration in `pwbs/core/logging.py`.

---

#### TASK-114: Health-Check-Endpunkt implementieren

| Feld             | Wert                                           |
| ---------------- | ---------------------------------------------- |
| **Priorität**    | P1                                             |
| **Bereich**      | Backend                                        |
| **Aufwand**      | S                                              |
| **Status**       | 🔴 Offen                                       |
| **Quelle**       | D1 API Layer (/api/v1/admin/health), D4 NF-006 |
| **Abhängig von** | DB-Schema (Agent 1)                            |
| **Blockiert**    | –                                              |

**Beschreibung:** Health-Check-Endpunkt GET `/api/v1/admin/health` implementieren, der den Status aller drei Datenbanken (PostgreSQL, Weaviate, Neo4j), Redis und der LLM-API-Erreichbarkeit prüft. Keine Authentifizierung erforderlich (für ALB/Monitoring). Response: HTTP 200 wenn alle Komponenten erreichbar, HTTP 503 bei kritischen Ausfällen.

**Acceptance Criteria:**

- [ ] GET /health gibt `{status: "healthy", components: {postgres, weaviate, neo4j, redis, llm_api}}` zurück
- [ ] Pro Komponente: `{status: "up"/"down"/"degraded", latency_ms}` mit tatsächlichem Verbindungstest
- [ ] HTTP 200 wenn PostgreSQL und mindestens eine Suchkomponente (Weaviate oder Keyword-Fallback) erreichbar
- [ ] HTTP 503 wenn PostgreSQL nicht erreichbar (kritischer Ausfall)
- [ ] Kein Auth erforderlich; Rate-Limited auf 10 Requests/Minute pro IP

**Technische Hinweise:** Leichtgewichtige Checks: PostgreSQL `SELECT 1`, Weaviate `/v1/.well-known/ready`, Neo4j Bolt-Ping, Redis PING. Timeout: 5 Sekunden pro Check.

---

#### TASK-115: Error-Tracking mit Sentry einrichten

| Feld             | Wert                |
| ---------------- | ------------------- |
| **Priorität**    | P2                  |
| **Bereich**      | Backend             |
| **Aufwand**      | S                   |
| **Status**       | 🔴 Offen            |
| **Quelle**       | D4 NF-006, D4 AR-08 |
| **Abhängig von** | TASK-093, TASK-113  |
| **Blockiert**    | –                   |

**Beschreibung:** Sentry-SDK für Backend (Python) und Frontend (Next.js) integrieren. Unbehandelte Exceptions automatisch erfassen. Request-ID und User-ID (pseudonymisiert) als Kontext anhängen. PII-Scrubbing aktivieren: Keine E-Mails, Passwörter oder Dokumentinhalte an Sentry. Environment-Tags (development, staging, production). Performance-Tracing für API-Requests.

**Acceptance Criteria:**

- [ ] Sentry-SDK im Backend (FastAPI) und Frontend (Next.js) integriert
- [ ] Unbehandelte Exceptions werden automatisch mit Stack-Trace an Sentry gesendet
- [ ] Request-ID und pseudonymisierte User-ID als Sentry-Context; keine PII (E-Mail, Passwort, Content)
- [ ] Environment-Tags: `PWBS_ENV` wird als Sentry-Environment gesetzt
- [ ] Performance-Tracing: API-Request-Dauer wird als Sentry-Transaction erfasst

**Technische Hinweise:** `sentry-sdk[fastapi]` für Backend. `@sentry/nextjs` für Frontend. DSN über Umgebungsvariable `SENTRY_DSN`. PII-Scrubbing in `before_send` Hook.

---

#### TASK-116: Basis-Metriken erfassen und exponieren

| Feld             | Wert                                                            |
| ---------------- | --------------------------------------------------------------- |
| **Priorität**    | P2                                                              |
| **Bereich**      | Backend                                                         |
| **Aufwand**      | M                                                               |
| **Status**       | 🔴 Offen                                                        |
| **Quelle**       | D4 Abschnitt 10 (Metriken & Erfolgskriterien), D4 NF-001–NF-003 |
| **Abhängig von** | TASK-093, TASK-113                                              |
| **Blockiert**    | –                                                               |

**Beschreibung:** Basis-Metriken für das MVP erfassen: Request-Latenz (p50, p95, p99 pro Endpunkt), Fehlerrate (4xx, 5xx pro Endpunkt), aktive Nutzer (DAU basierend auf Auth-Events), Briefing-Abrufe pro Nutzer/Woche, Suchanfragen pro Nutzer/Woche, verbundene Konnektoren pro Nutzer. Metriken über Structured Logging (TASK-113) und optionalen Prometheus-Endpunkt exponieren.

**Acceptance Criteria:**

- [ ] Request-Latenz (p50, p95, p99) wird pro Endpunkt-Gruppe erfasst und über Logs/Metriken exponiert
- [ ] Fehlerrate (4xx/5xx) wird pro Endpunkt erfasst
- [ ] DAU/MAU-Ratio berechenbar aus Auth-Events im Audit-Log
- [ ] Briefing-Abrufe und Suchanfragen pro Nutzer/Woche aggregierbar
- [ ] Optionaler Prometheus-Endpunkt `/metrics` für Grafana-Integration

**Technische Hinweise:** `prometheus-fastapi-instrumentator` für automatische Request-Metriken. Custom-Metriken für Business-KPIs über Audit-Log-Aggregation.

---

## Ergänzende Tasks

#### TASK-117: Auth-Context-Provider und Token-Refresh im Frontend implementieren

| Feld             | Wert                                                             |
| ---------------- | ---------------------------------------------------------------- |
| **Priorität**    | P0                                                               |
| **Bereich**      | Frontend                                                         |
| **Aufwand**      | M                                                                |
| **Status**       | 🔴 Offen                                                         |
| **Quelle**       | D1 Abschnitt 3.7 (lib/auth.ts, State-Management), D4 User Flow 2 |
| **Abhängig von** | TASK-094, TASK-095, TASK-086                                     |
| **Blockiert**    | TASK-096, TASK-097                                               |

**Beschreibung:** React-Context-Provider für Auth-State implementieren. Verwaltet JWT-Tokens (Access + Refresh), User-Profil und Authentifizierungsstatus. Automatischer Token-Refresh im Hintergrund bei abgelaufendem Access-Token. Redirect zur Login-Seite bei abgelaufenem Refresh-Token. Protected-Route-Wrapper für `(dashboard)/`-Seiten. Session-Persistenz über httpOnly-Cookie oder Secure Storage.

**Acceptance Criteria:**

- [ ] AuthProvider stellt `user`, `isAuthenticated`, `login()`, `logout()`, `refreshToken()` bereit
- [ ] Automatischer Token-Refresh bei 401-Response ohne Nutzer-Unterbrechung (D4 User Flow 2)
- [ ] Redirect zu `/login` bei abgelaufenem Refresh-Token mit Meldung „Sitzung abgelaufen"
- [ ] Protected-Route-Wrapper leitet nicht-authentifizierte Nutzer auf `/login` um
- [ ] Auth-State überlebt Page-Refresh (httpOnly-Cookie oder Secure Storage)

**Technische Hinweise:** React Context für Auth-State gemäß D1 State-Management. Token-Refresh-Logik im API-Client (TASK-095) integriert.

---

#### TASK-118: WebSocket-Verbindung für Echtzeit-Updates implementieren

| Feld             | Wert                                                                             |
| ---------------- | -------------------------------------------------------------------------------- |
| **Priorität**    | P2                                                                               |
| **Bereich**      | Backend                                                                          |
| **Aufwand**      | M                                                                                |
| **Status**       | 🔴 Offen                                                                         |
| **Quelle**       | D1 Abschnitt 3.7 (use-websocket.ts), D1 Abschnitt 3.5 (WebSocket Push), D4 OQ-09 |
| **Abhängig von** | TASK-081, TASK-093                                                               |
| **Blockiert**    | –                                                                                |

**Beschreibung:** WebSocket-Endpunkt in FastAPI implementieren, der authentifizierten Nutzern Echtzeit-Updates sendet. Events: Sync-Fortschritt (Konnektor-Sync gestartet/abgeschlossen), Briefing-Generierung abgeschlossen, Export-Download bereit. Frontend: `use-websocket.ts` Hook, der TanStack Query Cache bei relevanten Events invalidiert.

**Acceptance Criteria:**

- [ ] WebSocket-Endpunkt `/ws` mit JWT-Authentifizierung (Token als Query-Parameter oder Cookie)
- [ ] Server sendet Events: `sync.progress`, `sync.completed`, `briefing.ready`, `export.ready`
- [ ] Frontend-Hook `useWebSocket` verbindet bei Dashboard-Load und invalidiert gezielt TanStack Query Cache
- [ ] Automatische Reconnection bei Verbindungsabbruch (exponentieller Backoff)
- [ ] Graceful Degradation: System funktioniert auch ohne WebSocket (Polling-Fallback)

**Technische Hinweise:** FastAPI WebSocket via `@app.websocket("/ws")`. Fallback: TanStack Query Polling-Intervall (60s) bei WebSocket-Ausfall.

---

#### TASK-119: OpenAPI-Schema-Generierung und API-Dokumentation einrichten

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P2                           |
| **Bereich**      | Backend                      |
| **Aufwand**      | S                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D1 API Layer, D4 Abschnitt 8 |
| **Abhängig von** | TASK-086–TASK-093            |
| **Blockiert**    | –                            |

**Beschreibung:** OpenAPI-Schema-Generierung über FastAPI automatisieren. Alle Endpunkte mit vollständigen Pydantic-Response-Modellen, Fehler-Responses und Beschreibungen versehen. OpenAPI-JSON unter `/api/v1/openapi.json` exportierbar (auch in Produktion). SwaggerUI/ReDoc nur in Development. TypeScript-Typen aus OpenAPI-Schema generierbar (für TASK-095).

**Acceptance Criteria:**

- [ ] OpenAPI 3.1 Schema unter `/api/v1/openapi.json` erreichbar
- [ ] Alle Endpunkte mit Response-Modellen, Fehler-Codes und Beschreibungen dokumentiert
- [ ] SwaggerUI und ReDoc in Development verfügbar; in Produktion deaktiviert
- [ ] TypeScript-Typen können aus Schema generiert werden (`openapi-typescript` oder äquivalent)
- [ ] Schema ist valide (OpenAPI-Validator-Check in CI)

**Technische Hinweise:** FastAPI generiert OpenAPI automatisch aus Pydantic-Modellen. `openapi_url` in Produktion auf `/api/v1/openapi.json` beschränken (ohne UI).

---

#### TASK-120: Frontend-Barrierefreiheit (WCAG 2.1 AA) sicherstellen

| Feld             | Wert                        |
| ---------------- | --------------------------- |
| **Priorität**    | P3                          |
| **Bereich**      | Frontend                    |
| **Aufwand**      | M                           |
| **Status**       | 🔴 Offen                    |
| **Quelle**       | D4 NF-026                   |
| **Abhängig von** | TASK-094, TASK-096–TASK-103 |
| **Blockiert**    | –                           |

**Beschreibung:** Barrierefreiheit gemäß WCAG 2.1 Level AA für alle Kernfunktionen sicherstellen. Semantisches HTML in allen Komponenten. ARIA-Labels für interaktive Elemente (Buttons, Links, Formulare). Keyboard-Navigation für alle Views. Farbkontraste ≥ 4.5:1 für Texte. Fokus-Management bei Dialogen und Modals. Axe/Lighthouse Accessibility-Audit in CI.

**Acceptance Criteria:**

- [ ] Alle interaktiven Elemente sind per Tastatur erreichbar und bedienbar (Tab, Enter, Escape)
- [ ] ARIA-Labels auf allen Buttons, Links und Formularfeldern; semantische HTML-Elemente (nav, main, section)
- [ ] Farbkontraste ≥ 4.5:1 für normalen Text, ≥ 3:1 für großen Text (WCAG AA)
- [ ] Fokus-Management: Dialoge fangen Fokus; Schließen gibt Fokus zurück an Trigger-Element
- [ ] Lighthouse Accessibility Score ≥ 90 auf allen Kernseiten

**Technische Hinweise:** Shadcn/ui-Komponenten sind standardmäßig accessible. `eslint-plugin-jsx-a11y` in ESLint-Konfiguration aktivieren. Axe-core in Playwright-E2E-Tests integrieren.

---

## Statistik Teil 3

| Bereich    | Anzahl |
| ---------- | ------ |
| Auth       | 5      |
| API        | 8      |
| Frontend   | 11     |
| DSGVO      | 4      |
| Testing    | 5      |
| Monitoring | 4      |
| Ergänzend  | 3      |
| **Gesamt** | **40** |

<!-- AGENT_3_LAST: TASK-120 -->
