# Tracking-Plan: PWBS – Persönliches Wissens-Betriebssystem

**Version:** 1.0
**Datum:** 17. März 2026
**Status:** Entwurf
**Basisdokumente:** [GTM_PLAN.md](GTM_PLAN.md), [PRD-SPEC.md](../PRD-SPEC.md), [UX_ONBOARDING_SPEC.md](UX_ONBOARDING_SPEC.md), [LEGAL_COMPLIANCE.md](LEGAL_COMPLIANCE.md), [onboarding-flow.md](public-beta/onboarding-flow.md)

---

## Inhaltsverzeichnis

1. [Scope & Tooling-Entscheidung](#1-scope--tooling-entscheidung)
2. [KPI → Event-Mapping](#2-kpi--event-mapping)
3. [Event-Taxonomie](#3-event-taxonomie)
4. [Event-Katalog](#4-event-katalog)
5. [User Properties](#5-user-properties)
6. [Funnel-Definitionen](#6-funnel-definitionen)
7. [DSGVO-Konformität des Trackings](#7-dsgvo-konformität-des-trackings)
8. [Dashboard-Spezifikation](#8-dashboard-spezifikation)
9. [Implementierungs-Checkliste](#9-implementierungs-checkliste)

---

## 1. Scope & Tooling-Entscheidung

### 1.1 Anforderungsprofil

Das PWBS wird von einem Solo-/Kleinteam in der EU betrieben. Analytics muss folgende Kriterien erfüllen:

| Kriterium                   | Gewichtung | Begründung                                                                                   |
| --------------------------- | ---------- | -------------------------------------------------------------------------------------------- |
| DSGVO-Konformität           | Hoch       | EU-Betrieb, DACH-Zielgruppe, Datenschutz als Differenzierungsmerkmal (GTM_PLAN Abschnitt 3)  |
| Self-Hosting-Fähigkeit      | Hoch       | Minimales Budget, volle Kontrolle über Daten, kein Drittanbieter-Risiko                      |
| Event-basiertes Tracking    | Hoch       | KPIs erfordern granulares Event-Tracking (Time-to-First-Briefing, Connector Completion Rate) |
| Funnel-Analyse              | Hoch       | Activation Funnel (Register → Briefing) ist der kritischste Optimierungshebel                |
| Kosten                      | Hoch       | Solo-Entwickler-Budget; keine monatlichen SaaS-Kosten wenn vermeidbar                        |
| Integration FastAPI/Next.js | Mittel     | SDKs oder REST-API für Backend-Events, JS-Snippet oder React-SDK für Frontend                |
| Kohorten-Analyse            | Mittel     | Retention über Kohorten ist KPI #3 (7-Day Retention)                                         |

### 1.2 Tool-Bewertung

| Kriterium                | PostHog Self-Hosted                   | Plausible Self-Hosted          | Matomo Self-Hosted                  | Umami Self-Hosted  |
| ------------------------ | ------------------------------------- | ------------------------------ | ----------------------------------- | ------------------ |
| DSGVO-Konformität        | ✅ Voll (Self-Hosted)                 | ✅ Voll                        | ✅ Voll                             | ✅ Voll            |
| Self-Hosting             | ✅ Docker Compose                     | ✅ Docker Compose              | ✅ Docker/Deb                       | ✅ Docker Compose  |
| Event-basiertes Tracking | ✅ Kern-Feature                       | ❌ Nur Pageviews + Goals       | ⚠️ Nachgebaut via Custom Dimensions | ⚠️ Basis-Events    |
| Funnel-Analyse           | ✅ Nativ                              | ❌ Nicht vorhanden             | ⚠️ Plugin (begrenzt)                | ❌ Nicht vorhanden |
| Kohorten-Retention       | ✅ Nativ                              | ❌ Nicht vorhanden             | ⚠️ Plugin                           | ❌ Nicht vorhanden |
| Kosten (Self-Hosted)     | ⚠️ ~2 GB RAM, PostgreSQL + ClickHouse | ✅ ~256 MB RAM                 | ⚠️ ~1 GB RAM                        | ✅ ~512 MB RAM     |
| FastAPI-Integration      | ✅ Python SDK + REST API              | ⚠️ Nur Events-API (rudimentär) | ⚠️ PHP-nativ, Python-SDK veraltet   | ⚠️ REST API        |
| Next.js-Integration      | ✅ React SDK (`posthog-js`)           | ✅ Script-Tag                  | ✅ JS-Tracker                       | ✅ Script-Tag      |
| User Identification      | ✅ Nativ (identify + alias)           | ❌ Anonymisiert only           | ⚠️ User ID möglich                  | ⚠️ Basis           |
| Feature Flags            | ✅ Integriert                         | ❌ Nicht vorhanden             | ❌ Nicht vorhanden                  | ❌ Nicht vorhanden |

### 1.3 Empfehlung: PostHog Self-Hosted

**PostHog Self-Hosted** ist die einzige Option, die alle Anforderungen erfüllt:

1. **Event-basiertes Tracking mit Funnel-Analyse und Kohorten-Retention** – die drei anderen Tools bieten dies nicht nativ. Plausible und Umami sind Pageview-Analytics, keine Product-Analytics-Plattformen.
2. **User Identification** – PostHog kann `user_id` nach Login zuordnen und Anonymous-Events retroaktiv verknüpfen. Essentiell für Time-to-First-Briefing und Retention-Berechnung.
3. **Feature Flags** – bereits im PWBS-Stack vorhanden (eigener Feature-Flag-Service), aber PostHog könnte als Backup dienen.
4. **Self-Hosted auf bestehender Infrastruktur** – PostHog läuft in Docker Compose parallel zu den bestehenden Services (PostgreSQL, Redis sind bereits vorhanden). ClickHouse wird als zusätzlicher Container benötigt (~1 GB RAM).
5. **Python SDK** – `posthog-python` ermöglicht Server-Side-Tracking direkt aus FastAPI-Routen.

**Ressourcenbedarf:** ~2 GB RAM zusätzlich (ClickHouse + PostHog-Worker). Bei 20 Nutzern (Closed Beta) kein Problem auf der bestehenden AWS-Instanz.

### 1.4 Server-Side vs. Client-Side Tracking

**Empfehlung: Hybrid – Server-Side-First mit ergänzendem Client-Side-Tracking.**

| Tracking-Methode | Eingesetzt für                                                                                                                                                        | Begründung                                                                             |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **Server-Side**  | `user_registered`, `connector_connected`, `connector_sync_completed`, `briefing_generated`, `search_executed`, `user_logged_in`, `user_logged_out`                    | Zuverlässig (kein Ad-Blocker), `owner_id` direkt verfügbar, alle KPI-kritischen Events |
| **Client-Side**  | `page_viewed`, `onboarding_started`, `onboarding_step_completed`, `onboarding_skipped`, `briefing_viewed`, `search_result_clicked`, `session_started`, `feature_used` | UI-Interaktionen, die nur im Browser stattfinden                                       |

**Begründung für Server-Side-First:**

- Die 5 Launch-KPIs (GTM_PLAN Abschnitt 8) basieren auf Backend-Events: Registrierung, Konnektor-Verbindung, Briefing-Generierung, Briefing-Abruf, Login-Aktivität.
- Server-Side-Events sind manipulations- und adblocker-resistent.
- `owner_id` ist im Backend direkt aus dem JWT verfügbar – keine clientseitige User-Zuordnung nötig.
- Consent-Management wird vereinfacht: Server-Side-Events unter Vertragserfüllung (Art. 6 Abs. 1 lit. b DSGVO) benötigen keinen separaten Tracking-Consent.

**Integration mit bestehendem Stack:**

```
Frontend (Next.js)                    Backend (FastAPI)
┌─────────────────┐                  ┌─────────────────────┐
│ posthog-js SDK  │──page_viewed──→  │                     │
│ (Client-Side)   │──onboarding_*──→ │ posthog-python SDK  │
│                 │                  │ (Server-Side)       │
│                 │                  │                     │
│                 │                  │ ──user_registered──→│
│                 │                  │ ──connector_*─────→ │ → PostHog
│                 │                  │ ──briefing_*──────→ │   Self-Hosted
│                 │                  │ ──search_*────────→ │
└─────────────────┘                  └─────────────────────┘
```

---

## 2. KPI → Event-Mapping

Die folgenden KPIs stammen aus dem GTM_PLAN (Abschnitt 8) und der PRD-SPEC (Produkthypothese, Abschnitt 2).

| KPI                                     | Definition                                                                      | Berechnung                                                                                                                        | Benötigte Events                                                                                      | Zielwert (Closed Beta) | Zielwert (Open Beta) |
| --------------------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------------------- | -------------------- |
| **Waitlist-to-Signup Conversion Rate**  | Anteil der Waitlist-Einträge, die sich registrieren und ≥ 1 Konnektor verbinden | `COUNT(user_registered WHERE referral_source = 'waitlist' AND has_connector) / COUNT(waitlist_signed_up)`                         | `waitlist_signed_up`, `user_registered`, `connector_connected`                                        | ≥ 80 %                 | ≥ 40 %               |
| **Time-to-First-Briefing**              | Zeitspanne zwischen Registrierung und erstem generiertem Briefing               | `MEDIAN(briefing_generated[0].timestamp - user_registered.timestamp)` pro Kohorte                                                 | `user_registered` (mit Timestamp), `briefing_generated` (mit Timestamp, `is_first = true`)            | ≤ 20 Minuten           | ≤ 30 Minuten         |
| **7-Day Retention Rate**                | Anteil Nutzer, die 7 Tage nach Registrierung mindestens eine Aktion ausführen   | `COUNT(users WITH any_event IN day[7..13]) / COUNT(user_registered IN cohort_week)`                                               | `user_registered`, `briefing_viewed`, `search_executed`, `page_viewed` (mit Timestamps und `user_id`) | ≥ 80 %                 | ≥ 65 %               |
| **Connector Completion Rate**           | Anteil registrierter Nutzer mit ≥ 1 Konnektor innerhalb von 24h                 | `COUNT(users WITH connector_connected.timestamp - user_registered.timestamp <= 24h) / COUNT(user_registered)`                     | `user_registered`, `connector_connected` (mit Timestamps)                                             | ≥ 90 %                 | ≥ 70 %               |
| **Weekly Active Briefing Views**        | Durchschnittliche Briefing-Abrufe pro aktivem Nutzer pro Woche                  | `COUNT(briefing_viewed IN week) / COUNT(DISTINCT user_id WITH briefing_viewed IN week)`                                           | `briefing_viewed` (mit `user_id` und Timestamp)                                                       | ≥ 3                    | ≥ 3                  |
| **14-Tage-Retention** (PRD-SPEC)        | Anteil Nutzer, die 14 Tage nach Registrierung aktiv sind                        | `COUNT(users WITH any_event IN day[14..20]) / COUNT(user_registered IN cohort)`                                                   | `user_registered`, alle Aktivitäts-Events                                                             | ≥ 60 %                 | ≥ 60 %               |
| **Briefing-Relevanz-Score** (ergänzend) | Positives Feedback / Gesamtfeedback                                             | `COUNT(briefing_feedback_given WHERE rating = 'positive') / COUNT(briefing_feedback_given)`                                       | `briefing_feedback_given` (mit `rating`)                                                              | ≥ 60 %                 | ≥ 70 %               |
| **Konnektor-Erfolgsrate** (PRD-SPEC)    | Erfolgreiche Syncs / Gesamtsyncs                                                | `COUNT(connector_sync_completed) / (COUNT(connector_sync_completed) + COUNT(connector_connection_failed WHERE trigger = 'sync'))` | `connector_sync_completed`, `connector_connection_failed`                                             | ≥ 90 %                 | ≥ 90 %               |

---

## 3. Event-Taxonomie

### 3.1 Naming Convention

```
{object}_{action}
```

**Regeln:**

| Regel                          | Beispiel korrekt              | Beispiel falsch                     |
| ------------------------------ | ----------------------------- | ----------------------------------- |
| Lowercase, Underscore-getrennt | `briefing_viewed`             | `BriefingViewed`, `briefing-viewed` |
| Verben im Past Tense           | `connector_connected`         | `connector_connect`                 |
| Keine Abkürzungen              | `connector_connection_failed` | `conn_fail`                         |
| Objekt zuerst, Aktion danach   | `search_executed`             | `executed_search`                   |
| Kein Plural für Objekte        | `briefing_generated`          | `briefings_generated`               |

### 3.2 Namespace-Struktur

| Namespace      | Beschreibung                                | Beispiele                                         |
| -------------- | ------------------------------------------- | ------------------------------------------------- |
| `auth_*`       | Authentifizierung und Account-Lifecycle     | `auth_user_registered`, `auth_user_logged_in`     |
| `connector_*`  | Datenquellen-Verbindung und Synchronisation | `connector_connected`, `connector_sync_completed` |
| `briefing_*`   | Briefing-Generierung und -Nutzung           | `briefing_generated`, `briefing_viewed`           |
| `search_*`     | Semantische Suche                           | `search_executed`, `search_result_clicked`        |
| `onboarding_*` | Onboarding-Wizard-Flow                      | `onboarding_started`, `onboarding_step_completed` |
| `app_*`        | Allgemeine App-Nutzung und Navigation       | `app_page_viewed`, `app_session_started`          |
| `waitlist_*`   | Waitlist/Pre-Launch-Events                  | `waitlist_signed_up`                              |

### 3.3 Property-Naming

- Properties: `snake_case`
- Datentypen: explizit angegeben (string, integer, float, boolean, ISO 8601)
- Zeitdauern: immer in Millisekunden (`_ms`-Suffix)
- Zählwerte: `_count`-Suffix
- IDs: UUID als String

---

## 4. Event-Katalog

### 4.1 Waitlist

| Event-Name           | Kategorie | Trigger-Bedingung                                               | Properties                                                                                                                 | Consent-Pflicht          | Backend/Frontend |
| -------------------- | --------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------- |
| `waitlist_signed_up` | Waitlist  | Nutzer trägt sich in die Waitlist ein (`POST /api/v1/waitlist`) | `email_hash: string` (SHA-256, kein Klartext), `referral_source: string` (utm_source oder 'direct'), `timestamp: ISO 8601` | Nein (Vertragserfüllung) | Backend          |

### 4.2 Auth & Registration

| Event-Name             | Kategorie | Trigger-Bedingung                                                 | Properties                                                                                                                 | Consent-Pflicht          | Backend/Frontend |
| ---------------------- | --------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------- |
| `auth_user_registered` | Auth      | Account erfolgreich erstellt (`POST /api/v1/auth/register` → 201) | `user_id: string (UUID)`, `signup_method: string` ('email'), `referral_code: string \| null`, `timestamp: ISO 8601`        | Nein (Vertragserfüllung) | Backend          |
| `auth_user_logged_in`  | Auth      | Login erfolgreich (`POST /api/v1/auth/login` → 200)               | `user_id: string (UUID)`, `login_method: string` ('email'), `session_number: integer` (n-ter Login), `timestamp: ISO 8601` | Nein (Vertragserfüllung) | Backend          |
| `auth_user_logged_out` | Auth      | Logout durchgeführt (`POST /api/v1/auth/logout` → 200)            | `user_id: string (UUID)`, `session_duration_ms: integer`, `timestamp: ISO 8601`                                            | Nein (Vertragserfüllung) | Backend          |

### 4.3 Onboarding

| Event-Name                  | Kategorie  | Trigger-Bedingung                                                                        | Properties                                                                                                                                                                                                        | Consent-Pflicht | Backend/Frontend |
| --------------------------- | ---------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ---------------- |
| `onboarding_started`        | Onboarding | Welcome-Screen (Wizard Step 1) wird angezeigt                                            | `user_id: string (UUID)`, `timestamp: ISO 8601`                                                                                                                                                                   | Ja (Analytics)  | Frontend         |
| `onboarding_step_completed` | Onboarding | Nutzer schließt einen Wizard-Schritt ab (klickt „Weiter")                                | `user_id: string (UUID)`, `step_number: integer` (1–4), `step_name: string` ('welcome' \| 'connector_select' \| 'sync' \| 'first_briefing'), `duration_ms: integer` (Zeit auf dem Schritt), `timestamp: ISO 8601` | Ja (Analytics)  | Frontend         |
| `onboarding_completed`      | Onboarding | Wizard vollständig durchlaufen (alle 4 Schritte abgeschlossen, „Zum Dashboard" geklickt) | `user_id: string (UUID)`, `total_duration_ms: integer` (Gesamtzeit Wizard), `connectors_connected: integer`, `timestamp: ISO 8601`                                                                                | Ja (Analytics)  | Frontend         |
| `onboarding_skipped`        | Onboarding | Nutzer klickt „Überspringen" oder „Später" im Wizard                                     | `user_id: string (UUID)`, `skipped_at_step: integer` (1–4), `step_name: string`, `timestamp: ISO 8601`                                                                                                            | Ja (Analytics)  | Frontend         |

### 4.4 Connectors

| Event-Name                    | Kategorie | Trigger-Bedingung                                                                         | Properties                                                                                                                                                                                                                                             | Consent-Pflicht          | Backend/Frontend |
| ----------------------------- | --------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ | ---------------- |
| `connector_oauth_started`     | Connector | Nutzer initiiert OAuth-Flow (`GET /api/v1/connectors/{type}/auth-url`)                    | `user_id: string (UUID)`, `connector_type: string` ('google_calendar' \| 'notion' \| 'zoom' \| 'obsidian'), `is_first_connector: boolean`, `timestamp: ISO 8601`                                                                                       | Nein (Vertragserfüllung) | Backend          |
| `connector_connected`         | Connector | Konnektor erfolgreich verbunden (OAuth-Callback verarbeitet oder Obsidian-Pfad validiert) | `user_id: string (UUID)`, `connector_type: string`, `is_first_connector: boolean`, `time_since_registration_ms: integer`, `total_connectors: integer` (nach Verbindung), `timestamp: ISO 8601`                                                         | Nein (Vertragserfüllung) | Backend          |
| `connector_connection_failed` | Connector | OAuth-Fehler, Callback-Fehler oder Validierungsfehler                                     | `user_id: string (UUID)`, `connector_type: string`, `error_type: string` ('oauth_denied' \| 'oauth_timeout' \| 'token_exchange_failed' \| 'invalid_vault_path' \| 'api_error'), `error_message: string` (sanitisiert, kein PII), `timestamp: ISO 8601` | Nein (Vertragserfüllung) | Backend          |
| `connector_sync_completed`    | Connector | Synchronisation erfolgreich abgeschlossen                                                 | `user_id: string (UUID)`, `connector_type: string`, `sync_type: string` ('initial' \| 'incremental' \| 'manual'), `documents_count: integer`, `duration_ms: integer`, `is_first_sync: boolean`, `timestamp: ISO 8601`                                  | Nein (Vertragserfüllung) | Backend          |
| `connector_disconnected`      | Connector | Nutzer trennt Konnektor (Daten kaskadiert gelöscht)                                       | `user_id: string (UUID)`, `connector_type: string`, `documents_deleted_count: integer`, `connection_duration_days: integer` (Tage seit Verbindung), `timestamp: ISO 8601`                                                                              | Nein (Vertragserfüllung) | Backend          |

### 4.5 Briefings

| Event-Name                | Kategorie | Trigger-Bedingung                                                                                                           | Properties                                                                                                                                                                                                                                                                                                                                                      | Consent-Pflicht                                                     | Backend/Frontend                              |
| ------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------- |
| `briefing_generated`      | Briefing  | Briefing erfolgreich erzeugt und persistiert                                                                                | `user_id: string (UUID)`, `briefing_id: string (UUID)`, `briefing_type: string` ('morning' \| 'meeting' \| 'weekly'), `sources_count: integer` (Anzahl referenzierter Quellen), `generation_duration_ms: integer`, `word_count: integer`, `is_first_briefing: boolean`, `trigger: string` ('scheduled' \| 'manual' \| 'auto_onboarding'), `timestamp: ISO 8601` | Nein (Vertragserfüllung)                                            | Backend                                       |
| `briefing_viewed`         | Briefing  | Nutzer ruft ein Briefing auf (`GET /api/v1/briefings/{id}` → 200 oder Briefing-Card im Dashboard sichtbar für ≥ 3 Sekunden) | `user_id: string (UUID)`, `briefing_id: string (UUID)`, `briefing_type: string`, `briefing_age_hours: float` (Stunden seit Generierung), `view_source: string` ('dashboard' \| 'briefing_list' \| 'notification'), `timestamp: ISO 8601`                                                                                                                        | Ja (Analytics)                                                      | Frontend (Sichtbarkeit) + Backend (API-Abruf) |
| `briefing_feedback_given` | Briefing  | Nutzer gibt Daumen-hoch/runter-Feedback                                                                                     | `user_id: string (UUID)`, `briefing_id: string (UUID)`, `briefing_type: string`, `rating: string` ('positive' \| 'negative'), `has_comment: boolean`, `timestamp: ISO 8601`                                                                                                                                                                                     | Nein (Vertragserfüllung – Feedback-Mechanismus ist Produktfunktion) | Backend                                       |

### 4.6 Search

| Event-Name              | Kategorie | Trigger-Bedingung                                | Properties                                                                                                                                                                                                                                                                          | Consent-Pflicht          | Backend/Frontend |
| ----------------------- | --------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------- |
| `search_executed`       | Search    | Suche durchgeführt (`POST /api/v1/search` → 200) | `user_id: string (UUID)`, `query_length: integer` (Zeichen), `results_count: integer`, `search_mode: string` ('hybrid' \| 'semantic' \| 'keyword'), `has_filters: boolean`, `filter_types: string[]` (z.B. ['person', 'date_range']), `duration_ms: integer`, `timestamp: ISO 8601` | Nein (Vertragserfüllung) | Backend          |
| `search_result_clicked` | Search    | Nutzer klickt auf ein Suchergebnis               | `user_id: string (UUID)`, `result_position: integer` (1-basiert), `result_type: string` ('document' \| 'chunk' \| 'entity'), `result_source: string` ('google_calendar' \| 'notion' \| 'zoom' \| 'obsidian'), `query_length: integer`, `timestamp: ISO 8601`                        | Ja (Analytics)           | Frontend         |

### 4.7 Engagement / App

| Event-Name            | Kategorie | Trigger-Bedingung                                                         | Properties                                                                                                                                                                                                                                                                                  | Consent-Pflicht | Backend/Frontend |
| --------------------- | --------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ---------------- |
| `app_page_viewed`     | App       | Seitenaufruf im Frontend (Route-Change)                                   | `user_id: string (UUID) \| null` (null bei nicht eingeloggtem Besuch), `page_name: string` ('dashboard' \| 'briefings' \| 'search' \| 'knowledge' \| 'connectors' \| 'settings' \| 'landing' \| 'register' \| 'login'), `referrer: string` (vorherige Seite, intern), `timestamp: ISO 8601` | Ja (Analytics)  | Frontend         |
| `app_session_started` | App       | Neues Browser-Tab/Fenster oder > 30 Min. Inaktivität                      | `user_id: string (UUID) \| null`, `session_number: integer` (n-te Session dieses Nutzers), `is_authenticated: boolean`, `timestamp: ISO 8601`                                                                                                                                               | Ja (Analytics)  | Frontend         |
| `app_feature_used`    | App       | Nutzer interagiert mit einem spezifischen Feature außerhalb der Kernflows | `user_id: string (UUID)`, `feature_name: string` ('knowledge_explorer' \| 'entity_detail' \| 'graph_view' \| 'data_export' \| 'manual_sync' \| 'briefing_regenerate' \| 'source_link_clicked'), `timestamp: ISO 8601`                                                                       | Ja (Analytics)  | Frontend         |

---

## 5. User Properties

Persistente Nutzer-Attribute, die in PostHog als Person Properties gespeichert und bei jedem `identify()`-Aufruf aktualisiert werden.

| Property                    | Datentyp                  | Berechnung                                               | Aktualisierung                                                             |
| --------------------------- | ------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------- |
| `signup_date`               | string (ISO 8601)         | Zeitpunkt der Registrierung                              | Einmalig bei `auth_user_registered`                                        |
| `days_since_signup`         | integer                   | `DATEDIFF(NOW(), signup_date)`                           | Berechnet (PostHog-Formula oder bei jedem Event)                           |
| `connected_sources_count`   | integer                   | `COUNT(DISTINCT connector_type WHERE status = 'active')` | Bei `connector_connected` und `connector_disconnected`                     |
| `connected_source_types`    | string[]                  | Liste der aktiven Konnektor-Typen                        | Bei `connector_connected` und `connector_disconnected`                     |
| `total_briefings_generated` | integer                   | Kumulierte Anzahl generierter Briefings                  | Inkrement bei `briefing_generated`                                         |
| `last_briefing_date`        | string (ISO 8601)         | Zeitpunkt des letzten generierten Briefings              | Bei `briefing_generated`                                                   |
| `onboarding_completed`      | boolean                   | `true` wenn Wizard vollständig durchlaufen               | Bei `onboarding_completed`                                                 |
| `onboarding_completed_date` | string (ISO 8601) \| null | Zeitpunkt des Abschlusses                                | Bei `onboarding_completed`                                                 |
| `plan_type`                 | string                    | Aktueller Plan-Typ                                       | Statisch: `'free_beta'` (bis Phase 3)                                      |
| `referral_source`           | string                    | Herkunft des Nutzers                                     | Einmalig bei `auth_user_registered` (aus UTM-Parameter oder Referral-Code) |
| `first_briefing_date`       | string (ISO 8601) \| null | Zeitpunkt des ersten Briefings                           | Bei `briefing_generated` wo `is_first_briefing = true`                     |
| `total_searches`            | integer                   | Kumulierte Anzahl Suchen                                 | Inkrement bei `search_executed`                                            |
| `last_active_date`          | string (ISO 8601)         | Letzter Tag mit einer Aktivität                          | Bei jedem authentifizierten Event                                          |

---

## 6. Funnel-Definitionen

### 6.1 Activation Funnel

Der kritischste Funnel – misst den Weg vom Erstbesuch bis zum Value Moment (erstes Briefing).

| Schritt                      | Event                                           | Erwartete Conversion (Closed Beta) | Erwartete Conversion (Open Beta) | Akzeptabler Drop-off |
| ---------------------------- | ----------------------------------------------- | ---------------------------------- | -------------------------------- | -------------------- |
| 1. Registrierung             | `auth_user_registered`                          | 100 % (Basis)                      | 100 % (Basis)                    | —                    |
| 2. Welcome-Screen            | `onboarding_started`                            | 95 %                               | 85 %                             | 15 %                 |
| 3. Konnektor verbunden       | `connector_connected`                           | 90 % (1-on-1 Onboarding)           | 70 % (Self-Serve)                | 20 %                 |
| 4. Erstes Briefing generiert | `briefing_generated` (is_first_briefing = true) | 90 %                               | 65 %                             | 10 %                 |
| 5. Erstes Briefing angesehen | `briefing_viewed` (erstes Mal)                  | 85 %                               | 55 %                             | 15 %                 |

**Gesamt-Conversion Register → Briefing Viewed:**

- Closed Beta: ~70 % (mit 1-on-1 Onboarding)
- Open Beta: ~35 % (Self-Serve, ohne persönliche Betreuung)

**Optimierungsziele:**

- Drop-off zwischen Schritt 2 und 3 (Konnektor-Verbindung) ist die größte Hürde. UX_ONBOARDING_SPEC identifiziert OAuth-Abbruch und fehlenden Fortschrittsindikator als Hauptursachen.
- Drop-off zwischen Schritt 4 und 5 zeigt „Briefing generiert, aber nicht gelesen" – weist auf fehlende Benachrichtigung hin.

### 6.2 Retention Funnel (wöchentlich)

Misst wiederkehrende Nutzung in einer typischen Woche.

| Schritt                       | Event                                                              | Erwartete Conversion                   | Akzeptabler Drop-off                                           |
| ----------------------------- | ------------------------------------------------------------------ | -------------------------------------- | -------------------------------------------------------------- |
| 1. Login / App-Besuch         | `auth_user_logged_in` oder `app_session_started` (authentifiziert) | 100 % (Basis: aktive Nutzer der Woche) | —                                                              |
| 2. Briefing angesehen         | `briefing_viewed`                                                  | 80 %                                   | 20 %                                                           |
| 3. Suche durchgeführt         | `search_executed`                                                  | 40 %                                   | 50 % (Suche ist optional, nicht alle Nutzer suchen jede Woche) |
| 4. Rückkehr innerhalb 7 Tagen | `app_session_started` (innerhalb 7 Tage nach letzter Session)      | 65 % (Open Beta) / 80 % (Closed Beta)  | 20–35 %                                                        |

**Interpretation:**

- Schritt 2 → 3 hat einen hohen erwarteten Drop-off, da Suche ein aktiver Akt ist; Briefings sind passiver Konsum. Dies ist akzeptabel.
- Der kritische Wert ist Schritt 4: Rückkehr innerhalb 7 Tagen = 7-Day Retention (KPI #3).

### 6.3 Connector Completion Funnel

Misst den Konnektor-Verbindungsprozess von der Initiierung bis zur erfolgreichen Indexierung.

| Schritt                  | Event                                             | Erwartete Conversion               | Akzeptabler Drop-off                        |
| ------------------------ | ------------------------------------------------- | ---------------------------------- | ------------------------------------------- |
| 1. OAuth gestartet       | `connector_oauth_started`                         | 100 % (Basis)                      | —                                           |
| 2. OAuth abgeschlossen   | `connector_connected`                             | 80 %                               | 20 % (Nutzer bricht OAuth beim Provider ab) |
| 3. Erster Sync gestartet | `connector_sync_completed` (is_first_sync = true) | 98 % (automatisch nach Verbindung) | 2 % (technischer Fehler)                    |
| 4. Sync erfolgreich      | `connector_sync_completed` (documents_count > 0)  | 90 %                               | 10 % (leere Kalender, API-Fehler, Timeout)  |

**Alarmschwellen:**

- Wenn OAuth-Abbruch > 30 %: UX-Problem im Consent-Dialog oder Pop-up-Blocker-Issue untersuchen.
- Wenn Sync-Fehler > 15 %: Backend-Logs prüfen, Provider-API-Stabilität evaluieren.

---

## 7. DSGVO-Konformität des Trackings

### 7.1 Rechtsgrundlagen pro Event-Kategorie

Die Zuordnung basiert auf der Consent-Architektur in LEGAL_COMPLIANCE.md (Abschnitt 4).

| Event-Kategorie                                      | Consent nötig? | Rechtsgrundlage                                | Begründung                                                                                                 |
| ---------------------------------------------------- | -------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `waitlist_*`                                         | Nein           | Art. 6 Abs. 1 lit. b DSGVO (Vertragsanbahnung) | Waitlist-Eintrag ist vorvertragliche Maßnahme auf Anfrage des Betroffenen                                  |
| `auth_*`                                             | Nein           | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) | Registrierung und Login sind für die Dienstleistung erforderlich. Tracking dient der Betriebssicherheit    |
| `connector_*`                                        | Nein           | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) | Konnektor-Verbindung und Sync sind die vertraglich zugesicherte Kernfunktion                               |
| `briefing_generated`, `briefing_feedback_given`      | Nein           | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) | Briefing-Generierung ist die Kerndienstleistung; Feedback ist Produktfunktion                              |
| `briefing_viewed` (Backend: API-Abruf)               | Nein           | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) | API-Abruf ist technisch notwendig für die Diensteerbringung                                                |
| `briefing_viewed` (Frontend: Sichtbarkeits-Tracking) | Ja             | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)      | Clientseitige Messung von Sichtbarkeit/Verweildauer dient der Nutzungsanalyse, nicht der Vertragserfüllung |
| `search_executed`                                    | Nein           | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) | Suche ist eine Kernfunktion; Performance-Messung (duration_ms) dient dem Betrieb                           |
| `search_result_clicked`                              | Ja             | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)      | Klick-Tracking auf Ergebnisse dient der Optimierung, nicht der Vertragserfüllung                           |
| `onboarding_*`                                       | Ja             | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)      | Onboarding-Wizard-Tracking analysiert Nutzerverhalten; nicht technisch notwendig                           |
| `app_page_viewed`                                    | Ja             | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)      | Pageview-Tracking ist klassische Nutzungsanalyse (TDDDG § 25: Opt-in erforderlich)                         |
| `app_session_started`                                | Ja             | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)      | Session-Tracking ist Nutzungsanalyse                                                                       |
| `app_feature_used`                                   | Ja             | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)      | Feature-Nutzungs-Analyse dient der Optimierung                                                             |

### 7.2 Events ohne Consent (berechtigtes Interesse / Vertragserfüllung)

Folgende Events werden **ohne expliziten Tracking-Consent** erfasst, da sie unter Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) oder lit. f (berechtigtes Interesse) fallen:

