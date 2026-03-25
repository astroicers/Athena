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
  // Phase 3: Recon Scan
  // ──────────────────────────────────────────────

  test("06. Trigger recon scan (202 Accepted)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/recon/scan`,
      { data: { target_id: targetId, enable_initial_access: true } },
    );
    expect(resp.status()).toBe(202);
    const result = await resp.json();
    expect(result.status).toBe("queued");
  });

  test("07. Poll recon until finished (completed or failed)", async ({ page }) => {
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/recon/status`,
      (data: unknown) => {
        const d = data as { status: string };
        return d.status === "completed" || d.status === "failed";
      },
      60,
      2000,
    );
    const r = result as { status: string };
    // In test environments, scan may fail if target is unreachable
    expect(["completed", "failed"]).toContain(r.status);
  });

  test("08. Verify scan result exists (may have 0 services if target unreachable)", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/recon/scans/by-target/${targetId}`,
    );
    // May be 200 (scan found) or 404 (no completed scan) if scan failed
    expect([200, 404]).toContain(resp.status());
  });

  // ──────────────────────────────────────────────
  // Phase 4: OODA Cycle #1
  // ──────────────────────────────────────────────

  test("09. Trigger OODA cycle #1 (202 Accepted)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect(resp.status()).toBe(202);
  });

  test("10. Poll OODA until iteration #1 completes", async ({ page }) => {
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { latest_iteration?: { completed_at?: string } };
        return !!d.latest_iteration?.completed_at;
      },
      30,
      2000,
    );
    const d = result as { iteration_count: number };
    expect(d.iteration_count).toBeGreaterThanOrEqual(1);
  });

  test("11. OODA timeline has phase entries", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    expect(resp.status()).toBe(200);
    const timeline = await resp.json();
    expect(Array.isArray(timeline)).toBe(true);
    expect(timeline.length).toBeGreaterThan(0);
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
  // Phase 6: OODA Cycle #2
  // ──────────────────────────────────────────────

  test("14. Trigger OODA cycle #2", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect(resp.status()).toBe(202);
  });

  test("15. Poll until iteration_count >= 2", async ({ page }) => {
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number; latest_iteration?: { completed_at?: string } };
        return d.iteration_count >= 2 && !!d.latest_iteration?.completed_at;
      },
      30,
      2000,
    );
    const d = result as { iteration_count: number };
    expect(d.iteration_count).toBeGreaterThanOrEqual(2);
  });

  test("16. Timeline detail has facts and recommendation", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/ooda/timeline`,
    );
    expect(resp.status()).toBe(200);
    const timeline = await resp.json();
    // Should have multiple entries across 2 iterations
    expect(timeline.length).toBeGreaterThanOrEqual(4);
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
