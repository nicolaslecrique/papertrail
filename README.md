# papertrail

Tool to study the manipulation of science by lobbies

input a paper, scientist, journal, and we will evaluate the biases surrounding it.

## Development environment

### Why this setup

We want to run several Claude Code agents at once, each on its own task, without them ever touching
each other's files, database, or processes. Two mechanisms combine to give that:

1. **Git worktrees** give each agent its own checkout and branch, so file edits never collide.
2. **A devcontainer per worktree** gives each agent its own sandboxed runtime — its own app container,
   its own Postgres container, its own Docker network, and its own Postgres data volume. This is the
   isolation git worktrees alone don't give you: two agents editing different files could otherwise
   still stomp on the same database.

The trick that makes this "free" (no manual bookkeeping per agent) is that the Dev Containers CLI names
the underlying Docker Compose project after the workspace folder's name. Since every worktree lives in
its own uniquely-named directory, every agent's containers/network/DB volume land in a separate,
uniquely-named Compose project automatically.

Two things were deliberately left out to keep this simple, worth knowing about:

- **No network egress firewall.** Anthropic's reference Claude Code devcontainer includes an
  iptables-based allowlist so a compromised dependency can't phone home. We skipped it here: every
  agent's container has full outbound internet access. The container boundary is still real isolation,
  just not hardened against a malicious dependency exfiltrating data. Revisit if that risk profile changes.
- **Shared Claude Code login.** All agents share one `~/.claude` config volume so you sign in once
  instead of per worktree. Session history/settings are shared as a result — a convenience trade-off,
  not a correctness one.

### How to use it

**One-time host setup** (Docker isn't installed by default):

```bash
# Docker Engine (see https://docs.docker.com/engine/install/ubuntu/ for the full apt-repo steps)
sudo usermod -aG docker "$USER"   # log out/in afterwards so this takes effect
code --install-extension ms-vscode-remote.remote-containers
```

`scripts/agent.sh` drives the `@devcontainers/cli` via `npx`, so no global npm install is required —
only Node/npm need to be on your PATH.

**Start a new agent on its own task:**

```bash
./scripts/agent.sh new fix-auth-bug
```

This creates a worktree at `../papertrail-worktrees/fix-auth-bug` on branch `agent/fix-auth-bug`,
builds/starts its devcontainer (FastAPI app + Postgres), and drops you into a `claude` session running
inside it. Pass extra flags to `claude` after `--`:

```bash
./scripts/agent.sh new fix-auth-bug -- --dangerously-skip-permissions
```

**Run several agents at once:** just run the command again with a different task name from another
terminal. Each gets fully separate containers, network, and database.

**Finish up:**

```bash
./scripts/agent.sh remove fix-auth-bug
```

Stops and removes that agent's containers, network, and Postgres volume, then removes the git worktree
and branch.

**Poking at a running agent's database directly:**

```bash
docker compose -f ../papertrail-worktrees/fix-auth-bug/.devcontainer/docker-compose.yml exec db \
  psql -U papertrail
```

**Exploring without a task-specific agent:** open the main checkout in VS Code and run "Dev Containers:
Reopen in Container" — it uses the same `.devcontainer/` config and won't collide with any agent's
containers (its Compose project is named after the main checkout's folder, e.g. `papertrail_devcontainer`).
