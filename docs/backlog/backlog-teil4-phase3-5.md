# PWBS – Backlog Teil 4: Phase 3–5 & Klärungspunkte

---

## Phase 3 – Private Beta & Produktreife (Monate 10–15)

---

#### TASK-121: Celery + Redis Queue-Infrastruktur einrichten

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P1                           |
| **Bereich**      | Infra / DevOps               |
| **Aufwand**      | L                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D1 Abschnitt 6.3, D2 Phase 3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)        |
| **Blockiert**    | TASK-122                     |

**Beschreibung:** Celery als Task-Queue mit Redis als Message Broker aufsetzen. Queue-Topologie gemäß D1 Abschnitt 6.3 konfigurieren (ingestion.high, ingestion.bulk, processing.embed, processing.extract, briefing.generate). Redis-Persistenz (AOF) aktivieren, um Nachrichtenverlust bei Redis-Restart zu minimieren.

**Acceptance Criteria:**

- [ ] Celery-Worker starten erfolgreich und verbinden sich mit Redis als Broker
- [ ] Fünf dedizierte Queues sind konfiguriert mit korrekten Prioritäten und Timeouts
- [ ] Redis AOF-Persistenz ist aktiviert; bei Redis-Neustart gehen keine ausstehenden Tasks verloren
- [ ] Docker-Compose und Terraform-Module sind um Celery-Worker-Services erweitert
- [ ] Health-Check-Endpoint `/api/v1/admin/health` meldet Queue-Status (Tiefe, Worker-Anzahl)

**Technische Hinweise:** Redis wird bereits für Caching genutzt (D1 Abschnitt 6.4). Celery ist Python-nativ und reduziert Infrastrukturkomplexität gegenüber AWS SQS (ADR-011). Kritische Jobs zusätzlich in PostgreSQL loggen als Fallback.

---

#### TASK-122: Ingestion- und Processing-Pipeline auf Queue-Worker migrieren

| Feld             | Wert                                           |
| ---------------- | ---------------------------------------------- |
| **Priorität**    | P1                                             |
| **Bereich**      | Backend                                        |
| **Aufwand**      | L                                              |
| **Status**       | 🔴 Offen                                       |
| **Quelle**       | D1 Abschnitt 3.2, D1 Abschnitt 6.2, D2 Phase 3 |
| **Abhängig von** | TASK-121                                       |
| **Blockiert**    | –                                              |

**Beschreibung:** Die im MVP synchron in FastAPI-Background-Tasks laufende Processing-Pipeline auf asynchrone Celery-Worker umstellen. Ingestion-Jobs (Webhook-getriggert und Bulk-Syncs) und Processing-Steps (Embedding, NER, Graph-Build) als eigenständige Celery-Tasks implementieren. Pipeline-Orchestrierung über Celery-Chains/Chords realisieren.

**Acceptance Criteria:**

- [ ] Ingestion-Jobs werden als Celery-Tasks in die korrekte Queue dispatcht (high für Echtzeit, bulk für Backfill)
- [ ] Processing-Schritte (Chunking → Embedding → NER → Graph-Build) laufen als verkettete Celery-Tasks
- [ ] Idempotenz bleibt gewährleistet: Wiederholte Task-Ausführung erzeugt keine Duplikate
- [ ] Retry-Logik mit Exponential Backoff bei transienten Fehlern (max. 3 Retries)
- [ ] Monitoring: Task-Dauer, Fehlerrate und Queue-Tiefe sind als Prometheus-Metriken exportiert

**Technische Hinweise:** Im MVP laufen Ingestion und Processing synchron im FastAPI-Prozess (D1 Abschnitt 3.2). Die Modul-Interfaces bleiben erhalten – nur die Orchestrierung wechselt von direkten Aufrufen zu Queue-Dispatch.

---

#### TASK-123: Gmail-Konnektor – OAuth2 und Google Pub/Sub Push Notifications

| Feld             | Wert                             |
| ---------------- | -------------------------------- |
| **Priorität**    | P1                               |
| **Bereich**      | Backend                          |
| **Aufwand**      | L                                |
| **Status**       | 🔴 Offen                         |
| **Quelle**       | D1 Konnektor-Tabelle, D2 Phase 3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)            |
| **Blockiert**    | TASK-124                         |

**Beschreibung:** Gmail-Konnektor auf Basis des `BaseConnector`-Interfaces implementieren. OAuth2-Flow mit Google-Scopes `gmail.readonly` aufsetzen. Google Pub/Sub Push Notifications konfigurieren, damit neue E-Mails in Echtzeit als Events empfangen werden. Webhook-Endpoint für Pub/Sub-Messages bereitstellen.

**Acceptance Criteria:**

- [ ] OAuth2-Flow für Gmail funktioniert mit korrekten Scopes; Tokens werden verschlüsselt mit User-DEK gespeichert
- [ ] Google Pub/Sub Topic und Subscription sind konfiguriert; Push-Endpoint empfängt Notifications
- [ ] Bei neuer E-Mail wird automatisch ein Ingestion-Job in die Queue geschoben
- [ ] Token-Rotation (Refresh) funktioniert automatisch bei abgelaufenen Access-Tokens
- [ ] Datenschutz: Nur Metadaten und Content werden importiert, keine Anhänge im MVP (opt-in für Metadaten)

**Technische Hinweise:** D1 listet Gmail mit Auth via OAuth2 (Google), Sync via Push Notifications (Pub/Sub) + History API. Pub/Sub erfordert ein Google Cloud-Projekt mit aktivierter Gmail API und Pub/Sub API.

---

#### TASK-124: Gmail-Konnektor – History API, Thread-Resolution und UDF-Normalisierung

| Feld             | Wert                             |
| ---------------- | -------------------------------- |
| **Priorität**    | P1                               |
| **Bereich**      | Backend                          |
| **Aufwand**      | M                                |
| **Status**       | 🔴 Offen                         |
| **Quelle**       | D1 Konnektor-Tabelle, D2 Phase 3 |
| **Abhängig von** | TASK-123                         |
| **Blockiert**    | –                                |

**Beschreibung:** Gmail History API für inkrementellen Sync implementieren. Watermark als `historyId` persistieren. Thread-Resolution: E-Mail-Threads zusammenführen, damit der vollständige Konversationsverlauf als ein logisches Dokument importiert wird. Normalisierung in das Unified Document Format (UDF) mit korrekten Metadaten (Absender, Empfänger, Datum, Thread-ID).

**Acceptance Criteria:**

- [ ] Inkrementeller Sync über `history.list()` mit persistiertem `historyId`-Watermark
- [ ] E-Mail-Threads werden zu einem UDF-Dokument pro Thread zusammengeführt
- [ ] Participants-Feld im UDF enthält alle Absender und Empfänger des Threads
- [ ] Idempotenz: Re-Import derselben E-Mails erzeugt keine Duplikate (content_hash-Prüfung)

**Technische Hinweise:** Die History API gibt nur geänderte Message-IDs zurück; der Content muss separat per `messages.get()` geholt werden. E-Mail-Body als Plaintext (HTML-Stripping) in UDF-Content übernehmen. Datenminimierung: Keine rohen HTML-Bodies langfristig speichern (D1 Abschnitt 5.2).

---

#### TASK-125: Slack-Konnektor – OAuth2 und Events API

| Feld             | Wert                             |
| ---------------- | -------------------------------- |
| **Priorität**    | P1                               |
| **Bereich**      | Backend                          |
| **Aufwand**      | L                                |
| **Status**       | 🔴 Offen                         |
| **Quelle**       | D1 Konnektor-Tabelle, D2 Phase 3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)            |
| **Blockiert**    | TASK-126                         |

**Beschreibung:** Slack-Konnektor auf Basis des `BaseConnector`-Interfaces implementieren. Slack-App mit OAuth2-Flow erstellen (Scopes: `channels:history`, `channels:read`, `users:read`). Events API konfigurieren für Echtzeit-Nachrichten-Events. URL-Verification-Challenge und Event-Signature-Validierung implementieren.

**Acceptance Criteria:**

