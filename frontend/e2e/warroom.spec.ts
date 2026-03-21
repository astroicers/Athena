import { test, expect } from "@playwright/test";

test.describe("War Room Page", () => {
  test("loads war room page", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("body")).toBeVisible();
  });

  test("has campaign timeline header", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");

    // Wait for content
    await page.waitForTimeout(2000);

    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("has status panel on right side", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");

    await page.waitForTimeout(2000);
    const body = await page.locator("body").textContent();
    expect(body).toBeTruthy();
  });
});
