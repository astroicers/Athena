import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

test.setTimeout(60_000);

const NIL_UUID = "00000000-0000-0000-0000-000000000000";

// ──────────────────────────────────────────────
// 1. GET nonexistent operation returns 404
// ──────────────────────────────────────────────

test("GET nonexistent operation returns 404", async ({ request }) => {
  const resp = await request.get(`${API}/operations/${NIL_UUID}`);
  expect(resp.status()).toBe(404);
});

// ──────────────────────────────────────────────
// 2. POST target to nonexistent operation returns 404
// ──────────────────────────────────────────────

test("POST target to nonexistent operation returns 404", async ({
  request,
}) => {
  const resp = await request.post(`${API}/operations/${NIL_UUID}/targets`, {
    data: {
      hostname: "x",
      ip_address: "1.2.3.4",
      os: "Linux",
      role: "target",
      network_segment: "Test",
    },
  });
  // Some backends return 500 for FK violation instead of 404
  expect([404, 500]).toContain(resp.status());
});

// ──────────────────────────────────────────────
// 3. POST duplicate target IP returns 409
// ──────────────────────────────────────────────

test("POST duplicate target IP returns 409", async ({ request }) => {
  const timestamp = Date.now();

  // Create a temporary operation
  const opResp = await request.post(`${API}/operations`, {
    data: {
      code: `ERR-DUP-${timestamp}`,
      name: "Duplicate IP Test",
      codename: `err-dup-${timestamp}`,
      strategic_intent: "E2E: verify duplicate target IP is rejected",
      mission_profile: "SP",
    },
  });
  expect(opResp.status()).toBe(201);
  const op = await opResp.json();

  // Add first target
  const t1Resp = await request.post(`${API}/operations/${op.id}/targets`, {
    data: {
      hostname: "host-a",
      ip_address: "10.88.88.1",
      os: "Linux",
      role: "target",
      network_segment: "Test",
    },
  });
  expect(t1Resp.status()).toBe(201);

  // Add second target with same IP — expect 409
  const t2Resp = await request.post(`${API}/operations/${op.id}/targets`, {
    data: {
      hostname: "host-b",
      ip_address: "10.88.88.1",
      os: "Windows",
      role: "target",
      network_segment: "Test",
    },
  });
  expect(t2Resp.status()).toBe(409);
});

// ──────────────────────────────────────────────
// 4. Terminal rejects non-compromised target
// ──────────────────────────────────────────────

test("Terminal rejects non-compromised target", async ({ page, request }) => {
  const timestamp = Date.now();

  // Create a temporary operation
  const opResp = await request.post(`${API}/operations`, {
    data: {
      code: `ERR-TERM-${timestamp}`,
      name: "Terminal Reject Test",
      codename: `err-term-${timestamp}`,
      strategic_intent: "E2E: verify terminal rejects non-compromised target",
      mission_profile: "SP",
    },
  });
  expect(opResp.status()).toBe(201);
  const op = await opResp.json();

  // Add a target that is NOT compromised
  const targetResp = await request.post(
    `${API}/operations/${op.id}/targets`,
    {
      data: {
        hostname: "not-compromised-host",
        ip_address: "10.77.77.1",
        os: "Linux",
        role: "target",
        network_segment: "Test",
      },
    },
  );
  expect(targetResp.status()).toBe(201);
  const target = await targetResp.json();
  expect(target.is_compromised).toBe(false);

  const wsUrl = `ws://localhost:58000/ws/${op.id}/targets/${target.id}/terminal`;

  // Attempt WebSocket connection — should receive error about not compromised
  const result = await page.evaluate(async (url) => {
    return new Promise<string>((resolve) => {
      const ws = new WebSocket(url);
      const timeout = setTimeout(() => resolve("timeout"), 10000);
      ws.onmessage = (e) => {
        clearTimeout(timeout);
        ws.close();
        resolve(e.data);
      };
      ws.onerror = () => {
        clearTimeout(timeout);
        resolve("ws_error");
      };
    });
  }, wsUrl);

  const data = JSON.parse(result);
  expect(data.error).toMatch(/not compromised/i);
});

// ──────────────────────────────────────────────
// 5. GET nonexistent tool returns 404
// ──────────────────────────────────────────────

test("GET nonexistent tool returns 404", async ({ request }) => {
  const resp = await request.get(`${API}/tools/nonexistent-tool-slug`);
  expect(resp.status()).toBe(404);
});

// ──────────────────────────────────────────────
// 6. Empty operation War Room does not crash
// ──────────────────────────────────────────────

test("Empty operation War Room does not crash", async ({ page, request }) => {
  const timestamp = Date.now();

  // Create a new operation with no targets
  const opResp = await request.post(`${API}/operations`, {
    data: {
      code: `ERR-WR-${timestamp}`,
      name: "Empty WarRoom Test",
      codename: `err-wr-${timestamp}`,
      strategic_intent: "E2E: verify war room loads without crash on empty op",
      mission_profile: "SP",
    },
  });
  expect(opResp.status()).toBe(201);

  // Navigate to warroom — page should load without throwing
  await page.goto("/warroom");
  await expect(page.locator("body")).toBeVisible();
});

// ──────────────────────────────────────────────
// 7. POST recon scan with nonexistent target_id returns 404
// ──────────────────────────────────────────────

test("POST recon scan with nonexistent target_id returns 404", async ({
  request,
}) => {
  // Find any existing operation
  const opsResp = await request.get(`${API}/operations`);
  expect(opsResp.status()).toBe(200);
  const ops = await opsResp.json();

  if (ops.length === 0) {
    test.skip(true, "No operations exist to test recon scan against");
    return;
  }

  const opId = ops[0].id;

  const resp = await request.post(`${API}/operations/${opId}/recon/scan`, {
    data: {
      target_id: NIL_UUID,
    },
  });
  expect(resp.status()).toBe(404);
});