- [ ] OAuth2-Flow für Slack funktioniert; Bot-Token und User-Token werden verschlüsselt gespeichert
- [ ] Events API Webhook empfängt `message`-Events und validiert Slack-Signaturen (HMAC-SHA256)
- [ ] Neue Nachrichten in konfigurierten Channels lösen automatisch Ingestion-Jobs aus
- [ ] Channel-Auswahl: Nutzer kann bei der Einrichtung Channels für den Import auswählen
- [ ] Rate-Limiting: Tier-1-Konformität mit Slack-Rate-Limits eingehalten

**Technische Hinweise:** D1 listet Slack mit Events API (Webhook) + Cursor-basiertem Backfill. Slack-Event-Signatures müssen mit dem Signing Secret der App verifiziert werden (OWASP A03: Injection-Schutz). Nur öffentliche und vom Nutzer autorisierte Channels importieren.

---

#### TASK-126: Slack-Konnektor – Cursor-basiertes Backfill und Thread-Auflösung

| Feld             | Wert                             |
| ---------------- | -------------------------------- |
| **Priorität**    | P2                               |
| **Bereich**      | Backend                          |
| **Aufwand**      | M                                |
| **Status**       | 🔴 Offen                         |
| **Quelle**       | D1 Konnektor-Tabelle, D2 Phase 3 |
| **Abhängig von** | TASK-125                         |
| **Blockiert**    | –                                |

**Beschreibung:** Historische Slack-Nachrichten über die `conversations.history`-API mit Cursor-basierter Pagination abrufen. Thread-Replies über `conversations.replies` auflösen und mit dem Parent-Message zusammenführen. Reaktionen als Metadaten erfassen. UDF-Normalisierung mit Channel-Name, Autor, Timestamp und Thread-Kontext.

**Acceptance Criteria:**

- [ ] Initialer Backfill importiert alle Nachrichten der letzten 90 Tage in konfigurierten Channels
- [ ] Cursor wird nach jedem erfolgreichen Batch persistiert; Abbruch und Fortsetzung sind möglich
- [ ] Thread-Replies werden dem Parent-Message als zusammenhängendes UDF-Dokument zugeordnet
- [ ] Reaktionen (Emoji-Reactions) werden als Metadaten im UDF gespeichert

**Technische Hinweise:** Slack-API paginiert mit Cursor und liefert max. 200 Messages pro Request. Thread-Replies sind separate API-Calls. Batch-Größe und Rate-Limiting beachten (Tier-1: ~1 Request/Sekunde).

---

#### TASK-127: Google Docs-Konnektor implementieren

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P2                           |
| **Bereich**      | Backend                      |
| **Aufwand**      | L                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D2 Phase 3, D1 Phase-Mapping |
| **Abhängig von** | MVP-Basis (Agent 1–3)        |
| **Blockiert**    | –                            |

**Beschreibung:** Google Docs-Konnektor auf Basis des `BaseConnector`-Interfaces implementieren. OAuth2-Flow mit Google-Scopes für Drive und Docs API. Inkrementeller Sync über `modifiedTime`-Cursor. Dokumenteninhalt als strukturierten Plaintext exportieren (Google Docs JSON → Markdown-Konvertierung). Normalisierung ins UDF.

**Acceptance Criteria:**

- [ ] OAuth2-Flow für Google Docs/Drive funktioniert mit korrekten Scopes
- [ ] Inkrementeller Sync basiert auf `modifiedTime`-Watermark; nur geänderte Docs werden re-importiert
- [ ] Google Docs-Strukturelemente (Überschriften, Listen, Tabellen) werden als Markdown normalisiert
- [ ] Idempotenz: content_hash-basierte Deduplizierung verhindert redundante Verarbeitung
- [ ] Shared Docs: Nur Docs importieren, auf die der Nutzer Zugriff hat; Ownership wird korrekt dem PWBS-Nutzer zugeordnet

**Technische Hinweise:** Google Docs API liefert strukturiertes JSON des Dokumenteninhalts. Die Konvertierung in Markdown muss Überschriften-Hierarchie, Inline-Formatierungen und Tabellen korrekt abbilden. Drive API für Dateiliste + Metadaten, Docs API für Inhalt.

---

#### TASK-128: Outlook-Mail-Konnektor implementieren

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P2                           |
| **Bereich**      | Backend                      |
| **Aufwand**      | L                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D2 Phase 3, D1 Phase-Mapping |
| **Abhängig von** | MVP-Basis (Agent 1–3)        |
| **Blockiert**    | –                            |

**Beschreibung:** Outlook-Mail-Konnektor über Microsoft Graph API implementieren. OAuth2-Flow mit Azure AD (Scopes: `Mail.Read`). Delta-Sync über `deltaLink` für inkrementelle Abfragen. E-Mail-Threads über `conversationId` zusammenführen. UDF-Normalisierung analog zum Gmail-Konnektor.

**Acceptance Criteria:**

- [ ] OAuth2-Flow über Azure AD / Microsoft Identity Platform funktioniert
- [ ] Delta-Sync über Microsoft Graph `$deltatoken` liefert nur neue/geänderte Mails
- [ ] E-Mail-Threads werden über `conversationId` zu einem logischen UDF-Dokument zusammengeführt
- [ ] HTML-Body wird zu Plaintext konvertiert; Anhänge werden als Metadaten referenziert (kein Download im MVP)

**Technische Hinweise:** Microsoft Graph API verwendet OData-Konventionen und Delta-Queries. Azure-App-Registrierung erforderlich. Tenant-Konfiguration: Sowohl persönliche Microsoft-Konten als auch Azure-AD-Organisationskonten unterstützen.

---

#### TASK-129: Entscheidungsunterstützung – Datenmodell und Graph-Schema erweitern

| Feld             | Wert                                              |
| ---------------- | ------------------------------------------------- |
| **Priorität**    | P1                                                |
| **Bereich**      | Backend                                           |
| **Aufwand**      | M                                                 |
| **Status**       | 🔴 Offen                                          |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 4, D1 Abschnitt 3.3.3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)                             |
| **Blockiert**    | TASK-130                                          |

**Beschreibung:** Das Datenmodell für Entscheidungsunterstützung erweitern. PostgreSQL-Tabelle `decisions` mit Feldern für Pro/Contra-Argumente, Annahmen, Abhängigkeiten und Status (pending, made, revised). Neo4j-Schema erweitern: Entscheidungs-Knoten mit Kanten zu Projekten, Meetings und vorangehenden Entscheidungen (`:SUPERSEDES`). API-Endpoints für CRUD auf Entscheidungen bereitstellen.

**Acceptance Criteria:**

- [ ] Alembic-Migration erstellt `decisions`-Tabelle mit Feldern: pro_arguments, contra_arguments, assumptions, dependencies, status, decided_by, decided_at
- [ ] Neo4j-Schema enthält Decision-Knoten mit AFFECTS-, DECIDED_IN- und SUPERSEDES-Kanten
- [ ] API-Endpoints: GET/POST/PATCH `/api/v1/knowledge/decisions` mit owner_id-Isolation
- [ ] NER extrahiert automatisch Entscheidungen aus Dokumenten und verknüpft sie im Graph

**Technische Hinweise:** D1 Abschnitt 3.3.3 definiert bereits Decision-Knoten im Graph-Schema. D3 Kernfunktion 4 fordert „Sichtbarmachung relevanter früherer Erkenntnisse bei neuen Entscheidungen". Die SUPERSEDES-Kante ermöglicht die Nachverfolgung revidierter Entscheidungen.

---

#### TASK-130: Entscheidungsunterstützung – Pro/Contra-UI und Nachverfolgung

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P1                            |
| **Bereich**      | Frontend                      |
| **Aufwand**      | L                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 4 |
| **Abhängig von** | TASK-129                      |
| **Blockiert**    | –                             |

**Beschreibung:** Frontend-Komponenten für Entscheidungsunterstützung implementieren. Entscheidungs-Detailansicht mit Pro/Contra-Spalten, Annahmen-Liste und Abhängigkeiten. Timeline-Darstellung der Entscheidungshistorie pro Projekt. Kontextuelle Einblendung relevanter früherer Entscheidungen beim Erstellen einer neuen Entscheidung.

**Acceptance Criteria:**

