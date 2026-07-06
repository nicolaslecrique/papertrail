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
2. `ruff format --check .` — formatting
3. `ruff check .` — linting (`select = ["ALL"]`)
4. `pyrefly check` — type checking (strict preset)
5. `pytest` — unit tests + Playwright e2e tests

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.

## Tech stack

- **Dependency management:** `uv` (`pyproject.toml` + `uv.lock`)
- **Type checker:** Pyrefly, strict (`[tool.pyrefly] preset = "strict"`)
- **Linter:** Ruff, `select = ["ALL"]` (minimal, justified ignores only)
- **Formatter:** `ruff format`
- **Tests:** pytest + pytest-playwright (e2e)
- **Web:** FastAPI, htmx + Jinja2 templates, daisyUI components

## Layout

```
app/
  main.py                     FastAPI app + routes (GET /, POST /greet)
  templates/index.html        full page (daisyUI + htmx)
  templates/partials/         htmx fragments
  static/htmx.min.js          vendored htmx (committed)
  static/app.css              vendored, prebuilt Tailwind+daisyUI CSS (committed)
  static/app.tailwind.css     source for app.css (see "Rebuilding the CSS")
tests/                        unit tests + conftest live-server fixture + e2e
scripts/check.sh              the quality gate
.devcontainer/                image (uv + Chromium baked in) + compose (app + Postgres)
```

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

## Frontend assets are vendored (offline, no CDN)

htmx and the Tailwind/daisyUI CSS are committed under `app/static/` and served by
FastAPI, so e2e tests are deterministic and need no network.

### Rebuilding the CSS

`app/static/app.css` is generated from `app/static/app.tailwind.css` and only
includes classes actually used by the templates. **This build is intentionally NOT
part of `check.sh`** (the committed CSS is what ships). Rebuild it only after adding
or changing daisyUI/Tailwind classes in the templates:

```bash
# One-off, needs Node (present in the devcontainer). Runs in a scratch dir so it
# never adds node_modules to the repo.
BUILD="$(mktemp -d)"
( cd "$BUILD" && npm init -y >/dev/null \
  && npm install tailwindcss@4 @tailwindcss/cli@4 daisyui@5 >/dev/null )
printf '@import "tailwindcss";\n@plugin "daisyui";\n@source "%s/app/templates";\n' "$PWD" \
  > "$BUILD/input.css"
"$BUILD/node_modules/.bin/tailwindcss" \
  -i "$BUILD/input.css" -o app/static/app.css --minify
```

## Playwright / Chromium

Chromium and its OS libraries are baked into the devcontainer image (see
`.devcontainer/Dockerfile`, `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`) so container
startup stays fast and e2e tests run offline. The `playwright` version pinned in the
Dockerfile **must match** the `playwright` version in `uv.lock`; bump both together.
