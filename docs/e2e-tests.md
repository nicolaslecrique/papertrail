# End-to-end tests are TypeScript Playwright

The browser tests live in `e2e/` as a **self-contained TypeScript Playwright
project** — its own `package.json`, `pnpm-lock.yaml`, `tsconfig.json`, and
`playwright.config.ts`. TypeScript is Playwright's primary language, so the VS
Code **Playwright Test** extension (Test Explorer, codegen, trace viewer,
step-debugging) works out of the box. The Python side keeps only unit and
integration tests (httpx against the ASGI app); nothing in `tests/` drives a
browser anymore.

`e2e/` is deliberately its own pnpm project (own `pnpm-workspace.yaml`), separate
from the `frontend/` app so its lockfile and dev tooling stay independent of the
app's.

## Running

```bash
just test-e2e    # runs the Playwright suite (deps installed by `just install`)
```

`just test-e2e` runs `pnpm exec playwright test` in `e2e/`. To drive Playwright
directly for the variants below, `cd e2e` first (`just install` handles the initial
`pnpm install`).

Useful variants (all from `e2e/`):

```bash
pnpm exec playwright test --ui      # watch-mode UI runner (or: pnpm test:ui)
pnpm exec playwright test --debug   # step through with the inspector
pnpm exec playwright show-report    # open the last HTML report
pnpm exec tsc --noEmit              # type-check the specs (also: pnpm typecheck)
```

Or just open the **Testing** panel in VS Code: the extension discovers
`e2e/playwright.config.ts` and lets you run or debug individual tests inline.

The gate (`just check`) runs the same thing in its last step —
`pnpm install --frozen-lockfile` then `pnpm exec playwright test` — so a green local
run means a green gate.

**axe-core** (`@axe-core/playwright`) — `tests/accessibility.spec.ts` runs it over
every rendered page and fails on broken markup (dangling labels, duplicate ids,
bad ARIA) or WCAG A/AA violations. It's just another spec, so it runs with
`pnpm exec playwright test`.

## How it wires up

`playwright.config.ts` owns the whole lifecycle; no external services need to be
started by hand:

- **`webServer`** boots **both tiers** (`support/config.ts` holds the ports and
  env): FastAPI via `uv run uvicorn app.main:app`, and the frontend via
  `pnpm exec vite dev` in `frontend/` with `API_PROXY_TARGET` pointed at the test
  API so `/api` is proxied there. Both are pointed at a dedicated `papertrail_test`
  database / throwaway `AUTH_SECRET`, log emails to the console, and skip the
  network breach check. Tests drive the **frontend origin** (`baseURL`); both
  servers are torn down when the run ends.
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
(they match the accessible React UI and survive markup changes):

```ts
import { expect, test } from "@playwright/test";

test("home greeting updates from the API", async ({ page }) => {
  await page.goto("/");                                    // baseURL is preset
  await expect(page.getByTestId("greeting")).toHaveText("Hello, world!"); // hydrated
  await page.getByLabel("Your name").fill("Ada");
  await expect(page.getByTestId("greeting")).toHaveText("Hello, Ada!");
});
```

Two things to know about the React UI:

- **Hydration.** The auth screens are client-rendered (`ssr: false`), so
  `getByLabel(...)` naturally waits for them to render before interacting. On the
  server-rendered home page, wait for a client-driven change (e.g. the greeting
  text) before typing, so the input's handlers are wired up.
- **Auth.** For a test that needs a session, log in with the seeded account from
  `support/credentials.ts` (see `tests/auth.spec.ts`) — the user is already
  verified, so no email-confirmation step is needed.
