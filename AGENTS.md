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
2. playwright version check — the Dockerfile's baked-Chromium pin must match `uv.lock`
3. frontend assets fresh — committed `app/web/static/{app.css,htmx.min.js}` are not
   stale vs their sources (see "Frontend assets are vendored")
4. `gitleaks git` — secret scanning over the full git history
5. `uv audit` — known vulnerabilities in resolved dependencies
6. `ruff format --check .` — Python formatting
7. `ruff check .` — linting (`select = ["ALL"]`)
8. `pyrefly check` — type checking (strict preset)
9. `deptry .` — dependency hygiene (unused / missing / transitive / misplaced deps)
10. `lint-imports` — architecture layering contracts (see "Architecture" below)
11. `djlint app/web/templates --check` — template formatting
12. `djlint app/web/templates --lint` — template well-formedness (unclosed tags, ...)
13. `pytest` — unit + Playwright e2e tests, with a coverage report (see "Coverage")

Reformat templates with `uv run djlint app/web/templates --reformat`.

If it fails, fix the code (or the test) until it passes. Do not weaken the linter,
the type checker, or delete tests to make it pass. New behavior needs new tests.

## Tech stack

- **Dependency management:** `uv` (`pyproject.toml` + `uv.lock`)
- **Type checker:** Pyrefly, strict (`[tool.pyrefly] preset = "strict"`)
- **Linter:** Ruff, `select = ["ALL"]` (minimal, justified ignores only)
- **Formatter:** `ruff format`
- **Dependency hygiene:** deptry (unused/missing/transitive/misplaced deps)
- **Dependency vulnerabilities:** `uv audit` (native, preview; scans `uv.lock` against OSV)
- **Secret scanning:** gitleaks (full git history, baked into the devcontainer image)
- **Architecture enforcement:** import-linter (layering contracts in `pyproject.toml`)
- **Tests:** pytest + pytest-playwright (e2e), coverage via pytest-cov
- **Web:** FastAPI, htmx + Jinja2 templates, daisyUI components
- **Frontend build tooling:** pnpm (`package.json` + `pnpm-lock.yaml`), Node baked
  into the devcontainer — see "When (and how) to rebuild the frontend assets"

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
    static/app.tailwind.css   source for app.css (see "When to rebuild")
    static/assets.sha256      fingerprint of the build inputs (staleness gate)
tests/                        unit tests + conftest live-server fixture + e2e
scripts/check.sh              the quality gate
scripts/assets-fingerprint.sh hash of frontend build inputs (build + gate share it)
package.json, pnpm-lock.yaml  frontend build deps (Tailwind/daisyUI, htmx) - pinned, committed
.devcontainer/                image (uv + Node/pnpm + Chromium baked in) + compose (app + Postgres)
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
by FastAPI, so e2e tests are deterministic and need no network. They're built from
JS/CSS dependencies managed like any other dependency: `package.json` declares them,
`pnpm-lock.yaml` pins their exact resolved versions (commit both), and `pnpm` (baked
into the devcontainer, see `.devcontainer/Dockerfile`) installs and builds them.

**The committed `app/web/static/*` files are what ships** — `pnpm run build` does
*not* run inside `check.sh` (the gate stays Python-only and fast, and needs no
Node). But you can't silently ship a stale asset either: `check.sh` recomputes a
fingerprint of the build *inputs* and compares it to the committed
`app/web/static/assets.sha256`, so forgetting to rebuild fails the gate (see below).

### When (and how) to rebuild the frontend assets

Rebuild whenever you change a build **input**:

- add / change / remove a daisyUI or Tailwind class in `app/web/templates/**`
  (that's what Tailwind tree-shakes against),
- edit `app/web/static/app.tailwind.css` (the Tailwind entry / config),
- bump a frontend dependency (`tailwindcss`, `daisyui`, `htmx.org`) — i.e. anything
  that changes `pnpm-lock.yaml`.

You don't need to rebuild for anything else (Python changes, prose, non-template
files don't affect the output). If in doubt, run `check.sh`: step 3 tells you if a
rebuild is owed.

```bash
pnpm install   # sync node_modules with package.json / pnpm-lock.yaml
pnpm run build # regenerates app.css, htmx.min.js AND assets.sha256
```

Then `git diff app/web/static/` to review the regenerated output before committing it,
and commit `app.css`, `htmx.min.js`, and `assets.sha256` together.

`pnpm run build` runs three scripts (see `package.json`):
- `build:css` — runs the Tailwind CLI over `app/web/static/app.tailwind.css`,
  tree-shaken to classes actually used in `app/web/templates`, writing
  `app/web/static/app.css`. (The `source(none)` in `app.tailwind.css` restricts
  scanning to the explicit `@source` templates — **keep it**; without it Tailwind
  auto-scans the whole repo and leaks prose that happens to match class names, e.g.
  daisyUI's `diff`, into the shipped CSS, making the build non-deterministic.)
- `build:js` — copies `htmx.org`'s built bundle from `node_modules` to
  `app/web/static/htmx.min.js`.
- `build:hash` — writes `app/web/static/assets.sha256`, the input fingerprint that
  `check.sh` uses to detect a stale build. Both sides compute it via the single
  `scripts/assets-fingerprint.sh`, so they can never disagree.

### Adding a new JS dependency

```bash
pnpm add <pkg>            # runtime dependency (e.g. another vendored JS library)
pnpm add -D <pkg>         # build-only dependency (e.g. a new Tailwind plugin)
```

Then wire it into a `build:*` script in `package.json` (mirroring `build:js`'s
copy-from-`node_modules` pattern, or `build:css` if it's a CSS build input) and
run `pnpm run build` to regenerate the vendored output.

## Security checks

- **Secrets:** `gitleaks git` scans the full git history (not just the working tree)
  on every `check.sh` run, so a secret is caught even if it's later removed from
  HEAD. The binary is baked into the devcontainer image (`.devcontainer/Dockerfile`,
  same pinned-static-binary pattern as `uv`) — if `check.sh` reports gitleaks
  missing, rebuild the devcontainer. If it ever flags a genuine false positive
  (e.g. a low-entropy dev-only placeholder), add a `.gitleaks.toml` allowlist
  entry with a comment explaining why — do not skip the step. If it flags a real
  secret, rotate the credential; removing it from the current file is not enough
  once it's in history.
- **Dependency vulnerabilities:** `uv audit` scans `uv.lock` against the OSV
  database. It's a native `uv` subcommand (currently preview, hence
  `--preview-features audit-command` in `check.sh`) that reuses `uv`'s already-
  resolved lockfile instead of re-resolving dependencies, so it's fast. If it
  flags a real vulnerability, bump the affected dependency (`uv lock --upgrade-package
  <pkg>`); don't ignore or suppress a finding without understanding it first.

## Playwright / Chromium

Chromium and its OS libraries are baked into the devcontainer image (see
`.devcontainer/Dockerfile`, `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`) so container
startup stays fast and e2e tests run offline. The `playwright` version pinned in the
Dockerfile **must match** the `playwright` version in `uv.lock`; bump both together.
