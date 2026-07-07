#!/usr/bin/env bash
set -euo pipefail

# scripts/agent.sh - create/destroy a fully isolated Claude Code agent.
#
# Each agent = one git worktree (own branch, own files) + one devcontainer
# (own app+db containers, own Docker network, own Postgres volume). Because
# the devcontainer CLI derives its Compose "project name" from the worktree
# directory's basename when the compose file lives under <dir>/.devcontainer/,
# giving each agent a unique directory name is *all* it takes to keep every
# agent's containers/network/DB completely separate - no manual -p flags.
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
# Worktrees live next to the repo, not inside it, so they never show up as
# untracked files in `git status` - no .gitignore entries needed for them.
WORKTREES_ROOT="$(dirname "$REPO_ROOT")/papertrail-worktrees"

case "$COMMAND" in
  new)
    [ $# -ge 1 ] || usage
    SAFE_NAME="$(sanitize "$1")"; shift
    [ "${1:-}" = "--" ] && shift        # optional separator before claude args
    CLAUDE_ARGS=("$@")                  # anything left is passed to `claude` as-is

    [ -n "$SAFE_NAME" ] || { echo "error: task name has no valid characters after sanitizing" >&2; exit 1; }
    WORKTREE_DIR="$WORKTREES_ROOT/$SAFE_NAME"
    BRANCH="agent/$SAFE_NAME"

    # The isolation guarantee below depends on this directory name being
    # unique, so refuse to silently reuse/overwrite one.
    if [ -e "$WORKTREE_DIR" ]; then
      echo "error: $WORKTREE_DIR already exists - pick another name, or run '$0 remove $SAFE_NAME' first" >&2
      exit 1
    fi

    mkdir -p "$WORKTREES_ROOT"
    echo "==> Creating worktree at $WORKTREE_DIR on branch $BRANCH"
    # No base ref given: branches from whatever commit is currently checked
    # out in the main repo (usually main) - the normal git worktree default.
    git -C "$REPO_ROOT" worktree add -b "$BRANCH" "$WORKTREE_DIR"

    # A worktree's `.git` is a *file* pointing at the main repo's git dir
    # (its objects/refs/index all live there, under .git/worktrees/<name>).
    # The compose file only mounts the worktree itself at /workspace, so
    # without also mounting that git dir every in-container git command fails
    # with "not a git repository". Bind-mount it at the SAME absolute path it
    # already points to (identity mount) so the existing pointer just resolves.
    # It's derived at runtime, so this works wherever the repo is cloned - no
    # hardcoded path. It can't live in the committed compose/devcontainer files
    # (the path is per-machine), and the devcontainer CLI's own
    # --mount-git-worktree-common-dir flag is silently ignored for the
    # Compose-based flow this project uses, so we pass a plain --mount instead.
    GIT_COMMON_DIR="$(cd "$(git -C "$WORKTREE_DIR" rev-parse --git-common-dir)" && pwd)"

    echo "==> Building/starting isolated devcontainer for '$SAFE_NAME'"
    npx --yes @devcontainers/cli up --workspace-folder "$WORKTREE_DIR" \
      --mount "type=bind,source=$GIT_COMMON_DIR,target=$GIT_COMMON_DIR"

    echo "==> Launching Claude Code (Compose project: ${SAFE_NAME}_devcontainer, branch: $BRANCH)"
    exec npx --yes @devcontainers/cli exec --workspace-folder "$WORKTREE_DIR" claude "${CLAUDE_ARGS[@]}"
    ;;

  remove)
    [ $# -ge 1 ] || usage
    SAFE_NAME="$(sanitize "$1")"
    WORKTREE_DIR="$WORKTREES_ROOT/$SAFE_NAME"

    if [ -d "$WORKTREE_DIR" ]; then
      # The `devcontainer` CLI has no down/stop command (yet), so tear the
      # containers/network/volume down directly via docker compose. This
      # project name must match the one `up` derived automatically above -
      # both are `<worktree-basename>_devcontainer`.
      echo "==> Stopping containers and deleting the Postgres volume for '${SAFE_NAME}_devcontainer'"
      docker compose -p "${SAFE_NAME}_devcontainer" -f "$WORKTREE_DIR/.devcontainer/docker-compose.yml" down -v || true

      echo "==> Removing worktree $WORKTREE_DIR"
      git -C "$REPO_ROOT" worktree remove "$WORKTREE_DIR" --force
    else
      echo "warning: $WORKTREE_DIR not found - skipping container/worktree removal" >&2
    fi

    git -C "$REPO_ROOT" branch -D "agent/$SAFE_NAME" 2>/dev/null || true
    echo "==> Done."
    ;;

  *)
    usage
    ;;
esac