- [ ] Entscheidungs-Detailseite zeigt Pro/Contra-Argumente, Annahmen und Abhängigkeiten strukturiert an
- [ ] Timeline-Ansicht zeigt Entscheidungshistorie pro Projekt mit Status (pending, made, revised)
- [ ] Beim Erstellen einer neuen Entscheidung werden automatisch relevante frühere Entscheidungen als Kontext vorgeschlagen (via SearchAgent)
- [ ] Nachverfolgung: Status-Änderungen einer Entscheidung werden mit Quellenreferenz im Audit-Log protokolliert
- [ ] Quellenreferenzen: Jede Entscheidung verlinkt auf die Dokumente/Meetings, in denen sie getroffen wurde

**Technische Hinweise:** React-Komponenten in `components/decisions/` anlegen. Server Components für initiale Daten, Client Components für interaktive Pro/Contra-Bearbeitung. D3 fordert explizit „Was wurde entschieden, warum, und was ist daraus geworden?"

---

#### TASK-131: Aktive Erinnerungen – Follow-up-Detection und Trigger-Engine

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P1                            |
| **Bereich**      | Backend                       |
| **Aufwand**      | L                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 5 |
| **Abhängig von** | MVP-Basis (Agent 1–3)         |
| **Blockiert**    | TASK-132                      |

**Beschreibung:** Engine für aktive Erinnerungen implementieren. Follow-up-Detection: NER um Erkennung von Follow-up-Commitments erweitern ("Ich schicke dir das morgen", "Bis Freitag liefern wir X"). Trigger-Engine: Regelbasiertes System, das anhand von Zeitablauf, Entitäts-Inaktivität und ungelösten offenen Fragen Erinnerungen generiert. Scheduler-Job für tägliche Prüfung überfälliger Follow-ups.

**Acceptance Criteria:**

- [ ] NER extrahiert Follow-up-Commitments mit Deadline und verantwortlicher Person aus Dokumenten
- [ ] Trigger-Engine prüft täglich: überfällige Follow-ups, inaktive Themen (> 30 Tage ohne Erwähnung), offene Fragen ohne Antwort
- [ ] Erinnerungen werden als strukturierte Objekte in PostgreSQL persistiert mit Status (pending, acknowledged, dismissed)
- [ ] API-Endpoint: GET `/api/v1/reminders` liefert offene Erinnerungen sortiert nach Dringlichkeit

**Technische Hinweise:** D3 Kernfunktion 5 beschreibt: „Hinweise auf vergessene Themen, überfällige Follow-ups, wiederkehrende Probleme." Die Detection basiert auf LLM-basierter NER (Erweiterung des Entity-Extraction-Prompts) plus regelbasierter Zeitprüfung.

---

#### TASK-132: Aktive Erinnerungen – Notification-UI und proaktive Fragen

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P2                            |
| **Bereich**      | Frontend                      |
| **Aufwand**      | M                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 5 |
| **Abhängig von** | TASK-131                      |
| **Blockiert**    | –                             |

**Beschreibung:** Frontend-Komponenten für aktive Erinnerungen implementieren. Notification-Center im Dashboard mit Badge-Counter. Erinnerungs-Cards mit Kontext (wann wurde das Thema zuletzt erwähnt, welche Quelle). Proaktive Fragen als interaktive Cards: "Thema X wurde vor 3 Monaten bearbeitet – ist das noch relevant?" mit Aktionen (Acknowledge, Dismiss, Snooze).

**Acceptance Criteria:**

- [ ] Notification-Center im Dashboard-Header zeigt Anzahl offener Erinnerungen als Badge
- [ ] Erinnerungs-Cards zeigen Kontext, Quellenreferenz und Zeitspanne seit letzter Aktivität
- [ ] Proaktive Fragen sind als interaktive Cards implementiert mit Aktionen: "Noch relevant", "Erledigt", "Später erinnern"
- [ ] Nutzer kann Erinnerungsfrequenz in den Einstellungen konfigurieren (täglich/wöchentlich/aus)

**Technische Hinweise:** D3 beschreibt proaktive Fragen als „Fragen wie: Du hast vor drei Monaten über X nachgedacht – ist das noch relevant?" D2 Annahme: Risiko, dass aktive Erinnerungen als aufdringlich empfunden werden – daher konfigurierbare Frequenz.

---

#### TASK-133: Projektbriefings – Generierung, API und Frontend

| Feld             | Wert                                            |
| ---------------- | ----------------------------------------------- |
| **Priorität**    | P1                                              |
| **Bereich**      | Backend / Frontend                              |
| **Aufwand**      | L                                               |
| **Status**       | 🔴 Offen                                        |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 3, D1 Abschnitt 3.5 |
| **Abhängig von** | MVP-Basis (Agent 1–3), TASK-129                 |
| **Blockiert**    | –                                               |

**Beschreibung:** Projektbriefings als dritten Briefing-Typ implementieren. On-Demand-Generierung pro Projekt: Status, Entscheidungshistorie, offene Punkte, beteiligte Personen, relevante Dokumente. Max. 1200 Wörter. Frontend: Projektübersichtsseite mit Briefing-Integration. BriefingAgent um `ProjectBriefing`-Template erweitern.

**Acceptance Criteria:**

- [ ] API-Endpoint POST `/api/v1/briefings/generate` akzeptiert `type: "project"` mit `project_entity_id` als Kontext
- [ ] Projektbriefing enthält: Projektstatus, Entscheidungshistorie, offene Punkte, beteiligte Personen – alle mit Quellenreferenzen
- [ ] Max. 1200 Wörter, LLM-Temperatur 0.3 (sachliche Inhalte)
- [ ] Frontend: Projektübersichtsseite mit On-Demand-Briefing-Button und persistiertem Briefing-Cache

**Technische Hinweise:** D1 Abschnitt 3.5 definiert bereits die Briefing-Trigger-Logik. ProjectBriefing nutzt Neo4j-Abfrage `get_project_history(project_name, owner_id)` für Entscheidungs-Timeline und Weaviate-Suche für relevante Dokumente.

---

#### TASK-134: Persönliches Lernmodell – Arbeitsmuster-Erkennung

| Feld             | Wert                                   |
| ---------------- | -------------------------------------- |
| **Priorität**    | P2                                     |
| **Bereich**      | Backend                                |
| **Aufwand**      | XL                                     |
| **Status**       | 🔴 Offen                               |
| **Quelle**       | D2 Phase 3, D3 Alleinstellungsmerkmale |
| **Abhängig von** | MVP-Basis (Agent 1–3)                  |
| **Blockiert**    | –                                      |

**Beschreibung:** System zur Erkennung individueller Arbeitsmuster, Prioritäten und Denkgewohnheiten implementieren. Analyse von: Meeting-Häufigkeit pro Woche, häufig bearbeitete Themen, bevorzugte Arbeitszeiten, Entscheidungsmuster (schnell vs. iterativ). Ergebnisse als Nutzer-Profil in PostgreSQL persistieren und für Briefing-Personalisierung nutzen.

**Acceptance Criteria:**

- [ ] Wöchentlicher Analyse-Job extrahiert Arbeitsmuster aus den letzten 30 Tagen Aktivitätsdaten
- [ ] Erkannte Muster umfassen: Top-5-Themen, durchschnittliche Meeting-Last, bevorzugte Arbeitszeiten, Entscheidungsgeschwindigkeit
- [ ] Muster werden in einem `user_profile`-Modell in PostgreSQL gespeichert (mit Versionierung)
- [ ] Briefing-Engine verwendet Nutzerprofil zur Priorisierung: Häufigere Themen werden prominenter dargestellt

**Technische Hinweise:** D3 beschreibt als Alleinstellungsmerkmal das „Persönliche Lernmodell: Es lernt individuelle Denk- und Arbeitsmuster, nicht nur generische Wissensstrukturen." Start mit regelbasierter Musteranalyse; LLM-basierte Analyse als optionale Erweiterung.

---

#### TASK-135: Desktop-App – Tauri-Grundgerüst mit WebView und System Tray

| Feld             | Wert                                    |
| ---------------- | --------------------------------------- |
| **Priorität**    | P1                                      |
| **Bereich**      | Frontend                                |
| **Aufwand**      | XL                                      |
| **Status**       | 🔴 Offen                                |
| **Quelle**       | D1 Client Layer, D1 ADR-008, D2 Phase 3 |
| **Abhängig von** | MVP-Basis (Agent 1–3)                   |
| **Blockiert**    | TASK-136                                |

