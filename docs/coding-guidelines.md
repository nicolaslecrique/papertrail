# Coding guidelines

Project-specific style and best-practice rules, beyond what the linters already
enforce (see [quality-gate.md](quality-gate.md) for those). Add to this list as new
rules come up; keep each entry short and justified.

## Don't default a value that genuinely differs by context

Don't give a field or argument a default value unless that default is correct
*everywhere it's used* — regardless of environment, caller, or deployment target.
If the right value genuinely differs by context (a secret, a URL, an
environment flag, a feature toggle that's on in one place and off in another),
make it required instead, and supply each context's value explicitly there
(e.g. a config file per environment, explicit kwargs at each call site) rather
than letting one context's value silently stand in as the fallback for every
other.

A default that's wrong for the caller who forgot to override it fails silently:
the code runs, just with the wrong behavior, instead of refusing to start.
Making the value required turns that same mistake into an immediate, loud
failure at construction time.

**Worked example:** `app/config.py`'s `Settings` used to give every field a
"development-friendly default." That's fine for values that really are the same
everywhere (`access_token_lifetime_seconds`, `cookie_samesite`) — but
`database_url`, `auth_secret`, `base_url`, `email_backend`, `cookie_secure`, and
`environment` itself only had *dev* values as their default. A production
deployment that forgot to override one of them wouldn't fail to boot — it would
boot with a devcontainer database URL, a placeholder JWT secret, or (worst case)
silently think it was still `dev` and skip the production guard entirely. Those
fields now have no default; the devcontainer supplies its values from the
committed `.env.dev` (wired through `.devcontainer/docker-compose.yml`), and
tests/e2e set their own explicitly — so every context states its own answer
instead of one of them being assumed for all.

This isn't a blanket ban on defaults — `pwned_check_enabled: bool = True` is a
default that's correct in every context (secure by default; the few contexts
that need to go offline opt out explicitly). The test is not "does this field
have a default," it's "would this default ever be the *wrong* value for some
caller, silently."
