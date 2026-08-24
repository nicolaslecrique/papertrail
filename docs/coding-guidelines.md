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
"development-friendly default," including `database_url`. A production deployment
that forgot to override it wouldn't fail to boot — it would boot pointed at a
devcontainer database URL. `database_url` now has no default: the devcontainer
supplies its value from the committed `.env.dev` (wired through
`.devcontainer/docker-compose.yml`), and tests/e2e set their own explicitly — so
every context states its own answer instead of one of them being assumed for all.

This isn't a blanket ban on defaults. A value that really is the same everywhere
(a timeout, a page size, a secure-by-default feature flag that the odd context
opts out of explicitly) should keep its default. The test is not "does this field
have a default," it's "would this default ever be the *wrong* value for some
caller, silently."
