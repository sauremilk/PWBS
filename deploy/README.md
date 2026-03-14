# PWBS Self-Hosting Deployment Guide

## Ueberblick

Dieses Verzeichnis enthaelt alles fuer das Self-Hosting des PWBS:

- **docker-compose.prod.yml**  Komplette Instanz mit einem Befehl starten
- **helm/**  Kubernetes Helm-Chart fuer skalierbare Deployments
- **.env.example**  Vorlage fuer alle benoetigten Umgebungsvariablen

## Schnellstart (Docker Compose)

### Voraussetzungen

- Docker >= 24.0 und Docker Compose >= 2.20
- Mindestens 8 GB RAM, 4 CPU-Kerne, 50 GB Speicher
- Fuer Ollama (lokale LLMs): 16 GB RAM empfohlen, GPU optional

### Installation

```bash
cd deploy

# 1. Umgebungsvariablen konfigurieren
cp .env.example .env
# .env bearbeiten: Alle CHANGE_ME-Werte ersetzen!

# 2. PWBS starten
docker compose -f docker-compose.prod.yml up -d

# 3. Status pruefen
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/api/v1/admin/health
```

### Mit lokalem LLM (Ollama)

```bash
# In .env setzen:
#   LLM_PROVIDER=ollama
#   OLLAMA_MODEL=llama3.1

# Ollama-Profil aktivieren:
docker compose -f docker-compose.prod.yml --profile ollama up -d

# Modell herunterladen (einmalig):
docker compose -f docker-compose.prod.yml exec ollama ollama pull llama3.1
```

### Updates

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Logs

```bash
# Alle Services
docker compose -f docker-compose.prod.yml logs -f

# Einzelner Service
docker compose -f docker-compose.prod.yml logs -f api
```

### Stoppen

```bash
docker compose -f docker-compose.prod.yml down

# Mit Datenlöschung (ACHTUNG: unwiderruflich!)
docker compose -f docker-compose.prod.yml down -v
```

## Kubernetes (Helm)

### Voraussetzungen

- Kubernetes >= 1.28
- Helm >= 3.14
- kubectl konfiguriert

### Installation

```bash
# 1. Namespace erstellen
kubectl create namespace pwbs

# 2. Secrets erstellen
kubectl -n pwbs create secret generic pwbs-secrets \
  --from-literal=JWT_SECRET_KEY=$(openssl rand -hex 64) \
  --from-literal=ENCRYPTION_MASTER_KEY=$(openssl rand -hex 32) \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -base64 24) \
  --from-literal=NEO4J_PASSWORD=$(openssl rand -base64 24)

# 3. Helm-Chart installieren
helm install pwbs deploy/helm/pwbs -n pwbs \
  --set llm.provider=claude \
  --set llm.anthropicApiKey=sk-ant-...

# Mit Ollama:
helm install pwbs deploy/helm/pwbs -n pwbs \
  --set llm.provider=ollama \
  --set ollama.enabled=true
```

### Konfiguration

Alle konfigurierbaren Werte in `helm/pwbs/values.yaml`. Wichtige Optionen:

| Parameter | Default | Beschreibung |
|---|---|---|
| `api.replicas` | 2 | API-Server Replicas |
| `api.resources.limits.memory` | 1Gi | Memory Limit |
| `llm.provider` | claude | LLM-Provider (claude/gpt4/ollama) |
| `ollama.enabled` | false | Ollama-Deployment aktivieren |
| `ollama.model` | llama3.1 | Ollama-Modell |
| `persistence.postgres.size` | 20Gi | PostgreSQL Speicher |
| `persistence.weaviate.size` | 50Gi | Weaviate Speicher |

## LLM-Provider Umschaltung

Das PWBS unterstuetzt drei LLM-Provider:

| Provider | `LLM_PROVIDER` | Voraussetzung | Empfehlung |
|---|---|---|---|
| Claude (Anthropic) | `claude` | `ANTHROPIC_API_KEY` | Beste Qualitaet |
| GPT-4 (OpenAI) | `gpt4` | `OPENAI_API_KEY` | Guter Fallback |
| Ollama (lokal) | `ollama` | Ollama-Service | Datenschutz-sensitiv |

Umschaltung zur Laufzeit: Aendere `LLM_PROVIDER` in `.env` und starte die API neu:

```bash
docker compose -f docker-compose.prod.yml restart api celery-worker-briefing
```

## Sicherheitshinweise

- Alle `CHANGE_ME`-Werte in `.env` MUESSEN geaendert werden
- Secrets mit `openssl rand -hex 64` generieren
- PostgreSQL und Neo4j sind nur intern erreichbar (keine Port-Mappings)
- Weaviate-Authentifizierung ist in der Production-Konfiguration aktiviert
- CORS-Origins auf die tatsaechliche Domain einschraenken
