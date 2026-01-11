.PHONY: help install dev test lint format type-check clean run-stdio run-http docker-build docker-run

help: ## Show this help message
	@echo "SolaGuard MCP Server - Development Commands"
	@echo "==========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync

dev: install ## Setup development environment
	uv run pre-commit install

test: ## Run all tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=src --cov-report=html --cov-report=term

test-property: ## Run property-based tests only
	uv run pytest -m property

lint: ## Run linting
	uv run ruff check src tests

format: ## Format code
	uv run black src tests
	uv run ruff check --fix src tests

type-check: ## Run type checking
	uv run mypy src

clean: ## Clean up generated files
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

run-stdio: ## Run server in stdio mode (for MCP testing)
	uv run python -m solaguard.server

run-http: ## Run server in HTTP mode (for hosted deployment)
	uv run uvicorn solaguard.server:app --host 0.0.0.0 --port 8000 --reload

docker-build: ## Build Docker image
	docker build -t solaguard-mcp .

docker-run: ## Run Docker container
	docker run -p 8000:8000 solaguard-mcp

# Quality checks (run before committing)
check: lint type-check test ## Run all quality checks

# Full development setup
setup: install dev ## Complete development setup