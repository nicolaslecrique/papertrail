#!/usr/bin/env bash
set -euo pipefail

# scripts/fix.sh - the opt-in auto-fixer companion to scripts/check.sh.
#
# check.sh is a read-only GATE: it reports whether a change is ready and never
# touches your working tree. This script is the opposite: it MUTATES files,
# applying every fix that can be applied mechanically and safely. Run it when
# you want, review the diff, then run check.sh to verify.
#
# It only covers the steps that have a trustworthy auto-fix. The rest of the
# gate (pyrefly, pytest, alembic drift, the playwright pin, the API-client drift
# guard, gitleaks, deptry, import contracts, knip, dependency-cruiser, the build)
# needs real edits or a human decision, so it stays in check.sh only.

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> ruff check --fix (backend lint autofixes)"
uv run ruff check --fix .

echo "==> ruff format (backend Python formatting)"
uv run ruff format .

echo "==> frontend: prettier --write (formatting)"
(cd frontend && pnpm install --frozen-lockfile && pnpm format)

echo "==> frontend: eslint --fix (lint autofixes)"
(cd frontend && pnpm exec eslint . --fix)

echo "==> done. Review the diff, then run scripts/check.sh to verify ✅"
