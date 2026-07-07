#!/usr/bin/env bash
set -euo pipefail

# scripts/agent.sh - create/destroy a fully isolated Claude Code agent.
#
# Each agent = one fresh git clone (own checkout, branch, and .git) + one
# devcontainer (own app+db containers, own Docker network, own Postgres
# volume). Because the devcontainer CLI derives its Compose "project name" from
# the clone directory's basename when the compose file lives under
# <dir>/.devcontainer/, giving each agent a unique directory name is *all* it
# takes to keep every agent's containers/network/DB completely separate - no
# manual -p flags.
#
# We use a clone rather than a git worktree because a clone is self-contained:
# its .git is a real directory inside the folder, so the devcontainer's
# `..:/workspace` mount already contains everything git needs - no bind-mounting
# the main repo's git dir, no host-path juggling. A local clone hardlinks the
# object store, so it is fast and space-cheap despite being independent.
#
# Usage:
#   scripts/agent.sh new <task-name> [-- <extra claude args>]
#   scripts/agent.sh remove <task-name>
#
# Examples:
#   scripts/agent.sh new fix-auth-bug
#   scripts/agent.sh new fix-auth-bug -- --dangerously-skip-permissions
#   scripts/agent.sh remove fix-auth-bug

usage() {
  echo "Usage: $0 new <task-name> [-- <extra claude args>]" >&2
  echo "       $0 remove <task-name>" >&2
  exit 1
}

# Turn a free-form task name into something safe to use as both a directory
# basename and (via the devcontainer CLI's project-naming rule) a Docker
# Compose project name: lowercase, alphanumeric-and-hyphens only.
sanitize() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-' | sed -E 's/-+/-/g; s/^-|-$//g'
}

[ $# -ge 1 ] || usage
COMMAND="$1"; shift

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Clones live next to the repo, not inside it, so they never show up as
# untracked files in the main checkout's `git status`.
CLONES_ROOT="$(dirname "$REPO_ROOT")/papertrail-clones"

case "$COMMAND" in
  new)
    [ $# -ge 1 ] || usage
    SAFE_NAME="$(sanitize "$1")"; shift
    [ "${1:-}" = "--" ] && shift        # optional separator before claude args
    CLAUDE_ARGS=("$@")                  # anything left is passed to `claude` as-is

    [ -n "$SAFE_NAME" ] || { echo "error: task name has no valid characters after sanitizing" >&2; exit 1; }
    CLONE_DIR="$CLONES_ROOT/$SAFE_NAME"
    BRANCH="agent/$SAFE_NAME"

    # The isolation guarantee above depends on this directory name being
    # unique, so refuse to silently reuse/overwrite one.
    if [ -e "$CLONE_DIR" ]; then
      echo "error: $CLONE_DIR already exists - pick another name, or run '$0 remove $SAFE_NAME' first" >&2
      exit 1
    fi

    mkdir -p "$CLONES_ROOT"
    echo "==> Cloning into $CLONE_DIR on branch $BRANCH"
    # Local clone: hardlinks objects (fast, cheap) and copies main's current
    # HEAD as the starting point, but is fully independent afterwards.
    git clone --quiet "$REPO_ROOT" "$CLONE_DIR"
    # Point the clone at the real upstream (if any) so `git push`/`pull` from
    # inside the agent go to GitHub, not back to the local main checkout.
    UPSTREAM_URL="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
    [ -n "$UPSTREAM_URL" ] && git -C "$CLONE_DIR" remote set-url origin "$UPSTREAM_URL"
    git -C "$CLONE_DIR" checkout --quiet -b "$BRANCH"

    echo "==> Building/starting isolated devcontainer for '$SAFE_NAME'"
    npx --yes @devcontainers/cli up --workspace-folder "$CLONE_DIR"

    echo "==> Launching Claude Code (Compose project: ${SAFE_NAME}_devcontainer, branch: $BRANCH)"
    exec npx --yes @devcontainers/cli exec --workspace-folder "$CLONE_DIR" claude "${CLAUDE_ARGS[@]}"
    ;;

  remove)
    [ $# -ge 1 ] || usage
    SAFE_NAME="$(sanitize "$1")"
    CLONE_DIR="$CLONES_ROOT/$SAFE_NAME"

    if [ -d "$CLONE_DIR" ]; then
      # The `devcontainer` CLI has no down/stop command (yet), so tear the
      # containers/network/volume down directly via docker compose. This
      # project name must match the one `up` derived automatically above -
      # both are `<clone-basename>_devcontainer`.
      echo "==> Stopping containers and deleting the Postgres volume for '${SAFE_NAME}_devcontainer'"
      docker compose -p "${SAFE_NAME}_devcontainer" -f "$CLONE_DIR/.devcontainer/docker-compose.yml" down -v || true

      # The clone is self-contained, so removing the agent is just deleting its
      # directory. Any `agent/<name>` branch it pushed to GitHub is untouched.
      echo "==> Removing clone $CLONE_DIR"
      rm -rf "$CLONE_DIR"
    else
      echo "warning: $CLONE_DIR not found - skipping container/clone removal" >&2
    fi

    echo "==> Done."
    ;;

  *)
    usage
    ;;
esac
