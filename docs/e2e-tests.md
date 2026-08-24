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
just test-e2e    # installs e2e deps, then runs the Playwright suite
```

`just test-e2e` runs `pnpm install --frozen-lockfile` then `pnpm exec playwright
test` in `e2e/`. To drive Playwright directly for the variants below, `cd e2e`
first.

Useful variants (all from `e2e/`):

```bash
pnpm exec playwright test --ui      # watch-mode UI runner (or: pnpm test:ui)
pnpm exec playwright test --debug   # step through with the inspector
pnpm exec playwright show-report    # open the last HTML report
pnpm exec tsc --noEmit              # type-check the specs (also: pnpm typecheck)
```

Or just open the **Testing** panel in VS Code: the extension discovers
`e2e/playwright.config.ts` and lets you run or debug individual tests inline.

The gate (`just check`) runs this exact recipe (`just test-e2e`) as its last step,
so a green local run means a green gate.

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
  API so `/api` is proxied there. The API is pointed at a dedicated
  `papertrail_test` database, so a run never touches the dev database. Tests drive
  the **frontend origin** (`baseURL`); both servers are torn down when the run ends.
- **The browser is the baked Chromium** at `/ms-playwright`
  (`PLAYWRIGHT_BROWSERS_PATH`, set in the devcontainer image). `@playwright/test`
  is pinned to the **same version** the Dockerfile bakes (`playwright==1.61.0`),
  so no browser is ever downloaded and the tests run offline. `just test-e2e`
  (and so `just check`, which calls it) fails before running anything if the
  Dockerfile pin and `e2e/package.json` drift — keep them in lockstep (and
  rebuild the devcontainer image when you bump the Dockerfile).

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

One thing to know about the React UI:

- **Hydration.** On a server-rendered page, wait for a client-driven change (e.g.
  the greeting text) before typing, so the input's handlers are wired up. A
  client-rendered route (`ssr: false`) needs no such care: `getByLabel(...)`
  naturally waits for it to render before interacting.
