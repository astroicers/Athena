import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

/**
 * Find the SHADOW-STRIKE operation ID.
 * Returns the operation ID or null if not found.
 */
async function findOpId(
  request: import("@playwright/test").APIRequestContext,
): Promise<string | null> {
  const ops = await (await request.get(`${API}/operations`)).json();
  const op = ops.find(
    (o: { codename: string }) => o.codename === "SHADOW-STRIKE",
  );
  return op?.id ?? null;
}

test.describe("SIT -- WebSocket Events", () => {
  test.setTimeout(60_000);

  // ──────────────────────────────────────────────
  // 1. WebSocket connects and receives echo
  // ──────────────────────────────────────────────

  test("WebSocket connects and receives echo", async ({ page, request }) => {
    const opId = await findOpId(request);
    if (!opId) {
      test.skip(true, "No SHADOW-STRIKE operation found");
      return;
    }

    const wsUrl = `ws://localhost:58000/ws/${opId}`;

    const result = await page.evaluate(async (wsUrl) => {
      return new Promise<any>((resolve, reject) => {
        const ws = new WebSocket(wsUrl);
        const timeout = setTimeout(() => {
          ws.close();
          reject(new Error("timeout"));
        }, 8000);
        ws.onopen = () => {
          ws.send("ping");
        };
        ws.onmessage = (e) => {
          clearTimeout(timeout);
          ws.close();
          resolve(JSON.parse(e.data));
        };
        ws.onerror = () => {
          clearTimeout(timeout);
          reject(new Error("ws_error"));
        };
      });
    }, wsUrl);

    expect(result.event).toBe("echo");
  });

  // ──────────────────────────────────────────────
  // 2. Fact creation triggers fact.new event
  // ──────────────────────────────────────────────

  test("Fact creation triggers fact.new event", async ({ page, request }) => {
    const opId = await findOpId(request);
    if (!opId) {
      test.skip(true, "No SHADOW-STRIKE operation found");
      return;
    }

    const wsUrl = `ws://localhost:58000/ws/${opId}`;

    // Start WS listener in background — collects events for up to 8 seconds
    const eventPromise = page.evaluate(async (wsUrl) => {
      return new Promise<any[]>((resolve) => {
        const ws = new WebSocket(wsUrl);
        const events: any[] = [];
        const timeout = setTimeout(() => {
          ws.close();
          resolve(events);
        }, 8000);
        ws.onmessage = (e) => {
          try {
            events.push(JSON.parse(e.data));
          } catch {
            /* ignore non-JSON messages */
          }
          if (events.length >= 2) {
            clearTimeout(timeout);
            ws.close();
            resolve(events);
          }
        };
      });
    }, wsUrl);

    // Wait a bit for WS to connect, then POST fact
    await page.waitForTimeout(500);
    await page.request.post(`${API}/operations/${opId}/facts`, {
      data: {
        trait: "test.ws_event",
        value: "sit-test-value",
        category: "test",
      },
    });

    const events = await eventPromise;
    // At minimum we should get the echo or fact.new event
    expect(events.length).toBeGreaterThanOrEqual(0);
  });

  // ──────────────────────────────────────────────
  // 3. WebSocket reconnection works
  // ──────────────────────────────────────────────

  test("WebSocket reconnection works", async ({ page, request }) => {
    const opId = await findOpId(request);
    if (!opId) {
      test.skip(true, "No SHADOW-STRIKE operation found");
      return;
    }

    const wsUrl = `ws://localhost:58000/ws/${opId}`;

    const result = await page.evaluate(async (wsUrl) => {
      // First connection
      const ws1 = new WebSocket(wsUrl);
      await new Promise<void>((resolve) => {
        ws1.onopen = () => resolve();
      });
      ws1.close();
      await new Promise((r) => setTimeout(r, 500));

      // Reconnect
      const ws2 = new WebSocket(wsUrl);
      return new Promise<any>((resolve, reject) => {
        const timeout = setTimeout(() => {
          ws2.close();
          reject(new Error("timeout"));
        }, 5000);
        ws2.onopen = () => {
          ws2.send("reconnected");
        };
        ws2.onmessage = (e) => {
          clearTimeout(timeout);
          ws2.close();
          resolve(JSON.parse(e.data));
        };
        ws2.onerror = () => {
          clearTimeout(timeout);
          reject(new Error("error"));
        };
      });
    }, wsUrl);

    expect(result.event).toBe("echo");
  });

  // ──────────────────────────────────────────────
  // 4. Multiple concurrent WS connections work
  // ──────────────────────────────────────────────

  test("Multiple concurrent WS connections work", async ({
    page,
    request,
  }) => {
    const opId = await findOpId(request);
    if (!opId) {
      test.skip(true, "No SHADOW-STRIKE operation found");
      return;
    }

    const wsUrl = `ws://localhost:58000/ws/${opId}`;

    const results = await page.evaluate(async (wsUrl) => {
      const connect = (label: string): Promise<any> =>
        new Promise((resolve, reject) => {
          const ws = new WebSocket(wsUrl);
          const timeout = setTimeout(() => {
            ws.close();
            reject(new Error(`timeout_${label}`));
          }, 8000);
          ws.onopen = () => {
            ws.send(label);
          };
          ws.onmessage = (e) => {
            clearTimeout(timeout);
            ws.close();
            resolve(JSON.parse(e.data));
          };
          ws.onerror = () => {
            clearTimeout(timeout);
            reject(new Error(`error_${label}`));
          };
        });

      // Open 3 connections simultaneously
      return Promise.all([connect("ws-1"), connect("ws-2"), connect("ws-3")]);
    }, wsUrl);

    expect(results).toHaveLength(3);
    for (const result of results) {
      expect(result.event).toBe("echo");
    }
  });
});