**Beschreibung:** Tauri-basierte Desktop-App als eigenständiges Projekt aufsetzen. WebView lädt die bestehende Next.js-Web-App. System-Tray-Integration mit Quick-Actions (Suche öffnen, heutiges Briefing, letztes Meeting-Briefing). Native Notifications für neue Briefings und Erinnerungen. Auto-Update-Mechanismus.

**Acceptance Criteria:**

- [ ] Tauri-App startet auf Windows, macOS und Linux und zeigt die PWBS-Web-App im WebView
- [ ] System-Tray-Icon mit Kontextmenü: "Dashboard öffnen", "Suche", "Heutiges Briefing"
- [ ] Native OS-Notifications werden bei neuen Briefings und aktiven Erinnerungen angezeigt
- [ ] Auto-Updater prüft auf neue Versionen und installiert Updates im Hintergrund
- [ ] Binary-Größe < 20 MB (Tauri-Vorteil gegenüber Electron)

**Technische Hinweise:** ADR-008 entscheidet Tauri statt Electron: kleinere Binary (~10 MB vs. ~150 MB), geringerer Speicherverbrauch, Rust-Backend für lokale Operationen. Desktop-App nutzt dasselbe Web-Frontend (WebView), nur der System-Layer ist Tauri/Rust.

---

#### TASK-136: Desktop-App – Offline-Modus mit lokalem Datensync

| Feld             | Wert                                       |
| ---------------- | ------------------------------------------ |
| **Priorität**    | P2                                         |
| **Bereich**      | Frontend / Backend                         |
| **Aufwand**      | XL                                         |
| **Status**       | 🔴 Offen                                   |
| **Quelle**       | D1 Designprinzip Offline-First, D2 Phase 3 |
| **Abhängig von** | TASK-135                                   |
| **Blockiert**    | –                                          |

**Beschreibung:** Offline-Modus für die Tauri-Desktop-App implementieren. Lokales SQLite als Offline-Vault für zuletzt abgerufene Briefings, Suchergebnisse und Entitäten. Sync-Mechanismus: Bei Internetverbindung werden lokale Daten mit dem Cloud-Backend synchronisiert. Obsidian-Vault-Zugriff funktioniert auch offline über den lokalen File-System-Watcher.

**Acceptance Criteria:**

- [ ] Letzte 7 Tage Briefings und Top-50 Entitäten werden lokal im SQLite-Vault gecacht
- [ ] Suche funktioniert offline gegen einen lokalen Embedding-Index (Sentence Transformers via Ollama)
- [ ] Sync-Status wird im UI angezeigt: "Online", "Offline – letzte Sync vor X Minuten"
- [ ] Obsidian-Vault-Watcher funktioniert offline; neue Dokumente werden bei Reconnect synchronisiert

**Technische Hinweise:** D1 OQ-005 identifiziert die Offline-Sync-Architektur als offene Frage: CRDT-basierter Sync oder Last-Write-Wins. Für den MVP des Offline-Modus ist Last-Write-Wins ausreichend; CRDT kann in Phase 4 evaluiert werden.

---

#### TASK-137: Pricing und Billing – Stripe-Integration und Abo-Verwaltung

| Feld             | Wert                  |
| ---------------- | --------------------- |
| **Priorität**    | P1                    |
| **Bereich**      | Backend / Frontend    |
| **Aufwand**      | L                     |
| **Status**       | 🔴 Offen              |
| **Quelle**       | D2 Phase 3            |
| **Abhängig von** | MVP-Basis (Agent 1–3) |
| **Blockiert**    | –                     |

**Beschreibung:** Stripe-Integration für Abonnement-Verwaltung implementieren. Zielkorridor 20–50 €/Monat. Stripe Checkout-Session für Erstabschluss, Customer Portal für Selbstverwaltung (Kündigung, Zahlungsart ändern). Webhook für Zahlungsstatus-Updates. Feature-Gating: Ohne aktives Abo eingeschränkter Zugriff (z.B. nur 1 Konnektor, keine Projektbriefings).

**Acceptance Criteria:**

- [ ] Stripe Checkout leitet Nutzer zum Zahlungsflow weiter und erstellt bei Erfolg ein Subscription-Objekt
- [ ] Webhook-Endpoint verarbeitet Stripe-Events (payment_succeeded, subscription_cancelled, payment_failed) idempotent
- [ ] Feature-Gating: Free-Tier (1 Konnektor, 3 Suchen/Tag), Paid-Tier (unbegrenzt) korrekt durchgesetzt
- [ ] Nutzer kann über Stripe Customer Portal Abo kündigen, Zahlungsmethode ändern und Rechnungen einsehen
- [ ] A/B-Testing-Infrastruktur: Verschiedene Preispunkte können pro Nutzerkohorte konfiguriert werden

**Technische Hinweise:** D2 Phase 3 definiert „Zielkorridor: 20–50 €/Monat" und erwähnt „A/B-Tests verschiedener Preispunkte". Stripe-Webhook-Signatur mit Signing Secret verifizieren (HMAC). Subscription-Status in PostgreSQL cachen, um nicht bei jedem Request Stripe zu befragen.

---

#### TASK-138: Erweiterte NER – Ziele, Risiken, Hypothesen und offene Fragen extrahieren

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P1                            |
| **Bereich**      | Backend                       |
| **Aufwand**      | L                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 2 |
| **Abhängig von** | MVP-Basis (Agent 1–3)         |
| **Blockiert**    | TASK-139                      |

**Beschreibung:** Die NER-Pipeline um zusätzliche Entitätstypen erweitern: Ziele, Risiken, Hypothesen und offene Fragen. LLM-basiertes Entity-Extraction-Prompt erweitern. Neue Entitätstypen in PostgreSQL, Weaviate und Neo4j persistieren. Graph-Schema um entsprechende Knoten-Labels und Kanten erweitern (GOAL, RISK, HYPOTHESIS, OPEN_QUESTION).

**Acceptance Criteria:**

- [ ] Entity-Extraction-Prompt extrahiert neben Personen/Projekten/Themen/Entscheidungen auch: Ziele, Risiken, Hypothesen, offene Fragen
- [ ] Neue Entitätstypen sind in der `entities`-Tabelle als entity_type gespeichert
- [ ] Neo4j-Graph enthält neue Knotentypen mit Kanten zu Projekten und Dokumenten
- [ ] Knowledge Explorer zeigt neue Entitätstypen als filterbare Kategorien an

**Technische Hinweise:** D3 Kernfunktion 2 fordert: „Automatische Extraktion von [...] Zielen, Risiken, offenen Fragen und Hypothesen." Das bestehende LLM-Prompt in `pwbs/prompts/entity_extraction.jinja2` muss um die neuen Kategorien erweitert werden. Konfidenz-Schwelle wie bei bestehender NER: > 0.75 für Graph-Aufnahme.

---

#### TASK-139: Mustererkennung – Wiederkehrende Themen und sich ändernde Annahmen

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P2                            |
| **Bereich**      | Backend                       |
| **Aufwand**      | L                             |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 3, D3 Kernfunktion 2 |
| **Abhängig von** | TASK-138                      |
| **Blockiert**    | –                             |

**Beschreibung:** Mustererkennung über die im Knowledge Graph gespeicherten Entitäten implementieren. Erkennung von: wiederkehrende Themen (selbes Topic in > 3 verschiedenen Kontexten innerhalb von 30 Tagen), sich ändernde Annahmen (Hypothese wird in späterem Dokument widerlegt), ungelöste Muster (offene Frage wird wiederholt gestellt). Ergebnisse als Teil der Briefings und als dedizierte Insights-Seite bereitstellen.

**Acceptance Criteria:**

- [ ] Wöchentlicher Analyse-Job identifiziert wiederkehrende Themen über Neo4j-Graph-Traversals
- [ ] Sich ändernde Annahmen werden durch Vergleich von Hypothesen-Entitäten über Zeitverlauf erkannt
- [ ] Erkannte Muster werden in Morgenbriefings als „Muster im Blick"-Abschnitt integriert
- [ ] Insights-Endpunkt: GET `/api/v1/knowledge/patterns` liefert erkannte Muster mit Quellenreferenzen