- `waitlist_signed_up`
- `auth_user_registered`, `auth_user_logged_in`, `auth_user_logged_out`
- `connector_oauth_started`, `connector_connected`, `connector_connection_failed`, `connector_sync_completed`, `connector_disconnected`
- `briefing_generated`, `briefing_feedback_given`
- `search_executed`

**Begründung:** Diese Events sind entweder technisch notwendig für den Dienst (Vertragserfüllung) oder dienen der Betriebssicherheit und Fehleranalyse (berechtigtes Interesse). Sie enthalten keine Nutzungsmuster-Analyse, sondern protokollieren den Vollzug vertraglicher Leistungen. Dies ist konsistent mit der Consent-Architektur in LEGAL_COMPLIANCE.md Abschnitt 4.1.

### 7.3 Events mit Consent-Pflicht (Analytics-Opt-in)

Folgende Events werden **nur nach explizitem Opt-in** (TDDDG § 25) erfasst:

- `onboarding_started`, `onboarding_step_completed`, `onboarding_completed`, `onboarding_skipped`
- `briefing_viewed` (Frontend-Sichtbarkeits-Tracking)
- `search_result_clicked`
- `app_page_viewed`, `app_session_started`, `app_feature_used`

**Implementierung:** PostHog JS-SDK wird erst initialisiert, wenn der Nutzer dem Analytics-Tracking zustimmt. Ohne Consent: Kein `posthog-js`-Laden, keine Client-Side-Events. Server-Side-Events (PostHog Python SDK) bleiben aktiv, da sie unter Vertragserfüllung fallen.

