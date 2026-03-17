# Deployment & Rollback Runbook

> **Zuletzt geprüft:** März 2026
> **Verantwortlich:** Entwicklung / Ops
> **Quelle:** SUPPORT_OPERATIONS_PLAN §6.1, RELEASE_READINESS OPS-08

---

## 1. Voraussetzungen

- AWS CLI konfiguriert mit ECS- und ECR-Zugriff
- Docker CLI installiert (für lokales Image-Building)
- Zugriff auf `ghcr.io/sauremilk/pwbs-backend` Container Registry
- Alembic CLI verfügbar (`pip install alembic`)
- Umgebungsvariablen gesetzt (siehe `deploy/.env.example`)

---

## 2. Deployment-Übersicht

| Schritt | Aktion                        | Dauer (ca.) | Automatisiert |
| :-----: | ----------------------------- | :---------: | :-----------: |
|    1    | Docker Image bauen & pushen   |   3–5 min   |      CI       |
|    2    | Alembic-Migration ausführen   |   < 1 min   |    CI / CD    |
|    3    | ECS Task Definition erstellen |   < 1 min   |      CD       |
|    4    | ECS Service Update (Rolling)  |   3–5 min   |      CD       |
|    5    | Health-Check-Validierung      |   1–2 min   |    Manuell    |

---

## 3. Zero-Downtime-Deploy (ECS Rolling Update)

### 3.1 Docker Image bauen und taggen

```bash
# Image bauen (Multi-Stage, siehe backend/Dockerfile)
docker build -t ghcr.io/sauremilk/pwbs-backend:v<VERSION> backend/

# Image pushen
docker push ghcr.io/sauremilk/pwbs-backend:v<VERSION>
```

**Tag-Konvention:** Immer versionierte Tags verwenden (`v1.2.3`), niemals `:latest` in Produktion.

### 3.2 Alembic-Migration ausführen (vor Deploy)

```bash
# Gegen Produktions-DB ausführen (über Bastion oder CI-Runner)
DATABASE_URL=postgresql+asyncpg://<user>:<pw>@<host>:5432/pwbs \
  alembic upgrade head

# Ergebnis prüfen
alembic current
# Erwartete Ausgabe: <revision> (head)
```

