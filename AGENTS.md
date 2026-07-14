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

It must exit 0. It's a read-only gate that runs, in order, dependency/asset/secret
checks, formatting, linting, type checking, dependency and architecture contracts,
template checks, the pytest suite, `alembic check`, and the Playwright e2e suite.
The script is the source of truth for the exact steps — read it, or see
[docs/quality-gate.md](docs/quality-gate.md) for what each one does.

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.

`check.sh` never edits your files. To apply the fixes that *can* be applied
mechanically (`ruff check --fix`, `ruff format`, `djlint --reformat`), run the
opt-in companion `./scripts/fix.sh`, review the diff, then re-run `check.sh`. The
rest of the gate has no safe auto-fix and stays check-only.

## Tech stack

- **Language / deps:** Python, managed with `uv` (`pyproject.toml` + `uv.lock`)
- **Web:** FastAPI, htmx + Jinja2 templates, daisyUI components
- **Database:** Postgres via async SQLAlchemy; schema managed by **Alembic**
  migrations (see "Database migrations")
- **Frontend build:** pnpm (`package.json` + `pnpm-lock.yaml`), Node baked into
  the devcontainer — see [docs/frontend-assets.md](docs/frontend-assets.md)
- **Tests:** pytest (unit + integration, coverage via pytest-cov); Playwright in
  TypeScript for browser e2e in `e2e/` — see [docs/e2e-tests.md](docs/e2e-tests.md)
- **Quality tooling** (all run by `check.sh`): Pyrefly (strict types), Ruff
  (`select = ["ALL"]` + `ruff format`), deptry, import-linter (layering), gitleaks
  and `uv audit` (security). See [docs/quality-gate.md](docs/quality-gate.md).

## Layout

Top-level map; for the `app/` layers see "Architecture" below.

```
app/            the application, split into layers (dependencies point downward)
  main.py         composition root: builds the FastAPI app, wires the layers
  domain/         pure-Python business logic (no framework imports)
  db/             the only layer that talks to Postgres (SQLAlchemy: engine, models, migrate)
  web/            presentation: FastAPI routes, Jinja templates, vendored static assets
tests/          Python unit + integration tests (+ conftest DB/client fixtures)
e2e/            self-contained TypeScript Playwright project — see docs/e2e-tests.md
migrations/     Alembic migration environment + committed revisions
scripts/        check.sh (the gate), fix.sh, e2e seeder, asset fingerprint
.devcontainer/  image (uv + Node/pnpm + Chromium) + compose (app + Postgres)
docs/           extra docs (quality gate, migrations, frontend assets, e2e, security, ...)
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

The schema is managed by **Alembic** (async), not `metadata.create_all`. When you
change the schema, edit the ORM models in [app/db/models.py](app/db/models.py),
autogenerate a migration, review it, and **commit it alongside the model change**
— `check.sh`'s `alembic check` fails if the models drift ahead of the migrations.
See [docs/migrations.md](docs/migrations.md) for the commands and details.

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
seeds a verified user in its global setup. Chromium is baked into the devcontainer
image and driven offline; keep the `@playwright/test` pin in lockstep with the
Dockerfile (check.sh guards this). See [docs/e2e-tests.md](docs/e2e-tests.md) for
how to run and write them, and the baked-browser details.