### 7.4 Anonymisierung und Pseudonymisierung

| Property                    | Behandlung                           | Begründung                                                               |
| --------------------------- | ------------------------------------ | ------------------------------------------------------------------------ |
| `user_id`                   | Pseudonymisiert (UUID, kein PII)     | UUID ist nicht direkt zuordenbar ohne DB-Zugriff                         |
| `email_hash` (nur Waitlist) | SHA-256-Hash, kein Klartext          | Datenminimierung; E-Mail wird nicht an PostHog übermittelt               |
| `error_message`             | Sanitisiert                          | Keine E-Mail-Adressen, Passwörter oder Token-Fragmente in Error-Messages |
| `query_length`              | Nur Länge, nicht der Query-Text      | Suchbegriffe können PII enthalten; nur Zeichenanzahl wird getrackt       |
| Suchbegriff                 | Nicht getrackt                       | Suchqueries können Namen, Projekte und andere PII enthalten              |
| `page_name`                 | Route-Name, keine URL mit Parametern | Keine dynamischen Parameter (IDs etc.) in Pageview-Events                |

### 7.5 IP-Handling

**Konfiguration:** PostHog Self-Hosted wird so konfiguriert, dass IP-Adressen **nicht gespeichert** werden.

- PostHog-Einstellung: `POSTHOG_PERSONAL_API_KEY` mit `anonymize_ips: true`
- Alternativ: Reverse-Proxy vor PostHog, der IP-Adressen vor der Weiterleitung entfernt
- Geolokalisierung: Nicht benötigt (Zielgruppe DACH ist bekannt)

