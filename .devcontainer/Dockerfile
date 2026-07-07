FROM mcr.microsoft.com/devcontainers/python:3.12

# Astral's recommended way to add uv to any Dockerfile: copy the static
# binaries, no curl/pip step, fully reproducible via the version pin.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /usr/local/bin/
ENV UV_LINK_MODE=copy

# gitleaks (secret scanning, run by scripts/check.sh): same static-binary-copy
# trick as uv above, no curl/pip step, fully reproducible via the version pin.
COPY --from=zricethezav/gitleaks:v8.30.1 /usr/bin/gitleaks /usr/local/bin/gitleaks

# Bake Playwright's Chromium + its OS libraries into the image so the
# devcontainer starts fast (no ~150MB browser download during `uv sync`) and
# e2e tests run offline. Browsers install to PLAYWRIGHT_BROWSERS_PATH, which
# lives outside the /workspace bind mount, so it persists in the image; the
# runtime `playwright` (installed later by `uv sync`) finds them via this env.
# Keep this pin in lockstep with the `playwright` version in uv.lock so the
# baked browser matches the runtime package (see AGENTS.md).
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN uvx --from playwright==1.61.0 playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright

# Node + pnpm (frontend build tooling: rebuilding app/web/static/app.css from
# Tailwind/daisyUI, and vendoring JS deps like htmx - see the "Rebuilding the
# CSS" section of AGENTS.md). Node isn't a single static binary like uv/gitleaks
# above, so copy its install tree from the official image instead; corepack
# (bundled with Node) then pins the exact pnpm version from `packageManager` in
# package.json, reproducibly, with no separate npm-install-pnpm step.
COPY --from=node:24.18.0-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:24.18.0-slim /usr/local/bin/corepack /usr/local/bin/corepack
COPY --from=node:24.18.0-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN corepack enable && corepack prepare pnpm@11.10.0 --activate

WORKDIR /workspace
