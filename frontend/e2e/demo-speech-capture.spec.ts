// Demo Speech Capture — produces all演講 screenshots in one run
// Run: npx playwright test e2e/demo-speech-capture.spec.ts --headed

import { test, expect, type Page } from "@playwright/test";

const API = "http://localhost:58000/api";
const SHOTS = "test-results/demo-speech";

async function snap(page: Page, name: string) {
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

async function pollUntil(
  page: Page, url: string, condition: (d: unknown) => boolean,
  maxAttempts = 150, intervalMs = 2000,
): Promise<unknown> {
  for (let i = 0; i < maxAttempts; i++) {
    const resp = await page.request.get(url);
    if (resp.ok()) { const d = await resp.json(); if (condition(d)) return d; }
    await page.waitForTimeout(intervalMs);
  }
  return null;
}

test.describe.serial("Demo Speech Capture", () => {
  let operationId: string;
  let targetId: string;
  const ts = Date.now();

  test.setTimeout(600_000);

  test("01. Operations page — create new operation", async ({ page }) => {
    await page.goto("http://localhost:58080/operations");
    await page.waitForTimeout(2000);
    await snap(page, "01-operations-page");

    // Create via API
    const opResp = await page.request.post(`${API}/operations`, {
      data: {
        code: `DEMO-${ts}`,
        name: "Demo: AI-Driven Pentest",
        codename: "IRON-TEMPEST",
        strategic_intent: "Demonstrate OODA-driven autonomous penetration testing with session continuity",
        mission_profile: "SP",
      },
    });
    expect(opResp.status()).toBe(201);
    operationId = (await opResp.json()).id;
  });

  test("02. War Room — empty state (new operation)", async ({ page }) => {
    await page.goto("http://localhost:58080/warroom");
    await page.evaluate((id) => { localStorage.setItem("athena-op-id", id); }, operationId);
    await page.reload();
    await page.waitForTimeout(2000);
    await snap(page, "02-warroom-empty");
  });

  test("03. Add target — 192.168.0.26 (metasploitable2)", async ({ page }) => {
    const tResp = await page.request.post(`${API}/operations/${operationId}/targets`, {
      data: {
        hostname: "metasploitable2",
        ip_address: "192.168.0.26",
        os: "Linux",
        role: "target",
        network_segment: "Internal",
      },
    });
    expect(tResp.status()).toBe(201);
    targetId = (await tResp.json()).id;

    await page.request.patch(`${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetId } });

    await page.goto("http://localhost:58080/warroom");
    await page.evaluate((id) => { localStorage.setItem("athena-op-id", id); }, operationId);
    await page.reload();
    await page.waitForTimeout(1500);
    await snap(page, "03-target-added");
  });

  test("04. Wait for OODA auto-cycle + capture Timeline", async ({ page }) => {
    // Target creation auto-triggers OODA; manual fallback
    await page.waitForTimeout(10_000);
    const dash = await page.request.get(`${API}/operations/${operationId}/ooda/dashboard`);
    const d = (await dash.json()) as { iteration_count?: number };
    if ((d.iteration_count ?? 0) < 1) {
      await page.request.post(`${API}/operations/${operationId}/ooda/trigger`);
    }
    await pollUntil(page, `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => ((data as { iteration_count?: number }).iteration_count ?? 0) >= 1);

    // Also wait for brief to be generated
    await pollUntil(page, `${API}/operations/${operationId}/brief`,
      (data: unknown) => !!(data as { markdown?: string }).markdown,
      60, 2000);

    await page.goto("http://localhost:58080/warroom");
    await page.evaluate((id) => { localStorage.setItem("athena-op-id", id); }, operationId);
    await page.reload();
    await page.waitForTimeout(2000);
    await snap(page, "04-timeline-after-ooda");
  });

  test("05. Brief Tab — auto-generated MD report", async ({ page }) => {
    await page.goto("http://localhost:58080/warroom");
    await page.evaluate((id) => { localStorage.setItem("athena-op-id", id); }, operationId);
    await page.reload();
    await page.waitForTimeout(1500);

    // Click Brief tab
    const briefTab = page.getByText("BRIEF", { exact: false }).first();
    await briefTab.click();
    await page.waitForTimeout(2000);
    await snap(page, "05-brief-tab");
  });

  test("06. Brief API — verify markdown content", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations/${operationId}/brief`);
    const data = (await resp.json()) as { markdown: string; updated_at: string };

    // Save the full markdown to a file for演講 demo
    const fs = require("fs");
    fs.mkdirSync(SHOTS, { recursive: true });
    fs.writeFileSync(`${SHOTS}/OPERATION_BRIEF.md`, data.markdown);

    expect(data.markdown.length).toBeGreaterThan(0);
    expect(data.updated_at).toBeTruthy();
  });

  test("07. Mode toggle — Autonomous", async ({ page }) => {
    await page.goto("http://localhost:58080/warroom");
    await page.evaluate((id) => { localStorage.setItem("athena-op-id", id); }, operationId);
    await page.reload();
    await page.waitForTimeout(1500);

    // Click Autonomous in ModeControl
    const autoBtn = page.getByText("Autonomous", { exact: true }).first();
    if (await autoBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await autoBtn.click();
      await page.waitForTimeout(1500);
      // Dismiss confirm if exists
      const confirmBtn = page.getByRole("button", { name: /confirm/i }).first();
      if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await confirmBtn.click();
        await page.waitForTimeout(1500);
      }
    }
    await snap(page, "07-autonomous-mode");

    // Stop auto
    await page.request.delete(`${API}/operations/${operationId}/ooda/auto-stop`).catch(() => {});
  });

  test("08. Tools page — MCP servers", async ({ page }) => {
    await page.goto("http://localhost:58080/tools");
    await page.waitForTimeout(2000);
    await snap(page, "08-tools-registry");
  });

  test("09. Attack Surface", async ({ page }) => {
    await page.goto(`http://localhost:58080/attack-surface?operation=${operationId}`);
    await page.waitForTimeout(2000);
    await snap(page, "09-attack-surface");
  });

  test("99. Cleanup", async ({ page }) => {
    await page.request.post(`${API}/operations/${operationId}/reset`);
  });
});