**Technische Hinweise:** D3 beschreibt: „Erkennung von Mustern: Was wiederholt sich? Was wurde vergessen? Welche Annahmen ändern sich?" Graph-Queries nutzen zeitliche Co-Occurrence-Analyse und Kantengewichtung (D1 Abschnitt 3.3.3).

---

#### TASK-140: Browser-Extension-Prototyp für Kontextanzeige

| Feld             | Wert                         |
| ---------------- | ---------------------------- |
| **Priorität**    | P3                           |
| **Bereich**      | Frontend                     |
| **Aufwand**      | M                            |
| **Status**       | 🔴 Offen                     |
| **Quelle**       | D2 Phase 3, D1 Phase-Mapping |
| **Abhängig von** | MVP-Basis (Agent 1–3)        |
| **Blockiert**    | –                            |

**Beschreibung:** Browser-Extension (Chrome/Firefox) als Prototyp entwickeln. Kontextuelle Sidebar, die beim Besuch von Notion-Seiten, Google Docs oder Gmail relevanten PWBS-Kontext einblendet. Quick-Search direkt aus der Extension. Authentifizierung über bestehenden JWT-Token (Session-Sharing mit Web-App).

**Acceptance Criteria:**

- [ ] Chrome-Extension installierbar und authentifiziert sich über gespeicherten JWT
- [ ] Sidebar zeigt relevante Entitäten und verknüpfte Dokumente basierend auf der aktuell besuchten Seite
- [ ] Quick-Search-Feld in der Extension löst semantische Suche über die PWBS-API aus
- [ ] Prototyp-Scope: Nur Chrome, nur Notion/Google Docs, keine Daten-Ingestion über Extension

**Technische Hinweise:** D1 Phase-Mapping listet Browser-Extension als „Prototyp" in Phase 3, „Extension" in Phase 4. D3 erwähnt Browser-History als potenzielle Datenquelle (nicht im Prototyp). Extension nutzt ausschließlich die bestehende Search-API.

---

#### TASK-141: Slack-Bot-Prototyp für Quick Search und Briefings

| Feld             | Wert                            |
| ---------------- | ------------------------------- |
| **Priorität**    | P3                              |
| **Bereich**      | Backend                         |
| **Aufwand**      | M                               |
| **Status**       | 🔴 Offen                        |
| **Quelle**       | D2 Phase 3, D1 Client Layer     |
| **Abhängig von** | TASK-125, MVP-Basis (Agent 1–3) |
| **Blockiert**    | –                               |

**Beschreibung:** Slack-Bot als Prototyp implementieren, der in Slack-Channels und DMs PWBS-Funktionalität bereitstellt. Slash-Commands: `/pwbs search <query>` für semantische Suche, `/pwbs briefing` für Abruf des aktuellen Morgenbriefings. Bot-Antworten mit Quellenreferenzen und Links zur PWBS-Web-App.

**Acceptance Criteria:**

- [ ] Slash-Command `/pwbs search <query>` führt semantische Suche aus und liefert Top-3-Ergebnisse mit Quellenangabe als Slack-Message
- [ ] Slash-Command `/pwbs briefing` liefert das aktuelle Morgenbriefing als formatierte Slack-Message
- [ ] Bot authentifiziert den Slack-User gegen den PWBS-Account (Mapping Slack-User-ID ↔ PWBS-User-ID)
- [ ] Rate-Limiting: Max. 10 Bot-Anfragen pro Nutzer pro Stunde

**Technische Hinweise:** D1 Client Layer zeigt Slack-Bot als Phase-3-Deliverable mit Funktionen „Context Sidebar" und „Quick Search". Der Bot nutzt die bestehende Search- und Briefing-API. Slack-Bot-Token separat von Connector-Token verwalten.

---

#### TASK-142: Notion-Sidebar-Prototyp

| Feld             | Wert                                   |
| ---------------- | -------------------------------------- |
| **Priorität**    | P3                                     |
| **Bereich**      | Frontend                               |
| **Aufwand**      | M                                      |
| **Status**       | 🔴 Offen                               |
| **Quelle**       | D2 Phase 3, D3 Technische Überlegungen |
| **Abhängig von** | MVP-Basis (Agent 1–3)                  |
| **Blockiert**    | –                                      |

**Beschreibung:** Notion-Integration als Sidebar-Prototyp evaluieren und implementieren. Da Notion keine native Sidebar-API bietet, wird dies als Browser-Extension-Feature realisiert: Wenn eine Notion-Seite im Browser geöffnet ist, zeigt die Extension eine Kontextleiste mit verknüpften Entitäten, verwandten Dokumenten und offenen Fragen zum aktuellen Notion-Thema.

**Acceptance Criteria:**

- [ ] Browser-Extension erkennt geöffnete Notion-Seiten und extrahiert den Seitentitel als Suchkontext
- [ ] Sidebar zeigt verknüpfte PWBS-Entitäten (Personen, Projekte, Entscheidungen) zur aktuellen Notion-Seite
- [ ] Verwandte Dokumente aus anderen Quellen (Zoom-Transkripte, Kalender) werden als Links angezeigt

**Technische Hinweise:** D3 erwähnt „Notion-Sidebar" unter Tool-Integrationen. Da Notion keine direkten Third-Party-Sidebars unterstützt, wird dies über die Browser-Extension (TASK-140) als Feature-Erweiterung realisiert.

---

#### TASK-143: Weekly Briefings implementieren

| Feld             | Wert                               |
| ---------------- | ---------------------------------- |
| **Priorität**    | P2                                 |
| **Bereich**      | Backend                            |
| **Aufwand**      | M                                  |
| **Status**       | 🔴 Offen                           |
| **Quelle**       | D1 Abschnitt 3.5, D1 Phase-Mapping |
| **Abhängig von** | MVP-Basis (Agent 1–3)              |
| **Blockiert**    | –                                  |

**Beschreibung:** Weekly Briefing als vierten Briefing-Typ implementieren. Automatische Generierung freitags 17:00 Uhr (Nutzer-Timezone). Wochenzusammenfassung: Wichtigste Themen, getroffene Entscheidungen, offene Punkte, Fortschritt pro Projekt. Max. 600 Wörter. Scheduler-Job und BriefingAgent-Template erweitern.

**Acceptance Criteria:**

- [ ] Scheduler triggert Weekly Briefing freitags gemäß Nutzer-Timezone
- [ ] Briefing enthält: Top-Themen der Woche, getroffene Entscheidungen, offene Punkte, Projektfortschritt – mit Quellenreferenzen
- [ ] Max. 600 Wörter, LLM-Temperatur 0.3
- [ ] Frontend: Weekly Briefing als eigener Tab in der Briefing-Übersicht abrufbar

**Technische Hinweise:** D1 Abschnitt 3.5 definiert `weekly_digest` mit Schedule `0 8 * * 1` (Montag 08:00). D2 Phase 3 fordert Weekly Briefings. AGENTS.md SchedulerAgent definiert `weekly_briefing` mit `cron "0 17 * * 5"` (Freitag 17:00). Hier Freitag 17:00 gemäß AGENTS.md verwenden.

---

## Phase 4 – Launch & Skalierung (Monate 16–21)

---

#### TASK-144: Multi-Tenancy – Team-Features und gemeinsames Wissensmodell

| Feld             | Wert                                 |
| ---------------- | ------------------------------------ |
| **Priorität**    | P1                                   |
| **Bereich**      | Backend / Frontend                   |
| **Aufwand**      | XL                                   |
| **Status**       | 🔴 Offen                             |
| **Quelle**       | D2 Phase 4, D1 Abschnitt 6.5         |
| **Abhängig von** | MVP-Basis (Agent 1–3), Phase 3-Tasks |
| **Blockiert**    | –                                    |

**Beschreibung:** Multi-Tenancy für Teams (3–10 Personen) implementieren. Gemeinsamer Weaviate-Tenant und Neo4j-Subgraph pro Organisation. Zugriffskontrolle: Owner, Member, Viewer. Private vs. Shared Entities. Onboarding-Unterstützung: Neue Teammitglieder erhalten automatisch relevanten Projektkontext. Wissensübergabe bei Rollenwechseln.

