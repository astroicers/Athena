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
 * SIT — OODA Loop Complete Lifecycle
 *
 * Self-contained: creates own operation + target, runs recon, triggers
 * OODA cycles, tests directive/auto-mode, verifies all API endpoints.
 * Does NOT depend on seed data.
 */

import { test, expect, Page } from "@playwright/test";

const API = "http://localhost:58000/api";

async function pollUntil(
  page: Page,
  url: string,
  condition: (data: unknown) => boolean,
  maxAttempts = 60,
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
  throw new Error(`Polling timeout after ${maxAttempts} attempts: ${url}`);
}

test.describe.serial("SIT — OODA Loop Complete Lifecycle", () => {
  let operationId: string;
  let targetId: string;
  const ts = Date.now();

  test.setTimeout(180_000);

  // ──────────────────────────────────────────────────────────────
  //  Setup: Create operation + target
  // ──────────────────────────────────────────────────────────────

  test("01. Create operation", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations`, {
      data: {
        code: `SIT-OODA-${ts}`,
        name: "SIT OODA Lifecycle Test",
        codename: `sit-ooda-${ts}`,
        strategic_intent: "Full OODA lifecycle test",
        mission_profile: "SP",
      },
    });
    expect(resp.status()).toBe(201);
    const op = await resp.json();
    operationId = op.id;
    expect(op.status).toBe("planning");
  });

  test("02. Add target 192.168.0.26", async ({ page }) => {
    const resp = await page.request.post(
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
    expect(resp.status()).toBe(201);
    const target = await resp.json();
    targetId = target.id;
  });

  test("03. Set target as active", async ({ page }) => {
    const resp = await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetId } },
    );
    expect(resp.status()).toBe(200);
  });

  // ──────────────────────────────────────────────────────────────
  //  Recon scan
  // ──────────────────────────────────────────────────────────────

  test("04. Trigger recon scan (202)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/recon/scan`,
      { data: { target_id: targetId, enable_initial_access: true } },
    );
    expect(resp.status()).toBe(202);
  });

  test("05. Poll recon until finished", async ({ page }) => {
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/recon/status`,
      (data: unknown) => {
        const d = data as { status: string };
        return d.status === "completed" || d.status === "failed";
      },
      90,
      2000,
    );
    const r = result as { status: string };
    expect(["completed", "failed"]).toContain(r.status);
  });

  // ──────────────────────────────────────────────────────────────
  //  OODA Trigger + Verification
  // ──────────────────────────────────────────────────────────────

  test("06. GET /ooda/dashboard — baseline", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    expect(resp.status()).toBe(200);
    const d = await resp.json();
    // After recon auto-trigger, may already have 1+ iteration
    expect(d.iteration_count).toBeGreaterThanOrEqual(0);
  });

  test("07. POST /ooda/trigger — manual trigger (202)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect(resp.status()).toBe(202);
  });

  test("08. Poll until iteration completes", async ({ page }) => {
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number; latest_iteration?: { completed_at?: string } };
        return d.iteration_count >= 1 && !!d.latest_iteration?.completed_at;
      },
      60,
      2000,
    );
    const d = result as { iteration_count: number };
    expect(d.iteration_count).toBeGreaterThanOrEqual(1);
  });

  test("09. Timeline has all 4 phases", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    expect(resp.status()).toBe(200);
    const timeline = await resp.json();
    expect(Array.isArray(timeline)).toBe(true);

    const maxIter = Math.max(...timeline.map((e: { iteration_number: number }) => e.iteration_number));
    const phases = timeline
      .filter((e: { iteration_number: number }) => e.iteration_number === maxIter)
      .map((e: { phase: string }) => e.phase);
    expect(phases).toContain("observe");
    expect(phases).toContain("orient");
    expect(phases).toContain("decide");
    expect(phases).toContain("act");
  });

  test("10. Orient has recommended_technique_id", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    const timeline = await resp.json();
    const maxIter = Math.max(...timeline.map((e: { iteration_number: number }) => e.iteration_number));
    const orient = timeline.find(
      (e: { iteration_number: number; phase: string }) =>
        e.iteration_number === maxIter && e.phase === "orient",
    );
    expect(orient).toBeTruthy();
    expect(orient.detail?.recommended_technique_id).toBeTruthy();
    expect(orient.detail?.confidence).toBeGreaterThan(0);
  });

  // ──────────────────────────────────────────────────────────────
  //  Directive
  // ──────────────────────────────────────────────────────────────

  test("11. Store directive", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/directive`,
      { data: { directive: "Focus on SSH and FTP services", scope: "next_cycle" } },
    );
    expect([200, 201]).toContain(resp.status());
  });

  test("12. Get latest directive", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/directive/latest`,
    );
    expect(resp.status()).toBe(200);
    const d = await resp.json();
    expect(d.directive).toContain("SSH");
  });

  // ──────────────────────────────────────────────────────────────
  //  Auto Mode
  // ──────────────────────────────────────────────────────────────

  test("13. Start auto mode", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/auto-start`,
      {},
    );
    expect([200, 202]).toContain(resp.status());
  });

  test("14. Auto status = running", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(resp.status()).toBe(200);
    const d = await resp.json();
    expect(d.status).toBe("running");
  });

  test("15. Stop auto mode", async ({ page }) => {
    const resp = await page.request.delete(
      `${API}/operations/${operationId}/ooda/auto-stop`,
    );
    expect([200, 204]).toContain(resp.status());
  });

  test("16. Auto status = stopped/idle", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(resp.status()).toBe(200);
    const d = await resp.json();
    expect(["idle", "stopped"]).toContain(d.status);
  });

  // ──────────────────────────────────────────────────────────────
  //  History + Dashboard + Recommendations
  // ──────────────────────────────────────────────────────────────

  test("17. History length matches iteration_count", async ({ page }) => {
    const dashResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    const dashboard = await dashResp.json();

    const histResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/history`,
    );
    expect(histResp.status()).toBe(200);
    const history = await histResp.json();
    expect(history.length).toBe(dashboard.iteration_count);
  });

  test("18. Dashboard aggregate has all sections", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/dashboard`,
    );
    expect(resp.status()).toBe(200);
    const d = await resp.json();
    expect(d.operation).toBeTruthy();
    expect(d.c5isr).toBeTruthy();
    expect(d.targets).toBeTruthy();
    expect(d.opsec).toBeTruthy();
    expect(d.objectives).toBeTruthy();
  });

  test("19. Recommendations exist after OODA", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/recommendations`,
    );
    expect(resp.status()).toBe(200);
    const recs = await resp.json();
    expect(Array.isArray(recs)).toBe(true);
    expect(recs.length).toBeGreaterThanOrEqual(1);
  });

  // ──────────────────────────────────────────────────────────────
  //  Cleanup
  // ──────────────────────────────────────────────────────────────

  test("20. Soft reset preserves targets", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/reset/soft`,
    );
    expect(resp.status()).toBe(204);

    // Verify targets still exist
    const tResp = await page.request.get(
      `${API}/operations/${operationId}/targets`,
    );
    const targets = await tResp.json();
    expect(targets.length).toBeGreaterThanOrEqual(1);

    // Verify iterations cleared
    const dResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    const d = await dResp.json();
    expect(d.iteration_count).toBe(0);
  });
});
