// Shared configuration for the e2e run, imported by playwright.config.ts so the
// API server and the frontend server agree.
//
// Two servers run: FastAPI (the JSON API) and the TanStack Start frontend, which
// proxies /api to FastAPI so the browser sees a single origin. Tests drive the
// frontend origin.

export const API_PORT = 8123;
export const WEB_PORT = 3123;
export const API_URL = `http://127.0.0.1:${API_PORT}`;
export const BASE_URL = `http://127.0.0.1:${WEB_PORT}`;

// The test database. Defaults to the devcontainer's `db` service; CI overrides it
// via TEST_DATABASE_URL to point at its own Postgres (same override the pytest
// suite and `just check` already honour).
const TEST_DATABASE_URL =
  process.env.TEST_DATABASE_URL ??
  "postgresql://papertrail:papertrail@db:5432/papertrail_test";

// The API under test is pointed at a dedicated `papertrail_test` database, so a
// run never touches the dev database.
export const SERVER_ENV = {
  DATABASE_URL: TEST_DATABASE_URL,
} as const;
