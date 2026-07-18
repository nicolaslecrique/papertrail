import { expect, test } from "@playwright/test";

import { signIn } from "../support/auth";
import { E2E_EMAIL } from "../support/credentials";

test("sign in and sign out", async ({ page }) => {
  // The protected page bounces an anonymous visitor to sign in.
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);

  // Sign in with the seeded, verified account.
  await signIn(page);
  await expect(page.getByTestId("user-email")).toContainText(E2E_EMAIL);

  // Signing out returns to the sign-in page and drops the session.
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});