### 7.6 Data Retention der Analytics-Daten

| Datentyp                        | Speicherdauer                    | Lösch-Mechanismus                                                                 |
| ------------------------------- | -------------------------------- | --------------------------------------------------------------------------------- |
| Event-Daten (ClickHouse)        | 365 Tage                         | PostHog-intern: `PLUGIN_STORAGE_TTL` oder manueller ClickHouse-Retention-Job      |
| Person Properties               | Bis Account-Löschung des Nutzers | Bei Account-Löschung: PostHog-Person löschen via API (`DELETE /api/persons/{id}`) |
| Funnel-/Dashboard-Aggregationen | Unbegrenzt (anonymisiert)        | Aggregierte Daten ohne Personenbezug – keine Löschpflicht                         |

### 7.7 Consent-Banner-Spezifikation

Da Server-Side-Events keinen Consent benötigen, bezieht sich der Consent-Banner nur auf Client-Side-Analytics:

```
┌────────────────────────────────────────────────────────┐
│  🔒 Wir nutzen anonymisierte Nutzungsanalysen,        │
│  um PWBS zu verbessern. Deine Daten bleiben in der EU │
│  und werden nie an Dritte weitergegeben.               │
│                                                        │
│  [ Ablehnen ]          [ Akzeptieren ]                 │
│                                                        │
│  Details in unserer Datenschutzerklärung               │
└────────────────────────────────────────────────────────┘
```

