# AGENTS.md

Guidance for AI agents (and humans) working in this repo.

`papertrail` is a tool to study the manipulation of science by lobbies. This is
currently a **Hello World** slice that stands up the full production stack end to end.

## Git workflow: no pull requests

This is a solo project — the author works alone, so pull requests add no value.
Do **not** open a PR. Once the check is green (see below), merge the work branch
straight into `main` and push. Keep commits focused and descriptive.

## The one rule: keep the check green

Before you consider **any** change complete, run:

```bash
./scripts/check.sh
```

It must exit 0. It runs, in order:

1. `uv sync` — dependencies match `pyproject.toml` / `uv.lock`
2. playwright version check — the Dockerfile's baked-Chromium pin must match the
   `@playwright/test` pin in `e2e/package.json`
3. frontend assets fresh — committed `app/web/static/{app.css,htmx.min.js}` are not
   stale vs their sources (see "Frontend assets are vendored")
4. `gitleaks git` — secret scanning over the full git history
5. `uv audit` — known vulnerabilities in resolved dependencies
6. `ruff format --check .` — Python formatting
7. `ruff check .` — linting (`select = ["ALL"]`)
8. `pyrefly check` — type checking (strict preset)
9. `deptry .` — dependency hygiene (unused / missing / transitive / misplaced deps)
10. `lint-imports` — architecture layering contracts (see "Architecture" below)
11. `djlint app/web/templates --check` — template formatting (reformat with
    `uv run djlint app/web/templates --reformat`)
