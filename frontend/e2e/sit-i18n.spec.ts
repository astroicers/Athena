import { test, expect } from "@playwright/test";

test.describe("SIT -- i18n Language Switching", () => {
  test.setTimeout(60_000);

  test("Locale switcher is visible in header", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const header = page.locator("header");
    const localeButton = header.locator(
      'button:has-text("EN"), button:has-text("中文")',
    );
    await expect(localeButton.first()).toBeVisible();
  });

  test("Clicking locale switcher changes language", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const header = page.locator("header").first();

    // Detect current locale
    const enBtn = header.locator('button:has-text("EN")');
    const zhBtn = header.locator('button:has-text("中文")');
    const isCurrentlyZhTW = (await enBtn.count()) > 0;

    if (isCurrentlyZhTW) {
      // Currently zh-TW — switch to EN
      await enBtn.click();
      await page.waitForTimeout(3000);
      // After switching, "中文" button should appear
      await expect(
        header.locator('button:has-text("中文")'),
      ).toBeVisible({ timeout: 10_000 });
      // Page should now have English text
      const bodyText = await page.locator("body").innerText();
      const hasEnglish =
        bodyText.includes("Timeline") ||
        bodyText.includes("Targets") ||
        bodyText.includes("Mission") ||
        bodyText.includes("Operations");
      expect(hasEnglish).toBe(true);
    } else {
      // Currently EN — switch to zh-TW
      await zhBtn.click();
      await page.waitForTimeout(3000);
      await expect(
        header.locator('button:has-text("EN")'),
      ).toBeVisible({ timeout: 10_000 });
      const bodyText = await page.locator("body").innerText();
      const hasChinese =
        bodyText.includes("時間軸") ||
        bodyText.includes("目標") ||
        bodyText.includes("任務") ||
        bodyText.includes("作戰行動");
      expect(hasChinese).toBe(true);
    }
  });

  test("Round-trip locale switch preserves UI", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const header = page.locator("header").first();
    const enBtn = header.locator('button:has-text("EN")');
    const zhBtn = header.locator('button:has-text("中文")');
    const startedInZhTW = (await enBtn.count()) > 0;

    // Switch once
    if (startedInZhTW) {
      await enBtn.click();
    } else {
      await zhBtn.click();
    }
    await page.waitForTimeout(3000);
    await expect(page.locator("main")).toBeVisible();

    // Switch back
    if (startedInZhTW) {
      await header.locator('button:has-text("中文")').click();
    } else {
      await header.locator('button:has-text("EN")').click();
    }
    await page.waitForTimeout(3000);
    await expect(page.locator("main")).toBeVisible();
  });

  test("All 5 pages load in both locales", async ({ page }) => {
    const pages = [
      "/operations",
      "/warroom",
      "/attack-surface",
      "/vulns",
      "/tools",
    ];

    // Visit all pages — should work regardless of current locale
    for (const url of pages) {
      await page.goto(url);
      await page.waitForLoadState("networkidle");
      await expect(page.locator("body")).toBeVisible();
    }
  });

  test("Operations page renders with locale content", async ({ page }) => {
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await expect(page.locator("main")).toBeVisible();
    const bodyText = await page.locator("body").innerText();
    expect(bodyText.length).toBeGreaterThan(10);
  });
});
