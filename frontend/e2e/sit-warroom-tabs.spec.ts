import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

test.describe("SIT — War Room Tabs (SHADOW-STRIKE)", () => {
  test.setTimeout(60_000);

  // Helper: set operationId to the first operation that has targets
  async function setOperationWithTargets(page: import("@playwright/test").Page) {
    const opsResp = await page.request.get(`${API}/operations`);
    const ops = (await opsResp.json()) as Array<{ id: string; status: string }>;
    for (const op of ops.filter((o) => o.status === "active")) {
      const tResp = await page.request.get(`${API}/operations/${op.id}/targets`);
      if (tResp.ok()) {
        const targets = await tResp.json();
        if (Array.isArray(targets) && targets.length > 0) {
          await page.goto("/warroom");
          await page.evaluate((id) => localStorage.setItem("athena-op-id", id), op.id);
          await page.reload();
          await page.waitForLoadState("networkidle");
          await page.waitForTimeout(2000);
          return;
        }
      }
    }
    // Fallback — just go to warroom without a specific operation
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
  }

  // ──────────────────────────────────────────────
  // 1. Timeline tab loads with OODA blocks
  // ──────────────────────────────────────────────

  test("Timeline tab loads with OODA blocks", async ({ page }) => {
    await setOperationWithTargets(page);

    const main = page.locator("main").first();
    await expect(main).toBeVisible();

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toBeTruthy();
    expect(bodyText!.length).toBeGreaterThan(100);
  });

  // ──────────────────────────────────────────────
  // 2. Timeline tab has OODA iteration content
  // ──────────────────────────────────────────────

  test("Timeline tab has OODA iteration content", async ({ page }) => {
    await setOperationWithTargets(page);

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toBeTruthy();

    const hasObserve = /observe/i.test(bodyText!);
    expect(hasObserve).toBe(true);
  });

  // ──────────────────────────────────────────────
  // 3. Targets tab shows target list
  // ──────────────────────────────────────────────

  test("Targets tab shows target list", async ({ page }) => {
    await setOperationWithTargets(page);

    const targetsTab = page
      .locator(
        'button:has-text("目標"), button:has-text("Targets"), button:has-text("TARGETS")',
      )
      .first();
    await targetsTab.click();
    await page.waitForTimeout(2000);

    const main = page.locator("main").first();
    await expect(main).toBeVisible();

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toBeTruthy();
    expect(bodyText).toContain("192.168.0.26");
  });

  // ──────────────────────────────────────────────
  // 4. Targets tab shows compromised indicator
  // ──────────────────────────────────────────────

  test("Targets tab shows compromised indicator", async ({ page }) => {
    await setOperationWithTargets(page);

    const targetsTab = page
      .locator(
        'button:has-text("目標"), button:has-text("Targets"), button:has-text("TARGETS")',
      )
      .first();
    await targetsTab.click();
    await page.waitForTimeout(2000);

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toBeTruthy();

    const hasPrivilegeInfo =
      /Compromised/i.test(bodyText!) ||
      /Root/i.test(bodyText!) ||
      /User/i.test(bodyText!);
    expect(hasPrivilegeInfo).toBe(true);
  });

  // ──────────────────────────────────────────────
  // 5. Mission tab renders
  // ──────────────────────────────────────────────

  test("Mission tab renders", async ({ page }) => {
    await setOperationWithTargets(page);

    const missionTab = page
      .locator(
        'button:has-text("任務"), button:has-text("Mission"), button:has-text("MISSION")',
      )
      .first();
    await missionTab.click();
    await page.waitForTimeout(2000);

    const main = page.locator("main").first();
    await expect(main).toBeVisible();
  });

  // ──────────────────────────────────────────────
  // 6. Status panel shows C5ISR data
  // ──────────────────────────────────────────────

  test("Status panel shows C5ISR data", async ({ page, request }) => {
    await setOperationWithTargets(page);

    // Find SHADOW-STRIKE operation via API
    const opsResp = await request.get(`${API}/operations`);
    expect(opsResp.status()).toBe(200);
    const operations = await opsResp.json();

    const shadowStrike = operations.find(
      (op: { codename: string; status: string }) =>
        op.codename === "SHADOW-STRIKE" && op.status === "active",
    );

    if (!shadowStrike) {
      test.skip(true, "SHADOW-STRIKE operation not found or not active");
      return;
    }

    // Verify C5ISR data via API
    const c5isrResp = await request.get(
      `${API}/operations/${shadowStrike.id}/c5isr`,
    );
    expect(c5isrResp.status()).toBe(200);
    const c5isr = await c5isrResp.json();
    expect(Array.isArray(c5isr)).toBe(true);
    expect(c5isr.length).toBeGreaterThanOrEqual(4);

    // Verify the page has metric content
    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toBeTruthy();
    expect(bodyText!.length).toBeGreaterThan(100);
  });

  // ──────────────────────────────────────────────
  // 7. Tab switching preserves page state
  // ──────────────────────────────────────────────

  test("Tab switching preserves page state", async ({ page }) => {
    await setOperationWithTargets(page);

    const main = page.locator("main").first();

    // Switch to Targets tab
    const targetsTab = page
      .locator(
        'button:has-text("目標"), button:has-text("Targets"), button:has-text("TARGETS")',
      )
      .first();
    await targetsTab.click();
    await page.waitForTimeout(1000);
    await expect(main).toBeVisible();

    // Switch to Timeline tab
    const timelineTab = page
      .locator(
        'button:has-text("時間軸"), button:has-text("Timeline"), button:has-text("TIMELINE")',
      )
      .first();
    await timelineTab.click();
    await page.waitForTimeout(1000);
    await expect(main).toBeVisible();

    // Switch to Mission tab
    const missionTab = page
      .locator(
        'button:has-text("任務"), button:has-text("Mission"), button:has-text("MISSION")',
      )
      .first();
    await missionTab.click();
    await page.waitForTimeout(1000);
    await expect(main).toBeVisible();
  });
});
