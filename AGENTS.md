# AGENTS.md

Guidance for AI agents (and humans) working in this repo.

`papertrail` is a tool to study the manipulation of science by lobbies. This is
currently a **Hello World** slice that stands up the full production stack end to end:
a FastAPI **REST API** backend and a separate **React / TanStack Start** frontend that
consumes it through a fully-typed, generated client.

## Git workflow: no pull requests

This is a solo project — the author works alone, so pull requests add no value.
Do **not** open a PR. Once the check is green (see below), merge the work branch
straight into `main` and push. Keep commits focused and descriptive.

## The one rule: keep the check green

Before you consider **any** change complete, run:

```bash
./scripts/check.sh
```

It must exit 0. It's a read-only gate that runs, in order: the **Python backend**
gate (secret scan, dependency audit, `ruff` format + lint, `pyrefly` strict types,
`deptry`, `import-linter`, the pytest suite, `alembic check`), then the **frontend**
gate (API-client drift guard, Prettier, ESLint, `tsc`, Knip, dependency-cruiser,
the production build), then the **Playwright e2e** suite (which boots both tiers).
The script is the source of truth for the exact steps — read it, or see
[docs/quality-gate.md](docs/quality-gate.md) for what each one does.

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.

`check.sh` never edits your files. To apply the fixes that *can* be applied
mechanically (`ruff check --fix`, `ruff format`, `prettier --write`, `eslint --fix`),
run the opt-in companion `./scripts/fix.sh`, review the diff, then re-run `check.sh`.
The rest of the gate has no safe auto-fix and stays check-only.

## Tech stack

- **Language / deps:** Python, managed with `uv` (`pyproject.toml` + `uv.lock`)
- **Backend:** FastAPI JSON REST API; auth via **fastapi-users** (JWT in an httponly
  cookie). No server-rendered HTML — the API only speaks JSON under `/api`.
- **Frontend:** **React 19 + TanStack Start** (SSR) in `frontend/`, styled with
  **Tailwind CSS v4** + **shadcn/ui**; server state via **TanStack Query**; the API
  client is generated from the backend's OpenAPI schema by **@hey-api/openapi-ts**.
  Package manager **pnpm**. See [docs/frontend.md](docs/frontend.md).
- **Database:** Postgres via async SQLAlchemy; schema managed by **Alembic**
  migrations (see "Database migrations")
- **Tests:** pytest (unit + integration, coverage via pytest-cov); Playwright in
  TypeScript for browser e2e in `e2e/` — see [docs/e2e-tests.md](docs/e2e-tests.md)
- **Quality tooling** (all run by `check.sh`): backend — Pyrefly (strict types),
  Ruff (`select = ["ALL"]` + `ruff format`), deptry, import-linter (layering),
  gitleaks + `uv audit` (security); frontend — strict `tsc`, typescript-eslint
  (strict, type-checked) with the TanStack Router/Query and Tailwind plugins,
  Prettier, Knip, dependency-cruiser. See [docs/quality-gate.md](docs/quality-gate.md).

## Layout

Top-level map; for the `app/` layers see "Architecture" below.

```
app/            the FastAPI REST API, split into layers (dependencies point downward)
  main.py         composition root: builds the FastAPI app, wires the layers
  domain/         pure-Python business logic (no framework imports)
  db/             the only layer that talks to Postgres (SQLAlchemy: engine, models, migrate)
  web/            presentation: FastAPI routers (JSON), auth wiring
frontend/       React / TanStack Start SPA+SSR app — see docs/frontend.md
  src/routes/     file-based routes (pages)
  src/client/     generated, typed API client (owned by @hey-api/openapi-ts)
  src/components/ui/  vendored shadcn/ui components (updated from the shadcn reference)
openapi.json    committed OpenAPI schema the client is generated from
tests/          Python unit + integration tests (+ conftest DB/client fixtures)
e2e/            self-contained TypeScript Playwright project — see docs/e2e-tests.md
migrations/     Alembic migration environment + committed revisions
scripts/        check.sh (the gate), fix.sh, export-openapi.py, e2e seeder
.devcontainer/  image (uv + Node/pnpm + Chromium) + compose (app + Postgres)
docs/           extra docs (quality gate, migrations, frontend, e2e, security, ...)
```

## Architecture

The backend is split into three layers, enforced by import-linter contracts in
`pyproject.toml`. Dependencies only ever point **downward**:

```
web (FastAPI REST)  →  domain (pure Python)  →  db (Postgres, SQLAlchemy)
```

- **`app.web`** — presentation only: parse the request, call the domain, return
  JSON. **No business logic in routes.** May import the domain, but **never the db
  directly** — persistence goes through the domain.
- **`app.domain`** — the business logic, and the layer that orchestrates
  persistence by calling `app.db`. Pure Python: no web framework and no direct
  SQLAlchemy (fastapi/starlette/sqlalchemy are *forbidden* here), which keeps the
  logic trivial to unit-test in isolation. Put the real rules here.
- **`app.db`** — the *only* layer that touches the database (SQLAlchemy, Postgres).
  The lowest layer: it must not import the domain or web layers, nor any web
  framework.
- **`app.main`** — the composition root that assembles the layers. No logic.

When you add a feature: business rules go in `domain`, persistence in `db`,
HTTP/JSON in `web`. If `lint-imports` reports a broken contract, the fix is almost
always to move code to the right layer — not to loosen the contract.

The **frontend** talks to the backend only through the generated client in
`frontend/src/client/`. When you change an API route or a Pydantic model,
regenerate the schema and client (see [docs/frontend.md](docs/frontend.md)); the
gate fails if they drift.

## Common tasks

Run the backend API (VS Code forwards the port):

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the frontend dev server (proxies `/api` to the backend above):

```bash
cd frontend && pnpm install && pnpm dev   # http://localhost:3000
```

Run the browser e2e tests (boots both tiers itself — see
[docs/e2e-tests.md](docs/e2e-tests.md)):

```bash
cd e2e && pnpm install && pnpm exec playwright test
```

Add dependencies:

```bash
uv add <pkg>                    # backend runtime dependency
uv add --dev <pkg>              # backend dev/test dependency
cd frontend && pnpm add <pkg>   # frontend dependency
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

## Frontend

The frontend is a self-contained pnpm project in `frontend/` (React + TanStack
Start, Tailwind v4, shadcn/ui). Its typed API client is generated from the
committed `openapi.json`, and the shadcn components under `src/components/ui/` are
treated as vendored (kept pristine so they can be updated from the shadcn
reference). See [docs/frontend.md](docs/frontend.md) for the build, the client
generation + drift guard, selective SSR, and how to add UI components.

## Security checks

`check.sh` runs secret scanning (gitleaks, full git history) and dependency
vulnerability scanning (`uv audit`). See
[docs/security-checks.md](docs/security-checks.md) for how each works and
what to do when one flags something.

## End-to-end tests

The browser e2e tests are a self-contained **TypeScript Playwright** project in
`e2e/`. It boots **both** tiers — the FastAPI API and the TanStack Start frontend
(which proxies `/api` to the API) — against a test database, and seeds a verified
user in its global setup. Chromium is baked into the devcontainer image and driven
offline; keep the `@playwright/test` pin in lockstep with the Dockerfile (check.sh
guards this). See [docs/e2e-tests.md](docs/e2e-tests.md) for how to run and write
them, and the baked-browser details.
