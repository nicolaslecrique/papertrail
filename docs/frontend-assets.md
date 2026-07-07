# Frontend assets are vendored (offline, no CDN)

htmx and the Tailwind/daisyUI CSS are committed under `app/web/static/`, so e2e
tests are deterministic and need no network. `package.json` + `pnpm-lock.yaml`
pin the JS/CSS dependencies; `pnpm` (baked into the devcontainer) builds them.

The committed files are what ships — `check.sh` doesn't run `pnpm run build`
(it stays Python-only and needs no Node). Instead it hashes the build *inputs*
and compares against the committed `assets.sha256`, so a forgotten rebuild
fails the gate rather than shipping silently stale.

## Rebuilding

Rebuild whenever a build input changes: a daisyUI/Tailwind class in
`app/web/templates/**`, `app/web/static/app.tailwind.css` itself, or a
frontend dependency bump (`pnpm-lock.yaml` changes). Nothing else affects the
output. If in doubt, `check.sh` step 3 tells you if a rebuild is owed.

```bash
pnpm install   # sync node_modules with package.json / pnpm-lock.yaml
pnpm run build # regenerates app.css, htmx.min.js AND assets.sha256
```

Review with `git diff app/web/static/`, then commit `app.css`, `htmx.min.js`,
and `assets.sha256` together.

`pnpm run build` = `build:css` (Tailwind CLI, tree-shaken against
`app/web/templates`) + `build:js` (copies htmx's bundle from `node_modules`)
+ `build:hash` (writes `assets.sha256` via `scripts/assets-fingerprint.sh`,
the same script `check.sh` uses, so they can't disagree).

Keep `source(none)` in `app.tailwind.css`: without it Tailwind auto-scans the
whole repo instead of just `app/web/templates`, and can pick up prose that
happens to match class names (e.g. daisyUI's `diff`), making the build
non-deterministic.

## Adding a new JS dependency

```bash
pnpm add <pkg>       # runtime (e.g. another vendored JS library)
pnpm add -D <pkg>    # build-only (e.g. a Tailwind plugin)
```

Wire it into a `build:*` script in `package.json` (mirroring `build:js` or
`build:css`), then `pnpm run build` to regenerate the vendored output.
