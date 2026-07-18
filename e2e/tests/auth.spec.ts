import { expect, test } from "@playwright/test";

import { E2E_EMAIL, E2E_PASSWORD } from "../support/credentials";

test("sign in and sign out", async ({ page }) => {
  // The protected page bounces an anonymous visitor to sign in.
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);

  // Sign in with the seeded, verified account.
  await page.getByLabel("Email").fill(E2E_EMAIL);
  await page.getByLabel("Password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByTestId("user-email")).toContainText(E2E_EMAIL);

  // Signing out returns to the sign-in page and drops the session.
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});
