#!/usr/bin/env bash
set -euo pipefail

# A brand-new worktree/scaffold has no pyproject.toml yet on first boot -
# don't fail on that, and don't mask a genuine `uv sync` failure either.
if [ -f pyproject.toml ]; then
  uv sync
else
  echo "No pyproject.toml yet - skipping uv sync"
fi

# devcontainer.json mounts the shared `papertrail-claude-config` volume at
# ~/.claude so every agent worktree reuses one Claude Code login. Docker
# creates fresh named volumes root-owned, which blocks the `vscode` user
# from writing into it - fix that up.
sudo chown -R vscode:vscode ~/.claude

# Claude Code keeps most persistent state (login, onboarding, theme) in
# ~/.claude.json - a *file* next to ~/.claude, not inside it - so the volume
# mount above doesn't cover it. Relocate it into the mounted directory and
# symlink it back, so a first-time login/onboarding is shared too.
if [ ! -L ~/.claude.json ]; then
  [ -f ~/.claude.json ] && mv ~/.claude.json ~/.claude/.claude.json
  [ -f ~/.claude/.claude.json ] || touch ~/.claude/.claude.json
  ln -sf ~/.claude/.claude.json ~/.claude.json
fi
