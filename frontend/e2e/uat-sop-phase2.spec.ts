// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { test, expect, Page } from "@playwright/test";

const API = "http://localhost:58000/api";
const SHOTS = "test-results/uat-screenshots-p2";

async function snap(page: Page, name: string) {
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

/** Find PHANTOM-EYE operation (has rich data for read-only tests) */
async function findPhantomEye(page: Page): Promise<{ id: string; targetId: string } | null> {
  const ops = await (await page.request.get(`${API}/operations`)).json();
  const pe = ops.find((o: { codename: string }) => o.codename === "PHANTOM-EYE");
  if (!pe) return null;
  const targets = await (await page.request.get(`${API}/operations/${pe.id}/targets`)).json();
  return { id: pe.id, targetId: targets[0]?.id || "" };
}

/** Select operation by clicking card on /operations */
async function selectOperation(page: Page, codename: string) {
  await page.goto("/operations");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  const card = page.locator(`button:has-text("${codename}")`).first();
  if (await card.isVisible().catch(() => false)) {
    await card.click();
    await page.waitForURL("**/warroom**");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
  }
}

// ════════════════════════════════════════════════════════════════════
//  UAT Phase 2 — Full Coverage (补齐所有未测 API + UI 互动)
// ════════════════════════════════════════════════════════════════════

test.describe.serial("UAT Phase 2 — Full Coverage", () => {
  let writeOpId: string;     // New operation for write tests
  let writeTargetId: string; // Target in write operation
  let peOpId: string;        // PHANTOM-EYE for read-only tests
  let peTargetId: string;
  const ts = Date.now();

  test.setTimeout(180_000);

  // ──────────────────────────────────────────────────────────────
  //  Setup: Create a fresh operation for write tests
  // ──────────────────────────────────────────────────────────────

  test("00. Setup — create operation + target for write tests", async ({ page }) => {
    // Create operation
    const opResp = await page.request.post(`${API}/operations`, {
      data: {
        code: `UAT-P2-${ts}`,
        name: "UAT Phase 2 Write Tests",
        codename: `UAT-P2-${ts}`,
        strategic_intent: "Phase 2 test coverage",
        mission_profile: "SR",
      },
    });
    expect(opResp.status()).toBe(201);
    const op = await opResp.json();
    writeOpId = op.id;

    // Add target
    const tResp = await page.request.post(`${API}/operations/${writeOpId}/targets`, {
      data: {
        hostname: `p2-target-${ts}`,
        ip_address: `10.20.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
        os: "Linux",
        role: "target",
        network_segment: "DMZ",
      },
    });
    expect(tResp.status()).toBe(201);
    writeTargetId = (await tResp.json()).id;

    // Find PHANTOM-EYE
    const pe = await findPhantomEye(page);
    if (pe) {
      peOpId = pe.id;
      peTargetId = pe.targetId;
    }
  });

  // ──────────────────────────────────────────────────────────────
  //  A. Engagement / Rules of Engagement
  // ──────────────────────────────────────────────────────────────

  test("A1. Create Engagement (ROE)", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations/${writeOpId}/engagement`, {
      data: {
        client_name: "UAT Corp",
        contact_email: "uat@test.com",
        in_scope: ["10.0.0.0/8", "192.168.0.0/16"],
        out_of_scope: ["10.0.0.1"],
        emergency_contact: "+886-900-000-000",
      },
    });
    expect(resp.status()).toBe(201);
    const eng = await resp.json();
    expect(eng.client_name).toBe("UAT Corp");
    expect(eng.status).toBe("draft");
  });

  test("A2. Get Engagement", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations/${writeOpId}/engagement`);
    expect(resp.status()).toBe(200);
    const eng = await resp.json();
    expect(eng.client_name).toBe("UAT Corp");
    expect(eng.in_scope).toContain("10.0.0.0/8");
  });

  test("A3. Activate Engagement", async ({ page }) => {
    const resp = await page.request.patch(`${API}/operations/${writeOpId}/engagement/activate`);
    expect(resp.status()).toBe(200);
    const eng = await resp.json();
    expect(eng.status).toBe("active");
  });

  test("A4. Suspend Engagement", async ({ page }) => {
    const resp = await page.request.patch(`${API}/operations/${writeOpId}/engagement/suspend`);
    expect(resp.status()).toBe(200);
    const eng = await resp.json();
    expect(eng.status).toBe("suspended");
  });

  // ──────────────────────────────────────────────────────────────
  //  B. Dashboard Aggregate APIs
  // ──────────────────────────────────────────────────────────────

  test("B1. Dashboard aggregate", async ({ page }) => {
    const opId = peOpId || writeOpId;
    const resp = await page.request.get(`${API}/operations/${opId}/dashboard`);
    expect(resp.status()).toBe(200);
    const d = await resp.json();
    expect(d.operation).toBeTruthy();
    expect(d.c5isr).toBeTruthy();
    expect(d.targets).toBeTruthy();
    expect(d.opsec).toBeTruthy();
    expect(d.objectives).toBeTruthy();
  });

  test("B2. Kill chain (per-target)", async ({ page }) => {
    if (!peOpId || !peTargetId) { test.skip(true, "PHANTOM-EYE not available"); return; }
    const resp = await page.request.get(
      `${API}/operations/${peOpId}/targets/${peTargetId}/kill-chain`,
    );
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test("B3. Attack surface distribution", async ({ page }) => {
    const opId = peOpId || writeOpId;
    const resp = await page.request.get(`${API}/operations/${opId}/attack-surface`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test("B4. Time-series metrics", async ({ page }) => {
    const opId = peOpId || writeOpId;
    const resp = await page.request.get(
      `${API}/operations/${opId}/metrics/time-series?metric=c5isr&granularity=5min`,
    );
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test("B5. Credential graph", async ({ page }) => {
    const opId = peOpId || writeOpId;
    const resp = await page.request.get(`${API}/operations/${opId}/credential-graph`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.nodes).toBeTruthy();
    expect(data.edges).toBeTruthy();
  });

  // ──────────────────────────────────────────────────────────────
  //  C. Operation Advanced (summary, reset, MCP status)
  // ──────────────────────────────────────────────────────────────

  test("C1. Operation summary", async ({ page }) => {
    const opId = peOpId || writeOpId;
    const resp = await page.request.get(`${API}/operations/${opId}/summary`);
    expect([200, 404]).toContain(resp.status());
  });

  test("C2. MCP subsystem status", async ({ page }) => {
    const resp = await page.request.get(`${API}/mcp/status`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toBeTruthy();
  });

  test("C3. Soft reset (preserves targets/facts)", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations/${writeOpId}/reset/soft`);
    expect(resp.status()).toBe(204);

    // Verify target still exists
    const tResp = await page.request.get(`${API}/operations/${writeOpId}/targets`);
    const targets = await tResp.json();
    expect(targets.length).toBeGreaterThanOrEqual(1);
  });

  test("C4. Admin rules reload", async ({ page }) => {
    const resp = await page.request.post(`${API}/admin/rules/reload`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.status).toBe("ok");
  });

  // ──────────────────────────────────────────────────────────────
  //  D. Recon Advanced
  // ──────────────────────────────────────────────────────────────

  test("D1. OSINT discover (202 queued)", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations/${writeOpId}/osint/discover`, {
      data: { domain: "example.com", max_subdomains: 10 },
    });
    expect(resp.status()).toBe(202);
    const data = await resp.json();
    expect(data.status).toBe("queued");
  });

  test("D2. Recon scan detail (by target, PHANTOM-EYE)", async ({ page }) => {
    if (!peOpId || !peTargetId) { test.skip(true, "PHANTOM-EYE not available"); return; }
    const resp = await page.request.get(
      `${API}/operations/${peOpId}/recon/scans/by-target/${peTargetId}`,
    );
    // 200 if scan exists, 200 with null if no scan
    expect([200]).toContain(resp.status());
  });

  test("D3. Recon status", async ({ page }) => {
    if (!peOpId) { test.skip(true, "PHANTOM-EYE not available"); return; }
    const resp = await page.request.get(`${API}/operations/${peOpId}/recon/status`);
    expect([200, 404]).toContain(resp.status());
  });

  // ──────────────────────────────────────────────────────────────
  //  E. OODA Directive
  // ──────────────────────────────────────────────────────────────

  test("E1. Store OODA directive", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations/${writeOpId}/ooda/directive`, {
      data: { directive: "Focus on SSH services, avoid noisy scans", scope: "next_cycle" },
    });
    expect([200, 201]).toContain(resp.status());
  });

  test("E2. Get latest directive", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${writeOpId}/ooda/directive/latest`,
    );
    expect([200, 404]).toContain(resp.status());
  });

  // ──────────────────────────────────────────────────────────────
  //  F. Recommendations
  // ──────────────────────────────────────────────────────────────

  test("F1. List recommendations (PHANTOM-EYE)", async ({ page }) => {
    if (!peOpId) { test.skip(true, "PHANTOM-EYE not available"); return; }
    const resp = await page.request.get(
      `${API}/operations/${peOpId}/recommendations?limit=5`,
    );
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test("F2. Latest recommendation", async ({ page }) => {
    if (!peOpId) { test.skip(true, "PHANTOM-EYE not available"); return; }
    const resp = await page.request.get(
      `${API}/operations/${peOpId}/recommendations/latest`,
    );
    expect(resp.status()).toBe(200);
  });

  // ──────────────────────────────────────────────────────────────
  //  G. Target Advanced
  // ──────────────────────────────────────────────────────────────

  test("G1. Target tactical summary", async ({ page }) => {
    if (!peOpId || !peTargetId) { test.skip(true, "PHANTOM-EYE not available"); return; }
    const resp = await page.request.get(
      `${API}/operations/${peOpId}/targets/${peTargetId}/summary`,
    );
    expect([200, 404]).toContain(resp.status());
  });

  test("G2. Network topology", async ({ page }) => {
    const opId = peOpId || writeOpId;
    const resp = await page.request.get(`${API}/operations/${opId}/topology`);
    expect([200, 404]).toContain(resp.status());
  });

  test("G3. Batch target import", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${writeOpId}/targets/batch`,
      {
        data: {
          entries: [
            { hostname: "batch-a", ip_address: "10.99.1.1" },
            { hostname: "batch-b", ip_address: "10.99.1.2" },
            { hostname: "batch-c", ip_address: "10.99.1.3" },
          ],
          role: "target",
          os: "Linux",
          network_segment: "Batch",
        },
      },
    );
    expect(resp.status()).toBe(201);
    const data = await resp.json();
    expect(data.total_created).toBe(3);
  });

  // ──────────────────────────────────────────────────────────────
  //  H. Mission Profiles + PoC + Agents
  // ──────────────────────────────────────────────────────────────

  test("H1. List mission profiles", async ({ page }) => {
    const resp = await page.request.get(`${API}/mission-profiles`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    // Returns a dict keyed by profile code: { SR: {...}, CO: {...}, SP: {...} }
    expect(data.SR).toBeTruthy();
    expect(data.CO).toBeTruthy();
    expect(data.SP).toBeTruthy();
  });

  test("H2. Get mission profile by code", async ({ page }) => {
    const resp = await page.request.get(`${API}/mission-profiles/SR`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.name).toBeTruthy();
  });

  test("H3. PoC records", async ({ page }) => {
    const opId = peOpId || writeOpId;
    const resp = await page.request.get(`${API}/operations/${opId}/poc`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toBeTruthy();
  });

  test("H4. Agent sync (202 background)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${writeOpId}/agents/sync`,
    );
    expect([200, 202]).toContain(resp.status());
  });

  // ──────────────────────────────────────────────────────────────
  //  I. Tool Advanced (create, check, execute, delete)
  // ──────────────────────────────────────────────────────────────

  test("I1. Create tool + delete", async ({ page }) => {
    const toolId = `uat-tool-${ts}`;
    const createResp = await page.request.post(`${API}/tools`, {
      data: {
        tool_id: toolId,
        name: "UAT Test Scanner",
        description: "Created by UAT Phase 2",
        kind: "tool",
        category: "reconnaissance",
        risk_level: "low",
      },
    });
    expect(createResp.status()).toBe(201);

    // Delete it
    const delResp = await page.request.delete(`${API}/tools/${toolId}`);
    expect(delResp.status()).toBe(204);
  });

  test("I2. Tool health check", async ({ page }) => {
    const resp = await page.request.post(`${API}/tools/nmap/check`);
    expect([200, 404, 503]).toContain(resp.status());
  });

  test("I3. Tool execute (nmap)", async ({ page }) => {
    const resp = await page.request.post(`${API}/tools/nmap/execute`, {
      data: { arguments: { target: "127.0.0.1", ports: "22" } },
    });
    // 200 success, 400 bad args, 503 tool unavailable
    expect([200, 400, 503]).toContain(resp.status());
  });

  // ──────────────────────────────────────────────────────────────
  //  J. Admin (playbook bulk import)
  // ──────────────────────────────────────────────────────────────

  test("J1. Playbook bulk import", async ({ page }) => {
    const resp = await page.request.post(`${API}/playbooks/bulk`, {
      data: {
        playbooks: [
          {
            mitre_id: `T9999.${ts}`,
            platform: "linux",
            command: "echo UAT-Phase2-bulk-test",
            output_parser: "default",
            facts_traits: ["test.bulk"],
            tags: ["uat"],
          },
        ],
      },
    });
    expect(resp.status()).toBe(200);
  });

  // ──────────────────────────────────────────────────────────────
  //  K. UI Interaction Tests (with screenshots)
  // ──────────────────────────────────────────────────────────────

  test("K1. Add Target Modal — SINGLE tab", async ({ page }) => {
    await selectOperation(page, `UAT-P2-${ts}`);

    // Switch to targets tab
    const targetsTab = page.locator(
      'button:has-text("TARGETS"), button:has-text("Targets")',
    ).first();
    await targetsTab.click();
    await page.waitForTimeout(1000);

    // Click + ADD TARGET
    const addBtn = page.locator('button:has-text("ADD TARGET")').first();
    if (await addBtn.isVisible().catch(() => false)) {
      await addBtn.click();
      await page.waitForTimeout(500);
      await snap(page, "K1a-add-target-modal");

      // Verify SINGLE / BATCH tabs exist
      const singleTab = page.locator('button:has-text("SINGLE")').first();
      const batchTab = page.locator('button:has-text("BATCH")').first();
      expect(await singleTab.isVisible().catch(() => false)).toBe(true);
      expect(await batchTab.isVisible().catch(() => false)).toBe(true);

      // Close modal
      const cancelBtn = page.locator('button:has-text("CANCEL"), button:has-text("Cancel")').first();
      if (await cancelBtn.isVisible().catch(() => false)) {
        await cancelBtn.click();
      }
    }
    await snap(page, "K1b-target-modal-closed");
  });

  test("K2. Tool ON/OFF toggle via UI", async ({ page }) => {
    await page.goto("/tools");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    await snap(page, "K2-tools-registry");

    // Verify ON/OFF badges are visible
    const body = await page.locator("body").textContent();
    const hasToggle = /\bON\b/.test(body || "") || /\bOFF\b/.test(body || "");
    expect(hasToggle).toBe(true);
  });

  test("K3. Notification center", async ({ page }) => {
    await page.goto("/warroom");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // Click notification bell icon
    const bellBtn = page.locator('button[aria-label="Notifications"], button[aria-label="notifications"]').first();
    if (await bellBtn.isVisible().catch(() => false)) {
      await bellBtn.click();
      await page.waitForTimeout(500);
      await snap(page, "K3a-notification-open");

      // Close by pressing Escape (panel overlays the bell button)
      await page.keyboard.press("Escape");
      await page.waitForTimeout(300);
    }
    await snap(page, "K3b-notification-closed");
  });

  test("K4. Mission tab — Objectives panel", async ({ page }) => {
    await selectOperation(page, `UAT-P2-${ts}`);

    const missionTab = page.locator(
      'button:has-text("MISSION"), button:has-text("Mission")',
    ).first();
    await missionTab.click();
    await page.waitForTimeout(1500);

    // Look for OBJECTIVES section and + ADD OBJECTIVE button
    const body = await page.locator("body").textContent();
    const hasObjectives = /objective/i.test(body || "");
    expect(hasObjectives).toBe(true);
    await snap(page, "K4-mission-objectives");
  });

  test("K5. War Room — Engagement panel display", async ({ page }) => {
    await selectOperation(page, `UAT-P2-${ts}`);

    const missionTab = page.locator(
      'button:has-text("MISSION"), button:has-text("Mission")',
    ).first();
    await missionTab.click();
    await page.waitForTimeout(1500);

    // Look for RULES OF ENGAGEMENT section
    const body = await page.locator("body").textContent();
    const hasRoe = /engagement|roe|rules/i.test(body || "");
    expect(hasRoe).toBe(true);
    await snap(page, "K5-engagement-panel");
  });

  test("K6. Tools — Onboarding Guide modal", async ({ page }) => {
    await page.goto("/tools");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // Click HOW TO ADD button
    const howToBtn = page.locator('button:has-text("HOW TO ADD")').first();
    if (await howToBtn.isVisible().catch(() => false)) {
      await howToBtn.click();
      await page.waitForTimeout(500);
      await snap(page, "K6a-onboarding-guide");

      // Verify guide content
      const body = await page.locator("body").textContent();
      const hasScaffold = /scaffold|implement|configure/i.test(body || "");
      expect(hasScaffold).toBe(true);

      // Close
      const closeBtn = page.locator('button:has-text("CLOSE"), button:has-text("Close")').first();
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
        await page.waitForTimeout(300);
      }
    }
    await snap(page, "K6b-guide-closed");
  });

  // ──────────────────────────────────────────────────────────────
  //  Cleanup: Hard reset the write operation
  // ──────────────────────────────────────────────────────────────

  test("Z. Cleanup — hard reset write operation", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations/${writeOpId}/reset`);
    expect(resp.status()).toBe(204);

    // Verify operation is back to planning
    const opResp = await page.request.get(`${API}/operations/${writeOpId}`);
    expect(opResp.status()).toBe(200);
    const op = await opResp.json();
    expect(op.status).toBe("planning");
    expect(op.ooda_iteration_count).toBe(0);
  });
});
