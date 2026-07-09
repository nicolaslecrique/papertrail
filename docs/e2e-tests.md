# End-to-end tests are TypeScript Playwright

The browser tests live in `e2e/` as a **self-contained TypeScript Playwright
project** — its own `package.json`, `pnpm-lock.yaml`, `tsconfig.json`, and
`playwright.config.ts`. TypeScript is Playwright's primary language, so the VS
Code **Playwright Test** extension (Test Explorer, codegen, trace viewer,
step-debugging) works out of the box. The Python side keeps only unit and
integration tests (httpx against the ASGI app); nothing in `tests/` drives a
browser anymore.

`e2e/` is deliberately outside the repo-root pnpm project: it has its own
`pnpm-workspace.yaml`, so `pnpm install` there resolves `e2e/package.json`
instead of being captured by the frontend build's workspace, and its lockfile
never touches the CSS `assets.sha256` fingerprint (see "Frontend assets are
vendored").

## Running

```bash
cd e2e
pnpm install                 # first time only; the pnpm store caches it after
pnpm exec playwright test    # or: pnpm test
```

Useful variants (all from `e2e/`):

```bash
pnpm exec playwright test --ui      # watch-mode UI runner (or: pnpm test:ui)
pnpm exec playwright test --debug   # step through with the inspector
pnpm exec playwright show-report    # open the last HTML report
pnpm exec tsc --noEmit              # type-check the specs (also: pnpm typecheck)
```

Or just open the **Testing** panel in VS Code: the extension discovers
`e2e/playwright.config.ts` and lets you run or debug individual tests inline.

`check.sh` runs the same thing in its last step — `pnpm install --frozen-lockfile`
then `pnpm exec playwright test` — so a green local run means a green gate.

## How it wires up

`playwright.config.ts` owns the whole lifecycle; no external services need to be
started by hand:

- **`webServer`** boots the real app with
  `uv run uvicorn app.main:app` on a fixed port, pointed at a dedicated
  `papertrail_test` database (`support/config.ts` sets `DATABASE_URL` /
  `AUTH_SECRET` / `EMAIL_BACKEND`). Playwright waits for `/` — which renders
  without touching the database — before starting, so readiness never races the
  schema. The server is torn down when the run ends.
- **`globalSetup`** (`support/global-setup.ts`) shells out to
  `uv run python scripts/e2e_seed.py`, which creates the test database + schema
  and seeds one active, **verified** user. The seeder reuses the app's own
  `UserManager`, so the password is hashed exactly as real registration would —
  the alternative (a raw SQL insert) can't reproduce that hash. The seeded
  credentials live in `support/credentials.ts`, the single source shared between
  the seeder (via env) and the login spec.
- **The browser is the baked Chromium** at `/ms-playwright`
  (`PLAYWRIGHT_BROWSERS_PATH`, set in the devcontainer image). `@playwright/test`
  is pinned to the **same version** the Dockerfile bakes (`playwright==1.61.0`),
  so no browser is ever downloaded and the tests run offline. `check.sh` step 2
  fails if the Dockerfile pin and `e2e/package.json` drift — keep them in
  lockstep (and rebuild the devcontainer image when you bump the Dockerfile).

## Writing a test

Specs live in `e2e/tests/*.spec.ts`. Prefer user-facing, role/label selectors
(they match the daisyUI templates and survive markup changes):

```ts
import { expect, test } from "@playwright/test";

test("greeting swaps in via htmx", async ({ page }) => {
  await page.goto("/");                                    // baseURL is preset
  await page.getByLabel("Your name").fill("Ada");          // <label for> / aria-label
  await page.getByRole("button", { name: "Greet me" }).click();
  await expect(page.getByText("Hello, Ada!")).toBeVisible();
});
```

For a test that needs an authenticated session, log in with the seeded account
from `support/credentials.ts` (see `tests/auth.spec.ts`) — the user is already
verified, so no email-confirmation step is needed. `getByRole` / `getByLabel` /
`getByText` mirror the Python `expect(...)` calls the old suite used, so porting
a flow is mostly mechanical.
