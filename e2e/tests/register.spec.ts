import { expect, test } from "@playwright/test";

const PASSWORD = "sup3r-secret-pw-123";

async function register(
  page: import("@playwright/test").Page,
  email: string,
): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
}

test("registration shows a neutral check-your-inbox message", async ({
  page,
}) => {
  await register(page, `e2e-reg-${Date.now().toString()}@example.com`);
  await expect(page.getByText(/check your inbox/i)).toBeVisible();
});

test("cannot sign in before confirming the email", async ({ page }) => {
  const email = `e2e-unverified-${Date.now().toString()}@example.com`;
  await register(page, email);
  await expect(page.getByText(/check your inbox/i)).toBeVisible();

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText(/confirm your email/i)).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});
