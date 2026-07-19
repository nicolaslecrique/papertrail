# Central command runner for papertrail. Run `just` (or `just --list`) to see all.
# Recipes delegate to scripts/check.sh, scripts/fix.sh, uv, pnpm, and alembic —
# those stay the source of truth; this is the discoverable entrypoint.

# List the available recipes.
default:
    @just --list

# Install everything: backend (uv), frontend + e2e (pnpm).
install:
    uv sync
    cd frontend && pnpm install
    cd e2e && pnpm install

# Build everything (the frontend SSR bundle; the backend has no build step).
build:
    cd frontend && pnpm build

# Run the full quality gate: static checks + tests + e2e (authoritative script).
check:
    ./scripts/check.sh

# Apply the mechanical auto-fixes (ruff, prettier, eslint), then re-run `just check`.
fix:
    ./scripts/fix.sh

# Apply DB migrations to head (dev database).
migrate:
    uv run alembic upgrade head

# Autogenerate a migration from model changes: `just migration "add users table"`.
migration message:
    uv run alembic revision --autogenerate -m "{{ message }}"

# Regenerate openapi.json + the typed frontend client (after changing an API route/model).
gen-client:
    PYTHONPATH=. uv run python scripts/export-openapi.py
    cd frontend && pnpm gen:api

# Backend unit + integration tests (pytest with coverage).
test:
    uv run pytest

# Browser end-to-end tests (Playwright boots both tiers itself).
test-e2e:
    cd e2e && pnpm exec playwright test

# Run only the backend API (auto-reload) on :8000.
backend:
    uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Run only the frontend dev server on :3000 (proxies /api to :8000).
frontend:
    cd frontend && pnpm dev

# Run backend + frontend together (Ctrl-C stops both).
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'kill 0' EXIT
    uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
    (cd frontend && pnpm dev) &
    wait
