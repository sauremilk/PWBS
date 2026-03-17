# Betriebs- und Support-Plan: PWBS

**Version:** 1.0
**Stand:** 17. März 2026
**Scope:** Phase 2 (MVP) → Closed Beta → Open Beta
**Betriebsmodell:** Solo-/Kleinteam (1–2 Personen)
**Basisdokumente:** [ARCHITECTURE.md](../ARCHITECTURE.md), [GTM_PLAN.md](GTM_PLAN.md), [disaster-recovery.md](runbooks/disaster-recovery.md), [security-audit.md](../legal/security-audit.md)

---

## Inhaltsverzeichnis

1. [Betriebsübersicht](#1-betriebsübersicht)
2. [Service Level Objectives (SLOs)](#2-service-level-objectives-slos)
3. [Monitoring & Alerting](#3-monitoring--alerting)
4. [Incident-Response-Protokoll](#4-incident-response-protokoll)
5. [Support-Kanäle](#5-support-kanäle)
6. [Runbook-Index](#6-runbook-index)
7. [Rollback-Strategie](#7-rollback-strategie)
8. [Kapazitätsplanung](#8-kapazitätsplanung)
9. [On-Call & Erreichbarkeit](#9-on-call--erreichbarkeit)
10. [Offene Maßnahmen](#10-offene-maßnahmen)

---

## 1. Betriebsübersicht

### 1.1 System-Topologie

Das PWBS ist ein modularer Monolith auf AWS (eu-central-1, Frankfurt). Die vollständige Architektur ist in [ARCHITECTURE.md](../ARCHITECTURE.md) dokumentiert.

```
Vercel (Edge)              AWS eu-central-1
┌──────────────┐           ┌────────────────────────────────────┐
│  Next.js     │──HTTPS──▶│  ALB → ECS Fargate (FastAPI, 2×)  │
│  Frontend    │           │         │                          │
└──────────────┘           │    ┌────┼────────┬──────────┐     │
                           │    ▼    ▼        ▼          ▼     │
                           │  RDS   Weaviate  Neo4j    Redis   │
                           │  (PG)  (EC2)    (EC2,opt) (EC)    │
                           │                                    │
                           │  Celery Workers (3 Queues):        │
                           │  - ingestion (4 Worker)            │
                           │  - processing (2 Worker)           │
                           │  - briefing (2 Worker)             │
                           │  Celery Beat (Scheduler)           │
                           └────────────────────────────────────┘
```

### 1.2 Service-Inventar

| Service                      | Hosting                  | Port | Abhängigkeiten              | Kritisch? |
| ---------------------------- | ------------------------ | ---- | --------------------------- | :-------: |
| **FastAPI Backend**          | ECS Fargate (2 Tasks)    | 8000 | PostgreSQL, Redis, Weaviate |    ✅     |
| **PostgreSQL 16**            | AWS RDS (t3)             | 5432 | —                           |    ✅     |
| **Weaviate 1.28**            | EC2 (t3.xlarge)          | 8080 | —                           |    ✅     |
| **Redis 7**                  | ElastiCache              | 6379 | —                           |    ✅     |
| **Neo4j 5.26**               | EC2 (t3.large), optional | 7687 | —                           |    ❌     |
| **Celery Ingestion Worker**  | ECS Fargate              | —    | Redis, PostgreSQL           |    ⚠️     |
| **Celery Processing Worker** | ECS Fargate              | —    | Redis, PostgreSQL, Weaviate |    ⚠️     |
| **Celery Briefing Worker**   | ECS Fargate              | —    | Redis, PostgreSQL, LLM-API  |    ⚠️     |
| **Celery Beat**              | ECS Fargate              | —    | Redis                       |    ⚠️     |
| **Next.js Frontend**         | Vercel                   | 443  | Backend-API                 |    ✅     |
| **Prometheus**               | EC2 / Container          | 9090 | Scrape-Target: API          |    ❌     |
| **Grafana**                  | EC2 / Container          | 3000 | Prometheus                  |    ❌     |

### 1.3 Kritischer Pfad: Nutzer → Briefing

Damit ein Nutzer ein Briefing erhält, müssen folgende Services funktionieren:

```
1. Frontend (Vercel)           – Login, Dashboard-Anzeige
2. API (ECS Fargate)           – Auth, Briefing-Endpoint
3. PostgreSQL (RDS)            – Nutzerdaten, Briefing-Persistenz
4. Redis (ElastiCache)         – Session-Cache, Rate Limiting
5. Weaviate                    – Semantische Suche für Kontextdaten
6. LLM-API (Claude/OpenAI)    – Briefing-Generierung
7. Celery Briefing Worker      – Asynchrone Generierung (bei Scheduled Briefings)
```

**Nicht-kritisch für Briefings:** Neo4j (Graceful Degradation → leere Graph-Ergebnisse), Prometheus/Grafana (nur Monitoring).

---

## 2. Service Level Objectives (SLOs)

Interne Zielwerte – kein vertraglicher Anspruch in der Beta-Phase. Die SLOs orientieren sich am realistischen Betrieb eines Kleinteams.

| Metrik                         | Zielwert                                 | Messmethode                                                                    | Alerting-Schwellwert                                   |
| ------------------------------ | ---------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------ |
| **API-Verfügbarkeit**          | 99,5 % (Geschäftszeiten Mo–Fr 07–20 Uhr) | Prometheus `up{job="pwbs-api"}` + Health-Check                                 | < 99 % über rollierendes 1h-Fenster                    |
| **API Response Time p95**      | < 500 ms (Standard-Endpoints)            | Prometheus `http_request_duration_seconds` p95                                 | p95 > 800 ms über 5 min                                |
| **Briefing-Generierungsdauer** | < 30 s (Morning Briefing)                | Custom-Metrik `briefing_generation_duration_seconds`                           | > 60 s über 3 aufeinanderfolgende Generierungen        |
| **Konnektor-Sync-Latenz**      | < 5 min (inkrementeller Sync)            | Differenz `sync_run.completed_at - sync_run.started_at`                        | > 10 min für einzelnen Sync-Run                        |
| **HTTP 5xx Error Rate**        | < 1 % aller Requests                     | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])` | > 2 % über 5 min                                       |
| **Datenbank-Verfügbarkeit**    | 99,9 %                                   | RDS Monitoring + `pg_isready` Health-Check                                     | PostgreSQL Health-Check schlägt 3× hintereinander fehl |
| **Weaviate-Verfügbarkeit**     | 99,5 %                                   | `/v1/.well-known/ready` Health-Check                                           | 3 aufeinanderfolgende Fehlschläge                      |
| **Redis-Verfügbarkeit**        | 99,9 %                                   | `redis-cli ping`                                                               | Ping-Fehler > 30 s                                     |

---

## 3. Monitoring & Alerting

### 3.1 Vorhandene Infrastruktur

- **Prometheus:** Konfiguriert (`infra/prometheus/prometheus.yml`), scrapt `/metrics` am API-Service im 15s-Intervall
- **Grafana:** Dashboard `pwbs-api-overview.json` vorhanden mit Panels: Request Duration p95/p99, Request Rate, Error Rate
- **Sentry:** Geplant, noch nicht konfiguriert

### 3.2 Monitoring-Matrix

#### Health-Metriken

| Metrik                  | Quelle                                    | Dashboard               | Alert-Regel                        | Eskalation               |
| ----------------------- | ----------------------------------------- | ----------------------- | ---------------------------------- | ------------------------ |
| API Health-Check        | `GET /api/v1/admin/health`                | Grafana: API Overview   | 3 Fehlschläge in 60 s → P0         | Discord-Webhook + E-Mail |
| PostgreSQL-Connections  | RDS CloudWatch `DatabaseConnections`      | Grafana: DB Panel       | > 80 % Connection-Pool → P2        | Discord-Webhook          |
| Redis-Ping              | `redis-cli ping` über Prometheus Exporter | Grafana: Redis Panel    | Fehlschlag > 30 s → P1             | Discord-Webhook + E-Mail |
| Weaviate-Ready          | `/v1/.well-known/ready`                   | Grafana: Weaviate Panel | 3 Fehlschläge in 60 s → P1         | Discord-Webhook + E-Mail |
| Neo4j-Status (optional) | `neo4j status`                            | Grafana: Graph Panel    | Fehlschlag → kein Alert (optional) | —                        |

#### Performance-Metriken

| Metrik                   | Quelle                                               | Dashboard               | Alert-Regel                  | Eskalation      |
| ------------------------ | ---------------------------------------------------- | ----------------------- | ---------------------------- | --------------- |
| Request Duration p95     | Prometheus `http_request_duration_seconds`           | Grafana: API Overview   | p95 > 800 ms über 5 min → P2 | Discord-Webhook |
| Request Duration p99     | Prometheus `http_request_duration_seconds`           | Grafana: API Overview   | p99 > 2 s über 5 min → P1    | Discord-Webhook |
| Briefing Generation Time | Custom Metrik `briefing_generation_duration_seconds` | Grafana: Briefing Panel | > 60 s → P2                  | Discord-Webhook |
| DB Query Duration        | Prometheus `sqlalchemy_query_duration_seconds`       | Grafana: DB Panel       | p95 > 200 ms → P2            | Discord-Webhook |

#### Error-Metriken

| Metrik                  | Quelle                                          | Dashboard                 | Alert-Regel                                        | Eskalation                   |
| ----------------------- | ----------------------------------------------- | ------------------------- | -------------------------------------------------- | ---------------------------- |
| HTTP 5xx Rate           | Prometheus `http_requests_total{status=~"5.."}` | Grafana: API Overview     | > 2 % über 5 min → P1                              | Discord-Webhook + E-Mail     |
| Unhandled Exceptions    | Sentry (nach Konfiguration)                     | Sentry Dashboard          | Jede neue Exception → Sentry-Alert                 | Sentry → Discord Integration |
| Connector Sync Failures | `sync_runs` Tabelle, Status = `error`           | Grafana: Connectors Panel | 3 aufeinanderfolgende Fehler eines Konnektors → P2 | Discord-Webhook              |
| Celery Task Failures    | Celery Flower / Prometheus Exporter             | Grafana: Worker Panel     | > 5 fehlgeschlagene Tasks in 15 min → P2           | Discord-Webhook              |

#### Ressourcen-Metriken

| Metrik                  | Quelle                              | Dashboard            | Alert-Regel                    | Eskalation               |
| ----------------------- | ----------------------------------- | -------------------- | ------------------------------ | ------------------------ |
| CPU-Auslastung          | ECS CloudWatch / Container-Metrics  | Grafana: Resources   | > 80 % über 10 min → P2        | Discord-Webhook          |
| Memory-Auslastung       | ECS CloudWatch / Container-Metrics  | Grafana: Resources   | > 85 % über 5 min → P1         | Discord-Webhook + E-Mail |
| Disk Usage (Weaviate)   | CloudWatch EBS Metrics              | Grafana: Resources   | > 80 % → P2                    | Discord-Webhook          |
| Disk Usage (PostgreSQL) | RDS CloudWatch `FreeStorageSpace`   | Grafana: Resources   | < 5 GB verbleibend → P1        | Discord-Webhook + E-Mail |
| Redis Memory            | ElastiCache CloudWatch `UsedMemory` | Grafana: Redis Panel | > 200 MB (von 256 MB max) → P2 | Discord-Webhook          |

#### Business-Metriken

| Metrik                  | Quelle                                 | Dashboard                 | Alert-Regel                        | Eskalation      |
| ----------------------- | -------------------------------------- | ------------------------- | ---------------------------------- | --------------- |
| Registrierungen/Tag     | `audit_log` + Analytics                | Grafana: Business Panel   | Nur Tracking (kein Alert)          | —               |
| Briefings generiert/Tag | Prometheus `briefings_generated_total` | Grafana: Business Panel   | 0 Briefings in 24 h (Werktag) → P2 | Discord-Webhook |
| Active Users (7-Tage)   | Analytics / DB-Query                   | Grafana: Business Panel   | Nur Tracking                       | —               |
| Connector-Syncs/Stunde  | `sync_runs` Tabelle                    | Grafana: Connectors Panel | Nur Tracking                       | —               |

### 3.3 Alerting-Konfiguration

**Notification-Kanäle:**

| Kanal               | Verwendung                | Konfiguration                                                   |
| ------------------- | ------------------------- | --------------------------------------------------------------- |
| **Discord-Webhook** | Alle Alerts (P0–P2)       | Webhook in `#ops-alerts` Channel, Grafana → Discord Integration |
| **E-Mail**          | Kritische Alerts (P0, P1) | Persönliche E-Mail des Betreibers, Grafana SMTP                 |
| **Sentry**          | Unhandled Exceptions      | Sentry → Discord Integration für `#bug-reports`                 |

**Alerting-Regeln (Grafana Alerting):**

```yaml
# Beispiel-Alert: API Down
- alert: ApiDown
  expr: up{job="pwbs-api"} == 0
  for: 1m
  labels:
    severity: P0
  annotations:
    summary: "PWBS API ist nicht erreichbar"
    runbook: "docs/runbooks/disaster-recovery.md"

# Beispiel-Alert: Hohe Error Rate
- alert: HighErrorRate
  expr: >
    sum(rate(http_requests_total{status=~"5.."}[5m]))
    / sum(rate(http_requests_total[5m])) > 0.02
  for: 5m
  labels:
    severity: P1
  annotations:
    summary: "HTTP 5xx Rate über 2%"

# Beispiel-Alert: Briefing-Generierung langsam
- alert: SlowBriefingGeneration
  expr: histogram_quantile(0.95, briefing_generation_duration_seconds_bucket) > 60
  for: 10m
  labels:
    severity: P2
  annotations:
    summary: "Briefing-Generierung p95 > 60s"
```

---

## 4. Incident-Response-Protokoll

### 4.1 Severity-Stufen

| Stufe  | Beschreibung                               | Beispiel                                                                        | Max. Reaktionszeit | Kommunikation                                                |
| :----: | ------------------------------------------ | ------------------------------------------------------------------------------- | :----------------: | ------------------------------------------------------------ |
| **P0** | System-Ausfall – kein Nutzer kann arbeiten | API komplett down, DB-Corruption, Datenverlust                                  |     30 Minuten     | Status-Page, Discord `#ankündigungen`, E-Mail an Beta-Nutzer |
| **P1** | Kritische Funktion ausgefallen             | Briefings werden nicht generiert, Login nicht möglich, Suchfunktion down        |     2 Stunden      | Discord `#ankündigungen`, `#bug-reports`                     |
| **P2** | Feature eingeschränkt                      | Einzelner Konnektor synct nicht, langsame Antwortzeiten, Neo4j nicht erreichbar |     24 Stunden     | Discord `#bug-reports`, nächster Werktag                     |
| **P3** | Kosmetisch / Minor                         | UI-Darstellungsfehler, falsche Sortierung, Typo in Briefing                     |  Nächster Sprint   | Backlog-Eintrag                                              |

### 4.2 Incident-Ablauf

#### P0 – System-Ausfall

1. **Erkennung** (automatisch): Grafana Alert → Discord `#ops-alerts` + E-Mail
2. **Sofortmaßnahmen** (< 30 min):
   - Health-Check aller Services prüfen: `curl http://API_URL/api/v1/admin/health`
   - ECS-Tasks prüfen: `aws ecs describe-services --cluster pwbs --services api`
   - Logs prüfen: `aws logs tail /ecs/pwbs-api --since 30m`
   - Falls API-Container crasht: ECS Force-New-Deployment (neuer Task)
   - Falls DB-Problem: Disaster-Recovery-Runbook folgen → `docs/runbooks/disaster-recovery.md`
3. **Kommunikation** (< 1h):
   - Discord `#ankündigungen`: „Wir sind informiert über ein aktuelles Problem mit [Bereich]. Wir arbeiten daran."
   - Status-Page aktualisieren (sofern vorhanden)
4. **Post-Mortem** (innerhalb 48h): Pflicht ab P0. Dokument mit Timeline, Root Cause, Maßnahmen. Ablage in `docs/runbooks/postmortems/`.

#### P1 – Kritische Funktion

1. **Erkennung**: Grafana Alert oder Nutzermeldung in Discord
2. **Sofortmaßnahmen** (< 2h):
   - Betroffene Komponente identifizieren
   - Logs und Metriken prüfen
   - Workaround aktivieren (z. B. LLM-Fallback, Feature-Flag deaktivieren)
3. **Kommunikation**: Discord `#bug-reports` mit Status-Update
4. **Post-Mortem**: Empfohlen, aber nicht verpflichtend

#### P2 – Feature eingeschränkt

1. **Erkennung**: Monitoring oder Nutzermeldung
2. **Bearbeitung**: Nächster Werktag, innerhalb 24h
3. **Kommunikation**: Antwort in Discord `#bug-reports` innerhalb 24h

#### P3 – Minor

1. Backlog-Eintrag erstellen
2. Im nächsten Sprint bearbeiten

### 4.3 Post-Mortem-Template

```markdown
# Post-Mortem: [Titel]

**Datum:** [Incident-Datum]
**Severity:** P0/P1
**Dauer:** [Von – Bis]
**Auswirkung:** [Wer war betroffen, wie viele Nutzer]

## Timeline

- HH:MM – Erster Alert
- HH:MM – Incident erkannt
- HH:MM – Maßnahme X eingeleitet
- HH:MM – Service wiederhergestellt

## Root Cause

[Ursache in 2–3 Sätzen]

## Was hat funktioniert?

- [Alerting, Runbooks, etc.]

## Was hat nicht funktioniert?

- [Fehlende Alerts, unklare Runbooks, etc.]

## Maßnahmen

| #   | Maßnahme | Verantwortlich | Deadline |
| --- | -------- | -------------- | -------- |
| 1   | ...      | ...            | ...      |
```

---

## 5. Support-Kanäle

### 5.1 Kanal-Übersicht

| Kanal                            | Zielgruppe                           |  Response-Zeit-Ziel   | Priorisierung                                                                 |
| -------------------------------- | ------------------------------------ | :-------------------: | ----------------------------------------------------------------------------- |
| **Discord `#bug-reports`**       | Alle Beta-Nutzer                     |        < 24 h         | Primärer Bug-Kanal – alles was kaputt ist                                     |
| **Discord `#feature-requests`**  | Alle Beta-Nutzer                     |        < 48 h         | Sekundär – Wünsche und Verbesserungen                                         |
| **Discord `#hilfe-und-support`** | Alle Beta-Nutzer                     |        < 24 h         | Fragen zur Nutzung, Onboarding-Hilfe                                          |
| **E-Mail (support@...)**         | Nicht-Discord-Nutzer, DSGVO-Anfragen |        < 48 h         | Fallback, datenschutzrelevante Anfragen                                       |
| **In-App Feedback**              | Alle Nutzer                          | Automatisch gesammelt | Briefing-Feedback (Daumen hoch/runter), direkt in `briefing_feedback` Tabelle |
| **1-on-1 Feedback-Calls**        | Design Partners (Closed Beta)        |  Wöchentlich, 15 min  | Höchste Qualität, nur Closed Beta                                             |

### 5.2 Eskalationspfad: Wann wird Support zu einem Bug?

```
Nutzer meldet Problem in Discord
       │
       ▼
Reproduzierbar? ──Nein──▶ Rückfrage stellen, ggf. Logs anfordern
       │
      Ja
       │
       ▼
Auswirkung bewerten:
  ├── System-Ausfall, Datenverlust          → P0 (sofort)
  ├── Funktion kaputt, kein Workaround      → P1 (< 2h)
  ├── Funktion eingeschränkt, Workaround da → P2 (< 24h)
  └── Kosmetisch, Edge-Case                 → P3 (Backlog)
       │
       ▼
GitHub Issue erstellen mit:
  - Severity-Label (P0–P3)
  - Reproduktionsschritte
  - Betroffene Nutzeranzahl
  - Workaround (falls vorhanden)
```

### 5.3 Support-Werkzeuge

| Werkzeug            | Zweck                                               |
| ------------------- | --------------------------------------------------- |
| Discord Threads     | Isolierte Diskussion pro Bug/Request                |
| GitHub Issues       | Bug-Tracking und Priorisierung                      |
| Sentry (geplant)    | Automatische Exception-Erfassung mit User-Kontext   |
| `audit_log` Tabelle | Nachvollziehen von User-Aktionen bei Bug-Reports    |
| Grafana Dashboards  | Performance-Kontext bei gemeldeten Latenz-Problemen |

---

## 6. Runbook-Index

| Runbook                                             | Pfad                                     |     Status      | Zuletzt geprüft |
| --------------------------------------------------- | ---------------------------------------- | :-------------: | :-------------: |
| **Disaster Recovery** (PostgreSQL, Weaviate, Neo4j) | `docs/runbooks/disaster-recovery.md`     |  ✅ Vorhanden   |    März 2026    |
| **Deployment & Rollback**                           | `docs/runbooks/deployment.md`            | ❌ Zu erstellen |        —        |
| **Database-Migration (Alembic)**                    | `docs/runbooks/database-migration.md`    | ❌ Zu erstellen |        —        |
| **Connector-Debugging** (OAuth, Sync)               | `docs/runbooks/connector-debugging.md`   | ❌ Zu erstellen |        —        |
| **LLM-Fallback** (Claude → OpenAI → Ollama)         | `docs/runbooks/llm-fallback.md`          | ❌ Zu erstellen |        —        |
| **Weaviate-Reindexing**                             | `docs/runbooks/weaviate-reindexing.md`   | ❌ Zu erstellen |        —        |
| **Redis-Troubleshooting**                           | `docs/runbooks/redis-troubleshooting.md` | ❌ Zu erstellen |        —        |

### 6.1 Noch zu erstellende Runbooks – Kurzskizze

**Deployment & Rollback:**

- Zero-Downtime-Deploy via ECS Rolling Update (min/max 50 %/200 %)
- Docker Image Tag Pinning, ECS Task Definition Revisions
- Rollback-Verfahren: Vorherige Task Definition Revision aktivieren
- Alembic-Migration vor Deploy, Downgrade bei Fehlern

**Database-Migration (Alembic):**

- `alembic upgrade head` im CI/CD vor neuem Container-Deploy
- Bei Fehler: `alembic downgrade -1` + vorheriges Image deployen
- Bei destruktiven Migrationen (DROP COLUMN): Backup vor Migration erzwingen

**Connector-Debugging:**

- OAuth-Token abgelaufen: `connections.status` prüfen, manuellen Token-Refresh triggern
- Sync hängt: `sync_runs` nach `status = 'running'` > 30 min filtern, Task forciert abbrechen
- Rate-Limit der Quell-API: Exponential Backoff, Sync-Intervall temporär erhöhen

**LLM-Fallback:**

- Primär: Claude API (Anthropic) – Latenz < 5 s, Rate Limit 60 req/min
- Fallback 1: OpenAI GPT-4o – automatisch bei Claude-Timeout > 10 s oder HTTP 429/5xx
- Fallback 2: Ollama (lokal) – nur bei komplettem Cloud-Ausfall, `LLM_PROVIDER=ollama`
- Circuit Breaker: Nach 3 aufeinanderfolgenden Fehlern bei einem Provider → 5 min Cooldown

**Weaviate-Reindexing:**

- Bei Schema-Änderung oder Embedding-Modellwechsel
- Collection löschen und neu erstellen (Multi-Tenancy-Konfiguration beibehalten)
- Re-Embedding aller Chunks über Processing-Queue (`processing.embed`)
- Dauer bei 10.000 Chunks: ~8 min (Cloud-Embedding), ~25 min (lokal)

---

## 7. Rollback-Strategie

### 7.1 Code-Rollback

**ECS Fargate Deployment:**

```bash
# Aktive Task Definition ermitteln
aws ecs describe-services --cluster pwbs --services api \
  --query 'services[0].taskDefinition'

# Vorherige Revision aktivieren (Rollback)
aws ecs update-service --cluster pwbs --service api \
  --task-definition pwbs-api:<VORHERIGE_REVISION>

# Status prüfen
aws ecs wait services-stable --cluster pwbs --services api
```

**Rollback-Entscheidung:** Wenn nach einem Deploy die Error Rate > 5 % steigt oder der Health-Check 3× fehlschlägt, wird automatisch auf die vorherige Task Definition Revision zurückgerollt (ECS Circuit Breaker mit `rollback`-Konfiguration).

### 7.2 DB-Migrations-Rollback (Alembic)

```bash
# Letzte Migration rückgängig machen
alembic downgrade -1

# Auf spezifische Revision zurück
alembic downgrade <revision_id>

# Aktuelle Revision prüfen
alembic current
```

**Risiken:**

- `DROP COLUMN`-Migrationen sind nicht reversibel → immer Backup vor destruktiven Migrationen
- Datenmigrationen (z. B. Spaltenumbenennung mit Datenkopie) erfordern manuelles Rollback
- **Regel:** Destruktive Migrationen nur mit vorherigem PostgreSQL-Snapshot (RDS Snapshot)

### 7.3 Feature-Flag-Deaktivierung

Folgende Features können per Feature-Flag (`feature_flags` Tabelle oder ENV-Override) deaktiviert werden:

| Feature-Flag                  | Wirkung                               | Deaktivierung                                        |
| ----------------------------- | ------------------------------------- | ---------------------------------------------------- |
| `beta_registration_open`      | Neue Registrierungen erlauben/sperren | Sofort, Notbremse bei Überlast                       |
| `briefing_generation_enabled` | Briefing-Generierung an/aus           | Sofort, bei LLM-Problemen                            |
| `neo4j_enabled`               | Knowledge-Graph-Features              | Sofort, Graceful Degradation über `NullGraphService` |
| `connector_sync_enabled`      | Automatische Connector-Syncs          | Sofort, bei API-Rate-Limit-Problemen                 |

**Verfahren:** Feature-Flags können über den Admin-Endpoint oder direkt in der DB gesetzt werden:

```sql
UPDATE feature_flags SET enabled = false WHERE name = 'briefing_generation_enabled';
```

Alternativ über ENV-Override: `FEATURE_BRIEFING_GENERATION_ENABLED=false` → ECS Service Update.

### 7.4 Daten-Rollback

Wenn ein Daten-Rollback nötig ist (korrupte Daten, fehlgeleitete Migration):

1. **Entscheidung:** Ist das Problem datenbankübergreifend oder auf eine DB beschränkt?
2. **Reihenfolge:** PostgreSQL → Weaviate → Neo4j (FK-Abhängigkeiten beachten)
3. **Verfahren:** Siehe [Disaster Recovery Runbook](runbooks/disaster-recovery.md)
4. **RPO:** < 1 Stunde (stündliche Backups)
5. **RTO:** < 4 Stunden
6. **Validierung nach Restore:** Checkliste aus dem DR-Runbook, Abschnitt 7

---

## 8. Kapazitätsplanung

### 8.1 Phasen-basierte Lastschätzung

| Phase            |   Nutzer   | API-Calls/Tag  | Briefings/Tag | Gespeicherte Dokumente | LLM-Calls/Tag |
| ---------------- | :--------: | :------------: | :-----------: | :--------------------: | :-----------: |
| **Closed Beta**  |   10–20    |    ~100–400    |    ~20–60     |     ~2.000–10.000      |   ~100–300    |
| **Open Beta**    |   50–200   |  ~1.000–4.000  |   ~100–600    |    ~10.000–100.000     |  ~500–2.000   |
| **GA (Phase 3)** | 500–1.000+ | ~10.000–40.000 | ~1.000–3.000  |       ~500.000+        | ~5.000–15.000 |

### 8.2 Infrastruktur-Anforderungen

| Phase           | API (ECS)             | PostgreSQL (RDS)         | Weaviate (EC2)            | Redis               | Geschätzte Kosten/Monat |
| --------------- | --------------------- | ------------------------ | ------------------------- | ------------------- | :---------------------: |
| **Closed Beta** | 2× 0.25 vCPU / 512 MB | t3.micro (2 vCPU, 1 GB)  | t3.medium (2 vCPU, 4 GB)  | t3.micro (cache)    |       ~150–250 €        |
| **Open Beta**   | 2× 0.5 vCPU / 1 GB    | t3.small (2 vCPU, 2 GB)  | t3.large (2 vCPU, 8 GB)   | t3.small (cache)    |       ~350–550 €        |
| **GA**          | 4× 1 vCPU / 2 GB      | t3.medium + Read Replica | t3.xlarge (4 vCPU, 16 GB) | t3.medium + Cluster |      ~800–1.500 €       |

### 8.3 Identifizierte Bottlenecks

| Bottleneck                     |              Wann kritisch?               | Symptom                                    | Gegenmaßnahme                                                                       |
| ------------------------------ | :---------------------------------------: | ------------------------------------------ | ----------------------------------------------------------------------------------- |
| **LLM-API-Rate-Limits**        | > 50 gleichzeitige Briefings (Open Beta+) | Briefing-Generierung verzögert, 429-Fehler | Zeitversetztes Generieren (±15 min Jitter), LLM-Response-Cache, Fallback auf OpenAI |
| **Weaviate RAM**               |  > 100.000 Dokumente (HNSW-Index in RAM)  | Langsame Suchanfragen, OOM-Kills           | RAM aufstocken (t3.xlarge → r6i), Quantisierung aktivieren                          |
| **PostgreSQL Connection Pool** |        > 200 gleichzeitige Nutzer         | Connection-Timeouts, 503-Fehler            | PgBouncer einführen, `max_connections` erhöhen                                      |
| **Redis Memory**               |  > 200 MB Cache-Nutzung (von 256 MB max)  | LRU-Evictions, Cache-Miss-Rate steigt      | `maxmemory` erhöhen, Cache-TTLs anpassen                                            |
| **Celery Worker-Queues**       |       > 100 Sync-Jobs gleichzeitig        | Stau in Ingestion-Queue, verzögerte Syncs  | Worker-Anzahl skalieren, Queue-Prioritäten anpassen                                 |
| **Disk (Weaviate)**            |            > 50 GB Index-Größe            | Disk-IO-Engpass, Schreibverzögerungen      | SSD-Upgrade (gp3 → io2), alte Daten bereinigen                                      |

### 8.4 Skalierungsmaßnahmen nach Phase

**Closed Beta → Open Beta:**

- ECS Tasks von 2 auf 4 skalieren (API)
- RDS auf t3.small upgraden
- Weaviate auf t3.large (8 GB RAM)
- Redis `maxmemory` auf 512 MB erhöhen
- Celery Worker: Ingestion 4→6, Processing 2→4

**Open Beta → GA:**

- ECS Auto-Scaling aktivieren (Target: CPU < 70 %)
- RDS Read Replica für Leseabfragen (Briefing-Liste, Suche)
- PgBouncer für Connection Pooling
- Weaviate: r6i.xlarge oder Weaviate Cloud evaluieren
- CDN für statische Frontend-Assets (bereits über Vercel abgedeckt)
- Celery: SQS als Broker evaluieren (höhere Resilienz)

---

## 9. On-Call & Erreichbarkeit

### 9.1 Realistisches Modell für Solo-/Kleinteam

| Zeitfenster              |        Erreichbarkeit        |     Für welche Severity?      |
| ------------------------ | :--------------------------: | :---------------------------: |
| **Mo–Fr, 08–20 Uhr**     |   Aktiv, < 30 min Reaktion   |          P0, P1, P2           |
| **Mo–Fr, 20–08 Uhr**     | Best-Effort, nächster Morgen | Nur P0 (bei Alert auf Handy)  |
| **Wochenende**           |       Nur bei P0-Alert       |   P0 (automatischer Alert)    |
| **Urlaub / Abwesenheit** |     Keine Erreichbarkeit     | System muss autonom überleben |

### 9.2 Automatisierung gegen menschliches Eingreifen

| Automatisierung                    | Was sie ersetzt                                    |                Status                |
| ---------------------------------- | -------------------------------------------------- | :----------------------------------: |
| **ECS Auto-Recovery**              | API-Container startet automatisch neu bei Crash    | ✅ Aktiv (`restart: unless-stopped`) |
| **ECS Circuit Breaker**            | Automatischer Rollback bei fehlgeschlagenem Deploy |          ✅ Konfigurierbar           |
| **RDS Automated Backups**          | Manuelles Backup-Triggern                          |         ✅ Aktiv (stündlich)         |
| **Health-Check-basiertes Routing** | Manuelles Umschalten bei Ausfall                   |         ✅ ALB Health Checks         |
| **LLM Circuit Breaker**            | Manuelles Umschalten Claude → OpenAI               |           ✅ Implementiert           |
| **Redis AOF Persistence**          | Datenverlust bei Redis-Neustart                    |     ✅ Aktiv (`appendonly yes`)      |
| **Feature-Flag-Notbremse**         | Manuelles Code-Deploy zum Deaktivieren             |       ✅ ENV-Override möglich        |
| **Grafana Alerting**               | Manuelles Monitoring-Prüfen                        |         🔧 Zu konfigurieren          |
| **Auto-Scaling (ECS)**             | Manuelles Skalieren bei Last                       |          🔧 Open Beta Phase          |

### 9.3 Was kann bis zum nächsten Werktag warten?

| Problem                           | Warten bis Werktag? | Begründung                                           |
| --------------------------------- | :-----------------: | ---------------------------------------------------- |
| Einzelner Konnektor synct nicht   |         ✅          | Daten max. 24h veraltet, kein Datenverlust           |
| Neo4j nicht erreichbar            |         ✅          | App funktioniert ohne Neo4j (Graceful Degradation)   |
| Sentry-Events (Exceptions)        |         ✅          | Einzelne Edge-Case-Fehler sind nicht systemkritisch  |
| Langsame Antwortzeiten (< 2s p95) |         ✅          | Nervig, aber nutzbar                                 |
| Briefing-Qualität schlecht        |         ✅          | Funktional vorhanden, Optimierung ist Sprint-Aufgabe |
| API komplett down                 |         ❌          | P0 – sofortige Reaktion nötig                        |
| Datenbankfehler / Corruption      |         ❌          | P0 – Datenverlust-Risiko                             |
| Sicherheitsvorfall (Datenleck)    |         ❌          | P0 – DSGVO-Meldepflicht 72h                          |

### 9.4 Abwesenheitsprotokoll

1. **Vor Abwesenheit:**
   - Sicherstellen, dass alle automatischen Recovery-Mechanismen aktiv sind
   - Keine riskanten Deployments in den 48h vor Abwesenheit
   - Discord `#ankündigungen`: „Support-Antworten können sich verzögern"
2. **Während Abwesenheit:**
   - P0-Alerts gehen auf Handy (E-Mail-Push)
   - P1–P3 werden in Discord gesammelt und nach Rückkehr abgearbeitet
   - Kein Deploy, keine DB-Migrationen
3. **Bei längerem Ausfall (> 3 Tage):**
   - Vertrauensperson mit AWS-Zugang briefen (Basiszugriff für ECS Force-Restart)
   - Runbooks müssen so geschrieben sein, dass eine technische Person den DR-Prozess durchführen kann

---

## 10. Offene Maßnahmen

Priorisierte Liste aller Ops-Tasks, geordnet nach Betriebsnotwendigkeit:

|  #  | Maßnahme                                                                                                                                       | Priorität |          Abhängigkeit           | Aufwand |
| :-: | ---------------------------------------------------------------------------------------------------------------------------------------------- | :-------: | :-----------------------------: | :-----: |
|  1  | **Sentry einrichten** – Error-Tracking, Exceptions mit User-Kontext, Discord-Integration                                                       |   Hoch    |   Sentry-Account, DSN in ENV    |  2–4 h  |
|  2  | **Grafana-Alerting konfigurieren** – Alert-Regeln für P0/P1 Metriken (API Down, Error Rate, DB-Fehler), Discord-Webhook als Notification-Kanal |   Hoch    | Grafana-Zugang, Discord-Webhook |  4–6 h  |
|  3  | **Deployment-Runbook schreiben** – Zero-Downtime-Deploy, Rollback-Verfahren, ECS Task Definition Management                                    |   Hoch    |                —                |  3–4 h  |
|  4  | **Status-Page einrichten** – Einfache Status-Page (z. B. Instatus, Cachet oder statische HTML auf S3) für Nutzer-Kommunikation bei Incidents   |  Mittel   |         Domain, Hosting         |  2–3 h  |
|  5  | **pip-audit in CI integrieren** – Automatischer CVE-Scan bei jedem PR (Security Finding A05-F01)                                               |   Hoch    |         GitHub Actions          |  1–2 h  |
|  6  | **CSP-Header implementieren** – Content-Security-Policy in SecurityHeadersMiddleware (Security Finding A03-F01)                                |  Mittel   |          Backend-Code           |  2–3 h  |
|  7  | **Production-Startup-Guard** – RSA-Key-Prüfung bei `PWBS_ENV=production`, kein Start ohne gültige Keys (Security Finding A02-F01)              |   Hoch    |          Backend-Code           |  1–2 h  |
|  8  | **Dependabot aktivieren** – `.github/dependabot.yml` für Python und npm (Security Finding A06-F01)                                             |  Mittel   |        GitHub-Repository        | 30 min  |
|  9  | **Database-Migration-Runbook schreiben** – Alembic-Verfahren, Rollback, Backup-Pflicht bei destruktiven Migrationen                            |  Mittel   |                —                |  2–3 h  |
| 10  | **Connector-Debugging-Runbook schreiben** – OAuth-Token-Refresh, Sync-Probleme, Rate-Limit-Handling                                            |  Mittel   |                —                |  2–3 h  |
| 11  | **LLM-Fallback-Runbook schreiben** – Provider-Kaskade, Circuit-Breaker-Konfiguration, Ollama-Setup                                             |  Mittel   |                —                |  2–3 h  |
| 12  | **Weaviate-Reindexing-Runbook schreiben** – Schema-Migration, Re-Embedding-Verfahren                                                           |  Niedrig  |                —                |  2–3 h  |
| 13  | **Grafana-Dashboards erweitern** – Panels für Business-Metriken, Celery-Worker-Status, Connector-Sync-Status                                   |  Niedrig  |             Grafana             |  4–6 h  |
| 14  | **Auto-Scaling konfigurieren** (ECS) – Target-Tracking auf CPU 70 %, min. 2 / max. 6 Tasks                                                     |  Niedrig  |         Open Beta Phase         |  2–3 h  |
| 15  | **Backup-Restore-Test durchführen** – DR-Runbook praktisch validieren, RTO-Messung                                                             |   Hoch    |          Testumgebung           |  4–6 h  |
| 16  | **CORS-Einschränkung** – `allow_methods` und `allow_headers` auf genutzte Werte beschränken (Security Finding A05-F02)                         |  Niedrig  |          Backend-Code           | 30 min  |
| 17  | **Docker Content Trust evaluieren** – Image-Signierung für Deployments (Security Finding A08-F01)                                              |  Niedrig  |         CI/CD-Pipeline          |  3–4 h  |

### Empfohlene Reihenfolge (vor Closed Beta Go-Live)

**Woche 1:** #1 (Sentry), #2 (Grafana Alerting), #5 (pip-audit), #7 (RSA-Guard), #8 (Dependabot)
**Woche 2:** #3 (Deployment-Runbook), #15 (Backup-Test), #6 (CSP-Header)
**Woche 3:** #4 (Status-Page), #9–#11 (Runbooks)
**Open Beta:** #13 (Dashboards), #14 (Auto-Scaling), #12 (Weaviate-Runbook)

---

_Erstellt: 17. März 2026 | Nächste Review: Vor Open Beta Launch_