- Kein Pre-Check (TDDDG § 25)
- „Ablehnen" muss gleichwertig prominent sein wie „Akzeptieren"
- Consent-Entscheidung wird in `localStorage` gespeichert (kein Cookie nötig)
- Consent-Status an PostHog Backend melden: Wenn abgelehnt, PostHog JS-SDK nicht laden

---

## 8. Dashboard-Spezifikation

### Dashboard 1: Activation Overview

**Zweck:** Tagesaktuelle Sicht auf Registrierungen und den Activation Funnel.

| Widget                              | Visualisierung                                                           | Datenquelle (Events)                                                                                                                | Zeitraum       |
| ----------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| Signup-Trend                        | Liniendiagramm: Registrierungen pro Tag                                  | `auth_user_registered` (COUNT pro Tag)                                                                                              | Letzte 30 Tage |
| Activation Funnel                   | Funnel-Diagramm (5 Schritte, siehe 6.1)                                  | `auth_user_registered` → `onboarding_started` → `connector_connected` → `briefing_generated` (is_first) → `briefing_viewed` (first) | Letzte 30 Tage |
| Time-to-First-Briefing Distribution | Histogramm: Verteilung in Minuten-Buckets (0–5, 5–10, 10–20, 20–30, 30+) | `DATEDIFF(briefing_generated[first].timestamp, auth_user_registered.timestamp)` pro Nutzer                                          | Letzte 30 Tage |
| Connector Completion Rate           | Einzelzahl (%) + Trend-Pfeil                                             | `COUNT(users WITH connector_connected IN first_24h) / COUNT(auth_user_registered)`                                                  | Letzte 30 Tage |
| Waitlist → Signup Conversion        | Einzelzahl (%)                                                           | Waitlist-DB + `auth_user_registered` mit `referral_source = 'waitlist'`                                                             | Letzte 30 Tage |

