import { expect, test } from "@playwright/test";

test("forgot password shows a neutral confirmation", async ({ page }) => {
  // Neutral by design: it never reveals whether the address has an account.
  await page.goto("/forgot-password");
  await page.getByLabel("Email").fill("nobody@example.com");
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByText(/sent a reset link/i)).toBeVisible();
});

test("reset password rejects an invalid token", async ({ page }) => {
  await page.goto("/reset-password?token=not-a-real-token");
  await page.getByLabel("New password").fill("a-brand-new-passw0rd");
  await page.getByRole("button", { name: "Update password" }).click();
  await expect(page.getByText(/invalid or has expired/i)).toBeVisible();
});
