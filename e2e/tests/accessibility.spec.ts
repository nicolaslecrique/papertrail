import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { E2E_EMAIL, E2E_PASSWORD } from "../support/credentials";

// A structural-HTML / accessibility gate for the rendered pages. axe-core catches
// the class of "dead markup" that static template linting can't see once the
// Jinja is rendered: labels pointing at controls that don't exist, duplicate ids,
// empty headings/buttons, broken ARIA references, and contrast failures. It runs
// against the real pages the app serves, so a regression in a macro or template
// surfaces here as a concrete violation rather than silently shipping.

// The anonymous pages, by URL. `/verify` with a bad token renders the
// "confirmation failed" branch of verify_result.html (its richest markup).
const ANON_PAGES = [
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password?token=example-token",
  "/verify?token=invalid-token",
];

// WCAG tags to enforce. Kept as the widely-adopted A/AA set so the gate is
// meaningful without chasing AAA rules that daisyUI doesn't target.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

for (const path of ANON_PAGES) {
  test(`no accessibility violations on ${path}`, async ({ page }) => {
    await page.goto(path);
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
  await expect(page).toHaveURL("/dashboard");

  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  expect(results.violations).toEqual([]);
});
