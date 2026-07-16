#!/usr/bin/env bash
set -euo pipefail

# scripts/check.sh - the single quality gate for this repo.
#
# Runs formatting, linting, strict type checking, the Python test suite (unit +
# integration), and the TypeScript Playwright e2e suite. Any agent or human MUST
# run this and make it pass before considering a change complete. See AGENTS.md.

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> uv sync (ensure deps match pyproject/uv.lock)"
uv sync

echo "==> playwright version pin matches between Dockerfile and e2e/package.json"
# The Dockerfile bakes Chromium at image-build time via a pinned `uvx --from
# playwright==X`. The e2e suite drives that baked browser through the TypeScript
# `@playwright/test` package (e2e/package.json). If the two versions drift, the
# baked browser can mismatch the JS runner in a way that's confusing to debug -
# fail loudly here instead.
DOCKERFILE_PLAYWRIGHT="$(grep -oE 'playwright==[0-9.]+' .devcontainer/Dockerfile | head -1 | cut -d= -f3)"
E2E_PLAYWRIGHT="$(grep -oE '"@playwright/test": "[0-9.]+"' e2e/package.json | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
if [ "$DOCKERFILE_PLAYWRIGHT" != "$E2E_PLAYWRIGHT" ]; then
  echo "error: .devcontainer/Dockerfile pins playwright==$DOCKERFILE_PLAYWRIGHT" \
       "but e2e/package.json pins @playwright/test==$E2E_PLAYWRIGHT" >&2
  echo "       align the two pins (and rebuild the devcontainer image if you bumped" \
       "the Dockerfile) so the baked Chromium matches the @playwright/test runner." >&2
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

echo "==> jscpd (template copy-paste detection)"
# Guard against duplicated markup creeping back into the templates: the pages are
# kept DRY via the macros in templates/components/, and jscpd fails if any block
# of >= minTokens is copy-pasted (config: e2e/.jscpd.json). jscpd ships in the e2e
# JS project (already installed below/for e2e), so run it from there; it reads
# .jscpd.json from that directory and scans ../app/web/templates.
(
  cd e2e
  PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pnpm install --frozen-lockfile
  pnpm exec jscpd
)

echo "==> pytest (unit + integration, with coverage report)"
uv run pytest

echo "==> alembic check (ORM models match the committed migrations)"
# Guard against the classic drift: someone edits app/db/models.py but forgets to
# `alembic revision --autogenerate`, so the models describe a schema the
# migrations don't produce. Nothing else catches it - the tests build their
# schema FROM the migrations, so a model that's ahead of them stays invisible
# until the ORM queries a column the migrations never created. `alembic check`
# autogenerates in-memory and exits non-zero if any upgrade ops are pending.
#
# Run it against the papertrail_test database, which the pytest step above just
# created and brought to head - so the dev DB is left untouched. Re-running
# `upgrade head` here is a harmless no-op that also documents the precondition
# (check compares the models against a DB that is already at head).
ALEMBIC_CHECK_DATABASE_URL="${TEST_DATABASE_URL:-postgresql://papertrail:papertrail@db:5432/papertrail_test}"
DATABASE_URL="$ALEMBIC_CHECK_DATABASE_URL" uv run alembic upgrade head
DATABASE_URL="$ALEMBIC_CHECK_DATABASE_URL" uv run alembic check

echo "==> playwright e2e (TypeScript)"
# The browser tests are a standalone TypeScript Playwright project under e2e/
# (see docs/e2e-tests.md). Install its JS deps - the pnpm store caches them, and
# PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD reuses the Chromium baked at /ms-playwright, so
# no browser is downloaded - then run the suite, which boots the app via uvicorn
# against the test database and seeds a verified user in its global setup.
(
  cd e2e
  PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pnpm install --frozen-lockfile
  pnpm exec playwright test
)

echo "==> all checks passed ✅"
