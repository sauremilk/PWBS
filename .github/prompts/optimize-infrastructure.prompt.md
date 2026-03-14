---
agent: agent
description: "Tiefenoptimierung der Infrastruktur und DevOps-Konfiguration im PWBS-Workspace. Analysiert Docker, Terraform, CI/CD, Development-Environment und Deployment-Readiness – zustandsunabhängig bei jeder Ausführung."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Infrastruktur- und DevOps-Optimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Infrastrukturkonfigurationen driften. Bei jeder Ausführung alle Konfigurationsdateien gegen Best Practices und den aktuellen Projekt-Bedarf abgleichen. Keine Annahmen über vorherige Optimierungen.

> **Robustheitsregeln:**
>
> - Prüfe, welche Infrastruktur-Dateien tatsächlich existieren.
> - Bei fehlenden CI/CD-Pipelines: Identifiziere als Aufbaupotenzial mit konkretem Vorschlag.
> - Berücksichtige den MVP-Kontext – nicht jedes Enterprise-Feature ist jetzt nötig.
> - Plattformgerechte Befehle verwenden.

---

## Phase 0: Infrastruktur-Inventar (Extended Thinking)

### 0.1 Docker-Konfiguration

Lies und analysiere alle Docker-bezogenen Dateien:

| Datei                   | Pfad                    | Existiert? | Zweck              |
| ----------------------- | ----------------------- | ---------- | ------------------ |
| docker-compose.yml      | ./docker-compose.yml    | ...        | Lokale Entwicklung |
| Backend Dockerfile      | backend/Dockerfile      | ...        | Production Build   |
| Backend Dockerfile.dev  | backend/Dockerfile.dev  | ...        | Development Build  |
| Frontend Dockerfile     | frontend/Dockerfile     | ...        | Production Build   |
| Frontend Dockerfile.dev | frontend/Dockerfile.dev | ...        | Development Build  |
| PoC docker-compose      | poc/docker-compose.yml  | ...        | PoC-Umgebung       |

### 0.2 Terraform

| Datei        | Pfad                          | Existiert? | Inhalt |
| ------------ | ----------------------------- | ---------- | ------ |
| main.tf      | infra/terraform/main.tf       | ...        | ...    |
| variables.tf | infra/terraform/variables.tf  | ...        | ...    |
| outputs.tf   | infra/terraform/outputs.tf    | ...        | ...    |
| Environments | infra/terraform/environments/ | ...        | ...    |
| Modules      | infra/terraform/modules/      | ...        | ...    |

### 0.3 CI/CD

Prüfe Existenz von:

- `.github/workflows/` – GitHub Actions
- `Makefile` – Build-Automatisierung
- Pre-Commit-Hooks (`.pre-commit-config.yaml`)

---

## Phase 1: Docker-Optimierung

### 1.1 docker-compose.yml

- [ ] Alle benötigten Services definiert (PostgreSQL, Weaviate, Neo4j, Redis)
- [ ] Versions-Pins auf stabile Releases (kein `latest`)
- [ ] Health Checks für alle Services
- [ ] Volumes für Datenpersistenz (keine Datenverluste bei Container-Restart)
- [ ] Netzwerk-Isolation (Backend und DBs in eigenem Netzwerk)
- [ ] Environment-Variables über `.env`-Datei, nicht hardcodiert
- [ ] Ports nur exponiert wo nötig (keine überflüssigen Port-Mappings)
- [ ] Resource Limits (Memory, CPU) für stabile lokale Entwicklung
- [ ] `depends_on` mit Condition: `service_healthy`

### 1.2 Backend Dockerfile

- [ ] Multi-Stage Build (Builder → Runtime)
- [ ] Nicht-Root-User (`RUN adduser --system pwbs`)
- [ ] Minimales Base-Image (`python:3.12-slim`)
- [ ] Layer-Caching optimiert (Dependencies vor Code kopieren)
- [ ] `.dockerignore` existiert und ist vollständig
- [ ] Keine Secrets im Image (kein COPY von `.env`)
- [ ] Health Check Endpoint (`/health`)
- [ ] Signal Handling (`SIGTERM` wird korrekt verarbeitet)

### 1.3 Frontend Dockerfile

- [ ] Multi-Stage Build (Install → Build → Serve)
- [ ] Node-Version gepinnt
- [ ] `npm ci` statt `npm install` (deterministisch)
- [ ] Standalone Next.js Build für minimales Image
- [ ] Nicht-Root-User

### 1.4 Dockerfile.dev (Entwicklung)

- [ ] Hot-Reload konfiguriert (Volume-Mount für Source Code)
- [ ] Dev-Dependencies installiert
- [ ] Debug-Ports exponiert
- [ ] Einfacher Start mit einem Befehl

---

## Phase 2: Terraform-Analyse

### 2.1 IaC-Vollständigkeit

Vergleiche Terraform mit der geplanten Deployment-Topologie aus ARCHITECTURE.md:

- [ ] VPC/Netzwerk-Konfiguration (eu-central-1)
- [ ] ECS Fargate Definition für Backend
- [ ] RDS PostgreSQL Instance
- [ ] EC2/ECS für Weaviate
- [ ] EC2/ECS für Neo4j
- [ ] ElastiCache für Redis
- [ ] ALB/API Gateway
- [ ] SSL-Zertifikate (ACM)
- [ ] IAM Roles (Least Privilege)
- [ ] Security Groups (minimale Ports)

