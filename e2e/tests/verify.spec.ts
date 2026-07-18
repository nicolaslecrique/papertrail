import { expect, test } from "@playwright/test";

test("verify page explains a link with no token", async ({ page }) => {
  await page.goto("/verify");
  await expect(page.getByText(/missing its token/i)).toBeVisible();
});

test("verify page rejects an invalid token", async ({ page }) => {
  await page.goto("/verify?token=not-a-real-token");
  await expect(page.getByText(/invalid or has expired/i)).toBeVisible();
});
