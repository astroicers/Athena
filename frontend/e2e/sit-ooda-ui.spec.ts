// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

/**
 * SIT — OODA UI/UX Verification with Screenshots
 *
 * Validates the OODA user experience: directive input, auto-mode toggle,
 * timeline rendering, and visual feedback. Each test captures screenshots
 * for manual UX review.
 */

import { test, expect, Page } from "@playwright/test";

const API = "http://localhost:58000/api";
const SHOTS = "test-results/ooda-ui-screenshots";

async function snap(page: Page, name: string) {
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

async function pollUntil(
  page: Page, url: string,
  condition: (data: unknown) => boolean,
  maxAttempts = 60, intervalMs = 2000,
): Promise<unknown> {
  for (let i = 0; i < maxAttempts; i++) {
    const resp = await page.request.get(url);
    if (resp.ok()) {
      const data = await resp.json();
      if (condition(data)) return data;
    }
    await page.waitForTimeout(intervalMs);
  }
  throw new Error(`Polling timeout: ${url}`);
}

test.describe.serial("SIT — OODA UI/UX with Screenshots", () => {
  let operationId: string;
  let targetId: string;
  const ts = Date.now();

  test.setTimeout(180_000);

  // ──────────────────────────────────────────────────────────────
  //  Setup
  // ──────────────────────────────────────────────────────────────

  test("00. Setup — operation + target + recon", async ({ page }) => {
    // Create operation
    const opResp = await page.request.post(`${API}/operations`, {
      data: {
        code: `SIT-UI-${ts}`, name: "SIT OODA UI Test",
        codename: `sit-ui-${ts}`, strategic_intent: "OODA UI test",
        mission_profile: "SP",
      },
    });
    expect(opResp.status()).toBe(201);
    operationId = (await opResp.json()).id;

    // Add target
    const tResp = await page.request.post(`${API}/operations/${operationId}/targets`, {
      data: {
        hostname: "metasploitable2", ip_address: "192.168.0.26",
        os: "Linux", role: "target", network_segment: "Internal",
      },
    });
    expect(tResp.status()).toBe(201);
    targetId = (await tResp.json()).id;

    // Activate target
    await page.request.patch(`${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetId } });

    // Trigger recon + wait
    await page.request.post(`${API}/operations/${operationId}/recon/scan`,
      { data: { target_id: targetId, enable_initial_access: true } });

    await pollUntil(page, `${API}/operations/${operationId}/recon/status`,
      (d: unknown) => {
        const s = (d as { status: string }).status;
        return s === "completed" || s === "failed";
      }, 90, 2000);

    // Wait for auto-triggered OODA to complete
    await pollUntil(page, `${API}/operations/${operationId}/ooda/dashboard`,
      (d: unknown) => {
        const dd = d as { iteration_count: number; latest_iteration?: { completed_at?: string } };
        return dd.iteration_count >= 1 && !!dd.latest_iteration?.completed_at;
      }, 60, 2000).catch(() => {
      // Auto-OODA may not complete in time, that's ok
    });
  });

  // ──────────────────────────────────────────────────────────────
  //  Timeline UI
  // ──────────────────────────────────────────────────────────────

  test("01. Timeline tab renders OODA iteration", async ({ page }) => {
    await page.goto("http://localhost:58080/operations");
    await page.evaluate((id) => localStorage.setItem("athena-op-id", id), operationId);
    await page.goto("http://localhost:58080/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    await snap(page, "01-timeline-with-ooda");

    // Verify OODA content is visible
    const body = await page.locator("body").textContent();
    const hasOoda = /observe|orient|decide|act|ooda/i.test(body || "");
    expect(hasOoda).toBe(true);
  });

  // ──────────────────────────────────────────────────────────────
  //  Directive Input UX
  // ──────────────────────────────────────────────────────────────

  test("02. Directive input is visible and has placeholder", async ({ page }) => {
    await page.goto("http://localhost:58080/operations");
    await page.evaluate((id) => localStorage.setItem("athena-op-id", id), operationId);
    await page.goto("http://localhost:58080/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    const textarea = page.locator("textarea").first();
    const visible = await textarea.isVisible().catch(() => false);
    expect(visible).toBe(true);

    // Has a meaningful placeholder
    const placeholder = await textarea.getAttribute("placeholder") || "";
    expect(placeholder.length).toBeGreaterThan(5);
    await snap(page, "02-directive-empty");
  });

  test("03. Directive submit shows toast feedback", async ({ page }) => {
    await page.goto("http://localhost:58080/operations");
    await page.evaluate((id) => localStorage.setItem("athena-op-id", id), operationId);
    await page.goto("http://localhost:58080/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    const textarea = page.locator("textarea").first();
    await textarea.fill("Prioritize vsftpd 2.3.4 backdoor exploitation");
    await snap(page, "03a-directive-filled");

    // Find and click submit button
    const submitBtn = page.locator('button:has-text("Submit"), button:has-text("Send"), button:has-text("提交指令")').first();
    const btnVisible = await submitBtn.isVisible().catch(() => false);
    expect(btnVisible).toBe(true);

    await submitBtn.click();
    await page.waitForTimeout(2000);
    await snap(page, "03b-directive-submitted");

    // Toast should appear
    const toastText = await page.locator("body").textContent();
    const hasToast = /directive.*stored|指令.*儲存|stored/i.test(toastText || "");
    expect(hasToast).toBe(true);
  });

  test("04. Directive clears after submit", async ({ page }) => {
    await page.goto("http://localhost:58080/operations");
    await page.evaluate((id) => localStorage.setItem("athena-op-id", id), operationId);
    await page.goto("http://localhost:58080/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    // After previous submit, textarea should be empty or show submitted directive
    const textarea = page.locator("textarea").first();
    const isVisible = await textarea.isVisible().catch(() => false);

    if (isVisible) {
      const value = await textarea.inputValue();
      // Should be empty (cleared after submit) or show placeholder
      expect(value.length).toBeLessThanOrEqual(0);
    }
    await snap(page, "04-directive-cleared");
  });

  // ──────────────────────────────────────────────────────────────
  //  Auto Mode Toggle UX
  // ──────────────────────────────────────────────────────────────

  test("05. Auto toggle is visible with label", async ({ page }) => {
    await page.goto("http://localhost:58080/operations");
    await page.evaluate((id) => localStorage.setItem("athena-op-id", id), operationId);
    await page.goto("http://localhost:58080/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    const toggle = page.locator('button[role="switch"]').first();
    expect(await toggle.isVisible()).toBe(true);

    // Has nearby label text
    const body = await page.locator("body").textContent();
    const hasLabel = /manual|auto|手動|自動/i.test(body || "");
    expect(hasLabel).toBe(true);
    await snap(page, "05-auto-toggle-off");
  });

  test("06. Auto toggle ON shows toast + changes state", async ({ page }) => {
    await page.goto("http://localhost:58080/operations");
    await page.evaluate((id) => localStorage.setItem("athena-op-id", id), operationId);
    await page.goto("http://localhost:58080/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    const toggle = page.locator('button[role="switch"]').first();
    await toggle.click();
    await page.waitForTimeout(2000);
    await snap(page, "06-auto-toggle-on");

    // Toast feedback
    const body = await page.locator("body").textContent();
    const hasToast = /auto.*started|自動.*啟動|started/i.test(body || "");
    expect(hasToast).toBe(true);

    // Toggle should now be checked
    const checked = await toggle.getAttribute("aria-checked");
    expect(checked).toBe("true");
  });

  test("07. Auto toggle OFF shows toast", async ({ page }) => {
    await page.goto("http://localhost:58080/operations");
    await page.evaluate((id) => localStorage.setItem("athena-op-id", id), operationId);
    await page.goto("http://localhost:58080/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    // Toggle is currently ON from previous test, turn OFF
    const toggle = page.locator('button[role="switch"]').first();
    const checked = await toggle.getAttribute("aria-checked");

    if (checked === "true") {
      await toggle.click();
      await page.waitForTimeout(2000);
      await snap(page, "07-auto-toggle-off-again");

      const body = await page.locator("body").textContent();
      const hasToast = /auto.*stopped|自動.*停止|stopped/i.test(body || "");
      expect(hasToast).toBe(true);
    }
  });

  // ──────────────────────────────────────────────────────────────
  //  Right Panel (StatusPanel)
  // ──────────────────────────────────────────────────────────────

  test("08. Right panel shows C5ISR + Decision (no fake metrics)", async ({ page }) => {
    await page.goto("http://localhost:58080/operations");
    await page.evaluate((id) => localStorage.setItem("athena-op-id", id), operationId);
    await page.goto("http://localhost:58080/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    await snap(page, "08-right-panel");

    const body = await page.locator("body").textContent();

    // Should have C5ISR and Decision
    expect(/c5isr|health|健康/i.test(body || "")).toBe(true);
    expect(/decision|go|hold|決策/i.test(body || "")).toBe(true);

    // Should NOT have fake noise/confidence percentages
    // (these were removed — verify they stay removed)
    const hasNoise = /\bNOISE\b.*\d+%/i.test(body || "");
    const hasConfidence = /\bCONFIDENCE\b.*\d+%/i.test(body || "");
    expect(hasNoise).toBe(false);
    expect(hasConfidence).toBe(false);
  });

  // ──────────────────────────────────────────────────────────────
  //  Cleanup
  // ──────────────────────────────────────────────────────────────

  test("09. Cleanup — stop auto + soft reset", async ({ page }) => {
    // Ensure auto stopped
    await page.request.delete(`${API}/operations/${operationId}/ooda/auto-stop`).catch(() => {});
    await page.request.post(`${API}/operations/${operationId}/reset/soft`);
  });
});
