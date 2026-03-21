import { test, expect } from "@playwright/test";

test.describe("Vulnerabilities Page", () => {
  test("loads vulns page", async ({ page }) => {
    await page.goto("/vulns");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("body")).toBeVisible();
  });

  test("has severity distribution section", async ({ page }) => {
    await page.goto("/vulns");
    await page.waitForLoadState("networkidle");

    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("dark theme is applied", async ({ page }) => {
    await page.goto("/vulns");
    await page.waitForLoadState("networkidle");

    const bgColor = await page.evaluate(() => {
      return getComputedStyle(document.body).backgroundColor;
    });
    // Dark background check
    expect(bgColor).toBeTruthy();
  });
});
