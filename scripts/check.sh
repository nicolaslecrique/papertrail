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

echo "==> frontend assets up to date (committed CSS/JS match their sources)"
# The built assets under app/web/static/ (app.css, htmx.min.js) are committed and
# are what ships - `pnpm run build` is a manual step, deliberately not run here.
# But we DO cheaply guard against forgetting it: `pnpm run build` also writes
# app/web/static/assets.sha256, a fingerprint of the build INPUTS (app.tailwind.css,
# templates/, pnpm-lock.yaml - see scripts/assets-fingerprint.sh). Recompute that
# fingerprint and compare. If it drifts, a source changed (a template class, the
# Tailwind config, a frontend dep) without the assets being rebuilt, so the
# committed CSS/JS is stale. Pure hash compare: no Node/pnpm, milliseconds.
EXPECTED_ASSETS_FP="$(scripts/assets-fingerprint.sh)"
COMMITTED_ASSETS_FP="$(cat app/web/static/assets.sha256 2>/dev/null || true)"
if [ "$EXPECTED_ASSETS_FP" != "$COMMITTED_ASSETS_FP" ]; then
  echo "error: frontend assets are stale - a build input changed but the committed" >&2
  echo "       app/web/static/{app.css,htmx.min.js} were not rebuilt." >&2
  echo "       Run 'pnpm install && pnpm run build', then commit the regenerated files." >&2
  exit 1
fi

echo "==> gitleaks (secret scanning, full git history)"
if ! command -v gitleaks >/dev/null 2>&1; then
  echo "error: gitleaks not found on PATH. It's baked into the devcontainer image" >&2
  echo "       (.devcontainer/Dockerfile) - rebuild the devcontainer, or install" >&2
  echo "       the same pinned version locally." >&2
  exit 1
fi
gitleaks git --no-banner

echo "==> uv audit (known dependency vulnerabilities)"
uv audit --preview-features audit-command

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