### Dashboard 2: Retention & Engagement

**Zweck:** Langfristiger Blick auf Nutzerbindung und Feature-Nutzung.

| Widget                          | Visualisierung                                                                | Datenquelle (Events)                                                                        | Zeitraum       |
| ------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------- |
| WAU / MAU                       | Liniendiagramm: Wöchentlich aktive Nutzer und monatlich aktive Nutzer         | `DISTINCT user_id` mit beliebigem Event pro Woche/Monat                                     | Letzte 90 Tage |
| Retention-Kurve (Kohorten)      | Heatmap: Kohorte (Registrierungswoche) × Woche (0–12)                         | `auth_user_registered` (Kohorte) + beliebiges Aktivitäts-Event pro Woche                    | Letzte 90 Tage |
| Weekly Active Briefing Views    | Liniendiagramm: Durchschnittliche Briefing-Views pro aktivem Nutzer pro Woche | `COUNT(briefing_viewed) / COUNT(DISTINCT user_id WITH briefing_viewed)` pro Woche           | Letzte 90 Tage |
| Feature Usage Heatmap           | Heatmap: Feature-Name × Wochentag                                             | `app_feature_used` mit `feature_name`, gruppiert nach Wochentag                             | Letzte 90 Tage |
| Briefing-Relevanz-Score (Trend) | Liniendiagramm: Positiv-Anteil pro Woche                                      | `COUNT(briefing_feedback_given WHERE rating = 'positive') / COUNT(briefing_feedback_given)` | Letzte 90 Tage |

