# papertrail

Tool to study the manipulation of science by lobbies

input a paper, scientist, journal, and we will evaluate the biases surrounding it.

## Technical Stack

### Guardrails

* dependancy management: uv
* type checker: Pyrefly, with strict mode activated
* tests: pytest, and pytest-playwright for e2e tests
* linter: ruff, with "ALL" activated
* formatter: ruff format

### Service

* web server: FastAPI
* htmx with Jinja2
* frontend components: daisyUI

## Development environment

### Why this setup

We want to run several Claude Code agents at once, each on its own task, without them ever touching
each other's files, database, or processes. Two mechanisms combine to give that:

1. **A fresh git clone per agent** gives each agent its own checkout, branch, and `.git`, so file edits
   never collide. A clone is used rather than a git worktree because it is fully self-contained — its
   `.git` is a real directory inside the folder, so the devcontainer just mounts it and in-container git
   works with no extra plumbing. Local clones hardlink the object store, so they are fast and cheap
   despite being independent.
2. **A devcontainer per clone** gives each agent its own sandboxed runtime — its own app container,
   its own Postgres container, its own Docker network, and its own Postgres data volume. This is the
   isolation separate checkouts alone don't give you: two agents editing different files could otherwise
   still stomp on the same database.

The trick that makes this "free" (no manual bookkeeping per agent) is that the Dev Containers CLI names
the underlying Docker Compose project after the workspace folder's name. Since every clone lives in
its own uniquely-named directory, every agent's containers/network/DB volume land in a separate,
uniquely-named Compose project automatically.

Two things were deliberately left out to keep this simple, worth knowing about:

- **No network egress firewall.** Anthropic's reference Claude Code devcontainer includes an
  iptables-based allowlist so a compromised dependency can't phone home. We skipped it here: every
  agent's container has full outbound internet access. The container boundary is still real isolation,
  just not hardened against a malicious dependency exfiltrating data. Revisit if that risk profile changes.
- **Shared Claude Code login.** All agents share one `~/.claude` config volume so you sign in once
  instead of per clone. Session history/settings are shared as a result — a convenience trade-off,
  not a correctness one.

### How to use it

**Prerequisites** (none of these are installed by default on a fresh machine):

- **Docker Engine**, with your user able to run `docker` without `sudo` (see
  [docs.docker.com/engine/install/ubuntu](https://docs.docker.com/engine/install/ubuntu/), then
  `sudo usermod -aG docker "$USER"` and log out/in for it to take effect).
- **Node.js/npm** on your `PATH`. This is all `scripts/agent.sh` needs on the host — it drives
  `@devcontainers/cli` via `npx --yes`, which fetches the CLI on first run, so there's no global
  npm install to manage. Recommended install method:
  [nvm](https://github.com/nvm-sh/nvm) (`nvm install --lts`), since it needs no `sudo` and keeps
  Node upgrades out of the system package manager's way.
- **git** (already present on most dev machines; needed to clone per agent).
- Optional, only if you want the point-and-click "Reopen in Container" workflow in the editor
  instead of `scripts/agent.sh`: VS Code plus the Dev Containers extension
  (`code --install-extension ms-vscode-remote.remote-containers`).

Everything else — the Claude Code CLI, Python, `uv`, Postgres — lives inside the devcontainer and
is installed automatically per-agent; nothing else is needed on the host.

**Start a new agent on its own task:**

```bash
./scripts/agent.sh new fix-auth-bug
```

This clones the repo into `../papertrail-clones/fix-auth-bug` on branch `agent/fix-auth-bug`,
builds/starts its devcontainer (FastAPI app + Postgres), and drops you into a `claude` session running
inside it. The clone's `origin` is repointed at the repo's upstream (GitHub) so the agent can push its
branch for review. Pass extra flags to `claude` after `--`:

```bash
./scripts/agent.sh new fix-auth-bug -- --dangerously-skip-permissions
```

**Run several agents at once:** just run the command again with a different task name from another
terminal. Each gets fully separate containers, network, and database.

**Finish up:**

```bash
./scripts/agent.sh remove fix-auth-bug
```

Stops and removes that agent's containers, network, and Postgres volume, then deletes the clone
directory. Any `agent/<name>` branch already pushed to GitHub is left untouched.

**Poking at a running agent's database directly:**

```bash
docker compose -f ../papertrail-clones/fix-auth-bug/.devcontainer/docker-compose.yml exec db \
  psql -U papertrail
```

**Exploring without a task-specific agent:** open the main checkout in VS Code and run "Dev Containers:
Reopen in Container" — it uses the same `.devcontainer/` config and won't collide with any agent's
containers (its Compose project is named after the main checkout's folder, e.g. `papertrail_devcontainer`).
