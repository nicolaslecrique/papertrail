#!/usr/bin/env bash
set -euo pipefail

# scripts/assets-fingerprint.sh - emit a stable hash of everything that
# determines the built frontend assets (app/web/static/app.css and htmx.min.js).
#
# This is the SINGLE source of truth for that fingerprint: `pnpm run build`
# writes it to app/web/static/assets.sha256, and scripts/check.sh recomputes it
# and compares - so the "are the committed assets stale?" gate is a millisecond
# hash compare with no Node/pnpm dependency, and the two sides can never disagree
# about how the hash is computed.
#
# Inputs that affect the build output (change any of these -> rebuild needed):
#   - app/web/static/app.tailwind.css   the Tailwind entry / config
#   - app/web/templates/**              content Tailwind scans for used classes
#   - pnpm-lock.yaml                    pinned tailwindcss / daisyui / htmx versions
# (package.json is intentionally excluded: pnpm-lock.yaml is the precise signal
# for dependency changes, so editing a script or metadata field in package.json
# doesn't spuriously flag the assets as stale.)

cd "$(dirname "${BASH_SOURCE[0]}")/.."

{
  sha256sum app/web/static/app.tailwind.css pnpm-lock.yaml
  # -print0 | sort -z: deterministic order regardless of filesystem listing.
  # -r (--no-run-if-empty): never run bare `sha256sum` (which would read stdin).
  find app/web/templates -type f -print0 | sort -z | xargs -0 -r sha256sum
} | sha256sum | cut -d' ' -f1
