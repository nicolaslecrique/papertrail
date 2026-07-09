// Shared configuration for the e2e run, imported by both playwright.config.ts
// and the global setup so the seeder and the app agree on the same database.

export const PORT = 8123;
export const BASE_URL = `http://127.0.0.1:${PORT}`;

// The app under test is pointed at a dedicated `papertrail_test` database and a
// throwaway auth secret, and logs (rather than sends) verification emails. These
// are passed to the uvicorn subprocess and to the Python seeder.
export const SERVER_ENV = {
  DATABASE_URL: "postgresql://papertrail:papertrail@db:5432/papertrail_test",
  AUTH_SECRET: "e2e-secret-not-for-production-0123456789",
  EMAIL_BACKEND: "console",
} as const;