### Dashboard 3: Connector Health

**Zweck:** Operative Sicht auf Konnektor-Stabilität und Datenqualität.

| Widget                          | Visualisierung                                                   | Datenquelle (Events)                                                                                                                              | Zeitraum      |
| ------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| Connector Completion Funnel     | Funnel-Diagramm (4 Schritte, siehe 6.3)                          | `connector_oauth_started` → `connector_connected` → `connector_sync_completed` (is_first_sync) → `connector_sync_completed` (documents_count > 0) | Letzte 7 Tage |
| Sync Success Rate pro Konnektor | Gestapeltes Balkendiagramm: Erfolg vs. Fehler pro connector_type | `connector_sync_completed` vs. `connector_connection_failed` (WHERE trigger = 'sync'), gruppiert nach `connector_type`                            | Letzte 7 Tage |
| Documents per Connector         | Balkendiagramm: Median-Dokumentenanzahl pro connector_type       | `MEDIAN(connector_sync_completed.documents_count)` pro `connector_type`                                                                           | Letzte 7 Tage |
| Sync-Dauer (p50/p95)            | Tabelle: connector_type × p50 × p95 (in Sekunden)                | `connector_sync_completed.duration_ms` pro `connector_type`                                                                                       | Letzte 7 Tage |
| Aktive Konnektoren pro Nutzer   | Histogramm: Verteilung 0–4                                       | `connected_sources_count` User Property                                                                                                           | Aktuell       |

---

## 9. Implementierungs-Checkliste

