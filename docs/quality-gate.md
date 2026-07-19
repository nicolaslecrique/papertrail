# The quality gate: `scripts/check.sh`

`scripts/check.sh` is the single source of truth for whether a change is ready.
Run it via `just check` before considering **any** change complete; it must exit 0.
**The script itself is authoritative** — it self-documents via its `echo "==> …"`
lines, so read it for the exact steps and order. This page explains what each tier
is _for_ and why, not a step-by-step transcript (which would just drift from the
script).

`just check` won't rewrite your source. It regenerates a few committed artifacts in
place (`openapi.json`, `frontend/src/client`, `routeTree.gen.ts`) to verify they're
current, but applies no lint/format fixes. Its opt-in companion `just fix`
(`scripts/fix.sh`) does that (`ruff check --fix`, `ruff format`, Prettier,
`eslint --fix`) — run it, review the diff, then re-run `just check`. The rest of
the gate has no safe auto-fix.

## What each tier checks, and why

**Backend (Python).** Security first (gitleaks over full history, `uv audit` for
known CVEs — see [security-checks.md](security-checks.md)), then `ruff format` +
`ruff check` (lint, `select = ["ALL"]`), `pyrefly` (strict types), `deptry`
(dependency hygiene), and `lint-imports` (the layered-architecture contracts — see
"Architecture" in AGENTS.md). Then `pytest` (unit + integration through httpx, with
a coverage report — see "Coverage" in AGENTS.md) and `alembic check`, which fails if
`app/db/models.py` has drifted ahead of the committed migrations (see
[migrations.md](migrations.md)).

**Frontend (`frontend/`, see [frontend.md](frontend.md)).** A frozen `pnpm install`,
then the **API-client drift guard**: re-export `openapi.json` from the app,
regenerate `frontend/src/client`, and fail if either differs from what's committed
(so the generated client can never silently fall behind the backend). Then the route
tree is generated so the rest can see it, followed by Prettier, ESLint (strict,
type-checked), `tsc`, Knip (dead code), dependency-cruiser (architecture), and the
production SSR build.

**End to end.** `playwright test` — the TypeScript browser suite in `e2e/` (see
[e2e-tests.md](e2e-tests.md)), which boots both tiers and includes
`accessibility.spec.ts` (axe-core, WCAG A/AA) over each rendered page.

There's also an early guard that the baked-Chromium `playwright==` pin in the
Dockerfile matches the `@playwright/test` pin in `e2e/package.json` (see
[e2e-tests.md](e2e-tests.md)).

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.
