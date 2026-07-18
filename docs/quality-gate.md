# The quality gate: `scripts/check.sh`

`scripts/check.sh` is the single source of truth for whether a change is ready.
Run it before considering **any** change complete; it must exit 0. This page
documents what each step does — but the script itself is authoritative, so if
this list and the script ever disagree, believe the script (and fix this page).

`check.sh` is **read-only**: it reports, never edits. Its opt-in companion
`scripts/fix.sh` applies the mechanical fixes — `ruff check --fix`, `ruff format`,
Prettier, and `eslint --fix` — and nothing else, because the rest of the gate
(types, tests, migrations, dependency and architecture checks, the API-client
drift guard, ...) has no safe auto-fix. Run `fix.sh`, review the diff, then run
`check.sh` to verify.

## The steps, in order

Backend (Python):

1. `uv sync` — dependencies match `pyproject.toml` / `uv.lock`
2. playwright version check — the Dockerfile's baked-Chromium pin must match the
   `@playwright/test` pin in `e2e/package.json` (see [e2e-tests.md](e2e-tests.md))
3. `gitleaks git` — secret scanning over the full git history (see
   [security-checks.md](security-checks.md))
4. `uv audit` — known vulnerabilities in resolved dependencies (see
   [security-checks.md](security-checks.md))
5. `ruff format --check .` — Python formatting
6. `ruff check .` — linting (`select = ["ALL"]`)
7. `pyrefly check` — type checking (strict preset)
8. `deptry .` — dependency hygiene (unused / missing / transitive / misplaced deps)
9. `lint-imports` — architecture layering contracts (see "Architecture" in AGENTS.md)
10. `pytest` — Python unit + integration tests (API driven through httpx), with a
    coverage report (see "Coverage" in AGENTS.md)
11. `alembic check` — the ORM models in `app/db/models.py` match the committed
    migrations (see [migrations.md](migrations.md))

Frontend (`frontend/`, see [frontend.md](frontend.md)):

12. `pnpm install --frozen-lockfile` — install exactly the committed lockfile
13. **API-client drift guard** — re-export `openapi.json` from the app and
    regenerate `frontend/src/client`; fail (via `git diff`) if either is stale.
    This is the analogue of the old vendored-asset fingerprint: the committed,
    generated client must always match the backend.
14. generate the route tree (`tsr generate`) so the next steps see it
15. `prettier --check` — frontend formatting
16. `eslint` (`--max-warnings 0`) — typescript-eslint strict + type-checked, plus
    the TanStack Router/Query and Tailwind plugins
17. `tsc --noEmit` — strict type checking
18. `knip` — unused files / exports / dependencies
19. `dependency-cruiser` — no circular deps, no orphans, vendored `ui/` isolation
20. `pnpm build` — the TanStack Start SSR bundle compiles

End to end:

21. `playwright test` — TypeScript browser e2e in `e2e/` (see [e2e-tests.md](e2e-tests.md)),
    which boots both tiers and includes `accessibility.spec.ts`, running axe-core
    over each rendered page for WCAG A/AA violations

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.
