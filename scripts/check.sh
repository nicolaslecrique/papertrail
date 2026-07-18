#!/usr/bin/env bash
set -euo pipefail

# scripts/check.sh - the single quality gate for this repo.
#
# Runs the Python backend gate (format, lint, strict types, deps, architecture,
# tests, migrations), then the frontend gate (API-client drift, format, lint,
# strict types, dead-code, architecture, build), then the TypeScript Playwright
# e2e suite. Any agent or human MUST run this and make it pass before considering
# a change complete. See AGENTS.md. It is read-only (never edits your files).

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

echo "==> pytest (unit + integration, with coverage report)"
uv run pytest

echo "==> alembic check (ORM models match the committed migrations)"
# Guard against the classic drift: someone edits app/db/models.py but forgets to
# `alembic revision --autogenerate`, so the models describe a schema the
# migrations don't produce. Run it against the papertrail_test database, which
# the pytest step above just created and brought to head - so the dev DB is left
# untouched. Re-running `upgrade head` here is a harmless no-op that also
# documents the precondition (check compares the models against a DB at head).
ALEMBIC_CHECK_DATABASE_URL="${TEST_DATABASE_URL:-postgresql://papertrail:papertrail@db:5432/papertrail_test}"
DATABASE_URL="$ALEMBIC_CHECK_DATABASE_URL" uv run alembic upgrade head
DATABASE_URL="$ALEMBIC_CHECK_DATABASE_URL" uv run alembic check

echo "==> frontend: pnpm install"
(cd frontend && pnpm install --frozen-lockfile)

echo "==> API client in sync with the backend OpenAPI"
# The frontend's typed client is generated from the committed openapi.json. Export
# the schema from the app and regenerate the client; if either drifts from what's
# committed, the backend changed without the client being regenerated. This is the
# frontend analogue of the old vendored-asset fingerprint guard.
PYTHONPATH=. uv run python scripts/export-openapi.py
(cd frontend && pnpm gen:api)
if ! git diff --exit-code -- openapi.json frontend/src/client >/dev/null 2>&1; then
  echo "error: openapi.json / frontend/src/client are stale - the backend API" >&2
  echo "       changed but the generated client was not regenerated." >&2
  echo "       Run: uv run python scripts/export-openapi.py && (cd frontend && pnpm gen:api)" >&2
  echo "       then commit openapi.json and frontend/src/client." >&2
  git --no-pager diff --stat -- openapi.json frontend/src/client >&2 || true
  exit 1
fi

echo "==> frontend: generate route tree"
# routeTree.gen.ts is generated (gitignored); tsc/eslint/knip need it present.
(cd frontend && pnpm gen:routes)

echo "==> frontend: prettier --check"
(cd frontend && pnpm format:check)

echo "==> frontend: eslint (typescript-eslint strict + tanstack + tailwind)"
(cd frontend && pnpm lint)

echo "==> frontend: tsc --noEmit (strict)"
(cd frontend && pnpm typecheck)

echo "==> frontend: knip (unused files / exports / dependencies)"
(cd frontend && pnpm knip)

echo "==> frontend: dependency-cruiser (architecture)"
(cd frontend && pnpm depcruise)

echo "==> frontend: build (SSR bundle compiles)"
(cd frontend && pnpm build)

echo "==> playwright e2e (TypeScript)"
# The browser tests boot both tiers (FastAPI + the TanStack Start frontend, which
# proxies /api to the API) against the test database, and seed a verified user in
# global setup. Chromium is baked at /ms-playwright; PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD
# reuses it. The frontend deps were installed above, so `vite dev` is available.
(
  cd e2e
  PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pnpm install --frozen-lockfile
  pnpm exec playwright test
)

echo "==> all checks passed ✅"
