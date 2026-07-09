import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

import { BASE_URL, PORT, SERVER_ENV } from "./support/config";

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
  // Boot the real FastAPI app against the test database. The `/` page renders
  // without touching the database, so the readiness check never races the schema.
  webServer: {
    command: `uv run uvicorn app.main:app --host 127.0.0.1 --port ${PORT}`,
    cwd: repoRoot,
    url: `${BASE_URL}/`,
    reuseExistingServer: false,
    timeout: 60_000,
    stdout: "pipe",
    stderr: "pipe",
    env: { ...process.env, ...SERVER_ENV },
  },
});
