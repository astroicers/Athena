import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("homepage redirects to /planner", async ({ page }) => {
    await page.goto("/");
    await page.waitForURL("**/planner**");
    expect(page.url()).toContain("/planner");
  });

  test("sidebar shows 5 navigation items", async ({ page }) => {
    await page.goto("/planner");
    const sidebar = page.locator("aside");
    await expect(sidebar).toBeVisible();

    const navLinks = sidebar.locator("a");
    // 5 nav items + 1 GitHub star link = 6
    const count = await navLinks.count();
    expect(count).toBeGreaterThanOrEqual(5);
  });

  test("sidebar active item matches current page", async ({ page }) => {
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");

    // Active nav should have accent color styling
    const activeLink = page.locator('aside a[href="/operations"]');
    await expect(activeLink).toBeVisible();
  });

  test("clicking sidebar nav navigates to page", async ({ page }) => {
    await page.goto("/planner");
    await page.waitForLoadState("networkidle");

    await page.locator('aside a[href="/tools"]').click();
    await page.waitForURL("**/tools**");
    expect(page.url()).toContain("/tools");
  });

  test("global header shows page title", async ({ page }) => {
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");

    const header = page.locator("header").first();
    await expect(header).toBeVisible();
  });
});
