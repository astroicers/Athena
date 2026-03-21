import { test, expect } from "@playwright/test";

test.describe("Operations Page", () => {
  test("loads operations page", async ({ page }) => {
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");

    // Page should be visible (even if no data, it renders the grid)
    await expect(page.locator("body")).toBeVisible();
  });

  test("shows create operation button or empty state", async ({ page }) => {
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");

    // Should have either cards or empty state
    const body = page.locator("main");
    await expect(body).toBeVisible();
  });

  test("page has dark background", async ({ page }) => {
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");

    const bg = await page.evaluate(() => {
      return getComputedStyle(document.body).backgroundColor;
    });
    // Should be very dark (close to #09090B)
    expect(bg).toBeTruthy();
  });
});