**Acceptance Criteria:**

- [ ] Organisationsmodell in PostgreSQL mit Rollenkonzept (Owner, Member, Viewer)
- [ ] Shared Knowledge Space: Team-Mitglieder teilen Weaviate-Tenant und Neo4j-Subgraph für als „team-sichtbar" markierte Entitäten
- [ ] Onboarding-Briefing: Neues Teammitglied erhält automatisch generiertes Briefing zum aktuellen Projektstand

**Technische Hinweise:** D1 Abschnitt 6.5 beschreibt die Isolation-Strategie: logische Isolation (Phase 3) → physische Isolation (Phase 4+ für Enterprise). D2 Phase 4 fordert Team-Features für 3–10 Personen mit gemeinsamer Wissensbasis.

---

#### TASK-145: Self-Hosting – Docker-Compose und Helm-Chart für On-Premise-Deployment

| Feld             | Wert                                                            |
| ---------------- | --------------------------------------------------------------- |
| **Priorität**    | P1                                                              |
| **Bereich**      | Infra / DevOps                                                  |
| **Aufwand**      | XL                                                              |
| **Status**       | 🔴 Offen                                                        |
| **Quelle**       | D1 Designprinzip Cloud+On-Premise, D2 Phase 4, D1 Abschnitt 5.3 |
| **Abhängig von** | MVP-Basis (Agent 1–3), Phase 3-Tasks                            |
| **Blockiert**    | –                                                               |

**Beschreibung:** Self-Hosting-Option für datenschutzsensible Nutzer und Enterprise-Kunden bereitstellen. Docker-Compose-Setup für einfaches lokales Deployment. Helm-Chart für Kubernetes-Deployment. Konfiguration für lokale LLM-Modelle (Ollama) statt Cloud-APIs. Vollständige Dokumentation für Installation, Konfiguration und Wartung.

**Acceptance Criteria:**

- [ ] `docker compose up` startet die komplette PWBS-Instanz (API, PostgreSQL, Weaviate, Neo4j, Redis) mit einem Befehl
- [ ] Helm-Chart ermöglicht Kubernetes-Deployment mit konfigurierbaren Replicas, Ressourcen und Persistenz
- [ ] LLM-Konfiguration: Umschaltung von Cloud-LLMs auf Ollama (lokal) über Umgebungsvariable

**Technische Hinweise:** D1 Designprinzip: „Self-Hosting ist ein Deployment-Profil, kein Fork." D1 Abschnitt 5.3 definiert On-Premise-Modus mit Docker-Compose auf kundeneigener Infrastruktur. Alle Secrets müssen über Umgebungsvariablen konfigurierbar sein.

---

#### TASK-146: Horizontale Skalierung – Load Balancer, Connection Pooling, Caching und CDN

| Feld             | Wert                       |
| ---------------- | -------------------------- |
| **Priorität**    | P1                         |
| **Bereich**      | Infra                      |
| **Aufwand**      | L                          |
| **Status**       | 🔴 Offen                   |
| **Quelle**       | D1 Abschnitt 6, D2 Phase 4 |
| **Abhängig von** | TASK-121, Phase 3-Tasks    |
| **Blockiert**    | –                          |

**Beschreibung:** Infrastruktur für horizontale Skalierung ausbauen. API-Server auf 3+ ECS-Tasks skalieren mit ALB. PgBouncer für PostgreSQL Connection Pooling. Redis-Cluster für verteiltes Caching. CDN (CloudFront) für statische Frontend-Assets. Read-Replicas für PostgreSQL. Weaviate-Cluster (2 Nodes) für Verfügbarkeit.

**Acceptance Criteria:**

- [ ] API skaliert horizontal auf 3+ Instanzen hinter ALB ohne Session-Abhängigkeit
- [ ] PgBouncer-Pool verwaltet PostgreSQL-Connections mit max. 50 Verbindungen pro Pool
- [ ] Redis-Cluster mit 2+ Nodes für Cache-Hochverfügbarkeit

**Technische Hinweise:** D1 Abschnitt 6.1 identifiziert Bottlenecks: Embedding-Generierung, LLM-Calls, Weaviate Search, Neo4j-Queries, PostgreSQL Writes. D1 Abschnitt 6.4 definiert die Caching-Strategie (API Response Cache, Search Cache, Embedding Cache, LLM Cache).

---

#### TASK-147: Sicherheitsaudit und DSGVO-Zertifizierung

| Feld             | Wert                                 |
| ---------------- | ------------------------------------ |
| **Priorität**    | P1                                   |
| **Bereich**      | Docs / Infra                         |
| **Aufwand**      | L                                    |
| **Status**       | 🔴 Offen                             |
| **Quelle**       | D2 Phase 4, D1 Abschnitt 5           |
| **Abhängig von** | MVP-Basis (Agent 1–3), Phase 3-Tasks |
| **Blockiert**    | TASK-148                             |

**Beschreibung:** Unabhängiges Sicherheitsaudit durch einen externen Dienstleister durchführen. DSGVO-Dokumentation vervollständigen: Technische und Organisatorische Maßnahmen (TOM), Verarbeitungsverzeichnis, Auftragsverarbeitungsverträge (AVV) mit allen Dienstleistern. Transparenzbericht zur Datennutzung veröffentlichen. Optional: DSGVO-Zertifizierung anstreben.

**Acceptance Criteria:**

- [ ] Externes Sicherheitsaudit durchgeführt; alle kritischen und hohen Findings geschlossen
- [ ] DSGVO-Dokumentation vollständig: TOM, Verarbeitungsverzeichnis, AVVs mit AWS/OpenAI/Anthropic/Vercel

**Technische Hinweise:** D1 Abschnitt 5.2 listet bestehende DSGVO-Maßnahmen. D2 Phase 4 fordert „Unabhängiges Sicherheitsaudit; DSGVO-Dokumentation und Zertifizierung; Transparenzbericht zur Datennutzung." AVVs sind in `/legal/avv/` zu dokumentieren.

---

#### TASK-148: Public Beta Infrastruktur und Community-Building

| Feld             | Wert          |
| ---------------- | ------------- |
| **Priorität**    | P2            |
| **Bereich**      | DevOps / Docs |
| **Aufwand**      | M             |
| **Status**       | 🔴 Offen      |
| **Quelle**       | D2 Phase 4    |
| **Abhängig von** | TASK-147      |
| **Blockiert**    | –             |

**Beschreibung:** Infrastruktur für die Public Beta vorbereiten: Skalierung auf 1.000–5.000 aktive Nutzer, Onboarding-Automatisierung, Content-Marketing-Pipeline (Blog, Docs, Tutorials). Community-Kanäle aufsetzen (Discord/Discourse). Monitoring-Dashboards für Wachstumsmetriken und Nutzerfeedback.

**Acceptance Criteria:**

- [ ] Infrastruktur skaliert nachweislich auf 1.000+ gleichzeitige Nutzer (Load-Test mit k6)
- [ ] Automatisierter Onboarding-Flow: Registrierung → erster Konnektor → erstes Briefing ohne manuelle Intervention
- [ ] Community-Plattform (Discord oder Discourse) eingerichtet mit Moderationsregeln und Feedback-Channel

**Technische Hinweise:** D2 Phase 4 beschreibt: „Public Beta mit gezieltem Marketing-Push (Content-Marketing, Community-Building, Partnerschaften mit Produktivitäts-Communities)." Ziel: 1.000–5.000 aktive Nutzer.

---

#### TASK-149: B2B-Pilot Features für Beratungshäuser und Tech-Startups

| Feld             | Wert               |
| ---------------- | ------------------ |
| **Priorität**    | P2                 |
| **Bereich**      | Backend / Frontend |
| **Aufwand**      | L                  |
| **Status**       | 🔴 Offen           |
| **Quelle**       | D2 Phase 4         |
| **Abhängig von** | TASK-144           |
| **Blockiert**    | –                  |

**Beschreibung:** B2B-spezifische Features für erste Pilotkunden implementieren. Admin-Dashboard für Organisations-Admins (Nutzerverwaltung, Konnektor-Konfiguration). Organisations-weite Konnektoren (ein Slack-Workspace für alle Mitglieder). SLA-konforme Uptime-Garantien. Angepasstes Onboarding für B2B-Kunden.

