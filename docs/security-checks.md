# Security checks

- **Secrets:** `gitleaks git` scans the full git history (not just the working tree)
  on every `just check` run, so a secret is caught even if it's later removed from
  HEAD. The binary is baked into the devcontainer image (`.devcontainer/Dockerfile`,
  same pinned-static-binary pattern as `uv`) — if the gate reports gitleaks
  missing, rebuild the devcontainer. If it ever flags a genuine false positive
  (e.g. a low-entropy dev-only placeholder), add a `.gitleaks.toml` allowlist
  entry with a comment explaining why — do not skip the step. If it flags a real
  secret, rotate the credential; removing it from the current file is not enough
  once it's in history.
- **Dependency vulnerabilities:** `uv audit` scans `uv.lock` against the OSV
  database. It's a native `uv` subcommand (currently preview, hence
  `--preview-features audit-command` in `check.sh`) that reuses `uv`'s already-
  resolved lockfile instead of re-resolving dependencies, so it's fast. If it
  flags a real vulnerability, bump the affected dependency (`uv lock --upgrade-package
  <pkg>`); don't ignore or suppress a finding without understanding it first.
