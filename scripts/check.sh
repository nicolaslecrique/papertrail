#!/usr/bin/env bash
set -euo pipefail

# scripts/check.sh - the single quality gate for this repo.
#
# Runs formatting, linting, strict type checking, and the full test suite
# (unit + Playwright e2e). Any agent or human MUST run this and make it pass
# before considering a change complete. See AGENTS.md.

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> uv sync (ensure deps match pyproject/uv.lock)"
uv sync

echo "==> ruff format --check"
uv run ruff format --check .

echo "==> ruff check (lint, select = ALL)"
uv run ruff check .

echo "==> pyrefly check (strict)"
uv run pyrefly check

echo "==> deptry (unused / missing / transitive dependencies)"
uv run deptry .

echo "==> lint-imports (architecture layering contracts)"
uv run lint-imports

echo "==> djlint --check (template formatting)"
uv run djlint app/web/templates --check

echo "==> djlint --lint (template well-formedness)"
uv run djlint app/web/templates --lint

echo "==> pytest (unit + e2e, with coverage report)"
uv run pytest

echo "==> all checks passed ✅"
