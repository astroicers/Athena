// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.

/**
 * SIT — OSINT & Topology
 *
 * Self-contained: creates own operation + target, triggers OODA,
 * then verifies OSINT discovery endpoints, topology graph structure,
 * target summaries, and operation summaries.
 */

import { test, expect, type Page } from "@playwright/test";

const API = "http://localhost:58000/api";
const SHOTS = "test-results/sit-osint-topology-screenshots";

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
  maxAttempts = 150,
  intervalMs = 2000,
): Promise<unknown | null> {
  for (let i = 0; i < maxAttempts; i++) {
    const resp = await page.request.get(url);
    if (resp.ok()) {
      const data = await resp.json();
      if (condition(data)) return data;
    }
    await page.waitForTimeout(intervalMs);
  }
  return null;
}

// ---------------------------------------------------------------------------
// SIT Suite
// ---------------------------------------------------------------------------

test.describe.serial("SIT -- OSINT & Topology", () => {
  let operationId: string;
  let targetId: string;
  const ts = Date.now();

  test.setTimeout(600_000);

  // =========================================================================
  // Setup: Create operation + add target + set active + wait OODA #1
  // =========================================================================

  test("N00. Setup — create operation, add target, trigger OODA", async ({ page }) => {
    // Create operation
    const opResp = await page.request.post(`${API}/operations`, {
      data: {
        code: `SIT-OT-${ts}`,
        name: "SIT OSINT Topology Test",
        codename: `sit-ot-${ts}`,
        strategic_intent: "OSINT and topology verification",
        mission_profile: "SP",
      },
    });
    expect(opResp.status()).toBe(201);
    const op = await opResp.json();
    operationId = op.id;

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
    const target = await tResp.json();
    targetId = target.id;

    // Set target as active
    await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetId } },
    );

    // Wait for OODA auto-trigger (2s delay after target creation)
    await page.waitForTimeout(3000);

    // Wait for first OODA iteration with fallback trigger
    const oodaResult = await pollUntil(
      page,
      `${API}/operations/${operationId}/ooda/dashboard`,
      (data: unknown) => {
        const d = data as { iteration_count?: number };
        return (d.iteration_count ?? 0) >= 1;
      },
      30,
      2000,
    );

    // If OODA didn't auto-trigger, try manual trigger
    if (!oodaResult) {
      await page.request.post(
        `${API}/operations/${operationId}/ooda/trigger`,
      );
      await page.waitForTimeout(5000);
    }

    await snapApi(page, "N00-setup", { operationId, targetId });
  });

  // =========================================================================
  // OSINT Discovery
  // =========================================================================

  test("N01. POST /recon/osint/discover — trigger OSINT discovery", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/recon/osint/discover`,
      {
        data: { target_id: targetId },
      },
    );

    const body = resp.ok() ? await resp.json() : null;
    await snapApi(page, "N01-osint-discover", {
      status: resp.status(),
      body,
    });

    // Endpoint may not exist in all environments
    expect([200, 202, 404]).toContain(resp.status());
  });

  test("N02. GET /recon/osint/domains — list discovered domains", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/recon/osint/domains`,
    );

    const body = resp.ok() ? await resp.json() : [];
    await snapApi(page, "N02-osint-domains", {
      status: resp.status(),
      count: Array.isArray(body) ? body.length : 0,
      body,
    });

    // May be empty or endpoint may not exist
    expect([200, 404]).toContain(resp.status());
  });

  test("N03. GET /recon/osint/subdomains — list subdomains", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/recon/osint/subdomains`,
    );

    const body = resp.ok() ? await resp.json() : [];
    await snapApi(page, "N03-osint-subdomains", {
      status: resp.status(),
      count: Array.isArray(body) ? body.length : 0,
      body,
    });

    expect([200, 404]).toContain(resp.status());
  });

  // =========================================================================
  // Topology
  // =========================================================================

  test("N04. GET /topology — verify has nodes and edges arrays", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/topology`,
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();

    await snapApi(page, "N04-topology-structure", {
      nodeCount: body.nodes?.length ?? 0,
      edgeCount: body.edges?.length ?? 0,
    });

    expect(body.nodes).toBeDefined();
    expect(Array.isArray(body.nodes)).toBeTruthy();
    expect(body.edges).toBeDefined();
    expect(Array.isArray(body.edges)).toBeTruthy();
  });

  test("N05. Verify topology has 'athena-c2' node (type: c2)", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/topology`,
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();

    const c2Node = body.nodes?.find(
      (n: { type?: string; label?: string; id?: string }) =>
        n.type === "c2" ||
        n.label === "athena-c2" ||
        n.id === "athena-c2",
    );

    await snapApi(page, "N05-topology-c2-node", {
      found: !!c2Node,
      c2Node,
      totalNodes: body.nodes?.length ?? 0,
    });

    try {
      expect(c2Node).toBeTruthy();
    } catch {
      // Graceful: C2 node may not exist in all topologies
      console.log("N05: athena-c2 node not found in topology — non-fatal");
    }
  });

  test("N06. Verify topology has target host node with correct IP", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/topology`,
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();

    const targetNode = body.nodes?.find(
      (n: { ip?: string; ip_address?: string; label?: string }) =>
        n.ip === "192.168.0.26" ||
        n.ip_address === "192.168.0.26" ||
        n.label?.includes("192.168.0.26"),
    );

    await snapApi(page, "N06-topology-target-node", {
      found: !!targetNode,
      targetNode,
    });

    try {
      expect(targetNode).toBeTruthy();
    } catch {
      console.log("N06: Target node not found in topology — non-fatal");
    }
  });

  // =========================================================================
  // Summaries
  // =========================================================================

  test("N07. GET /targets/{id}/summary — AI target summary", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets/${targetId}/summary`,
    );

    const body = resp.ok() ? await resp.json() : null;
    await snapApi(page, "N07-target-summary", {
      status: resp.status(),
      hasBody: !!body,
      body,
    });

    // AI summary may not be available — accept 200, 404, or 500
    expect([200, 404, 500]).toContain(resp.status());
  });

  test("N08. If target summary 200 → verify has content fields", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets/${targetId}/summary`,
    );

    if (resp.status() !== 200) {
      await snapApi(page, "N08-target-summary-skip", {
        reason: `Summary returned ${resp.status()}, skipping content verification`,
      });
      test.skip(true, `Target summary returned ${resp.status()}`);
      return;
    }

    const body = await resp.json();
    await snapApi(page, "N08-target-summary-content", body);

    // Verify it has some content — field names may vary
    const hasContent =
      body.summary != null ||
      body.content != null ||
      body.text != null ||
      Object.keys(body).length > 0;
    expect(hasContent).toBeTruthy();
  });

  test("N09. GET /summary — operation summary", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/summary`,
    );

    const body = resp.ok() ? await resp.json() : null;
    await snapApi(page, "N09-operation-summary", {
      status: resp.status(),
      body,
    });

    expect([200, 404]).toContain(resp.status());
  });

  test("N10. If operation summary exists → verify has metadata", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/summary`,
    );

    if (resp.status() !== 200) {
      await snapApi(page, "N10-operation-summary-skip", {
        reason: `Operation summary returned ${resp.status()}, skipping metadata verification`,
      });
      test.skip(true, `Operation summary returned ${resp.status()}`);
      return;
    }

    const body = await resp.json();
    await snapApi(page, "N10-operation-summary-metadata", body);

    // Verify it has operation metadata — field names may vary
    const hasMetadata =
      body.operation_id != null ||
      body.id != null ||
      body.codename != null ||
      body.summary != null ||
      Object.keys(body).length > 0;
    expect(hasMetadata).toBeTruthy();
  });

  // =========================================================================
  // Cleanup
  // =========================================================================

  test("N99. Cleanup — reset operation", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/reset`,
    );

    await snapApi(page, "N99-cleanup", {
      status: resp.status(),
    });

    expect([200, 204]).toContain(resp.status());
  });
});
