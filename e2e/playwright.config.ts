import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

import { API_PORT, API_URL, BASE_URL, SERVER_ENV, WEB_PORT } from "./support/config";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Seed the verified user (via the app's own UserManager) before any test runs.
  globalSetup: "./support/global-setup",
  // Boot both tiers: the FastAPI JSON API against the test database, and the
  // TanStack Start frontend (which proxies /api to that API via API_PROXY_TARGET).
  // Tests hit the frontend origin (BASE_URL).
  webServer: [
    {
      command: `uv run uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: repoRoot,
      url: `${API_URL}/openapi.json`,
      reuseExistingServer: false,
      timeout: 60_000,
      stdout: "pipe",
      stderr: "pipe",
      env: { ...process.env, ...SERVER_ENV },
    },
    {
      // --host 127.0.0.1 so it binds IPv4 (matches the URL Playwright waits on).
      command: `pnpm exec vite dev --host 127.0.0.1 --port ${WEB_PORT}`,
      cwd: resolve(repoRoot, "frontend"),
      url: BASE_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: { ...process.env, API_PROXY_TARGET: API_URL },
    },
  ],
});
