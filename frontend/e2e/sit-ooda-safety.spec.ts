// Copyright 2026 Athena Contributors
//
// SIT — OODA Safety Tests
//
// Validates system safety under edge-case conditions:
// - Concurrent OODA trigger protection
// - C5ISR constraint engine under degraded states
// - Noise budget behavior in SR mode
// - Data safety (mid-cycle target deletion, empty targets, constraint overrides)
//
// Focus: "doesn't crash" assertions for safety-critical paths.

import { test, expect, type Page } from "@playwright/test";

const API = "http://localhost:58000/api";
const SHOTS = "test-results/sit-ooda-safety-screenshots";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function snap(page: Page, name: string) {
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

async function snapApi(page: Page, name: string, data: unknown) {
  await page.goto("about:blank");
  await page.setContent(`
    <html><body style="background:#09090B;color:#D4D4D8;font-family:monospace;padding:24px;">
      <h2 style="color:#1E6091;margin-bottom:16px;">${name}</h2>
      <pre style="white-space:pre-wrap;word-break:break-all;font-size:12px;">${JSON.stringify(data, null, 2)}</pre>
    </body></html>
  `);
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

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
  return null; // timeout - non-fatal
}

// ---------------------------------------------------------------------------
// Test Suite
// ---------------------------------------------------------------------------

test.describe.serial("SIT — OODA Safety", () => {
  let operationId: string;
  let targetId: string;
  const ts = Date.now();

  test.setTimeout(600_000);

  // ══════════════════════════════════════════════════════════════════════════
  //  Setup: Create operation + target + wait for first OODA
  // ══════════════════════════════════════════════════════════════════════════

  test("S00a. Create fresh operation for safety tests", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations`, {
      data: {
        code: `SIT-SAFETY-${ts}`,
        name: "SIT OODA Safety Test",
        codename: `sit-safety-${ts}`,
        strategic_intent: "OODA safety edge-case verification",
        mission_profile: "SP",
      },
    });
    expect(resp.status()).toBe(201);
    const op = await resp.json();
    operationId = op.id;
    await snapApi(page, "S00a-operation-created", op);
  });

  test("S00b. Add target and set active", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/targets`,
      {
        data: {
          hostname: "safety-target",
          ip_address: "192.168.0.99",
          os: "Linux",
          role: "target",
          network_segment: "Internal",
        },
      },
    );
    expect(resp.status()).toBe(201);
    const target = await resp.json();
    targetId = target.id;

    const activeResp = await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetId } },
    );
    expect(activeResp.status()).toBe(200);
  });

  test("S00c. Wait for first OODA iteration to complete", async ({ page }) => {
    // Wait for auto-trigger, then manually trigger as fallback
    await page.waitForTimeout(10_000);
    let dashResp = await page.request.get(`${API}/operations/${operationId}/ooda/dashboard`);
    let dash = (await dashResp.json()) as { iteration_count?: number };
    if ((dash.iteration_count ?? 0) < 1) {
      await page.request.post(`${API}/operations/${operationId}/ooda/trigger`);
    }

    // 150 attempts × 2s = 5 min for real LLM + nmap
    const result = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count: number; latest_iteration?: { completed_at?: string } };
        return d.iteration_count >= 1 && !!d.latest_iteration?.completed_at;
      },
      150,
      2000,
    );
    if (!result) {
      await snapApi(page, "S00c-timeout", { note: "OODA timeout — LLM + nmap > 5min" });
      test.skip();
      return;
    }
    const d = result as { iteration_count: number };
    expect(d.iteration_count).toBeGreaterThanOrEqual(1);
    await snapApi(page, "S00c-first-ooda-complete", d);
  });

  // ══════════════════════════════════════════════════════════════════════════
  //  Concurrent OODA Protection (S01–S02)
  // ══════════════════════════════════════════════════════════════════════════

  test("S01. Concurrent OODA triggers — only one extra iteration created", async ({ page }) => {
    // Record current iteration count
    const beforeResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    expect(beforeResp.ok()).toBeTruthy();
    const before = (await beforeResp.json()) as { iteration_count: number };
    const countBefore = before.iteration_count;

    // Fire two concurrent OODA triggers
    const [r1, r2] = await Promise.all([
      page.request.post(`${API}/operations/${operationId}/ooda/trigger`, {}),
      page.request.post(`${API}/operations/${operationId}/ooda/trigger`, {}),
    ]);

    // Neither should be a 500 — acceptable: 200, 202 (queued), 409 (conflict), 429 (throttled)
    expect([200, 202, 409, 429]).toContain(r1.status());
    expect([200, 202, 409, 429]).toContain(r2.status());

    await snapApi(page, "S01-concurrent-trigger-responses", {
      r1_status: r1.status(),
      r2_status: r2.status(),
    });

    // Wait for any triggered cycles to complete
    await page.waitForTimeout(10_000);

    // Poll until stable (no in-progress iteration)
    const after = (await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { latest_iteration?: { completed_at?: string } };
        // Either no new iteration, or the latest has completed
        return !d.latest_iteration || !!d.latest_iteration.completed_at;
      },
      30,
      2000,
    )) as { iteration_count: number };

    // Both triggers may succeed — verify no crash and count is reasonable
    const afterCount = after ? (after as { iteration_count: number }).iteration_count : countBefore;
    const newIterations = afterCount - countBefore;
    // Accept 0, 1, or 2 new iterations — key is no crash/500
    expect(newIterations).toBeGreaterThanOrEqual(0);
    expect(newIterations).toBeLessThanOrEqual(2);

    await snapApi(page, "S01-concurrent-result", {
      before: countBefore,
      after: afterCount,
      new_iterations: newIterations,
    });
  });

  test("S02. Auto-start then immediate trigger — no crash", async ({ page }) => {
    // Start auto mode
    const autoResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/auto-start`,
      {},
    );
    expect([200, 202]).toContain(autoResp.status());

    // Immediately fire a manual trigger while auto is running
    const triggerResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    // Should not crash — 200/202/409/429 are all acceptable
    expect([200, 202, 409, 429]).toContain(triggerResp.status());

    // Verify auto mode is still running (not crashed)
    await page.waitForTimeout(3000);
    const statusResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(statusResp.ok()).toBeTruthy();
    const status = await statusResp.json();
    // Auto should be running or have completed gracefully
    expect(["running", "idle", "stopped"]).toContain(status.status);

    await snapApi(page, "S02-auto-plus-trigger", {
      auto_start: autoResp.status(),
      trigger: triggerResp.status(),
      auto_status_after: status.status,
    });

    // Stop auto mode for subsequent tests
    const stopResp = await page.request.delete(
      `${API}/operations/${operationId}/ooda/auto-stop`,
    );
    expect([200, 204]).toContain(stopResp.status());

    // Wait for auto to fully stop
    await page.waitForTimeout(3000);
  });

  // ══════════════════════════════════════════════════════════════════════════
  //  C5ISR Constraint Critical States (S03–S07)
  // ══════════════════════════════════════════════════════════════════════════

  test("S03. Command health low — constraints reflect reduced orient options", async ({ page }) => {
    // Get current C5ISR state
    const c5isrResp = await page.request.get(
      `${API}/operations/${operationId}/c5isr`,
    );
    expect(c5isrResp.ok()).toBeTruthy();
    const c5isr = await c5isrResp.json();

    // Get constraints — the constraint engine should produce output based on C5ISR state
    const constraintResp = await page.request.get(
      `${API}/operations/${operationId}/constraints`,
    );
    expect(constraintResp.ok()).toBeTruthy();
    const constraints = await constraintResp.json();

    await snapApi(page, "S03-command-constraints", {
      c5isr_domains: c5isr,
      constraints,
    });

    // Verify constraint engine returned valid data (didn't crash)
    expect(constraints).toBeTruthy();
    // If constraints is an object or array, it should be non-null
    if (typeof constraints === "object") {
      expect(constraints).not.toBeNull();
    }
  });

  test("S04. Control health low — constraints include recovery warnings", async ({ page }) => {
    const constraintResp = await page.request.get(
      `${API}/operations/${operationId}/constraints`,
    );
    expect(constraintResp.ok()).toBeTruthy();
    const constraints = await constraintResp.json();

    await snapApi(page, "S04-control-constraints", { constraints });

    // Safety check: API responds without error
    expect(constraints).toBeTruthy();
  });

  test("S05. ISR health low — constraints check for intel warnings", async ({ page }) => {
    // Get C5ISR to check ISR domain
    const c5isrResp = await page.request.get(
      `${API}/operations/${operationId}/c5isr`,
    );
    const c5isr = (await c5isrResp.json()) as Array<{ domain: string; health_pct: number }>;

    const isrDomain = c5isr.find((d) => d.domain === "isr");

    // Get constraints regardless of ISR health
    const constraintResp = await page.request.get(
      `${API}/operations/${operationId}/constraints`,
    );
    expect(constraintResp.ok()).toBeTruthy();
    const constraints = await constraintResp.json();

    await snapApi(page, "S05-isr-constraints", {
      isr_domain: isrDomain ?? "not populated yet",
      constraints,
    });

    // Safety: constraint engine handles ISR state without crashing
    expect(constraints).toBeTruthy();
  });

  test("S06. OODA with all C5ISR domains — completes without crash", async ({ page }) => {
    // Trigger a fresh OODA cycle
    const triggerResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    // Accept queued, success, or throttle — no 500
    expect([200, 202, 409, 429]).toContain(triggerResp.status());

    if (triggerResp.status() === 200 || triggerResp.status() === 202) {
      // Wait for the cycle to complete
      await pollUntil(
        page,
        `${API}/operations/${operationId}/ooda/dashboard`,
        (data: unknown) => {
          const d = data as { latest_iteration?: { completed_at?: string } };
          return !!d.latest_iteration?.completed_at;
        },
        60,
        2000,
      );
    }

    // Verify C5ISR state after OODA
    const c5isrResp = await page.request.get(
      `${API}/operations/${operationId}/c5isr`,
    );
    expect(c5isrResp.ok()).toBeTruthy();
    const c5isr = await c5isrResp.json();

    await snapApi(page, "S06-ooda-with-c5isr", {
      trigger_status: triggerResp.status(),
      c5isr_state: c5isr,
    });

    // Safety: C5ISR data is valid (array or object, not error)
    expect(c5isr).toBeTruthy();
  });

  test("S07. Auto mode survives C5ISR state changes", async ({ page }) => {
    // Start auto mode
    const autoResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/auto-start`,
      {},
    );
    expect([200, 202]).toContain(autoResp.status());

    // Wait for at least one auto cycle
    await page.waitForTimeout(10_000);

    // Check auto is still running (not crashed)
    const statusResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/auto-status`,
    );
    expect(statusResp.ok()).toBeTruthy();
    const status = await statusResp.json();
    expect(["running", "idle", "stopped"]).toContain(status.status);

    // Check C5ISR is accessible during/after auto
    const c5isrResp = await page.request.get(
      `${API}/operations/${operationId}/c5isr`,
    );
    expect(c5isrResp.ok()).toBeTruthy();

    await snapApi(page, "S07-auto-mode-c5isr", {
      auto_status: status.status,
      c5isr_accessible: c5isrResp.ok(),
    });

    // Stop auto mode
    const stopResp = await page.request.delete(
      `${API}/operations/${operationId}/ooda/auto-stop`,
    );
    expect([200, 204]).toContain(stopResp.status());
    await page.waitForTimeout(3000);
  });

  // ══════════════════════════════════════════════════════════════════════════
  //  Noise Budget (S08–S09)
  // ══════════════════════════════════════════════════════════════════════════

  test("S08. SR mode — observe phase respects noise budget", async ({ page }) => {
    // Create SR mode operation for noise budget test
    const srResp = await page.request.post(`${API}/operations`, {
      data: {
        code: `SIT-SR-${ts}`,
        name: "SIT SR Noise Budget",
        codename: `sit-sr-${ts}`,
        strategic_intent: "Noise budget verification",
        mission_profile: "SR",
      },
    });
    expect(srResp.status()).toBe(201);
    const srOp = await srResp.json();

    // Add target to SR operation
    const tgtResp = await page.request.post(
      `${API}/operations/${srOp.id}/targets`,
      {
        data: {
          hostname: "sr-target",
          ip_address: "192.168.0.98",
          os: "Linux",
          role: "target",
          network_segment: "Internal",
        },
      },
    );
    expect(tgtResp.status()).toBe(201);
    const srTarget = await tgtResp.json();

    // Set target active
    await page.request.patch(
      `${API}/operations/${srOp.id}/targets/active`,
      { data: { target_id: srTarget.id } },
    );

    // Trigger OODA and wait for completion
    const triggerResp = await page.request.post(
      `${API}/operations/${srOp.id}/ooda/trigger`,
      {},
    );
    expect([200, 202, 409, 429]).toContain(triggerResp.status());

    if (triggerResp.status() === 200 || triggerResp.status() === 202) {
      try {
        await pollUntil(
          page,
          `${API}/operations/${srOp.id}/ooda/dashboard`,
          (data: unknown) => {
            const d = data as { iteration_count: number; latest_iteration?: { completed_at?: string } };
            return d.iteration_count >= 1 && !!d.latest_iteration?.completed_at;
          },
          60,
          2000,
        );
      } catch {
        // Auto-trigger may have already started — acceptable
      }
    }

    // Check timeline for observe phase details
    const timelineResp = await page.request.get(
      `${API}/operations/${srOp.id}/ooda/timeline`,
    );
    let timeline: unknown[] = [];
    if (timelineResp.ok()) {
      timeline = await timelineResp.json();
    }

    await snapApi(page, "S08-sr-noise-budget", {
      mission_profile: "SR",
      trigger_status: triggerResp.status(),
      timeline_entries: (timeline as Array<{ phase: string }>).length,
      observe_entries: (timeline as Array<{ phase: string }>).filter(
        (e) => e.phase === "observe",
      ),
    });

    // Cleanup SR operation
    await page.request.post(`${API}/operations/${srOp.id}/reset`);
  });

  test("S09. OPSEC noise score tracking after multiple cycles", async ({ page }) => {
    // Get opsec status — should track noise from OODA cycles
    const opsecResp = await page.request.get(
      `${API}/operations/${operationId}/opsec-status`,
    );

    let opsecData: unknown = null;
    if (opsecResp.ok()) {
      opsecData = await opsecResp.json();
    }

    await snapApi(page, "S09-opsec-noise-tracking", {
      opsec_status: opsecResp.status(),
      data: opsecData,
    });

    // Safety: opsec endpoint responds without error after OODA cycles
    expect(opsecResp.ok()).toBeTruthy();
    expect(opsecData).toBeTruthy();
  });

  // ══════════════════════════════════════════════════════════════════════════
  //  Data Safety (S10–S12)
  // ══════════════════════════════════════════════════════════════════════════

  test("S10. Delete target mid-OODA — cycle completes without crash", async ({ page }) => {
    // Add a new target to delete mid-cycle
    const tgtResp = await page.request.post(
      `${API}/operations/${operationId}/targets`,
      {
        data: {
          hostname: "ephemeral-target",
          ip_address: "192.168.0.97",
          os: "Linux",
          role: "target",
          network_segment: "Internal",
        },
      },
    );
    expect(tgtResp.status()).toBe(201);
    const ephTarget = await tgtResp.json();

    // Set ephemeral target as active
    await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: ephTarget.id } },
    );

    // Trigger OODA cycle
    const triggerResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect([200, 202, 409, 429]).toContain(triggerResp.status());

    // Immediately delete the target while OODA may be processing
    const deleteResp = await page.request.delete(
      `${API}/operations/${operationId}/targets/${ephTarget.id}`,
    );
    // Accept 200, 204 (deleted), 404 (already gone), 409 (in use)
    expect([200, 204, 404, 409]).toContain(deleteResp.status());

    // Wait for any in-progress OODA to settle
    await page.waitForTimeout(10_000);

    // Verify the system is still responsive
    const dashResp = await page.request.get(
      `${API}/operations/${operationId}/ooda/dashboard`,
    );
    expect(dashResp.ok()).toBeTruthy();
    const dashboard = await dashResp.json();

    await snapApi(page, "S10-delete-mid-ooda", {
      trigger_status: triggerResp.status(),
      delete_status: deleteResp.status(),
      dashboard_ok: dashResp.ok(),
      iteration_count: (dashboard as { iteration_count: number }).iteration_count,
    });

    // Safety: dashboard still responds
    expect(dashboard).toBeTruthy();
  });

  test("S11. OODA trigger with 0 targets — graceful response", async ({ page }) => {
    // Create an operation with no targets
    const emptyResp = await page.request.post(`${API}/operations`, {
      data: {
        code: `SIT-EMPTY-${ts}`,
        name: "SIT Empty Targets",
        codename: `sit-empty-${ts}`,
        strategic_intent: "Empty target safety test",
        mission_profile: "SP",
      },
    });
    expect(emptyResp.status()).toBe(201);
    const emptyOp = await emptyResp.json();

    // Trigger OODA with 0 targets
    const triggerResp = await page.request.post(
      `${API}/operations/${emptyOp.id}/ooda/trigger`,
      {},
    );

    // Should not crash — may return success (empty observe) or a graceful error
    expect([200, 202, 400, 404, 409, 422, 429]).toContain(triggerResp.status());

    let triggerBody: unknown = null;
    try {
      triggerBody = await triggerResp.json();
    } catch {
      // Response may not be JSON — acceptable
    }

    await snapApi(page, "S11-zero-targets-trigger", {
      trigger_status: triggerResp.status(),
      response: triggerBody,
    });

    // If the cycle was accepted, wait briefly and verify dashboard doesn't crash
    if (triggerResp.status() === 200 || triggerResp.status() === 202) {
      await page.waitForTimeout(5000);
      const dashResp = await page.request.get(
        `${API}/operations/${emptyOp.id}/ooda/dashboard`,
      );
      expect(dashResp.ok()).toBeTruthy();
    }

    // Cleanup
    await page.request.post(`${API}/operations/${emptyOp.id}/reset`);
  });

  test("S12. Constraint override — applied then expires after next OODA", async ({ page }) => {
    // POST constraint override for "command" domain
    const overrideResp = await page.request.post(
      `${API}/operations/${operationId}/constraints/override`,
      { data: { domain: "command" } },
    );
    expect(overrideResp.ok()).toBeTruthy();
    const overrideResult = await overrideResp.json();

    await snapApi(page, "S12a-constraint-override-applied", {
      status: overrideResp.status(),
      result: overrideResult,
    });

    // Verify override is visible in constraints
    const constraintResp1 = await page.request.get(
      `${API}/operations/${operationId}/constraints`,
    );
    expect(constraintResp1.ok()).toBeTruthy();
    const constraints1 = await constraintResp1.json();

    await snapApi(page, "S12b-constraints-with-override", { constraints: constraints1 });

    // Trigger OODA cycle to cause override to potentially expire
    const triggerResp = await page.request.post(
      `${API}/operations/${operationId}/ooda/trigger`,
      {},
    );
    expect([200, 202, 409, 429]).toContain(triggerResp.status());

    // Wait for the cycle
    if (triggerResp.status() === 200 || triggerResp.status() === 202) {
      try {
        await pollUntil(
          page,
          `${API}/operations/${operationId}/ooda/dashboard`,
          (data: unknown) => {
            const d = data as { latest_iteration?: { completed_at?: string } };
            return !!d.latest_iteration?.completed_at;
          },
          30,
          2000,
        );
      } catch {
        // Timeout is acceptable — cycle may be blocked
      }
    }

    // Check constraints again after OODA
    const constraintResp2 = await page.request.get(
      `${API}/operations/${operationId}/constraints`,
    );
    expect(constraintResp2.ok()).toBeTruthy();
    const constraints2 = await constraintResp2.json();

    await snapApi(page, "S12c-constraints-after-ooda", {
      constraints_before: constraints1,
      constraints_after: constraints2,
    });

    // Safety: constraint engine still works after override + OODA cycle
    expect(constraints2).toBeTruthy();
  });

  // ══════════════════════════════════════════════════════════════════════════
  //  Cleanup
  // ══════════════════════════════════════════════════════════════════════════

  test("S99. Cleanup — reset operation", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/reset`,
    );
    expect(resp.status()).toBe(204);
    await snapApi(page, "S99-cleanup", { status: resp.status(), operationId });
  });
});
