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

echo "==> playwright version pin matches between Dockerfile and uv.lock"
# The Dockerfile bakes Chromium at image-build time via a pinned `uvx --from
# playwright==X`, decoupled from the `playwright` package uv actually resolves
# into uv.lock. If they drift, the baked browser can mismatch the runtime
# driver in a way that's confusing to debug - fail loudly here instead.
DOCKERFILE_PLAYWRIGHT="$(grep -oE 'playwright==[0-9.]+' .devcontainer/Dockerfile | head -1 | cut -d= -f3)"
LOCKFILE_PLAYWRIGHT="$(grep -A1 '^name = "playwright"$' uv.lock | grep '^version' | cut -d'"' -f2)"
if [ "$DOCKERFILE_PLAYWRIGHT" != "$LOCKFILE_PLAYWRIGHT" ]; then
  echo "error: .devcontainer/Dockerfile pins playwright==$DOCKERFILE_PLAYWRIGHT" \
       "but uv.lock resolved playwright==$LOCKFILE_PLAYWRIGHT" >&2
  echo "       bump the Dockerfile's uvx pin (and rebuild the devcontainer image) to match." >&2
  exit 1
fi

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
