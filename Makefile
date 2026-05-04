# Make targets for Smart eCommerce Intelligence

.PHONY: all build up down test lint format clean help

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

test: lint
	python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing --cov-fail-under=50

local-test:
	python scripts/local_test.py

up: build
	docker compose up -d

dev-up: build
	docker compose --profile dev up -d

build:
	@echo "==> Building Docker images..."
	docker compose build

all: build up

help:
	@echo "Available targets:"
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start services (production)"
	@echo "  make dev-up    - Start services with dev profile (Jupyter, pgAdmin)"
	@echo "  make down      - Stop services"
	@echo "  make clean     - Stop and remove volumes"
	@echo "  make test      - Run tests with coverage"
	@echo "  make lint      - Run linter (ruff)"
	@echo "  make format    - Format code (black + isort)"
	@echo "  make typecheck - Run type checker (mypy)"
	@echo "  make local-test - Run local Python tests (no Docker)"
	@echo "  make all       - Build and start services"
	@echo "  make help      - Show this help"