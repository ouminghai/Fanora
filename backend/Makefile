.DEFAULT_GOAL := help

install:
	uv sync --all-extras --group dev

dev:
	uv run uvicorn app.main:app --reload --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run pyright

check: lint typecheck test

migrate:
	uv run alembic upgrade head

migration:
	uv run alembic revision --autogenerate -m "$(MSG)"

docker-up:
	docker compose up -d --build db valkey app

docker-down:
	docker compose down

stack-up:
	docker compose --profile observability up -d --build

stack-down:
	docker compose --profile observability down

help:
	@echo "Fanora backend commands"
	@echo "  make install      Install runtime and development dependencies"
	@echo "  make dev          Run FastAPI with reload"
	@echo "  make check        Run lint, typecheck, and tests"
	@echo "  make migrate      Apply Alembic migrations"
	@echo "  make docker-up    Start API, PostgreSQL, and Valkey"
	@echo "  make stack-up     Also start Prometheus and Grafana"

.PHONY: install dev test lint format typecheck check migrate migration docker-up docker-down stack-up stack-down help

