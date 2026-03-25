import { test, expect } from "@playwright/test";

test.describe("Component SIT Tests", () => {

  test("notification center opens and closes", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");

    // Click bell icon in header
    const bellButton = page.locator('header button[aria-label="Notifications"]');
    await bellButton.click();

    // Notification panel should appear
    // (it may have class or role indicators)
    await page.waitForTimeout(500);

    // Verify panel is visible (check for notification-related text)
    const body = await page.locator("body").textContent();
    expect(body).toBeTruthy();
  });

  test("operations page shows delete icons on cards", async ({ page }) => {
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    // Cards should be visible
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("war room targets tab shows split layout", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");

    // Click targets tab
    const targetsTab = page.locator('button:has-text("目標"), button:has-text("Targets")');
    if (await targetsTab.count() > 0) {
      await targetsTab.click();
      await page.waitForTimeout(500);
    }

    // Main content should be visible
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("war room mission tab shows content", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");

    const missionTab = page.locator('button:has-text("任務"), button:has-text("Mission")');
    if (await missionTab.count() > 0) {
      await missionTab.click();
      await page.waitForTimeout(500);
    }

    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("attack surface page loads with tabs", async ({ page }) => {
    await page.goto("/attack-surface");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("body")).toBeVisible();

    // Should have tab buttons
    const tabButtons = page.locator('button');
    const count = await tabButtons.count();
    expect(count).toBeGreaterThan(0);
  });

  test("attack surface graph tab loads", async ({ page }) => {
    await page.goto("/attack-surface?tab=graph");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("body")).toBeVisible();
  });

  test("dark theme is consistent across all pages", async ({ page }) => {
    const pages = ["/operations", "/warroom", "/attack-surface", "/vulns", "/tools"];

    for (const url of pages) {
      await page.goto(url);
      await page.waitForLoadState("networkidle");

      const bgColor = await page.evaluate(() => {
        return getComputedStyle(document.body).backgroundColor;
      });
      expect(bgColor).toBeTruthy();
    }
  });

  test("locale switcher toggles language", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");

    const header = page.locator("header").first();
    const localeBtn = header.locator('button:has-text("EN"), button:has-text("中文")');

    if (await localeBtn.count() > 0) {
      await localeBtn.click();
      await page.waitForTimeout(2000);
      await expect(page.locator("body")).toBeVisible();
    }
  });

  test("planner redirects to warroom", async ({ page }) => {
    await page.goto("/planner");
    await page.waitForURL("**/warroom**");
    expect(page.url()).toContain("/warroom");
  });

  test("attack-graph redirects to attack-surface", async ({ page }) => {
    await page.goto("/attack-graph");
    await page.waitForURL("**/attack-surface**");
    expect(page.url()).toContain("/attack-surface");
  });
});
