import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { E2E_EMAIL, E2E_PASSWORD } from "../support/credentials";

// An accessibility gate over the rendered React pages. axe-core catches the class
// of problems component snapshots miss: labels pointing at controls that don't
// exist, duplicate ids, empty headings/buttons, broken ARIA references, and
// contrast failures — on the real pages the app serves.

// The anonymous pages, by URL. `/verify` and `/reset-password` are given tokens so
// they render their token-driven branches.
const ANON_PAGES = [
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password?token=example-token",
  "/verify?token=invalid-token",
];

// WCAG tags to enforce: the widely-adopted A/AA set.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

for (const path of ANON_PAGES) {
  test(`no accessibility violations on ${path}`, async ({ page }) => {
    await page.goto(path);
    // The auth screens are client-rendered, so wait for the content to render
    // into <main> before auditing (otherwise axe sees an empty shell).
    await expect(page.locator("main")).not.toBeEmpty();
    const results = await new AxeBuilder({ page })
      .withTags(WCAG_TAGS)
      .analyze();
    expect(results.violations).toEqual([]);
  });
}

test("no accessibility violations on the dashboard", async ({ page }) => {
  // The dashboard is behind auth, so sign in with the seeded user first.
  await page.goto("/login");
  await page.getByLabel("Email").fill(E2E_EMAIL);
  await page.getByLabel("Password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  expect(results.violations).toEqual([]);
});
