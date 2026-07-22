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
just check
```

It must exit 0. `just check` runs `scripts/check.sh`, which does, in order: the
**Python backend** gate (secret scan, dependency audit, `ruff` format + lint,
`pyrefly` strict types, `deptry`, `import-linter`, the pytest suite,
`alembic check`), then the **frontend** gate (API-client drift guard, Prettier,
ESLint, `tsc`, Knip, dependency-cruiser, the production build), then the
**Playwright e2e** suite (which boots both tiers). The script is the source of
truth for the exact steps — read it, or see
[docs/quality-gate.md](docs/quality-gate.md) for what each tier is for.

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.

`just check` won't rewrite your source: apart from regenerating a few committed
artifacts in place to verify they're current (`openapi.json`, the generated client,
the route tree), it makes no edits. To apply the fixes that *can* be applied
mechanically (`ruff check --fix`, `ruff format`, `prettier --write`, `eslint --fix`),
run the opt-in companion `just fix`, review the diff, then re-run `just check`.
The rest of the gate has no safe auto-fix and stays check-only.

**CI.** `.github/workflows/ci.yml` runs this same gate (`just check`) on every push,
using [`devcontainers/ci`](https://github.com/devcontainers/ci) to build and run it
*inside* the actual devcontainer image (`.devcontainer/Dockerfile`, via the
CI-only `.devcontainer/ci/devcontainer.json`) instead of reinstalling `uv`,
`gitleaks`, `just`, Node/pnpm, and Playwright's Chromium by hand — so there's only
one place those tool versions are pinned. Postgres comes up as the compose `db`
service alongside the devcontainer, reached via `TEST_DATABASE_URL`. The built
image is pushed to GHCR (`ghcr.io/nicolaslecrique/papertrail-devcontainer`) and
reused as a build cache on later runs.

## Command runner: `just`

The common commands live in one place — the [`justfile`](justfile) at the repo
root, run with [`just`](https://just.systems) (a Makefile-like task runner, baked
into the devcontainer image). It's the central, discoverable entrypoint; prefer it
over remembering the raw `uv`/`pnpm`/`alembic` invocations. Run `just` (or
`just --list`) to see every recipe. The recipes are thin wrappers — they delegate
to `scripts/check.sh`, `scripts/fix.sh`, `uv`, `pnpm`, and `alembic`, which stay the
source of truth.

```bash
just                 # list all recipes
just install         # install backend (uv) + frontend & e2e (pnpm) deps
just check           # the full quality gate (runs scripts/check.sh)
just fix             # apply the mechanical auto-fixes, then re-run just check
just backend         # run the API on :8000 (auto-reload)
just frontend        # run the frontend dev server on :3000
just dev             # run backend + frontend together (Ctrl-C stops both)
just test            # backend pytest;  just test-e2e  runs the Playwright suite
just build           # build the frontend SSR bundle
just migrate         # apply DB migrations;  just migration "msg"  autogenerates one
just gen-client      # regenerate openapi.json + the typed frontend client
```

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
justfile        `just` recipes — the central entrypoint for common commands
tests/          Python unit + integration tests (+ conftest DB/client fixtures)
e2e/            self-contained TypeScript Playwright project — see docs/e2e-tests.md
migrations/     Alembic migration environment + committed revisions
scripts/        check.sh (the gate), fix.sh, export-openapi.py, e2e seeder
.devcontainer/  image (uv + just + Node/pnpm + Chromium) + compose (app + Postgres)
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

All wrapped by `just` (see "Command runner: `just`" above; `just --list` for the
full set). The main ones:

```bash
just backend    # run the API on :8000 (VS Code forwards the port)
just frontend   # run the frontend dev server on :3000 (proxies /api to the backend)
just dev        # run both together (Ctrl-C stops both)
just test-e2e   # browser e2e tests, boots both tiers itself (see docs/e2e-tests.md)
```

Add dependencies (no recipe — run the package manager directly):

```bash
uv add <pkg>                    # backend runtime dependency
uv add --dev <pkg>              # backend dev/test dependency
cd frontend && pnpm add <pkg>   # frontend dependency
```

## Database migrations

The schema is managed by **Alembic** (async), not `metadata.create_all`. When you
change the schema, edit the ORM models in [app/db/models.py](app/db/models.py),
autogenerate a migration with `just migration "describe the change"`, review it,
and **commit it alongside the model change** — the gate's `alembic check` fails if
the models drift ahead of the migrations. Apply pending migrations with
`just migrate`. See [docs/migrations.md](docs/migrations.md) for details.

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
