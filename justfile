# Central command runner for papertrail. Run `just` (or `just --list`) to see all.
# Recipes are the source of truth themselves (thin wrappers over uv/pnpm/alembic);
# `check` and `fix` compose the other recipes instead of duplicating their steps.

# List the available recipes.
default:
    @just --list

# Install everything: backend (uv), frontend + e2e (pnpm).
install:
    uv sync
    cd frontend && pnpm install
    cd e2e && pnpm install

# Install frontend deps deterministically (frozen lockfile) - used by check/fix.
frontend-install:
    cd frontend && pnpm install --frozen-lockfile

# Build everything (the frontend SSR bundle; the backend has no build step).
build:
    cd frontend && pnpm build

# Apply DB migrations to head (dev database).
migrate:
    uv run alembic upgrade head

# Autogenerate a migration from model changes: `just migration "add users table"`.
migration message:
    uv run alembic revision --autogenerate -m "{{ message }}"

# Verify the ORM models match the committed migrations (used by `just check`).
migrate-check:
    #!/usr/bin/env bash
    set -euo pipefail
    # Guard against the classic drift: someone edits app/db/models.py but forgets to
    # `alembic revision --autogenerate`, so the models describe a schema the
    # migrations don't produce. Runs against the papertrail_test database, leaving
    # the dev DB untouched; `upgrade head` here is a harmless no-op that also
    # documents the precondition (`alembic check` compares the models against a DB
    # at head).
    ALEMBIC_CHECK_DATABASE_URL="${TEST_DATABASE_URL:-postgresql://papertrail:papertrail@db:5432/papertrail_test}"
    DATABASE_URL="$ALEMBIC_CHECK_DATABASE_URL" just migrate
    DATABASE_URL="$ALEMBIC_CHECK_DATABASE_URL" uv run alembic check

# Regenerate openapi.json + the typed frontend client (after changing an API route/model).
gen-client:
    PYTHONPATH=. uv run python scripts/export-openapi.py
    cd frontend && pnpm gen:api

# Backend unit + integration tests (pytest with coverage).
test:
    uv run pytest

# Browser end-to-end tests (installs e2e deps, then boots both tiers itself).
test-e2e:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "==> playwright version pin matches between Dockerfile and e2e/package.json"
    # The Dockerfile bakes Chromium at image-build time via a pinned `uvx --from
    # playwright==X`. The suite below drives that baked browser through the
    # TypeScript `@playwright/test` package (e2e/package.json). If the two versions
    # drift, the baked browser can mismatch the JS runner in a way that's confusing
    # to debug - fail loudly here instead.
    DOCKERFILE_PLAYWRIGHT="$(grep -oE 'playwright==[0-9.]+' .devcontainer/Dockerfile | head -1 | cut -d= -f3)"
    E2E_PLAYWRIGHT="$(grep -oE '"@playwright/test": "[0-9.]+"' e2e/package.json | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
    # A format change that makes either grep match nothing would turn the comparison
    # into a silent "" == "" no-op, so fail loudly if a version couldn't be parsed.
    if [ -z "$DOCKERFILE_PLAYWRIGHT" ] || [ -z "$E2E_PLAYWRIGHT" ]; then
      echo "error: could not parse the playwright version pin from" \
           ".devcontainer/Dockerfile ('$DOCKERFILE_PLAYWRIGHT') or e2e/package.json" \
           "('$E2E_PLAYWRIGHT') - the guard below can't run." >&2
      exit 1
    fi
    if [ "$DOCKERFILE_PLAYWRIGHT" != "$E2E_PLAYWRIGHT" ]; then
      echo "error: .devcontainer/Dockerfile pins playwright==$DOCKERFILE_PLAYWRIGHT" \
           "but e2e/package.json pins @playwright/test==$E2E_PLAYWRIGHT" >&2
      echo "       align the two pins (and rebuild the devcontainer image if you bumped" \
           "the Dockerfile) so the baked Chromium matches the @playwright/test runner." >&2
      exit 1
    fi

    echo "==> playwright e2e (TypeScript)"
    # Boots both tiers (FastAPI + the TanStack Start frontend, which proxies /api to
    # the API) against the test database, and seeds a verified user in global setup.
    # Chromium is baked at /ms-playwright; PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD reuses it.
    cd e2e
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pnpm install --frozen-lockfile
    pnpm exec playwright test

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
    just backend &
    just frontend &
    wait

# Run the full quality gate: static checks + tests + e2e (see AGENTS.md).
check:
    #!/usr/bin/env bash
    set -euo pipefail
    # This recipe is the source of truth for the exact steps and order - read it
    # top to bottom. It regenerates a few committed artifacts in place
    # (openapi.json, frontend/src/client, routeTree.gen.ts) to verify they're
    # current; apart from those it makes no edits. It never applies lint/format
    # fixes - run the opt-in `just fix` for that.

    echo "==> uv sync (ensure deps match pyproject/uv.lock)"
    uv sync

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
    just test

    echo "==> alembic check (ORM models match the committed migrations)"
    just migrate-check

    echo "==> frontend: pnpm install"
    just frontend-install

    echo "==> API client in sync with the backend OpenAPI"
    # The frontend's typed client is generated from the committed openapi.json. If
    # it drifts from what's committed, the backend changed without the client
    # being regenerated.
    just gen-client
    # git status --porcelain (not `git diff`) so a brand-new generated file - e.g. the
    # client module for a newly added endpoint - is caught too, not just edits to
    # already-tracked files.
    if [ -n "$(git status --porcelain -- openapi.json frontend/src/client)" ]; then
      echo "error: openapi.json / frontend/src/client are stale - the backend API" >&2
      echo "       changed but the generated client was not regenerated." >&2
      echo "       Run: just gen-client, then commit openapi.json and frontend/src/client." >&2
      git --no-pager status --porcelain -- openapi.json frontend/src/client >&2 || true
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
    just build

    just test-e2e

    echo "==> all checks passed ✅"

# Apply the mechanical auto-fixes (ruff, prettier, eslint), then re-run `just check`.
fix:
    #!/usr/bin/env bash
    set -euo pipefail
    # Covers only the steps that have a trustworthy auto-fix. The rest of the gate
    # (pyrefly, pytest, alembic drift, the playwright pin, the API-client drift
    # guard, gitleaks, deptry, import contracts, knip, dependency-cruiser, the
    # build) needs real edits or a human decision, so it stays check-only.

    echo "==> ruff check --fix (backend lint autofixes)"
    uv run ruff check --fix .

    echo "==> ruff format (backend Python formatting)"
    uv run ruff format .

    echo "==> frontend: install deps + generate route tree (eslint needs it present)"
    # check runs gen:routes before eslint for the same reason; mirror it here so a
    # clean checkout (routeTree.gen.ts is gitignored) doesn't make eslint --fix trip.
    just frontend-install
    (cd frontend && pnpm gen:routes)

    echo "==> frontend: prettier --write (formatting)"
    (cd frontend && pnpm format)

    echo "==> frontend: eslint --fix (lint autofixes)"
    (cd frontend && pnpm lint:fix)

    echo "==> done. Review the diff, then run \`just check\` to verify ✅"
