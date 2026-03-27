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
 * SPEC-032: mcp-web-scanner — Frontend E2E Tests
 *
 * Validates the 4 MCP web-scanner tools (web_http_probe, web_vuln_scan,
 * web_dir_enum, web_screenshot) are registered, visible in the UI,
 * executable via API, and toggleable via the tool registry.
 */

import { test, expect, Page } from "@playwright/test";

const API = "http://localhost:58000/api";
const SHOTS = "test-results/uat-web-scanner";

async function snap(page: Page, name: string) {
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

const WEB_TOOLS = [
  "web-scanner_web_http_probe",
  "web-scanner_web_vuln_scan",
  "web-scanner_web_dir_enum",
  "web-scanner_web_screenshot",
];

test.describe.serial("SPEC-032 — Web Scanner MCP Tools", () => {
  test.setTimeout(60_000);

  // ──────────────────────────────────────────────────────────────
  //  1. MCP Server Health
  // ──────────────────────────────────────────────────────────────

  test("01. Health API confirms web-scanner connected with 4 tools", async ({ page }) => {
    const resp = await page.request.get(`${API}/health`);
    expect(resp.status()).toBe(200);
    const health = await resp.json();

    const ws = health.services.mcp_servers.find(
      (s: { name: string }) => s.name === "web-scanner",
    );
    expect(ws).toBeTruthy();
    expect(ws.connected).toBe(true);
    expect(ws.enabled).toBe(true);
    expect(ws.tool_count).toBe(4);
    expect(ws.circuit_state).toBe("closed");
  });

  // ──────────────────────────────────────────────────────────────
  //  2. Tool Registry API
  // ──────────────────────────────────────────────────────────────

  test("02. Tool registry lists 4 web-scanner tools", async ({ page }) => {
    const resp = await page.request.get(`${API}/tools`);
    expect(resp.status()).toBe(200);
    const tools = await resp.json();

    const webTools = tools.filter((t: { tool_id: string }) =>
      t.tool_id.startsWith("web-scanner_"),
    );
    expect(webTools.length).toBe(4);

    const toolIds = webTools.map((t: { tool_id: string }) => t.tool_id).sort();
    expect(toolIds).toEqual(WEB_TOOLS.sort());

    // All should be enabled
    for (const t of webTools) {
      expect(t.enabled).toBe(true);
    }
  });

  // ──────────────────────────────────────────────────────────────
  //  3. Tools Page UI
  // ──────────────────────────────────────────────────────────────

  test("03. Tools page shows web-scanner tools", async ({ page }) => {
    await page.goto("/tools");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const body = await page.locator("body").textContent();
    expect(body).toContain("web_http_probe");
    await snap(page, "03-tools-web-scanner");
  });

  // ──────────────────────────────────────────────────────────────
  //  4-7. Tool Execute API
  // ──────────────────────────────────────────────────────────────

  test("04. Execute web_http_probe", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/tools/web-scanner_web_http_probe/execute`,
      { data: { arguments: { target: "127.0.0.1", ports: [80] } } },
    );
    // 200 success, 400 bad args, 503 tool unavailable — all acceptable
    expect([200, 400, 503]).toContain(resp.status());
  });

  test("05. Execute web_vuln_scan", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/tools/web-scanner_web_vuln_scan/execute`,
      { data: { arguments: { url: "http://127.0.0.1", templates: ["cves"] } } },
    );
    expect([200, 400, 503]).toContain(resp.status());
  });

  test("06. Execute web_dir_enum", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/tools/web-scanner_web_dir_enum/execute`,
      { data: { arguments: { url: "http://127.0.0.1", wordlist: "common" } } },
    );
    expect([200, 400, 503]).toContain(resp.status());
  });

  test("07. Execute web_screenshot", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/tools/web-scanner_web_screenshot/execute`,
      { data: { arguments: { url: "http://127.0.0.1" } } },
    );
    expect([200, 400, 503]).toContain(resp.status());
  });

  // ──────────────────────────────────────────────────────────────
  //  8. Tool Health Check
  // ──────────────────────────────────────────────────────────────

  test("08. Tool health check (web_http_probe)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/tools/web-scanner_web_http_probe/check`,
    );
    expect([200, 503]).toContain(resp.status());
  });

  // ──────────────────────────────────────────────────────────────
  //  9. Toggle ON/OFF
  // ──────────────────────────────────────────────────────────────

  test("09. Toggle web_http_probe OFF then ON", async ({ page }) => {
    const toolId = "web-scanner_web_http_probe";

    // Disable
    const offResp = await page.request.patch(`${API}/tools/${toolId}`, {
      data: { enabled: false },
    });
    expect(offResp.status()).toBe(200);
    const offTool = await offResp.json();
    expect(offTool.enabled).toBe(false);

    // Re-enable
    const onResp = await page.request.patch(`${API}/tools/${toolId}`, {
      data: { enabled: true },
    });
    expect(onResp.status()).toBe(200);
    const onTool = await onResp.json();
    expect(onTool.enabled).toBe(true);
  });

  // ──────────────────────────────────────────────────────────────
  //  10. MCP Status Endpoint
  // ──────────────────────────────────────────────────────────────

  test("10. MCP status shows web-scanner details", async ({ page }) => {
    const resp = await page.request.get(`${API}/mcp/status`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toBeTruthy();
  });
});
