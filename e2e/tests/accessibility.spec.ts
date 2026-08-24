import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// An accessibility gate over the rendered React pages. axe-core catches the class
// of problems component snapshots miss: labels pointing at controls that don't
// exist, duplicate ids, empty headings/buttons, broken ARIA references, and
// contrast failures — on the real pages the app serves.

// Every page the app serves, by URL.
const PAGES = ["/"];

// WCAG tags to enforce: the widely-adopted A/AA set.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

for (const path of PAGES) {
  test(`no accessibility violations on ${path}`, async ({ page }) => {
    await page.goto(path);
    // Wait for the content to render into <main> before auditing (otherwise axe
    // can see an empty shell).
    await expect(page.locator("main")).not.toBeEmpty();
    const results = await new AxeBuilder({ page })
      .withTags(WCAG_TAGS)
      .analyze();
    expect(results.violations).toEqual([]);
  });
}
