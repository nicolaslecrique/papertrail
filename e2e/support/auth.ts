import { expect, type Page } from "@playwright/test";

import { E2E_EMAIL, E2E_PASSWORD } from "./credentials";

/**
 * Sign in with the seeded, verified account and wait for the dashboard.
 *
 * Shared by the specs that need an authenticated session so the login steps live
 * in one place (see tests/auth.spec.ts and tests/accessibility.spec.ts).
 */
export async function signIn(
  page: Page,
  email: string = E2E_EMAIL,
  password: string = E2E_PASSWORD,
): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}
