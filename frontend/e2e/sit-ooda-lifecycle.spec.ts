import { test, expect, Page } from "@playwright/test";

const API = "http://localhost:58000/api";

/** Poll an API endpoint until condition is met or timeout */
async function pollUntil(
  page: Page,
  url: string,
  condition: (data: unknown) => boolean,
  maxAttempts = 30,
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

test.describe.serial("SIT — OODA Loop Multi-Iteration Lifecycle", () => {
  let operationId: string;
  let baselineIterationCount: number;

  // 3-minute timeout for OODA operations
  test.setTimeout(180_000);

  // ──────────────────────────────────────────────
  // Step 1: Find SHADOW-STRIKE operation
  // ──────────────────────────────────────────────

  test("01. Find SHADOW-STRIKE operation", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations`);
    expect(resp.status()).toBe(200);
    const operations = await resp.json();

    const shadowStrike = operations.find(
      (op: { codename: string; status: string }) =>
        op.codename === "SHADOW-STRIKE" && op.status === "active",
    );

    if (!shadowStrike) {
      test.skip(true, "SHADOW-STRIKE operation not found or not active");
      return;
    }

    operationId = shadowStrike.id;
    expect(operationId).toBeTruthy();
  });

  // ──────────────────────────────────────────────
  // Step 2: Record baseline iteration count
  // ──────────────────────────────────────────────

  test("02. GET /ooda/dashboard — record baseline iteration_count", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    expect(resp.status()).toBe(200);
    const dashboard = await resp.json();
    baselineIterationCount = dashboard.iteration_count ?? 0;
    expect(baselineIterationCount).toBeGreaterThanOrEqual(0);
  });

  // ──────────────────────────────────────────────
  // Step 3: Trigger new OODA iteration
  // ──────────────────────────────────────────────

  test("03. POST /ooda/trigger — expect 202", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect(resp.status()).toBe(202);
  });

  // ──────────────────────────────────────────────
  // Step 4: Poll until new iteration completes
  // ──────────────────────────────────────────────

  test("04. Poll dashboard until iteration_count > baseline", async ({ page }) => {
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number; latest_iteration?: { completed_at?: string } };
        return d.iteration_count > baselineIterationCount && !!d.latest_iteration?.completed_at;
      },
      60,
      3000,
    );
    const dashboard = result as {
      iteration_count: number;
      latest_iteration?: { completed_at?: string };
    };
    expect(dashboard.iteration_count).toBeGreaterThan(baselineIterationCount);
    expect(dashboard.latest_iteration?.completed_at).toBeTruthy();
  });

  // ──────────────────────────────────────────────
  // Step 5: Verify timeline has all 4 OODA phases
  // ──────────────────────────────────────────────

  test("05. GET /ooda/timeline — new iteration has all 4 phases", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    expect(resp.status()).toBe(200);
    const timeline = (await resp.json()) as Array<{
      iteration_number: number;
      phase: string;
      detail?: Record<string, unknown>;
    }>;
    expect(Array.isArray(timeline)).toBe(true);

    // Find entries for the latest completed iteration
    const maxIter = Math.max(...timeline.map((e) => e.iteration_number));
    const iterationEntries = timeline.filter(
      (entry) => entry.iteration_number === maxIter,
    );

    const phases = iterationEntries.map((entry) => entry.phase);
    expect(phases).toContain("observe");
    expect(phases).toContain("orient");
    expect(phases).toContain("decide");
    expect(phases).toContain("act");
  });

  // ──────────────────────────────────────────────
  // Step 6: Verify orient phase detail
  // ──────────────────────────────────────────────

  test("06. Orient entry has recommended_technique_id and confidence > 0", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    expect(resp.status()).toBe(200);
    const timeline = (await resp.json()) as Array<{
      iteration_number: number;
      phase: string;
      detail?: { recommended_technique_id?: string; confidence?: number };
    }>;

    const maxIter = Math.max(...timeline.map((e) => e.iteration_number));
    const orientEntry = timeline.find(
      (entry) => entry.iteration_number === maxIter && entry.phase === "orient",
    );

    expect(orientEntry).toBeTruthy();
    expect(orientEntry!.detail).toBeTruthy();
    expect(orientEntry!.detail!.recommended_technique_id).toBeTruthy();
    expect(orientEntry!.detail!.confidence).toBeGreaterThan(0);
  });

  // ──────────────────────────────────────────────
  // Step 7: Start OODA auto mode
  // ──────────────────────────────────────────────

  test("07. POST /ooda/auto-start — expect 200 or 202", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/auto-start`,
      {},
    );
    expect([200, 202]).toContain(resp.status());
  });

  // ──────────────────────────────────────────────
  // Step 8: Verify auto mode is active
  // ──────────────────────────────────────────────

  test("08. GET /ooda/auto-status — auto mode is active", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(resp.status()).toBe(200);
    const status = await resp.json();
    expect(status.status).toBe("running");
  });

  // ──────────────────────────────────────────────
  // Step 9: Stop OODA auto mode
  // ──────────────────────────────────────────────

  test("09. DELETE /ooda/auto-stop — expect 200 or 204", async ({ page }) => {
    const resp = await page.request.delete(
      `${API}/operations/${operationId}/ooda/auto-stop`,
    );
    expect([200, 204]).toContain(resp.status());
  });

  // ──────────────────────────────────────────────
  // Step 10: Verify auto mode stopped
  // ──────────────────────────────────────────────

  test("10. GET /ooda/auto-status — auto mode stopped", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(resp.status()).toBe(200);
    const status = await resp.json();
    // After stop, status returns to "idle" or "stopped"
    expect(["idle", "stopped"]).toContain(status.status);
  });

  // ──────────────────────────────────────────────
  // Step 11: Verify history matches iteration count
  // ──────────────────────────────────────────────

  test("11. GET /ooda/history — length matches iteration_count", async ({ page }) => {
    // Get current iteration count from dashboard
    const dashResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    expect(dashResp.status()).toBe(200);
    const dashboard = (await dashResp.json()) as { iteration_count: number };

    // Get history
    const histResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/history`,
    );
    expect(histResp.status()).toBe(200);
    const history = await histResp.json();
    expect(Array.isArray(history)).toBe(true);
    expect(history.length).toBe(dashboard.iteration_count);
  });
});
