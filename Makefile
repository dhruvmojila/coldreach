## ColdReach — common development commands
##
## Usage:  make <target>
##         make find DOMAIN=stripe.com

DOMAIN ?= acme.com

.PHONY: help setup up down restart status logs test lint fmt clean find

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

## ── Setup & Docker ─────────────────────────────────────────────────────────

setup: ## First-time setup: clone tools, build images, start services
	@bash scripts/setup.sh

up: ## Start all Docker services and show status
	@docker compose up -d
	@echo ""
	@coldreach status 2>/dev/null || docker compose ps

down: ## Stop all Docker services
	@docker compose down

restart: ## Restart all services (picks up config changes)
	@docker compose restart
	@echo ""
	@docker compose ps

status: ## Show service health and optional package status
	@coldreach status

logs: ## Follow logs from all services (Ctrl-C to stop)
	@docker compose logs -f

## ── Development ────────────────────────────────────────────────────────────

test: ## Run unit tests
	@uv run pytest tests/unit -v

lint: ## Lint (ruff) and type-check (mypy)
	@uv run ruff check coldreach tests
	@uv run mypy coldreach --ignore-missing-imports

fmt: ## Auto-format code
	@uv run ruff format coldreach tests

clean: ## Remove build artifacts and caches
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .mypy_cache .ruff_cache dist/ build/ *.egg-info/

## ── Usage ──────────────────────────────────────────────────────────────────

find: ## Quick email discovery: make find DOMAIN=stripe.com
	@coldreach find --domain $(DOMAIN) --quick
