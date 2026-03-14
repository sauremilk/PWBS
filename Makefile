# ══════════════════════════════════════════════════════════
# PWBS – Makefile (Entwickler-Shortcuts)
# ══════════════════════════════════════════════════════════
# Nutzung: make <target>
# Hilfe:   make help

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ── Farben ────────────────────────────────────────────────
CYAN  := \033[36m
GREEN := \033[32m
RESET := \033[0m

# ── Setup ─────────────────────────────────────────────────

.PHONY: setup
setup: setup-backend setup-frontend setup-hooks ## Vollständiges Setup (Backend + Frontend + Hooks)
	@echo "$(GREEN)✔ Setup abgeschlossen$(RESET)"

.PHONY: setup-backend
setup-backend: ## Python-Umgebung einrichten
	cd backend && python -m venv .venv
	cd backend && .venv/bin/pip install -e ".[dev,llm,vector,graph]"

.PHONY: setup-frontend
setup-frontend: ## Node-Dependencies installieren
	cd frontend && npm install

.PHONY: setup-hooks
setup-hooks: ## Pre-Commit-Hooks installieren
	pre-commit install
	pre-commit install --hook-type commit-msg

# ── Entwicklung ───────────────────────────────────────────

.PHONY: dev
dev: ## Backend + Frontend + Services starten
	docker compose up -d
	@echo "$(CYAN)Services gestartet. Backend: http://localhost:8000 | Frontend: http://localhost:3000$(RESET)"

.PHONY: dev-backend
dev-backend: ## Nur Backend starten (hot-reload)
	cd backend && .venv/bin/uvicorn pwbs.api.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: dev-frontend
dev-frontend: ## Nur Frontend starten
	cd frontend && npm run dev

.PHONY: services
services: ## Nur Docker-Services starten (DBs + Redis)
	docker compose up -d postgres weaviate neo4j redis

.PHONY: services-down
services-down: ## Docker-Services stoppen
	docker compose down

# ── Tests ─────────────────────────────────────────────────

.PHONY: test
test: test-backend test-frontend ## Alle Tests ausführen

.PHONY: test-backend
test-backend: ## Backend Unit-Tests
	cd backend && .venv/bin/pytest tests/unit/ -v

.PHONY: test-integration
test-integration: ## Backend Integration-Tests (Docker-Services erforderlich)
	cd backend && .venv/bin/pytest tests/integration/ -v --docker

.PHONY: test-e2e
test-e2e: ## End-to-End-Tests
	cd backend && .venv/bin/pytest tests/e2e/ -v

.PHONY: test-frontend
test-frontend: ## Frontend-Tests
	cd frontend && npm test 2>/dev/null || echo "$(CYAN)Frontend-Tests noch nicht konfiguriert$(RESET)"

.PHONY: test-coverage
test-coverage: ## Backend-Tests mit Coverage-Report
	cd backend && .venv/bin/pytest tests/ -v --cov=pwbs --cov-report=term-missing --cov-report=html

# ── Code-Qualität ─────────────────────────────────────────

.PHONY: lint
lint: lint-backend lint-frontend ## Alle Linter ausführen

.PHONY: lint-backend
lint-backend: ## Python-Linting (Ruff)
	cd backend && .venv/bin/ruff check pwbs/ tests/
	cd backend && .venv/bin/ruff format --check pwbs/ tests/

.PHONY: lint-frontend
lint-frontend: ## TypeScript-Linting (ESLint)
	cd frontend && npm run lint

.PHONY: format
format: ## Code automatisch formatieren
	cd backend && .venv/bin/ruff format pwbs/ tests/
	cd backend && .venv/bin/ruff check --fix pwbs/ tests/
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css,json}"

.PHONY: typecheck
typecheck: typecheck-backend typecheck-frontend ## Typenprüfung (Python + TypeScript)

.PHONY: typecheck-backend
typecheck-backend: ## Mypy-Typenprüfung
	cd backend && .venv/bin/mypy pwbs/

.PHONY: typecheck-frontend
typecheck-frontend: ## TypeScript-Typenprüfung
	cd frontend && npm run type-check

.PHONY: check
check: lint typecheck test ## Vollständiger Quality-Check (Lint + Typecheck + Tests)

# ── Datenbank ─────────────────────────────────────────────

.PHONY: db-migrate
db-migrate: ## Alembic-Migrationen ausführen
	cd backend && .venv/bin/alembic upgrade head

.PHONY: db-revision
db-revision: ## Neue Alembic-Migration erstellen (MSG=Beschreibung)
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(MSG)"

.PHONY: db-downgrade
db-downgrade: ## Letzte Migration rückgängig machen
	cd backend && .venv/bin/alembic downgrade -1

# ── Security ──────────────────────────────────────────────

.PHONY: security-audit
security-audit: ## Dependency-Sicherheitsaudit
	cd backend && .venv/bin/pip-audit
	cd frontend && npm audit

# ── Hilfe ─────────────────────────────────────────────────

.PHONY: help
help: ## Diese Hilfe anzeigen
	@echo ""
	@echo "$(CYAN)PWBS – Entwickler-Shortcuts$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
