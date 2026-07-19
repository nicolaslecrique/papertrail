// Shared configuration for the e2e run, imported by playwright.config.ts and the
// global setup so the API server, the frontend server, and the seeder all agree.
//
// Two servers run: FastAPI (the JSON API) and the TanStack Start frontend, which
// proxies /api to FastAPI so the browser sees a single origin (the httponly auth
// cookie stays first-party). Tests drive the frontend origin.

export const API_PORT = 8123;
export const WEB_PORT = 3123;
export const API_URL = `http://127.0.0.1:${API_PORT}`;
export const BASE_URL = `http://127.0.0.1:${WEB_PORT}`;

// The test database. Defaults to the devcontainer's `db` service; CI overrides it
// via TEST_DATABASE_URL to point at its own Postgres (same override the pytest
// suite and check.sh already honour).
const TEST_DATABASE_URL =
  process.env.TEST_DATABASE_URL ??
  "postgresql://papertrail:papertrail@db:5432/papertrail_test";

// The API under test is pointed at a dedicated `papertrail_test` database and a
// throwaway auth secret, logs (rather than sends) emails, and skips the network
// breach check so the run is fully offline. `BASE_URL` is the origin the emailed
// verification / reset links point at (the frontend app).
export const SERVER_ENV = {
  DATABASE_URL: TEST_DATABASE_URL,
  AUTH_SECRET: "e2e-secret-not-for-production-0123456789",
  EMAIL_BACKEND: "console",
  PWNED_CHECK_ENABLED: "false",
  BASE_URL,
} as const;
