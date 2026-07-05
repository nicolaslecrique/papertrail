FROM mcr.microsoft.com/devcontainers/python:3.12

# Astral's recommended way to add uv to any Dockerfile: copy the static
# binaries, no curl/pip step, fully reproducible via the version pin.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /usr/local/bin/
ENV UV_LINK_MODE=copy

WORKDIR /workspace
