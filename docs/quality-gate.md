# The quality gate: `scripts/check.sh`

`scripts/check.sh` is the single source of truth for whether a change is ready.
Run it before considering **any** change complete; it must exit 0. This page
documents what each step does — but the script itself is authoritative, so if
this list and the script ever disagree, believe the script (and fix this page).

`check.sh` is **read-only**: it reports, never edits. Its opt-in companion
`scripts/fix.sh` applies the mechanical fixes — `ruff check --fix`, `ruff
format`, and `djlint --reformat` — and nothing else, because the rest of the gate
(types, tests, migrations, dependency and architecture checks, ...) has no safe
auto-fix. Run `fix.sh`, review the diff, then run `check.sh` to verify.

## The steps, in order

1. `uv sync` — dependencies match `pyproject.toml` / `uv.lock`
2. playwright version check — the Dockerfile's baked-Chromium pin must match the
   `@playwright/test` pin in `e2e/package.json` (see [e2e-tests.md](e2e-tests.md))
3. frontend assets fresh — committed `app/web/static/{app.css,htmx.min.js}` are not
   stale vs their sources (see [frontend-assets.md](frontend-assets.md))
4. `gitleaks git` — secret scanning over the full git history (see
   [security-checks.md](security-checks.md))
5. `uv audit` — known vulnerabilities in resolved dependencies (see
   [security-checks.md](security-checks.md))
6. `ruff format --check .` — Python formatting
7. `ruff check .` — linting (`select = ["ALL"]`)
8. `pyrefly check` — type checking (strict preset)
9. `deptry .` — dependency hygiene (unused / missing / transitive / misplaced deps)
10. `lint-imports` — architecture layering contracts (see "Architecture" in AGENTS.md)
11. `djlint app/web/templates --check` — template formatting (reformat with
    `uv run djlint app/web/templates --reformat`)
12. `djlint app/web/templates --lint` — template well-formedness (unclosed tags, ...)
13. `jscpd` — copy-paste detection over `app/web/templates`; fails if any block of
    ≥ `minTokens` is duplicated, so shared markup stays in `templates/components/`
    macros instead of being pasted between pages (config: `e2e/.jscpd.json`). Runs
    from the e2e JS project, where the tool is installed.
14. `pytest` — Python unit + integration tests, with a coverage report (see
    "Coverage" in AGENTS.md). Includes `tests/test_templates.py`, which compiles
    every template and fails on a **dead template** — one no route or template
    references.
15. `alembic check` — the ORM models in `app/db/models.py` match the committed
    migrations (see [migrations.md](migrations.md))
16. `playwright test` — TypeScript browser e2e in `e2e/` (see [e2e-tests.md](e2e-tests.md)),
    including `accessibility.spec.ts`, which runs axe-core over each rendered page
    to catch broken/dead markup (dangling labels, duplicate ids, bad ARIA) and
    WCAG A/AA violations

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.
