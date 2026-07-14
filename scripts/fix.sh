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
# gate (pyrefly, pytest, alembic drift, the playwright pin, stale frontend
# assets, gitleaks, deptry, import contracts) needs real edits or a human
# decision, so it stays in check.sh only.

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> ruff check --fix (lint autofixes)"
uv run ruff check --fix .

echo "==> ruff format (Python formatting)"
uv run ruff format .

echo "==> djlint --reformat (template formatting)"
uv run djlint app/web/templates --reformat

echo "==> done. Review the diff, then run scripts/check.sh to verify ✅"
