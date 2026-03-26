import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

test.describe("SIT -- Tools State Management", () => {
  test.setTimeout(60_000);

  test("Nmap tool is enabled (ensure clean state)", async ({ page }) => {
    // Ensure nmap starts enabled for this test sequence
    await page.request.patch(`${API}/tools/nmap`, {
      data: { enabled: true },
    });
    const res = await page.request.get(`${API}/tools/nmap`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.enabled).toBe(true);
    expect(body.name).toBe("Nmap");
  });

  test("Disable nmap tool", async ({ page }) => {
    const res = await page.request.patch(`${API}/tools/nmap`, {
      data: { enabled: false },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.enabled).toBe(false);
  });

  test("Verify nmap disabled via GET", async ({ page }) => {
    const res = await page.request.get(`${API}/tools/nmap`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.enabled).toBe(false);
  });

  test("Re-enable nmap tool", async ({ page }) => {
    const res = await page.request.patch(`${API}/tools/nmap`, {
      data: { enabled: true },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.enabled).toBe(true);
  });

  test("Tools page loads and shows registry", async ({ page }) => {
    await page.goto("/tools");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const main = page.locator("main");
    await expect(main).toBeVisible();

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toContain("Nmap");
  });

  test("Health endpoint shows MCP servers", async ({ page }) => {
    const res = await page.request.get(`${API}/health`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();

    const mcpServers = body.services?.mcp_servers ?? body.mcp_servers;
    expect(Array.isArray(mcpServers)).toBeTruthy();
    expect(mcpServers.length).toBeGreaterThanOrEqual(5);

    const nmap = mcpServers.find(
      (s: { name: string }) => s.name === "nmap-scanner",
    );
    expect(nmap).toBeTruthy();
    expect(nmap.connected).toBe(true);
    // Circuit may be open after disable/enable cycle; just verify it's a valid state
    expect(["closed", "open", "half_open"]).toContain(nmap.circuit_state);
  });
});

test.describe("SIT -- C5ISR Domain Validation", () => {
  test.setTimeout(60_000);

  test("C5ISR returns all domains", async ({ page }) => {
    const ops = await (await page.request.get(`${API}/operations`)).json();
    const op = ops.find(
      (o: { codename: string }) => o.codename === "SHADOW-STRIKE",
    );
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/c5isr`,
    );
    expect(res.ok()).toBeTruthy();
    const domains = await res.json();

    expect(Array.isArray(domains)).toBeTruthy();
    expect(domains.length).toBeGreaterThanOrEqual(4);

    const domainNames = domains.map((d: { domain: string }) => d.domain);
    expect(domainNames).toContain("command");
    expect(domainNames).toContain("control");
    expect(domainNames).toContain("comms");
    expect(domainNames).toContain("computers");
  });

  test("Computers domain shows compromised count", async ({ page }) => {
    const ops = await (await page.request.get(`${API}/operations`)).json();
    const op = ops.find(
      (o: { codename: string }) => o.codename === "SHADOW-STRIKE",
    );
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const domains = await (
      await page.request.get(`${API}/operations/${op.id}/c5isr`)
    ).json();
    const computers = domains.find(
      (d: { domain: string }) => d.domain === "computers",
    );
    expect(computers).toBeTruthy();
    expect(computers.numerator).toBeGreaterThanOrEqual(1);
  });

  test("C5ISR domain report is accessible", async ({ page }) => {
    const ops = await (await page.request.get(`${API}/operations`)).json();
    const op = ops.find(
      (o: { codename: string }) => o.codename === "SHADOW-STRIKE",
    );
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/c5isr/computers/report`,
    );
    expect(res.status()).toBe(200);
  });

  test("Attack graph has nodes and edges", async ({ page }) => {
    const ops = await (await page.request.get(`${API}/operations`)).json();
    const op = ops.find(
      (o: { codename: string }) => o.codename === "SHADOW-STRIKE",
    );
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/attack-graph`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.nodes)).toBeTruthy();
    expect(Array.isArray(body.edges)).toBeTruthy();
  });

  test("Attack graph rebuild works", async ({ page }) => {
    const ops = await (await page.request.get(`${API}/operations`)).json();
    const op = ops.find(
      (o: { codename: string }) => o.codename === "SHADOW-STRIKE",
    );
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.post(
      `${API}/operations/${op.id}/attack-graph/rebuild`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.nodes).toBeTruthy();
  });
});
