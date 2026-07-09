import { execFileSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { SERVER_ENV } from "./config";
import { E2E_EMAIL, E2E_PASSWORD } from "./credentials";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

/**
 * Seed the test database with one active, verified user before the suite runs.
 *
 * Delegates to a small Python script that reuses the app's own `UserManager`, so
 * the password is hashed exactly as the real registration flow would hash it.
 * `execFileSync` throws on a non-zero exit, which fails the whole run loudly.
 */
export default function globalSetup(): void {
  execFileSync("uv", ["run", "python", "scripts/e2e_seed.py"], {
    cwd: repoRoot,
    stdio: "inherit",
    env: {
      ...process.env,
      ...SERVER_ENV,
      // Running a script file only puts scripts/ on sys.path; add the repo root
      // so the seeder can `import app`.
      PYTHONPATH: ".",
      E2E_USER_EMAIL: E2E_EMAIL,
      E2E_USER_PASSWORD: E2E_PASSWORD,
    },
  });
}
