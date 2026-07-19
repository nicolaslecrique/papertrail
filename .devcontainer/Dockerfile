FROM mcr.microsoft.com/devcontainers/python:3.12

# Astral's recommended way to add uv to any Dockerfile: copy the static
# binaries, no curl/pip step, fully reproducible via the version pin.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /usr/local/bin/
ENV UV_LINK_MODE=copy

# gitleaks (secret scanning, run by scripts/check.sh): same static-binary-copy
# trick as uv above, no curl/pip step, fully reproducible via the version pin.
COPY --from=zricethezav/gitleaks:v8.30.1 /usr/bin/gitleaks /usr/local/bin/gitleaks

# Bake Playwright's Chromium + its OS libraries into the image so the
# devcontainer starts fast (no ~150MB browser download) and the e2e tests run
# offline. Browsers install to PLAYWRIGHT_BROWSERS_PATH, which lives outside the
# /workspace bind mount, so it persists in the image; the TypeScript e2e runner
# (@playwright/test in e2e/package.json) finds them via this env. Keep this pin in
# lockstep with that @playwright/test version - check.sh fails if they drift.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN uvx --from playwright==1.61.0 playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright

# Node + pnpm: build tooling for the frontend/ app (React/TanStack Start, Vite)
# and the e2e/ Playwright suite. Node isn't a single static binary like
# uv/gitleaks above, so copy its install tree from the official image instead;
# corepack
# (bundled with Node) then pins the exact pnpm version from `packageManager` in
# package.json, reproducibly, with no separate npm-install-pnpm step.
COPY --from=node:24.18.0-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:24.18.0-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
# /usr/local/bin/corepack in the node image is a symlink into the node_modules
# tree above; COPYing that symlink directly dereferences it into a standalone
# file, which breaks corepack's own relative `require('./lib/corepack.cjs')`.
# Recreate the symlink ourselves instead of copying it.
RUN ln -s ../lib/node_modules/corepack/dist/corepack.js /usr/local/bin/corepack
RUN corepack enable && corepack prepare pnpm@11.10.0 --activate

WORKDIR /workspace