**Acceptance Criteria:**

- [ ] Admin-Dashboard: Organisationsadministratoren können Nutzer einladen, Rollen zuweisen und Konnektoren verwalten
- [ ] Organisations-weite Konnektoren: Ein Slack- oder Google-Workspace-Konnektor kann für alle Teammitglieder geteilt werden
- [ ] B2B-Onboarding-Wizard: Geführter Setup-Prozess für 3–10 Teammitglieder mit Konnektorauswahl und Rollenzuweisung

**Technische Hinweise:** D2 Phase 4: „Erste B2B-Piloten mit Beratungshäusern oder Tech-Startups." Ziel: ≥ 3 zahlende B2B-Pilotkunden. B2B-Features bauen auf der Multi-Tenancy-Grundlage (TASK-144) auf.

---

## Phase 5 – Plattform & Vertikalisierung (Monate 22–36)

---

#### TASK-150: Öffentliche API und Developer Portal

| Feld             | Wert            |
| ---------------- | --------------- |
| **Priorität**    | P1              |
| **Bereich**      | Backend / Docs  |
| **Aufwand**      | XL              |
| **Status**       | 🔴 Offen        |
| **Quelle**       | D2 Phase 5      |
| **Abhängig von** | Phase 3–4 Tasks |
| **Blockiert**    | TASK-151        |

**Beschreibung:** Öffentliche REST-API bereitstellen, über die externe Tools das Wissensmodell lesen und anreichern können. Developer Portal mit interaktiver API-Dokumentation (OpenAPI/Swagger), API-Key-Management, Rate-Limiting pro API-Key und Nutzungsstatistiken. Sandbox-Umgebung für Entwickler.

**Acceptance Criteria:**

- [ ] Öffentliche API v1 mit Endpunkten für Search, Entities, Briefings und Document-Ingestion (rate-limited)
- [ ] Developer Portal mit interaktiver API-Dokumentation, API-Key-Generierung und Nutzungs-Dashboard

**Technische Hinweise:** D2 Phase 5: „Offene API, über die externe Tools das Wissensmodell lesen und anreichern können." Die interne API (D1 Abschnitt 3.6) wird um öffentliche Endpunkte erweitert mit separatem Auth-Mechanismus (API-Keys statt JWT).

---

#### TASK-151: Marketplace für Community-Integrationen

| Feld             | Wert               |
| ---------------- | ------------------ |
| **Priorität**    | P2                 |
| **Bereich**      | Backend / Frontend |
| **Aufwand**      | XL                 |
| **Status**       | 🔴 Offen           |
| **Quelle**       | D2 Phase 5         |
| **Abhängig von** | TASK-150           |
| **Blockiert**    | –                  |

**Beschreibung:** Marketplace-Plattform für Community- und Drittanbieter-Integrationen aufbauen. Plugin-Architektur: Externe Entwickler können Konnektoren, Briefing-Templates und Processing-Schritte als Plugins bereitstellen. Review-Prozess für Sicherheit und Qualität. Installations- und Konfigurationsflow im Frontend.

**Acceptance Criteria:**

- [ ] Plugin-SDK mit Dokumentation für Connector-, Briefing-Template- und Processing-Plugins
- [ ] Marketplace-UI: Nutzer können Plugins durchsuchen, installieren und konfigurieren

**Technische Hinweise:** D2 Phase 5: „Marketplace-Ansatz für Community-Integrationen." Das Plugin-System baut auf dem bestehenden BaseConnector-Interface (D1 Abschnitt 3.1) und BriefingTemplate-Klasse auf. Plugins laufen sandboxed mit eingeschränkten Permissions.

---

#### TASK-152: Mobile Apps – iOS und Android

| Feld             | Wert                          |
| ---------------- | ----------------------------- |
| **Priorität**    | P1                            |
| **Bereich**      | Mobile                        |
| **Aufwand**      | XL                            |
| **Status**       | 🔴 Offen                      |
| **Quelle**       | D2 Phase 5, D3 Kernfunktion 1 |
| **Abhängig von** | Phase 3–4 Tasks               |
| **Blockiert**    | –                             |

**Beschreibung:** Native oder Cross-Platform Mobile Apps für iOS und Android entwickeln. Kernfunktionen: Briefings lesen, semantische Suche, Schnellnotizen (Text + Sprache), Push-Notifications für Erinnerungen und neue Briefings. Offline-Caching für zuletzt abgerufene Briefings.

**Acceptance Criteria:**

- [ ] iOS- und Android-App im jeweiligen App Store veröffentlicht mit Briefing-Ansicht, Suche, Schnellnotizen und Push-Notifications
- [ ] Offline-Caching: Letzte 3 Briefings und Top-20 Entitäten sind offline verfügbar

**Technische Hinweise:** D2 Phase 5: „iOS- und Android-Applikationen für unterwegs (Schnellnotizen, Spracherfassung, Briefings)." D3 erwähnt „Optionale manuelle Erfassung über Sprache, Fotos, Schnellnotizen" als Datenerfassungsoption.

---

#### TASK-153: RBAC – Rollenbasierte Zugriffssteuerung auf Organisationsebene

| Feld             | Wert       |
| ---------------- | ---------- |
| **Priorität**    | P1         |
| **Bereich**      | Backend    |
| **Aufwand**      | L          |
| **Status**       | 🔴 Offen   |
| **Quelle**       | D2 Phase 5 |
| **Abhängig von** | TASK-144   |
| **Blockiert**    | –          |

**Beschreibung:** Rollenbasierte Zugriffssteuerung (RBAC) für Organisationen implementieren. Rollen: Admin, Manager, Member, Viewer. Permissions: Konnektoren verwalten, Nutzer einladen, Organisationsdaten lesen, Briefings generieren. Vererbbare Rollen auf Projektebene. Audit-Log für Rollenänderungen.

**Acceptance Criteria:**

- [ ] Rollenmodell mit mindestens 4 Rollen und granularen Permissions auf Organisations- und Projektebene
- [ ] Admin-UI für Rollenzuweisung und Permission-Übersicht pro Nutzer

**Technische Hinweise:** D2 Phase 5 fordert „Rollenbasierte Zugriffssteuerung" für „gemeinsame Entscheidungshistorie und Wissensübergabe auf Organisationsebene." Baut auf Multi-Tenancy (TASK-144) auf. Basis-Rollenmodell (Owner, Member, Viewer) aus TASK-144 wird um Manager-Rolle und granulare Permissions erweitert.

---

#### TASK-154: Vertikale Spezialisierungen – Forscher, Berater, Entwickler

| Feld             | Wert                                          |
| ---------------- | --------------------------------------------- |
| **Priorität**    | P2                                            |
| **Bereich**      | Backend / Frontend                            |
| **Aufwand**      | XL                                            |
| **Status**       | 🔴 Offen                                      |
| **Quelle**       | D2 Phase 5, D3 Zielgruppe und Anwendungsfälle |
| **Abhängig von** | Phase 3–4 Tasks                               |
| **Blockiert**    | –                                             |

**Beschreibung:** Angepasste Workflows und Wissensmodelle für drei vertikale Zielgruppen: Forscher (Literaturnachweise, Hypothesen-Tracking, Experiment-Verknüpfung), Berater (Kundenprojekte, Lessons Learned, Cross-Projekt-Muster), Entwickler (Architekturentscheidungen, technische Schulden, Code-Review-Verknüpfung). Vertikale Templates für Briefings und NER.

**Acceptance Criteria:**

- [ ] Mindestens 3 vertikale Profile mit spezialisierten Briefing-Templates und NER-Konfigurationen
- [ ] Nutzer kann ein vertikales Profil auswählen, das Briefing-Inhalte und Entity-Prioritäten anpasst

**Technische Hinweise:** D3 beschreibt als Anwendungsfälle: Forscher (Literaturnachweise, Hypothesen-Tracking), Berater (Kundenprojekte, Lessons Learned), Entwickler (Architekturentscheidungen, technische Schulden). D2 Phase 5 listet diese als „Vertikale Spezialisierungen."

---

