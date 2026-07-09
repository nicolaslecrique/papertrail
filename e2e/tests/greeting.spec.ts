import { expect, test } from "@playwright/test";

test("greeting swaps in via htmx", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Hello World" })).toBeVisible();
  await page.getByLabel("Your name").fill("Ada");
  await page.getByRole("button", { name: "Greet me" }).click();
  await expect(page.getByText("Hello, Ada!")).toBeVisible();
});