### 2.2 Terraform Best Practices

- [ ] State Backend konfiguriert (S3 + DynamoDB Locking)
- [ ] Variables mit Beschreibungen und Validierungen
- [ ] Outputs für alle externen Endpunkte
- [ ] Module für wiederverwendbare Komponenten
- [ ] Environments (dev, staging, prod) getrennt
- [ ] Keine Secrets in `.tf`-Dateien
- [ ] `terraform fmt` und `terraform validate` bestanden

### 2.3 Sicherheit in Terraform

- [ ] Encryption at Rest für alle Datenbanken
- [ ] Encryption in Transit (TLS)
- [ ] VPC Flow Logs aktiviert
- [ ] Security Groups minimal (nur nötige Ports)
- [ ] Kein öffentlicher Zugriff auf Datenbanken
- [ ] IAM Roles mit Least Privilege
- [ ] Backup-Strategie für RDS

---

## Phase 3: CI/CD Pipeline

### 3.1 GitHub Actions

Falls Workflows existieren, prüfe:

- [ ] **Build:** Backend und Frontend Build in CI
- [ ] **Lint:** ruff (Python), ESLint (TypeScript)
- [ ] **Type Check:** mypy (Python), tsc --noEmit (TypeScript)
- [ ] **Unit Tests:** pytest, npm test
- [ ] **Integration Tests:** Mit Docker-Services
- [ ] **Security Scan:** Dependency-Audit (pip audit, npm audit)
- [ ] **Docker Build:** Images bauen und testen

Falls keine Workflows existieren, erstelle Empfehlungen:

```yaml
# Empfohlene Workflow-Struktur:
on: [push, pull_request]
jobs:
  lint: # ruff, ESLint
  type-check: # mypy, tsc
  unit-test: # pytest, jest
  build: # Docker Build
  security: # pip audit, npm audit
```

### 3.2 Makefile

- [ ] Alle häufigen Befehle als Make-Targets
- [ ] `make setup` – Vollständige Entwicklungsumgebung aufsetzen
- [ ] `make test` – Alle Tests ausführen
- [ ] `make lint` – Linting
- [ ] `make build` – Docker Build
- [ ] `make up` / `make down` – Docker Compose
- [ ] `make migrate` – Alembic-Migrationen
- [ ] Self-Documenting (jedes Target mit Beschreibung)

### 3.3 Pre-Commit Hooks

- [ ] ruff (Linting + Formatting)
- [ ] mypy (Type Checking)
- [ ] Secret Detection (detect-secrets oder ähnlich)
- [ ] Commit Message Convention (Conventional Commits)

---

## Phase 4: Development Environment

### 4.1 Onboarding-Erfahrung

Simuliere das Setup eines neuen Entwicklers:

1. `git clone` → Funktioniert die README-Anleitung?
2. `docker compose up -d` → Starten alle Services?
3. Backend-Setup: `pip install -e ".[dev]"` → Alle Dependencies installiert?
4. Frontend-Setup: `npm install` → Keine Fehler?
5. Migrations: `alembic upgrade head` → Schema erstellt?
6. Tests: `pytest tests/unit/` → Alle grün?

### 4.2 Umgebungsvariablen

- [ ] `.env.example` oder `.env.template` existiert mit allen nötigen Variablen
- [ ] Jede Variable mit Beschreibung und Default-Wert
- [ ] `.env` in `.gitignore`
- [ ] Pydantic Settings validiert Umgebungsvariablen beim Start

### 4.3 VSCode/IDE-Konfiguration

- [ ] `.vscode/settings.json` mit Formatter, Linter-Config
- [ ] `.vscode/extensions.json` mit empfohlenen Extensions
- [ ] `.vscode/launch.json` mit Debug-Konfigurationen

---

## Phase 5: Optimierungen implementieren

### Priorisierung

| Prio | Kategorie                          |
| ---- | ---------------------------------- |
| 🔴   | Sicherheitslücken in Infrastruktur |
| 🟡   | Build/Deploy-Blockaden             |
| 🟠   | Entwickler-Produktivität           |
| 🟢   | Nice-to-have-Verbesserungen        |

Implementiere 🔴- und 🟡-Findings sofort. Für 🟠 und 🟢 erstelle konkrete Empfehlungen.

---

## Phase 6: Infrastruktur-Bericht

```markdown
# Infrastruktur-Bericht – [Datum]

## Status

| Bereich         | Status   | Nächste Stufe |
| --------------- | -------- | ------------- |
| Docker Compose  | 🔴/🟡/🟢 | ...           |
| Dockerfiles     | ...      | ...           |
| Terraform       | ...      | ...           |
| CI/CD           | ...      | ...           |
| Dev-Environment | ...      | ...           |
| Makefile        | ...      | ...           |

## Durchgeführte Optimierungen

1. ...

## Empfehlungen

1. ...
```

---

## Opus 4.6 – Kognitive Verstärker

- **Systemintegritäts-Denken:** Wie interagieren Container, Netzwerke und Volumes im Fehlerzustand?
- **Drift-Erkennung:** Wo weichen deklarierte Konfiguration und Realität vermutlich ab?
- **Skalierungspfad-Analyse:** Welche aktuellen Infrastruktur-Entscheidungen blockieren den Weg zu Phase 3/4?
- **Failure-Mode-Analyse:** Was passiert, wenn jede einzelne Komponente ausfällt?
