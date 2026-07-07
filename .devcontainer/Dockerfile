FROM mcr.microsoft.com/devcontainers/python:3.12

# Astral's recommended way to add uv to any Dockerfile: copy the static
# binaries, no curl/pip step, fully reproducible via the version pin.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /usr/local/bin/
ENV UV_LINK_MODE=copy

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

WORKDIR /workspace
