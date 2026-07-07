# AGENTS.md

Guidance for AI agents (and humans) working in this repo.

`papertrail` is a tool to study the manipulation of science by lobbies. This is
currently a **Hello World** slice that stands up the full production stack end to end.

## The one rule: keep the check green

Before you consider **any** change complete, run:

```bash
./scripts/check.sh
```

It must exit 0. It runs, in order:

1. `uv sync` — dependencies match `pyproject.toml` / `uv.lock`
2. `ruff format --check .` — Python formatting
3. `ruff check .` — linting (`select = ["ALL"]`)
4. `pyrefly check` — type checking (strict preset)
5. `deptry .` — dependency hygiene (unused / missing / transitive / misplaced deps)
6. `lint-imports` — architecture layering contracts (see "Architecture" below)
7. `djlint app/web/templates --check` — template formatting
8. `djlint app/web/templates --lint` — template well-formedness (unclosed tags, ...)
9. `pytest` — unit + Playwright e2e tests, with a coverage report (see "Coverage")

Reformat templates with `uv run djlint app/web/templates --reformat`.

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.

## Tech stack

- **Dependency management:** `uv` (`pyproject.toml` + `uv.lock`)
- **Type checker:** Pyrefly, strict (`[tool.pyrefly] preset = "strict"`)
- **Linter:** Ruff, `select = ["ALL"]` (minimal, justified ignores only)
- **Formatter:** `ruff format`
- **Dependency hygiene:** deptry (unused/missing/transitive/misplaced deps)
- **Architecture enforcement:** import-linter (layering contracts in `pyproject.toml`)
- **Tests:** pytest + pytest-playwright (e2e), coverage via pytest-cov
- **Web:** FastAPI, htmx + Jinja2 templates, daisyUI components

## Layout

```
app/
  main.py                     composition root: builds the FastAPI app, wires layers
  domain/                     pure-Python business logic (no framework imports)
    greeting.py               e.g. normalize_name()
  db/                         the only place that talks to Postgres (empty for now)
  web/                        presentation only: FastAPI routes + htmx + templates
    routes.py                 APIRouter (GET /, POST /greet) + Jinja2Templates
    templates/index.html      full page (daisyUI + htmx)
    templates/partials/       htmx fragments
    static/htmx.min.js        vendored htmx (committed)
    static/app.css            vendored, prebuilt Tailwind+daisyUI CSS (committed)
    static/app.tailwind.css   source for app.css (see "Rebuilding the CSS")
tests/                        unit tests + conftest live-server fixture + e2e
scripts/check.sh              the quality gate
.devcontainer/                image (uv + Chromium baked in) + compose (app + Postgres)
docs/                         extra docs (e.g. the multi-agent devcontainer workflow)
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

Add dependencies:

```bash
uv add <pkg>            # runtime dependency
uv add --dev <pkg>      # dev/test dependency
```

## Coverage

`pytest` prints a coverage report (with the missing line numbers) on every run.
It is **report-only** — there is deliberately no `--cov-fail-under` gate, so a low
number never blocks you. Instead, **use the report as a checklist while coding**:
after adding or changing behavior, read the `Missing` column and ask whether each
uncovered line is an important path that deserves a test (an error branch, an edge
case, a new domain rule) or genuinely trivial. Add the tests that matter; don't
chase 100% for its own sake. New behavior still needs new tests.

## Frontend assets are vendored (offline, no CDN)

htmx and the Tailwind/daisyUI CSS are committed under `app/web/static/` and served
by FastAPI, so e2e tests are deterministic and need no network.

### Rebuilding the CSS

`app/web/static/app.css` is generated from `app/web/static/app.tailwind.css` and only
includes classes actually used by the templates. **This build is intentionally NOT
part of `check.sh`** (the committed CSS is what ships). Rebuild it only after adding
or changing daisyUI/Tailwind classes in the templates:

```bash
# One-off, needs Node (present in the devcontainer). Runs in a scratch dir so it
# never adds node_modules to the repo.
BUILD="$(mktemp -d)"
( cd "$BUILD" && npm init -y >/dev/null \
  && npm install tailwindcss@4 @tailwindcss/cli@4 daisyui@5 >/dev/null )
printf '@import "tailwindcss";\n@plugin "daisyui";\n@source "%s/app/web/templates";\n' "$PWD" \
  > "$BUILD/input.css"
"$BUILD/node_modules/.bin/tailwindcss" \
  -i "$BUILD/input.css" -o app/web/static/app.css --minify
```

## Playwright / Chromium

Chromium and its OS libraries are baked into the devcontainer image (see
`.devcontainer/Dockerfile`, `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`) so container
startup stays fast and e2e tests run offline. The `playwright` version pinned in the
Dockerfile **must match** the `playwright` version in `uv.lock`; bump both together.
