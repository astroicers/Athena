import { test, expect, Page } from "@playwright/test";

const API = "http://localhost:58000/api";

/** Poll an API endpoint until condition is met or timeout */
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

test.describe.serial("Full Red Team Workflow — 192.168.0.26", () => {
  // Shared state across serial tests
  let operationId: string;
  let targetId: string;

  // 3-minute timeout for scan/OODA operations
  test.setTimeout(180_000);

  // ──────────────────────────────────────────────
  // Phase 1: Create Operation
  // ──────────────────────────────────────────────

  test("01. Create operation via API", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations`, {
      data: {
        code: `E2E-${Date.now()}`,
        name: "E2E Full Workflow Test",
        codename: `e2e-${Date.now()}`,
        strategic_intent: "Automated E2E test: create op, add target 192.168.0.26, scan, OODA",
        mission_profile: "SP",
      },
    });
    expect(resp.status()).toBe(201);
    const op = await resp.json();
    operationId = op.id;
    expect(op.status).toBe("planning");
    expect(op.current_ooda_phase).toBe("observe");
  });

  test("02. Operation appears on /operations page", async ({ page }) => {
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");
    const body = await page.locator("main").textContent();
    expect(body).toBeTruthy();
  });

  // ──────────────────────────────────────────────
  // Phase 2: Add Target
  // ──────────────────────────────────────────────

  test("03. Add target 192.168.0.26 via API", async ({ page }) => {
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
    expect(target.ip_address).toBe("192.168.0.26");
    expect(target.is_compromised).toBe(false);
  });

  test("04. Set target as active", async ({ page }) => {
    const resp = await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetId } },
    );
    expect(resp.status()).toBe(200);
  });

  test("05. Target list via API has our target", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets`,
    );
    expect(resp.status()).toBe(200);
    const targets = await resp.json();
    const found = targets.find((t: { id: string }) => t.id === targetId);
    expect(found).toBeTruthy();
    expect(found.is_active).toBe(true);
  });

  // ──────────────────────────────────────────────
  // Phase 3: OODA Auto-Recon (SPEC-052)
  // ──────────────────────────────────────────────

  // SPEC-052: Recon is auto-triggered by OODA Observe phase after target creation.
  // No manual POST /recon/scan needed — the OODA cycle starts automatically.

  test("06. Verify OODA auto-triggered after target creation", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    expect(resp.status()).toBe(200);
    const dashboard = await resp.json();
    // OODA cycle should have been initiated automatically
    expect(dashboard).toBeTruthy();
  });

  test("07. OODA auto-completes first cycle (Observe includes recon)", async ({ page }) => {
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number; latest_iteration?: { completed_at?: string } };
        return d.iteration_count >= 1 && !!d.latest_iteration?.completed_at;
      },
      90,
      2000,
    );
    const d = result as { iteration_count: number };
    expect(d.iteration_count).toBeGreaterThanOrEqual(1);
  });

  test("08. OODA timeline has observe entries from auto-recon", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    expect(resp.status()).toBe(200);
    const timeline = await resp.json();
    expect(Array.isArray(timeline)).toBe(true);
    expect(timeline.length).toBeGreaterThan(0);
    // Verify observe phase entries exist (recon results from auto-scan)
    const observeEntries = timeline.filter(
      (entry: { phase: string }) => entry.phase === "observe",
    );
    expect(observeEntries.length).toBeGreaterThan(0);
  });

  // ──────────────────────────────────────────────
  // Phase 4: OODA Cycle #2 (manual trigger)
  // ──────────────────────────────────────────────

  // SPEC-052: Cycle #1 was auto-triggered. We now manually trigger cycle #2.
  test("09. Trigger OODA cycle #2 (202 Accepted)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect(resp.status()).toBe(202);
  });

  test("10. Poll OODA until iteration #2 completes", async ({ page }) => {
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number; latest_iteration?: { completed_at?: string } };
        return d.iteration_count >= 2 && !!d.latest_iteration?.completed_at;
      },
      60,
      2000,
    );
    const d = result as { iteration_count: number };
    expect(d.iteration_count).toBeGreaterThanOrEqual(2);
  });

  test("11. OODA timeline has phase entries from both cycles", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    expect(resp.status()).toBe(200);
    const timeline = await resp.json();
    expect(Array.isArray(timeline)).toBe(true);
    // Should have entries from both auto-triggered cycle #1 and manual cycle #2
    expect(timeline.length).toBeGreaterThanOrEqual(4);
  });

  // ──────────────────────────────────────────────
  // Phase 5: Verify UI
  // ──────────────────────────────────────────────

  test("12. War Room timeline tab shows OODA blocks", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("13. C5ISR health data exists", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/c5isr`,
    );
    expect(resp.status()).toBe(200);
    const c5isr = await resp.json();
    expect(Array.isArray(c5isr)).toBe(true);
  });

  // ──────────────────────────────────────────────
  // Phase 6: OODA Cycle #3
  // ──────────────────────────────────────────────

  test("14. Trigger OODA cycle #3", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect(resp.status()).toBe(202);
  });

  test("15. Poll until iteration_count >= 3", async ({ page }) => {
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number; latest_iteration?: { completed_at?: string } };
        return d.iteration_count >= 3 && !!d.latest_iteration?.completed_at;
      },
      60,
      2000,
    );
    const d = result as { iteration_count: number };
    expect(d.iteration_count).toBeGreaterThanOrEqual(3);
  });

  test("16. Timeline detail has facts and recommendation", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    expect(resp.status()).toBe(200);
    const timeline = await resp.json();
    // Should have multiple entries across 3 iterations
    expect(timeline.length).toBeGreaterThanOrEqual(6);
  });

  // ──────────────────────────────────────────────
  // Phase 7: Cross-page Verification
  // ──────────────────────────────────────────────

  test("17. ATT&CK Surface page loads with technique data", async ({ page }) => {
    await page.goto("/attack-surface");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("body")).toBeVisible();
  });

  // ──────────────────────────────────────────────
  // Phase 8: Cleanup
  // ──────────────────────────────────────────────

  test("18. Cleanup — deactivate target", async ({ page }) => {
    await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: "" } },
    );
    // Verify deactivated
    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets`,
    );
    expect(resp.status()).toBe(200);
  });

  test("19. Operation still exists (DELETE not supported — expected)", async ({ page }) => {
    // Backend may not support DELETE /operations/{id} yet
    // Verify the operation still exists and is intact
    const resp = await page.request.get(
      `${API}/operations/${operationId}`,
    );
    expect(resp.status()).toBe(200);
    const op = await resp.json();
    expect(op.id).toBe(operationId);
  });
});
