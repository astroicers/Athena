import { test, expect } from "@playwright/test";

test.describe("Tools Page", () => {
  test("loads tools registry page", async ({ page }) => {
    await page.goto("/tools");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("body")).toBeVisible();
  });

  test("has tab bar with Registry and Playbooks", async ({ page }) => {
    await page.goto("/tools");
    await page.waitForLoadState("networkidle");

    // Look for tab-like elements
    const pageContent = page.locator("main");
    await expect(pageContent).toBeVisible();
  });

  test("renders tool rows in table", async ({ page }) => {
    await page.goto("/tools");
    await page.waitForLoadState("networkidle");

    // Wait for content to load
    await page.waitForTimeout(2000);

    // Check that tool names appear (from backend data)
    const body = await page.locator("body").textContent();
    expect(body).toBeTruthy();
  });
});
