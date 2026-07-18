import { expect, test } from "@playwright/test";

test("home greeting updates from the API as you type", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "papertrail" }),
  ).toBeVisible();
  // The greeting is fetched from GET /api/greeting through the generated client.
  // Wait for the initial fetch to resolve (which also means the page has
  // hydrated) before typing, so the input's onChange is wired up.
  await expect(page.getByTestId("greeting")).toHaveText("Hello, world!");
  await page.getByLabel("Your name").fill("Ada");
  await expect(page.getByTestId("greeting")).toHaveText("Hello, Ada!");
});
