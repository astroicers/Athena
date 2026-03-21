import { test, expect } from "@playwright/test";

test.describe("Locale Switcher", () => {
  test("locale switcher is visible in header", async ({ page }) => {
    await page.goto("/planner");
    await page.waitForLoadState("networkidle");

    // The global header should be visible
    const header = page.locator("header").first();
    await expect(header).toBeVisible();

    // Look for the locale button — text will be "EN" or "中文"
    const localeButton = header.locator('button:has-text("EN"), button:has-text("中文")');
    await expect(localeButton).toBeVisible();
  });

  test("clicking switches language", async ({ page }) => {
    await page.goto("/planner");
    await page.waitForLoadState("networkidle");

    const header = page.locator("header").first();

    // Determine the current locale label
    const enButton = header.locator('button:has-text("EN")');
    const zhButton = header.locator('button:has-text("中文")');

    const isCurrentlyZhTW = (await enButton.count()) > 0; // "EN" shown means current locale is zh-TW

    if (isCurrentlyZhTW) {
      // Click "EN" to switch to English
      await enButton.click();
      // After switching, the button should now show "中文" (indicating locale is now en)
      await expect(header.locator('button:has-text("中文")')).toBeVisible({ timeout: 10_000 });
    } else {
      // Click "中文" to switch to Chinese
      await zhButton.click();
      // After switching, the button should now show "EN" (indicating locale is now zh-TW)
      await expect(header.locator('button:has-text("EN")')).toBeVisible({ timeout: 10_000 });
    }
  });
});
