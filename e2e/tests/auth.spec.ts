import { expect, test } from "@playwright/test";

import { E2E_EMAIL, E2E_PASSWORD } from "../support/credentials";

test("login and logout", async ({ page }) => {
  // The protected page bounces an anonymous visitor to sign in.
  await page.goto("/dashboard");
  await expect(page).toHaveURL("/login");

  // Sign in with the seeded, verified account.
  await page.getByLabel("Email").fill(E2E_EMAIL);
  await page.getByLabel("Password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL("/dashboard");
  await expect(page.getByText(E2E_EMAIL)).toBeVisible();

  // Logging out returns to the sign-in page.
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL("/login");
});