### Phase 1: Tracking-Infrastruktur (vor Closed Beta)

| #   | Task                                                                                                                                                                     | Priorität | Frontend/Backend | Abhängigkeit          |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------- | ---------------- | --------------------- |
| 1   | PostHog Self-Hosted deployen (Docker Compose Service hinzufügen: `posthog` + `clickhouse`)                                                                               | P0        | Infra            | Docker Compose Config |
| 2   | `posthog-python` SDK als Backend-Dependency installieren und in FastAPI-Lifespan initialisieren                                                                          | P0        | Backend          | Task 1                |
| 3   | Server-Side-Events implementieren: `auth_user_registered`, `auth_user_logged_in`, `auth_user_logged_out`                                                                 | P0        | Backend          | Task 2                |
| 4   | Server-Side-Events implementieren: `connector_oauth_started`, `connector_connected`, `connector_connection_failed`, `connector_sync_completed`, `connector_disconnected` | P0        | Backend          | Task 2                |
| 5   | Server-Side-Events implementieren: `briefing_generated`, `briefing_feedback_given`                                                                                       | P0        | Backend          | Task 2                |
| 6   | Server-Side-Events implementieren: `search_executed`                                                                                                                     | P0        | Backend          | Task 2                |
| 7   | PostHog `identify()` bei Login aufrufen: User Properties initial setzen                                                                                                  | P0        | Backend          | Task 2                |
| 8   | User Properties bei Konnektor- und Briefing-Events aktualisieren (`connected_sources_count`, `total_briefings_generated`, etc.)                                          | P0        | Backend          | Tasks 4, 5            |

### Phase 2: Client-Side Analytics (nach Consent-Banner)

| #   | Task                                                                                                                               | Priorität | Frontend/Backend | Abhängigkeit                                               |
| --- | ---------------------------------------------------------------------------------------------------------------------------------- | --------- | ---------------- | ---------------------------------------------------------- |
| 9   | Consent-Banner-Komponente implementieren (TDDDG § 25 konform)                                                                      | P1        | Frontend         | Datenschutzerklärung muss live sein (LEGAL_COMPLIANCE B-1) |
| 10  | `posthog-js` SDK bedingt laden (nur bei Consent) als Next.js Provider                                                              | P1        | Frontend         | Task 9                                                     |
| 11  | Client-Side-Events implementieren: `app_page_viewed` (Route-Change-Listener)                                                       | P1        | Frontend         | Task 10                                                    |
| 12  | Client-Side-Events implementieren: `onboarding_started`, `onboarding_step_completed`, `onboarding_completed`, `onboarding_skipped` | P1        | Frontend         | Task 10                                                    |
| 13  | Client-Side-Events implementieren: `briefing_viewed` (Intersection Observer: ≥ 3 Sek. sichtbar)                                    | P1        | Frontend         | Task 10                                                    |
| 14  | Client-Side-Events implementieren: `search_result_clicked`                                                                         | P1        | Frontend         | Task 10                                                    |
| 15  | Client-Side-Events implementieren: `app_session_started`, `app_feature_used`                                                       | P2        | Frontend         | Task 10                                                    |

### Phase 3: Dashboards und Monitoring

| #   | Task                                                                                       | Priorität | Frontend/Backend | Abhängigkeit     |
| --- | ------------------------------------------------------------------------------------------ | --------- | ---------------- | ---------------- |
| 16  | PostHog Dashboard „Activation Overview" einrichten (5 Widgets)                             | P1        | PostHog          | Tasks 3–8        |
| 17  | PostHog Dashboard „Retention & Engagement" einrichten (5 Widgets)                          | P1        | PostHog          | Tasks 3–8, 11–15 |
| 18  | PostHog Dashboard „Connector Health" einrichten (5 Widgets)                                | P1        | PostHog          | Tasks 4, 8       |
| 19  | Funnel-Definitionen in PostHog konfigurieren (Activation, Retention, Connector Completion) | P1        | PostHog          | Tasks 3–8        |
| 20  | Kohorten-Retention-Analyse konfigurieren (Registrierungs-Woche als Kohorte)                | P1        | PostHog          | Tasks 3, 11      |

### Phase 4: Datenhygiene und Account-Löschung

| #   | Task                                                                                         | Priorität | Frontend/Backend | Abhängigkeit                  |
| --- | -------------------------------------------------------------------------------------------- | --------- | ---------------- | ----------------------------- |
| 21  | PostHog-Person löschen via API bei PWBS-Account-Löschung (30-Tage-Karenzfrist-Job erweitern) | P1        | Backend          | Task 2, Account-Löschungs-Job |
| 22  | ClickHouse Retention Policy konfigurieren (365 Tage TTL auf Event-Daten)                     | P2        | Infra            | Task 1                        |
| 23  | IP-Anonymisierung in PostHog verifizieren (`anonymize_ips: true`)                            | P1        | Infra            | Task 1                        |
| 24  | `waitlist_signed_up` Event in Waitlist-Route integrieren                                     | P2        | Backend          | Task 2                        |

---

## Anhang: Referenzen auf Quelldokumente

| Dokument                                             | Relevanz für Tracking-Plan                                                                              |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| [GTM_PLAN.md](GTM_PLAN.md)                           | Top-5 Launch-KPIs, Zielwerte Closed/Open Beta, Beta-Exit-Kriterien                                      |
| [PRD-SPEC.md](../PRD-SPEC.md)                        | Produkthypothese (60 % 14-Tage-Retention, ≥ 3 Briefings/Woche), User Stories, Funktionale Anforderungen |
| [UX_ONBOARDING_SPEC.md](UX_ONBOARDING_SPEC.md)       | Critical User Journey (Register → First Briefing), Onboarding-Wizard-Schritte, Fehlerszenarien          |
| [LEGAL_COMPLIANCE.md](LEGAL_COMPLIANCE.md)           | Consent-Architektur (Art. 6 DSGVO), TDDDG § 25, Analytics-Anforderungen, IP-Handling                    |
| [onboarding-flow.md](public-beta/onboarding-flow.md) | API-Endpunkte, Metriken-Definitionen, technischer Backend-Flow                                          |