#### TASK-155: Langzeit-Intelligenz – Muster über Monate/Jahre und Annahmen-Tracking

| Feld             | Wert                              |
| ---------------- | --------------------------------- |
| **Priorität**    | P2                                |
| **Bereich**      | Backend                           |
| **Aufwand**      | XL                                |
| **Status**       | 🔴 Offen                          |
| **Quelle**       | D2 Phase 5, D3 Langzeitgedächtnis |
| **Abhängig von** | TASK-139, Phase 3–4 Tasks         |
| **Blockiert**    | –                                 |

**Beschreibung:** Langzeit-Intelligenz als strategisches Alleinstellungsmerkmal ausbauen. Erkennung von Mustern über Monate und Jahre: strategische Themenverschiebungen, Entscheidungsqualität im Nachhinein, wiederkehrende Fehler. Annahmen-Tracking: Welche Hypothesen haben sich bestätigt, welche widerlegt? Proaktive Hinweise auf strategische Veränderungen. Jahres- und Quartals-Reviews.

**Acceptance Criteria:**

- [ ] Quartals-Review-Briefing: Automatisch generierte Zusammenfassung der wichtigsten Themen, Entscheidungen und Muster der letzten 3 Monate
- [ ] Annahmen-Tracker: Dashboard zeigt Hypothesen mit Status (bestätigt/widerlegt/offen) und Zeitverlauf

**Technische Hinweise:** D3 beschreibt als Alleinstellungsmerkmal: „Kontinuierliches Langzeitgedächtnis – nicht nur Suche, sondern dauerhaftes Verständnis über Monate und Jahre." D2 Phase 5: „Erkennung von Mustern über Monate und Jahre; Nachverfolgung, welche Annahmen sich als falsch herausgestellt haben." Baut auf Mustererkennung (TASK-139) auf.

---

## Offene Klärungspunkte

| ID    | Frage                                                                                                                                                                                                                                                             | Betroffene Tasks             | Quelle                                 | Priorität |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | -------------------------------------- | --------- |
| KP-01 | **Phasennummerierung inkonsistent zwischen D2 und D3:** D2 zählt 5 Phasen (Discovery, MVP, Private Beta, Launch, Plattform), D3 zählt 4 Phasen (MVP, Private Beta, Launch, Erweiterung+Plattform) mit abweichenden Monatsangaben. Welche Zählung ist verbindlich? | Alle Tasks                   | D2, D3                                 | P1        |
| KP-02 | **Gmail und Slack: MVP- oder Phase-3-Scope?** D1 Konnektor-Tabelle listet Gmail und Slack als MVP-Konnektoren mit vollständiger Spezifikation. D4 listet sie explizit unter "Out of Scope für MVP". Welches Dokument ist maßgeblich?                              | TASK-123–126                 | D1 Abschnitt 3.1, D4 Abschnitt 2       | P1        |
| KP-03 | **Embedding-Modell für Mehrsprachigkeit:** Reicht `text-embedding-3-small` (OpenAI) für deutschsprachige und gemischt DE/EN-Inhalte, oder wird ein dediziertes multilinguales Modell benötigt? Benchmark mit realen Nutzer-Daten fehlt.                           | TASK-138, alle Suche-Tasks   | D1 OQ-001, D4 OQ-01                    | P1        |
| KP-04 | **Offline-Sync-Architektur (Tauri):** Wie wird die Synchronisierung zwischen lokalem Offline-Vault (SQLite) und Cloud-Backend gelöst? CRDT-basierter Sync oder Last-Write-Wins? Conflict Resolution bei gleichzeitiger Offline-Bearbeitung?                       | TASK-136                     | D1 OQ-005                              | P2        |
| KP-05 | **Entity-Deduplizierung über Quellen hinweg:** "Thomas K." in Slack = "Thomas Kramer" im Kalender = "t.kramer@firma.de" in Gmail? E-Mail als Merge-Key allein reicht nicht. LLM-basiertes Entity Resolution ist teuer. Nutzerfeedback-Loop für Korrekturen?       | TASK-123–128, TASK-138       | D1 OQ-009, D4 OQ-05                    | P1        |
| KP-06 | **LLM-Kosten-Deckel und Pricing-Kalkulation:** Wie viele LLM-Calls fallen pro Nutzer/Tag an? Ist der Zielkorridor 20–50 €/Monat deckbar bei geschätzten 3–8 €/Nutzer/Monat LLM-Kosten? Proof-of-Cost fehlt.                                                       | TASK-137                     | D1 OQ-004, D2 Phase 3                  | P1        |
| KP-07 | **AVV mit LLM-Providern:** Reichen die Standard-DPAs von OpenAI und Anthropic, oder müssen individuelle AVVs nach Art. 28 DSGVO abgeschlossen werden? Ohne AVV: DSGVO-Verstoß möglich.                                                                            | TASK-147                     | D4 OQ-06                               | P1        |
| KP-08 | **Desktop-App-Framework:** D1 entscheidet Tauri (ADR-008), D3 erwähnt „Electron oder Tauri" als Alternative. Ist die Entscheidung für Tauri final oder soll Electron nochmals evaluiert werden?                                                                   | TASK-135, TASK-136           | D1 ADR-008, D3 Technische Überlegungen | P2        |
| KP-09 | **Backup und Disaster Recovery für Weaviate/Neo4j:** RPO/RTO-Ziele sind nicht definiert. Weaviate und Neo4j haben keine managed Backups wie RDS. Automatisierte Backup-Lösung muss vor Phase 4 stehen.                                                            | TASK-146                     | D1 OQ-010                              | P1        |
| KP-10 | **Rate-Limiting bei Initial Sync großer Datenquellen:** Was passiert bei Gmail-Initial-Sync mit 10.000+ E-Mails oder Notion-Workspace mit 1.000+ Seiten? LLM-Extraction-Budget (100 Calls/Nutzer/Tag) reicht nicht. Batch-Extraktion oder Backfill-Budget nötig?  | TASK-123, TASK-127, TASK-128 | D1 OQ-006, D4 OQ-07                    | P2        |
| KP-11 | **Browser-History als Datenquelle:** D3 Kernfunktion 1 erwähnt „Browser-History" als Integrationsquelle. D1 und D2 listen keinen Browser-History-Konnektor. Soll dies in Phase 3 als Teil der Browser-Extension umgesetzt werden oder komplett entfallen?         | TASK-140                     | D3 Kernfunktion 1                      | P3        |
| KP-12 | **Neo4j Community vs. Enterprise Edition:** Community Edition hat keine Cluster-Fähigkeit. Bei 500 Nutzern werden 2,5M–25M Knoten geschätzt. Reicht Community Edition bis Phase 4? Wann muss die Migration zur Enterprise Edition erfolgen?                       | TASK-146                     | D1 OQ-003                              | P2        |
| KP-13 | **Meeting-Transkripte ohne Zoom Pro:** Nutzer ohne Zoom-Pro-Abo haben keinen Zugang zu AI-Transkripten. Soll ein manueller Upload-Mechanismus als Fallback bereitgestellt werden? Betrifft auch Teams-Transkripte.                                                | TASK-127                     | D4 OQ-03                               | P2        |

---

## Gesamt-Backlog-Statistik (Vorlage für Merge)

| Teil       | Agent   | Phase                                     | Anzahl Tasks  | Aufwand geschätzt |
| ---------- | ------- | ----------------------------------------- | ------------- | ----------------- |
| Teil 1     | Agent 1 | Phase 1 + Infra/DB                        | _[eintragen]_ | _[eintragen]_     |
| Teil 2     | Agent 2 | Konnektoren + Processing + LLM + Briefing | _[eintragen]_ | _[eintragen]_     |
| Teil 3     | Agent 3 | API + Frontend + Auth + DSGVO + QA        | _[eintragen]_ | _[eintragen]_     |
| Teil 4     | Agent 4 | Phase 3–5                                 | 35            | 8×M, 13×L, 14×XL  |
| **Gesamt** |         |                                           |               |                   |

---

## Statistik Teil 4

Phase 3: 23 Tasks | Phase 4: 6 Tasks | Phase 5: 6 Tasks | Klärungspunkte: 13 | Gesamt Tasks: 35

<!-- AGENT_4_LAST: TASK-155 -->
