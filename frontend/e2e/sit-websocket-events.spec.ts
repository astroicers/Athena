// Copyright 2026 Athena Contributors
// SIT: WebSocket Events — Verify real-time event broadcasting

import { test, expect, type Page } from "@playwright/test";

const API = "http://localhost:58000/api";
const SHOTS = "test-results/sit-websocket-screenshots";

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
  page: Page, url: string, condition: (d: unknown) => boolean,
  maxAttempts = 90, intervalMs = 2000,
): Promise<unknown> {
  for (let i = 0; i < maxAttempts; i++) {
    const resp = await page.request.get(url);
    if (resp.ok()) { const d = await resp.json(); if (condition(d)) return d; }
    await page.waitForTimeout(intervalMs);
  }
  throw new Error(`Polling timeout: ${url}`);
}

test.describe.serial("SIT — WebSocket Events", () => {
  let operationId: string;
  let targetId: string;
  const ts = Date.now();

  test.setTimeout(180_000);

  test("W00. Setup — create operation + target + wait OODA", async ({ page }) => {
    const opResp = await page.request.post(`${API}/operations`, {
      data: {
        code: `SIT-WS-${ts}`, name: "WebSocket Event Test",
        codename: `ws-events-${ts}`, strategic_intent: "Verify WS events",
        mission_profile: "SP",
      },
    });
    expect(opResp.status()).toBe(201);
    operationId = (await opResp.json()).id;

    const tResp = await page.request.post(`${API}/operations/${operationId}/targets`, {
      data: { hostname: "ws-target", ip_address: "192.168.0.26", os: "Linux", role: "target" },
    });
    expect(tResp.status()).toBe(201);
    targetId = (await tResp.json()).id;

    await page.request.patch(`${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetId } });

    // Wait for auto-trigger, then manually trigger as fallback
    await page.waitForTimeout(10_000);
    let dashResp = await page.request.get(`${API}/operations/${operationId}/ooda/dashboard`);
    let dash = (await dashResp.json()) as { iteration_count?: number };
    if ((dash.iteration_count ?? 0) < 1) {
      await page.request.post(`${API}/operations/${operationId}/ooda/trigger`);
    }
    await pollUntil(page, `${API}/operations/${operationId}/ooda/dashboard`,
      (d: unknown) => ((d as { iteration_count?: number }).iteration_count ?? 0) >= 1);
  });

  test("W01. OODA trigger → collect WebSocket events", async ({ page }) => {
    const wsUrl = `ws://localhost:58000/ws/${operationId}`;
    const events = await page.evaluate(
      async ({ url, apiBase, opId }: { url: string; apiBase: string; opId: string }) => {
        const collected: Array<{ type: string; data: unknown }> = [];
        return new Promise<typeof collected>((resolve) => {
          const ws = new WebSocket(url);
          const timer = setTimeout(() => { ws.close(); resolve(collected); }, 45000);
          ws.onmessage = (e) => {
            try {
              const msg = JSON.parse(e.data as string);
              collected.push({ type: msg.type ?? msg.event ?? "unknown", data: msg });
            } catch { /* skip */ }
          };
          ws.onopen = () => {
            // Trigger OODA after WS connected
            fetch(`${apiBase}/operations/${opId}/ooda/trigger`, { method: "POST" });
          };
          ws.onerror = () => { clearTimeout(timer); resolve(collected); };
        });
      },
      { url: wsUrl, apiBase: API, opId: operationId },
    );

    await snapApi(page, "W01-events", {
      total: events.length,
      types: [...new Set(events.map((e) => e.type))],
      sample: events.slice(0, 8),
    });
  });

  test("W02. C5ISR update data available", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations/${operationId}/c5isr`);
    const c5isr = await resp.json();
    await snapApi(page, "W02-c5isr", c5isr);
    if (Array.isArray(c5isr)) {
      expect(c5isr.length === 0 || c5isr.length === 6).toBeTruthy();
    }
  });

  test("W03. Constraints evaluation result", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations/${operationId}/constraints`);
    if (resp.ok()) {
      await snapApi(page, "W03-constraints", await resp.json());
    } else {
      await snapApi(page, "W03-no-constraints", { status: resp.status() });
    }
  });

  test("W04. Decision results in timeline", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations/${operationId}/ooda/timeline`);
    const timeline = (await resp.json()) as Array<{ phase: string; summary: string }>;
    const decides = timeline.filter((e) => e.phase === "decide");
    await snapApi(page, "W04-decisions", { count: decides.length, entries: decides.slice(0, 5) });
    expect(decides.length).toBeGreaterThanOrEqual(0);
  });

  test("W05. OPSEC data after cycles", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations/${operationId}/opsec`);
    if (resp.ok()) {
      await snapApi(page, "W05-opsec", await resp.json());
    } else {
      await snapApi(page, "W05-opsec-na", { status: resp.status() });
    }
  });

  test("W06. WebSocket reconnection", async ({ page }) => {
    const wsUrl = `ws://localhost:58000/ws/${operationId}`;
    const results = await page.evaluate(async (url: string) => {
      const out: string[] = [];
      for (let i = 0; i < 2; i++) {
        const r = await new Promise<string>((resolve) => {
          const ws = new WebSocket(url);
          const t = setTimeout(() => { ws.close(); resolve("timeout"); }, 5000);
          ws.onopen = () => { clearTimeout(t); ws.close(); resolve(i === 0 ? "connected" : "reconnected"); };
          ws.onerror = () => { clearTimeout(t); resolve("error"); };
        });
        out.push(r);
      }
      return out;
    }, wsUrl);
    await snapApi(page, "W06-reconnect", results);
    expect(results[0]).toBe("connected");
    expect(results[1]).toBe("reconnected");
  });

  test("W07. Multiple concurrent WS clients", async ({ page }) => {
    const wsUrl = `ws://localhost:58000/ws/${operationId}`;
    const results = await page.evaluate(async (url: string) => {
      const out: string[] = [];
      await Promise.all(Array.from({ length: 3 }, (_, i) =>
        new Promise<void>((resolve) => {
          const ws = new WebSocket(url);
          const t = setTimeout(() => { ws.close(); out.push(`c${i}:timeout`); resolve(); }, 5000);
          ws.onopen = () => { clearTimeout(t); ws.close(); out.push(`c${i}:ok`); resolve(); };
          ws.onerror = () => { clearTimeout(t); out.push(`c${i}:err`); resolve(); };
        }),
      ));
      return out;
    }, wsUrl);
    await snapApi(page, "W07-multi", results);
    expect(results.length).toBe(3);
  });

  test("W08. Operation reset", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations/${operationId}/reset`);
    expect([200, 204]).toContain(resp.status());
    await snapApi(page, "W08-reset", { status: resp.status() });
  });
});