12. `djlint app/web/templates --lint` — template well-formedness (unclosed tags, ...)
13. `pytest` — Python unit + integration tests, with a coverage report (see "Coverage")
14. `alembic check` — the ORM models in `app/db/models.py` match the committed
    migrations (fails if a model change has no matching migration; see "Database
    migrations")
15. `playwright test` — TypeScript browser e2e in `e2e/` (see "End-to-end tests")

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.

`check.sh` is **read-only** — it reports whether a change is ready and never edits
your files. To apply the fixes that *can* be applied mechanically, run the opt-in
companion:

```bash
./scripts/fix.sh
```

It mutates the working tree: `ruff check --fix`, `ruff format`, and
`djlint --reformat`. Review the diff, then run `check.sh` to verify. The rest of
the gate (types, tests, migrations, dependency and architecture checks, ...) has
no safe auto-fix and stays check-only.

## Tech stack

- **Dependency management:** `uv` (`pyproject.toml` + `uv.lock`)
- **Type checker:** Pyrefly, strict (`[tool.pyrefly] preset = "strict"`)
- **Linter:** Ruff, `select = ["ALL"]` (minimal, justified ignores only)
- **Formatter:** `ruff format`
- **Dependency hygiene:** deptry (unused/missing/transitive/misplaced deps)
- **Dependency vulnerabilities:** `uv audit` (see docs/security-checks.md)
- **Secret scanning:** gitleaks (see docs/security-checks.md)
- **Architecture enforcement:** import-linter (layering contracts in `pyproject.toml`)
- **Tests:** pytest (unit + integration, coverage via pytest-cov); Playwright in
  TypeScript for browser e2e (in `e2e/`) — see [docs/e2e-tests.md](docs/e2e-tests.md)
- **Database:** Postgres via async SQLAlchemy; schema managed by **Alembic**
  migrations (see "Database migrations")
- **Web:** FastAPI, htmx + Jinja2 templates, daisyUI components
- **Frontend build tooling:** pnpm (`package.json` + `pnpm-lock.yaml`), Node baked
  into the devcontainer — see [docs/frontend-assets.md](docs/frontend-assets.md)

## Layout

```
app/
  main.py                     composition root: builds the FastAPI app, wires layers
  domain/                     pure-Python business logic (no framework imports)
    greeting.py               e.g. normalize_name()
  db/                         the only place that talks to Postgres (SQLAlchemy)
    engine.py                 async engine + Base (declarative metadata)
    models.py                 ORM table definitions (Alembic autogenerates against these)
    migrate.py                programmatic `alembic upgrade head` (used by tests + e2e seeder)
    users.py                  user persistence
  web/                        presentation only: FastAPI routes + htmx + templates
    routes.py                 APIRouter (GET /, POST /greet) + Jinja2Templates
    templates/index.html      full page (daisyUI + htmx)
    templates/partials/       htmx fragments
    static/htmx.min.js        vendored htmx (committed)
    static/app.css            vendored, prebuilt Tailwind+daisyUI CSS (committed)
    static/app.tailwind.css   source for app.css (see docs/frontend-assets.md)
    static/assets.sha256      fingerprint of the build inputs (staleness gate)
tests/                        Python unit + integration tests (+ conftest DB/client fixtures)
e2e/                          self-contained TypeScript Playwright project (browser e2e)
  playwright.config.ts        boots the app via uvicorn + seeds a verified user
  tests/*.spec.ts             the browser specs
  support/                    shared config, seeded credentials, global setup
alembic.ini                   Alembic config (script_location = migrations/; URL from app settings)
migrations/                   Alembic migration environment
  env.py                      async env, wired to the app's engine + models metadata
  versions/                   the migration revisions (committed)
scripts/check.sh              the quality gate
scripts/e2e_seed.py           seeds the verified e2e user (reuses the app's UserManager)
scripts/assets-fingerprint.sh hash of frontend build inputs (build + gate share it)
package.json, pnpm-lock.yaml  frontend build deps (Tailwind/daisyUI, htmx) - pinned, committed
.devcontainer/                image (uv + Node/pnpm + Chromium baked in) + compose (app + Postgres)
docs/                         extra docs (e.g. frontend assets, e2e tests, security checks, multi-agent devcontainer workflow)
```

## Architecture

The code is split into three layers, enforced by import-linter contracts in
`pyproject.toml`. Dependencies only ever point **downward**:

```
web (FastAPI, htmx, Jinja)  →  domain (pure Python)  →  db (Postgres, SQLAlchemy)
```

- **`app.web`** — presentation only: parse the request, call the domain, render a
  template. **No business logic in routes or templates.** May import the domain,
  but **never the db directly** — persistence goes through the domain.
- **`app.domain`** — the business logic, and the layer that orchestrates
  persistence by calling `app.db`. Pure Python: no web framework and no direct
  SQLAlchemy (fastapi/starlette/jinja2/sqlalchemy are *forbidden* here), which
  keeps the logic trivial to unit-test in isolation. Put the real rules here.
- **`app.db`** — the *only* layer that touches the database (SQLAlchemy, Postgres).
  The lowest layer: it must not import the domain or web layers, nor any web
  framework.
- **`app.main`** — the composition root that assembles the layers. No logic.

When you add a feature: business rules go in `domain`, persistence in `db`,
HTTP/rendering in `web`. If `lint-imports` reports a broken contract, the fix is
almost always to move code to the right layer — not to loosen the contract.

## Common tasks

Run the app locally (VS Code forwards the port):

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the browser e2e tests (see [docs/e2e-tests.md](docs/e2e-tests.md)):

```bash
cd e2e && pnpm install && pnpm exec playwright test
```

Add dependencies:

```bash
uv add <pkg>            # runtime dependency
uv add --dev <pkg>      # dev/test dependency
```

## Database migrations

The schema is managed by **Alembic** (async), not `metadata.create_all`. Tests and
the e2e seeder build their schema by running the real migrations (via
`app/db/migrate.py`), so the migrations stay honest and dev/test schema matches
production.

When you change the schema, edit the ORM models in [app/db/models.py](app/db/models.py),
then generate and apply a migration:

```bash
uv run alembic revision --autogenerate -m "describe the change"  # writes migrations/versions/<rev>.py
uv run alembic upgrade head                                      # apply to the configured DB
```

Review the autogenerated revision before committing it (autogenerate isn't
perfect), and **commit it alongside the model change**. `check.sh` runs `alembic
check`, which fails if `models.py` has drifted ahead of the migrations — so a
model edit without its migration won't pass the gate. The connection URL comes
from app settings (`DATABASE_URL`) inside `migrations/env.py` — never hard-code
credentials in `alembic.ini`. Alembic's `env.py` and generated revisions are
exempt from `ruff format` (see `pyproject.toml`) so autogenerate doesn't fight the
formatter.

## Coverage

`pytest` prints a coverage report (with missing line numbers) on every run, but
there's no `--cov-fail-under` gate — a low number never blocks you. Instead, use
the `Missing` column as a checklist: for each uncovered line, decide whether it's
an important path (error branch, edge case, new domain rule) worth a test, or
genuinely trivial. Don't chase 100% for its own sake, but new behavior still
needs new tests.

## Frontend assets are vendored (offline, no CDN)

htmx and the Tailwind/daisyUI CSS are committed under `app/web/static/` and built
from pinned JS/CSS dependencies via pnpm. See
[docs/frontend-assets.md](docs/frontend-assets.md) for how the build works, when
to rebuild, and how to add a new JS dependency.

## Security checks

`check.sh` runs secret scanning (gitleaks, full git history) and dependency
vulnerability scanning (`uv audit`). See
[docs/security-checks.md](docs/security-checks.md) for how each works and
what to do when one flags something.

## End-to-end tests

The browser e2e tests are a self-contained **TypeScript Playwright** project in
`e2e/` (TypeScript is Playwright's primary language, so the VS Code Playwright
Test extension works). It boots the app via uvicorn against a test database and
seeds a verified user in its global setup. See
[docs/e2e-tests.md](docs/e2e-tests.md) for how to run and write them.

## Playwright / Chromium

Chromium and its OS libraries are baked into the devcontainer image
(`.devcontainer/Dockerfile`, `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`) so
container startup stays fast and e2e tests run offline. The e2e suite drives that
baked browser through the `@playwright/test` package in `e2e/package.json`. Keep
its version in lockstep with the Dockerfile's `uvx --from playwright==X` pin
(bump both, then rebuild the image) — check.sh step 2 fails if they drift.
