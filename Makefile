# Make targets for Smart eCommerce Intelligence

.PHONY: help build up down test lint format typecheck clean
.PHONY: test-docker test-integration pipeline kubeflow-submit
.PHONY: agents-start scheduler-start metrics-start
.PHONY: all-test all-lint all-doc

# ─────────────────────────────────────────────────────────────
# Docker & Services
# ─────────────────────────────────────────────────────────────
all: build up

build:
	@echo "==> Building Docker images..."
	docker compose build

up:
	@echo "==> Starting services (production)..."
	docker compose up -d

dev-up:
	@echo "==> Starting services with dev profile..."
	docker compose --profile dev up -d

down:
	@echo "==> Stopping services..."
	docker compose down

clean: down
	@echo "==> Removing volumes..."
	docker compose down -v

restart: down up

logs:
	docker compose logs -f

logs-scraper:
	docker compose logs -f scraper

logs-dashboard:
	docker compose logs -f dashboard

# ─────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────
test:
	@echo "==> Running tests with coverage..."
	python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing --cov-fail-under=50

test-unit:
	@echo "==> Running unit tests only..."
	python -m pytest tests/unit -v --tb=short

test-integration:
	@echo "==> Running integration tests..."
	python -m pytest tests/integration -v --tb=short -m integration

test-docker:
	@echo "==> Running tests in Docker (test-runner service)..."
	docker compose --profile test run --rm test-runner

test-lint:
	@echo "==> Running linters in Docker..."
	docker compose --profile test run --rm lint

# Run all test-related tasks
all-test: test test-integration

# ─────────────────────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────────────────────
lint:
	@echo "==> Running linter (ruff)..."
	ruff check src/ tests/ --fix

format:
	@echo "==> Formatting code (ruff format)..."
	ruff format src/ tests/

typecheck:
	@echo "==> Type checking (mypy)..."
	mypy src/ --ignore-missing-imports

all-lint: lint format typecheck

# ─────────────────────────────────────────────────────────────
# Kubeflow Pipelines
# ─────────────────────────────────────────────────────────────
pipeline:
	@echo "==> Compiling Kubeflow pipeline..."
	python -m src.pipelines.kubeflow.run_pipeline --compile-only
	@echo "Pipeline YAML: src/pipelines/kubeflow/pipeline.yaml"

kubeflow-submit:
	@echo "==> Submitting pipeline to Kubeflow..."
	python -m src.pipelines.kubeflow.run_pipeline

kubeflow-validate:
	@echo "==> Validating pipeline YAML..."
	kfp pipeline validate --file src/pipelines/kubeflow/pipeline.yaml

# ─────────────────────────────────────────────────────────────
# Additional Services (Production Profiles)
# ─────────────────────────────────────────────────────────────
agents-start:
	@echo "==> Starting A2A Agent Cluster..."
	docker compose --profile agents up -d agent-launcher
	docker compose logs -f agent-launcher

scheduler-start:
	@echo "==> Starting Scheduler..."
	docker compose --profile production up -d scheduler
	docker compose logs -f scheduler

metrics-start:
	@echo "==> Starting Prometheus Metrics Exporter..."
	docker compose --profile monitoring up -d metrics-exporter
	@echo "Metrics available at http://localhost:9090/metrics"

# ─────────────────────────────────────────────────────────────
# Database & Data
# ─────────────────────────────────────────────────────────────
db-shell:
	@echo "==> Opening PostgreSQL shell..."
	docker compose exec postgres psql -U $${POSTGRES_USER:-ecommerce_user} -d ecommerce_db

db-backup:
	@echo "==> Backing up database..."
	docker compose exec postgres pg_dump -U $${POSTGRES_USER:-ecommerce_user} ecommerce_db > backup_$$(date +%Y%m%d_%H%M%S).sql

db-restore:
	@echo "==> Restoring database from backup (set BACKUP_FILE)..."
	docker compose exec -T postgres psql -U $${POSTGRES_USER:-ecommerce_user} -d ecommerce_db < $(BACKUP_FILE)

# ─────────────────────────────────────────────────────────────
# Documentation
# ─────────────────────────────────────────────────────────────
docs:
	@echo "==> Building documentation..."
	@echo "No docs builder configured (consider mkdocs or sphinx)"

all-doc: docs

# ─────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────
install:
	@echo "==> Installing Python dependencies..."
	pip install -r requirements.txt
	pip install -e .

shell:
	@echo "==> Opening Python shell..."
	python -c "from src.__main__ import SmartECommerceIntelligence; print('Ready')"

demo:
	@echo "==> Running demo pipeline..."
	python -m src.__main__

docker-shell:
	@echo "==> Opening shell in dashboard container..."
	docker compose exec dashboard bash

# ─────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "╔═══════════════════════════════════════════════════════════╗"
	@echo "║  Smart eCommerce Intelligence — Make targets              ║"
	@echo "╚═══════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  Docker & Services"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make build           Build all Docker images"
	@echo "  make up              Start production services"
	@echo "  make dev-up          Start services with dev tools (Jupyter, pgAdmin)"
	@echo "  make down            Stop all services"
	@echo "  make clean           Stop + remove volumes"
	@echo "  make restart         Restart services"
	@echo "  make logs            View all logs"
	@echo "  make logs-scraper    View scraper logs"
	@echo ""
	@echo "  Testing"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make test            Run tests with coverage (local)"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make test-integration  Run integration tests"
	@echo "  make test-docker     Run tests inside Docker container"
	@echo "  make all-test        Run all test suites"
	@echo ""
	@echo "  Code Quality"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make lint            Run linter (ruff)"
	@echo "  make format          Auto-format code"
	@echo "  make typecheck       Run mypy type checking"
	@echo "  make all-lint        Run all quality checks"
	@echo ""
	@echo "  Kubeflow Pipelines"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make pipeline        Compile pipeline to YAML"
	@echo "  make kubeflow-validate  Validate compiled YAML"
	@echo "  make kubeflow-submit    Submit to running KFP"
	@echo ""
	@echo "  Additional Services"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make agents-start    Launch A2A agent cluster"
	@echo "  make scheduler-start Start periodic task scheduler"
	@echo "  make metrics-start   Start Prometheus metrics exporter :9090"
	@echo ""
	@echo "  Database"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make db-shell        Open PostgreSQL shell"
	@echo "  make db-backup       Backup database to .sql file"
	@echo "  make db-restore      Restore from backup (set BACKUP_FILE=...)"
	@echo ""
	@echo "  Utilities"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make install         Install Python dependencies"
	@echo "  make shell           Open Python shell with project context"
	@echo "  make demo            Run demo pipeline locally"
	@echo "  make docker-shell    Open shell in dashboard container"
	@echo ""
	@echo "  Example workflow:"
	@echo "    make build          # Build images"
	@echo "    make dev-up         # Start all services + dev tools"
	@echo "    make test-docker    # Run tests in Docker"
	@echo "    make pipeline       # Compile Kubeflow pipeline"
	@echo ""
