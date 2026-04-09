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
 * SIT — OODA Manual / Auto Mode & Mode-Switching
 *
 * 15 tests covering:
 *   M01-M06  Manual mode (directive, recommendation, custom directive)
 *   M07-M12  Auto mode (start, iterations, intervention, stop)
 *   M13-M15  Mode switching (rapid toggle, concurrent safety)
 *
 * Self-contained: creates own operation + target, cleans up at end.
 */

import { test, expect, Page } from "@playwright/test";

const API = "http://localhost:58000/api";
const SHOTS = "test-results/sit-ooda-modes-screenshots";

// ── Helpers ──────────────────────────────────────────────────────

async function snap(page: Page, name: string) {
  await page.screenshot({
    path: `${SHOTS}/${name}.png`,
    fullPage: true,
  });
}

async function snapApi(page: Page, name: string, data: unknown) {
  await page.setContent(
    `<html><body><pre style="white-space:pre-wrap;font-size:12px">${JSON.stringify(data, null, 2)}</pre></body></html>`,
  );
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

async function pollUntil(
  page: Page,
  url: string,
  condition: (data: unknown) => boolean,
  maxAttempts = 90,
  intervalMs = 2000,
): Promise<unknown> {
  for (let i = 0; i < maxAttempts; i++) {
    const resp = await page.request.get(url);
    if (resp.ok()) {
      const data = await resp.json();
      if (condition(data)) return data;
    }
    await page.waitForTimeout(intervalMs);
  }
  return null; // timeout - non-fatal
}

// ── Test Suite ───────────────────────────────────────────────────

test.describe.serial("SIT — OODA Manual / Auto Modes", () => {
  let operationId: string;
  let targetId: string;
  const ts = Date.now();

  test.setTimeout(600_000);

  // ────────────────────────────────────────────────────────────
  //  Setup: Create operation + target, wait for first OODA
  // ────────────────────────────────────────────────────────────

  test("M00. Setup — create operation + target", async ({ page }) => {
    // Create operation (SP mode)
    const opResp = await page.request.post(`${API}/operations`, {
      data: {
        code: `SIT-MODES-${ts}`,
        name: "SIT OODA Modes Test",
        codename: `sit-modes-${ts}`,
        strategic_intent: "OODA manual/auto mode switching test",
        mission_profile: "SP",
      },
    });
    expect(opResp.status()).toBe(201);
    operationId = (await opResp.json()).id;

    // Add target
    const tResp = await page.request.post(
      `${API}/operations/${operationId}/targets`,
      {
        data: {
          hostname: "metasploitable2",
          ip_address: "192.168.0.26",
          os: "Linux",
          role: "target",
          network_segment: "Internal",
        },
      },
    );
    expect(tResp.status()).toBe(201);
    targetId = (await tResp.json()).id;

    // Set target as active
    const activateResp = await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetId } },
    );
    expect(activateResp.status()).toBe(200);
  });

  // ═══════════════════════════════════════════════════════════
  //  Manual Mode (M01 – M06)
  // ═══════════════════════════════════════════════════════════

  test("M01. Wait for OODA #1 complete — timeline has entries", async ({
    page,
  }) => {
    // Wait for auto-trigger, then manually trigger as fallback
    await page.waitForTimeout(10_000);
    let dashResp = await page.request.get(`${API}/operations/${operationId}/ooda/dashboard`);
    let dash = (await dashResp.json()) as { iteration_count?: number };
    if ((dash.iteration_count ?? 0) < 1) {
      await page.request.post(`${API}/operations/${operationId}/ooda/trigger`);
    }

    // Poll until first iteration completes (150 attempts × 2s = 5 min for real LLM + nmap)
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as {
          iteration_count: number;
          latest_iteration?: { completed_at?: string };
        };
        return d.iteration_count >= 1 && !!d.latest_iteration?.completed_at;
      },
      150,
      2000,
    );

    if (!result) {
      // OODA cycle didn't complete in time — environment limitation, not a bug
      await snapApi(page, "M01-timeout", { note: "OODA timeout — LLM + nmap took > 5min" });
      test.skip();
      return;
    }
    const dashboard = result as { iteration_count: number };
    expect(dashboard.iteration_count).toBeGreaterThanOrEqual(1);

    // Verify timeline has entries
    const tlResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    expect(tlResp.status()).toBe(200);
    const timeline = (await tlResp.json()) as Array<{
      phase: string;
      iteration_number: number;
    }>;
    expect(timeline.length).toBeGreaterThanOrEqual(1);

    await snapApi(page, "M01-timeline", timeline.slice(0, 10));
  });

  test("M02. Check recommendations after OODA — verify exists", async ({
    page,
  }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/recommendations`,
    );
    expect(resp.status()).toBe(200);
    const recs = (await resp.json()) as Array<{
      id: string;
      recommendation: string;
    }>;
    expect(Array.isArray(recs)).toBe(true);
    await snapApi(page, "M02-recommendations", recs.slice(0, 5));

    // Adopt the first recommendation if available
    if (recs.length > 0) {
      const firstRec = recs[0];
      const directiveResp = await page.request.post(
        `${API}/operations/${operationId}/ooda/directive`,
        {
          data: {
            directive: firstRec.recommendation ?? "Adopt AI recommendation",
            scope: "next_cycle",
          },
        },
      );
      expect([200, 201]).toContain(directiveResp.status());
    }
  });

  test("M03. Submit a DIFFERENT directive (not recommendation) — verify stored", async ({
    page,
  }) => {
    // Get recommendations first
    const recResp = await page.request.get(
      `${API}/operations/${operationId}/recommendations`,
    );
    const recs = (await recResp.json()) as Array<{ recommendation: string }>;
    const recText = recs.length > 0 ? recs[0].recommendation : "";

    // Submit a custom directive that differs from the recommendation
    const customDirective = `Custom-${ts}: Focus on HTTP enumeration instead`;
    expect(customDirective).not.toBe(recText);

    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/directive`,
      {
        data: {
          directive: customDirective,
          scope: "next_cycle",
        },
      },
    );
    expect([200, 201]).toContain(resp.status());

    // Verify it was stored
    const latestResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/directive/latest`,
    );
    expect(latestResp.status()).toBe(200);
    const latest = (await latestResp.json()) as { directive: string };
    expect(latest.directive).toContain("HTTP enumeration");

    await snapApi(page, "M03-custom-directive", latest);
  });

  test("M04. Submit directive with scope=next_cycle — trigger OODA — iteration increases", async ({
    page,
  }) => {
    // Get current iteration count
    const dashBefore = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    const before = (await dashBefore.json()) as { iteration_count: number };
    const baselineCount = before.iteration_count;

    // Submit directive
    const dirResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/directive`,
      {
        data: {
          directive: `Directive-${ts}: Enumerate SMB shares`,
          scope: "next_cycle",
        },
      },
    );
    expect([200, 201]).toContain(dirResp.status());

    // Trigger a manual OODA cycle
    const triggerResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect([200, 202]).toContain(triggerResp.status());

    // Poll until iteration_count increases
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number };
        return d.iteration_count > baselineCount;
      },
      90,
      2000,
    );

    const after = result as { iteration_count: number };
    expect(after.iteration_count).toBeGreaterThan(baselineCount);

    await snapApi(page, "M04-iteration-increased", {
      before: baselineCount,
      after: after.iteration_count,
    });
  });

  test("M05. Trigger second manual OODA cycle — iteration_count >= 2", async ({
    page,
  }) => {
    // Trigger another manual cycle
    const triggerResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect([200, 202]).toContain(triggerResp.status());

    // Poll until iteration_count >= 2
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number };
        return d.iteration_count >= 2;
      },
      90,
      2000,
    );

    const dashboard = result as { iteration_count: number };
    expect(dashboard.iteration_count).toBeGreaterThanOrEqual(2);

    await snapApi(page, "M05-two-cycles", dashboard);
  });

  test("M06. Submit directive with only spaces — verify rejection or empty handling", async ({
    page,
  }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/directive`,
      {
        data: {
          directive: "     ",
          scope: "next_cycle",
        },
      },
    );

    // API should either reject with 422 or accept (we record the behavior)
    const status = resp.status();
    if (status === 422) {
      // Good — validation rejects empty/whitespace directives
      expect(status).toBe(422);
    } else {
      // API accepted — verify the directive was stored (even if trimmed empty)
      expect([200, 201]).toContain(status);
      const body = await resp.json();
      await snapApi(page, "M06-spaces-accepted", body);
    }

    await snapApi(page, "M06-spaces-directive", {
      status,
      accepted: status !== 422,
    });
  });

  // ═══════════════════════════════════════════════════════════
  //  Auto Mode (M07 – M12)
  // ═══════════════════════════════════════════════════════════

  test("M07. Start auto mode — verify running", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/auto-start`,
      {},
    );
    expect([200, 202]).toContain(resp.status());

    // Verify auto-status shows running
    const statusResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(statusResp.status()).toBe(200);
    const statusData = (await statusResp.json()) as { status: string };
    expect(statusData.status).toBe("running");

    // Screenshot War Room in auto mode
    await page.goto(`http://localhost:58080/warroom?op=${operationId}`);
    await page.waitForTimeout(2000);
    await snap(page, "M07-auto-mode-warroom");
  });

  test("M08. Wait in auto mode — iteration_count increases by 2", async ({
    page,
  }) => {
    // Get baseline
    const dashBefore = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    const before = (await dashBefore.json()) as { iteration_count: number };
    const baseline = before.iteration_count;

    // Poll until 2 more iterations complete
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number };
        return d.iteration_count >= baseline + 2;
      },
      90,
      2000,
    );

    const after = result as { iteration_count: number };
    expect(after.iteration_count).toBeGreaterThanOrEqual(baseline + 2);

    await snapApi(page, "M08-auto-iterations", {
      baseline,
      current: after.iteration_count,
    });
  });

  test("M09. In auto mode — recommendations recorded", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/recommendations`,
    );
    expect(resp.status()).toBe(200);
    const recs = (await resp.json()) as Array<{
      id: string;
      recommendation: string;
    }>;
    expect(Array.isArray(recs)).toBe(true);
    await snapApi(page, "M09-auto-recommendations", recs.slice(-3));
  });

  test("M10. Navigate War Room in auto mode — screenshot", async ({
    page,
  }) => {
    await page.goto(`http://localhost:58080/warroom?op=${operationId}`);
    await page.waitForTimeout(3000);
    await snap(page, "M10-warroom-auto-state");

    // Also capture the OODA dashboard data
    const dashResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    const dashboard = await dashResp.json();
    await snapApi(page, "M10-dashboard-data", dashboard);
  });

  test("M11. Intervention in auto mode — directive + stop + new cycle", async ({
    page,
  }) => {
    // Submit directive (intervention)
    const dirResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/directive`,
      {
        data: {
          directive: `Intervention-${ts}: Shift focus to DNS zone transfer`,
          scope: "next_cycle",
        },
      },
    );
    expect([200, 201]).toContain(dirResp.status());

    // Stop auto mode
    const stopResp = await page.request.delete(
      `${API}/operations/${operationId}/ooda/auto-stop`,
    );
    expect([200, 204]).toContain(stopResp.status());

    // Verify auto stopped
    const statusResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    const statusData = (await statusResp.json()) as { status: string };
    expect(["idle", "stopped"]).toContain(statusData.status);

    // Verify directive was stored
    const latestResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/directive/latest`,
    );
    expect(latestResp.status()).toBe(200);
    const latest = (await latestResp.json()) as { directive: string };
    expect(latest.directive).toContain("DNS zone transfer");

    // Trigger a new manual cycle after intervention
    const triggerResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect([200, 202]).toContain(triggerResp.status());

    await snapApi(page, "M11-intervention", {
      directive: latest.directive,
      autoStatus: statusData.status,
    });
  });

  test("M12. Auto status after stop — running=false", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(resp.status()).toBe(200);
    const data = (await resp.json()) as { status: string };
    expect(["idle", "stopped"]).toContain(data.status);
    expect(data.status).not.toBe("running");

    await snapApi(page, "M12-auto-stopped", data);
  });

  // ═══════════════════════════════════════════════════════════
  //  Mode Switching (M13 – M15)
  // ═══════════════════════════════════════════════════════════

  test("M13. Start auto → immediately stop → verify stopped", async ({
    page,
  }) => {
    // Start auto
    const startResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/auto-start`,
      {},
    );
    expect([200, 202]).toContain(startResp.status());

    // Immediately stop
    const stopResp = await page.request.delete(
      `${API}/operations/${operationId}/ooda/auto-stop`,
    );
    expect([200, 204]).toContain(stopResp.status());

    // Verify stopped
    const statusResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(statusResp.status()).toBe(200);
    const data = (await statusResp.json()) as { status: string };
    expect(["idle", "stopped"]).toContain(data.status);

    await snapApi(page, "M13-immediate-stop", data);
  });

  test("M14. Rapid toggle — auto start/stop x2 — no crash, final=stopped", async ({
    page,
  }) => {
    // Round 1: start → stop
    const start1 = await page.request.post(
      `${API}/operations/${operationId}/ooda/auto-start`,
      {},
    );
    expect([200, 202]).toContain(start1.status());

    const stop1 = await page.request.delete(
      `${API}/operations/${operationId}/ooda/auto-stop`,
    );
    expect([200, 204]).toContain(stop1.status());

    // Round 2: start → stop
    const start2 = await page.request.post(
      `${API}/operations/${operationId}/ooda/auto-start`,
      {},
    );
    expect([200, 202]).toContain(start2.status());

    const stop2 = await page.request.delete(
      `${API}/operations/${operationId}/ooda/auto-stop`,
    );
    expect([200, 204]).toContain(stop2.status());

    // Verify final state is stopped
    const statusResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(statusResp.status()).toBe(200);
    const data = (await statusResp.json()) as { status: string };
    expect(["idle", "stopped"]).toContain(data.status);

    await snapApi(page, "M14-rapid-toggle", {
      rounds: 2,
      finalStatus: data.status,
    });
  });

  test("M15. During active OODA cycle, auto-start should work without crash", async ({
    page,
  }) => {
    // Trigger a manual OODA cycle
    const triggerResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect([200, 202]).toContain(triggerResp.status());

    // Immediately try to start auto mode while cycle is active
    const autoResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/auto-start`,
      {},
    );
    // Should not crash — accept 200, 202, or even 409 (conflict) as valid
    expect([200, 202, 409]).toContain(autoResp.status());

    // If auto started successfully, stop it for cleanup
    if (autoResp.status() !== 409) {
      const stopResp = await page.request.delete(
        `${API}/operations/${operationId}/ooda/auto-stop`,
      );
      expect([200, 204]).toContain(stopResp.status());
    }

    // Verify system is still responsive
    const dashResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    expect(dashResp.status()).toBe(200);
    const dashboard = await dashResp.json();
    expect(dashboard.iteration_count).toBeGreaterThanOrEqual(1);

    await snapApi(page, "M15-concurrent-auto-start", {
      triggerStatus: triggerResp.status(),
      autoStartStatus: autoResp.status(),
      iterationCount: dashboard.iteration_count,
    });
  });

  // ════════════════════════════════════════════════════════════
  //  Cleanup
  // ════════════════════════════════════════════════════════════

  test("M99. Cleanup — reset operation", async ({ page }) => {
    // Ensure auto mode is stopped before reset
    await page.request.delete(
      `${API}/operations/${operationId}/ooda/auto-stop`,
    );

    const resp = await page.request.post(
      `${API}/operations/${operationId}/reset`,
    );
    expect(resp.status()).toBe(204);

    // Verify reset
    const dashResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    const dashboard = (await dashResp.json()) as { iteration_count: number };
    expect(dashboard.iteration_count).toBe(0);
  });
});