**Bei Fehler:** Migration NICHT fortsetzen. Siehe [Abschnitt 5: Rollback](#5-rollback-verfahren).

### 3.3 Neue ECS Task Definition registrieren

```bash
# Task Definition JSON vorbereiten (Image-Tag aktualisieren)
sed -i "s|ghcr.io/sauremilk/pwbs-backend:.*|ghcr.io/sauremilk/pwbs-backend:v<VERSION>\"|" task-definition.json

# Registrieren
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### 3.4 ECS Service Update (Rolling)

```bash
# Service aktualisieren mit Rolling Update
aws ecs update-service \
  --cluster pwbs \
  --service api \
  --task-definition pwbs-api:<NEUE_REVISION> \
  --deployment-configuration "minimumHealthyPercent=50,maximumPercent=200"
```

**Rolling-Update-Strategie:**

- `minimumHealthyPercent=50` – mind. 50 % der Tasks bleiben während des Deployments aktiv
- `maximumPercent=200` – bis zu 200 % der gewünschten Tasks gleichzeitig (neue starten bevor alte stoppen)

### 3.5 Deployment-Status überwachen

```bash
# Deployment-Status prüfen
aws ecs describe-services --cluster pwbs --services api \
  --query 'services[0].deployments'

# Warten bis Deployment stabil (PRIMARY = gewünschte Count)
aws ecs wait services-stable --cluster pwbs --services api
```

---

## 4. Health-Check-Validierung nach Deploy

### 4.1 Automatischer Health-Check (ECS)

ECS prüft automatisch:

```
GET http://localhost:8000/api/v1/admin/health
Intervall: 15s | Timeout: 10s | Retries: 5 | Start Period: 30s
```

### 4.2 Manuelle Validierung

```bash
# API erreichbar?
curl -f https://<api-domain>/api/v1/admin/health

# Erwartete Antwort (HTTP 200):
# {"status": "healthy", "version": "...", ...}

# Stichprobe: Auth-Endpunkt
curl -s https://<api-domain>/api/v1/auth/me -H "Authorization: Bearer <token>" | head

# Stichprobe: Briefing-Generierung
curl -s -X POST https://<api-domain>/api/v1/briefings/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"briefing_type": "morning"}'
```

### 4.3 Monitoring prüfen

- **Grafana:** Error Rate < 5 % nach Deploy
- **Sentry:** Keine neuen Exceptions in den ersten 5 Minuten
- **Logs:** `docker logs` oder CloudWatch auf Startup-Fehler prüfen

---

## 5. Rollback-Verfahren

### 5.1 Code-Rollback (ECS Task Definition)

```bash
# Aktive Task Definition ermitteln
aws ecs describe-services --cluster pwbs --services api \
  --query 'services[0].taskDefinition'

# Vorherige Revision aktivieren
aws ecs update-service \
  --cluster pwbs \
  --service api \
  --task-definition pwbs-api:<VORHERIGE_REVISION>

# Warten bis stabil
aws ecs wait services-stable --cluster pwbs --services api
```

### 5.2 Migrations-Rollback (Alembic)

```bash
# Letzte Migration rückgängig machen
DATABASE_URL=postgresql+asyncpg://<user>:<pw>@<host>:5432/pwbs \
  alembic downgrade -1

# Status prüfen
alembic current
```

**Achtung bei destruktiven Migrationen** (DROP COLUMN, DROP TABLE):

1. Vor der Migration: PostgreSQL-Backup erzwingen (siehe `docs/runbooks/disaster-recovery.md`)
2. Bei Rollback-Bedarf: Backup-Restore statt Alembic-Downgrade

### 5.3 Vollständiger Rollback (Docker Compose Deployment)

Für Self-Hosting-Deployments mit `deploy/docker-compose.prod.yml`:

```bash
# Image-Tag in docker-compose.prod.yml auf vorherige Version setzen
# PWBS_IMAGE=ghcr.io/sauremilk/pwbs-backend:v<VORHERIGE_VERSION>

# Services neu starten
docker compose -f deploy/docker-compose.prod.yml up -d api celery-worker-ingestion celery-worker-processing

# Health-Check
curl -f http://localhost:8000/api/v1/admin/health
```

---

## 6. Celery-Worker-Deployment

Celery-Worker verwenden dasselbe Docker Image wie die API. Bei Updates:

```bash
# Worker neu starten (Docker Compose)
docker compose -f deploy/docker-compose.prod.yml up -d \
  celery-worker-ingestion celery-worker-processing celery-beat

# Laufende Tasks prüfen (Redis)
docker compose -f deploy/docker-compose.prod.yml exec redis \
  redis-cli LLEN ingestion.high
```

**Graceful Shutdown:** Celery-Worker beenden laufende Tasks vor dem Shutdown (`SIGTERM` → warm shutdown mit 30s Timeout).

---

## 7. Checkliste vor jedem Deploy

- [ ] Alle Unit-Tests grün (CI/CD)
- [ ] Alembic-Migration auf Staging getestet
- [ ] Docker Image gebaut und getaggt (nicht `:latest`)
- [ ] Backup der Produktions-DB aktuell (< 1h alt)
- [ ] Rollback-Revision notiert (aktuelle Task Definition)
- [ ] Monitoring-Dashboard geöffnet (Grafana, Sentry)

---

## 8. Troubleshooting

| Problem                          | Ursache                       | Lösung                                           |
| -------------------------------- | ----------------------------- | ------------------------------------------------ |
| ECS Tasks starten nicht          | Health-Check schlägt fehl     | Logs prüfen, Umgebungsvariablen verifizieren     |
| Alembic `Multiple heads`         | Parallele Migrationen         | `alembic merge heads`, neuen Merge-Commit        |
| 502 Bad Gateway nach Deploy      | Container noch nicht ready    | Start Period abwarten (30s), Health-Check prüfen |
| Alte Tasks werden nicht gestoppt | Deployment hängt              | `aws ecs update-service --force-new-deployment`  |
| Celery-Tasks verschwinden        | Worker vor Task-Ende gestoppt | Graceful Shutdown Timeout erhöhen                |
