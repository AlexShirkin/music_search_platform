PYTHON ?= python3
PIP ?= pip

.PHONY: install install-dev lint format test up down download-models smoke-musicnn

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev,inference]"

lint:
	ruff check libs scripts tests dags spark_jobs
	ruff format --check libs scripts tests dags spark_jobs

format:
	ruff format libs scripts tests dags spark_jobs

test:
	pytest tests/unit -v

up:
	@echo "Полный docker-compose стек — этап 1+"
	@if [ -f deploy/docker-compose/docker-compose.yml ]; then \
		docker compose -f deploy/docker-compose/docker-compose.yml up -d; \
	else \
		echo "deploy/docker-compose/docker-compose.yml ещё не создан"; \
		exit 1; \
	fi

down:
	@if [ -f deploy/docker-compose/docker-compose.yml ]; then \
		docker compose -f deploy/docker-compose/docker-compose.yml down; \
	fi

download-models:
	bash scripts/download_models.sh

smoke-musicnn:
	$(PYTHON) scripts/smoke_musicnn.py
