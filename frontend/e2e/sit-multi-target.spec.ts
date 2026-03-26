import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

test.describe.serial("SIT Multi-Target Lifecycle Management", () => {
  // Shared state across serial tests
  let operationId: string;
  let targetAId: string;
  let targetBId: string;
  let targetCId: string;
  const timestamp = Date.now();

  test.setTimeout(60_000);

  // ──────────────────────────────────────────────
  // Step 1: Create Operation
  // ──────────────────────────────────────────────

  test("01. Create operation via API", async ({ page }) => {
    const resp = await page.request.post(`${API}/operations`, {
      data: {
        code: `SIT-MT-${timestamp}`,
        name: "SIT Multi-Target Test",
        codename: `sit-mt-${timestamp}`,
        strategic_intent: "SIT: multi-target lifecycle validation",
        mission_profile: "SP",
      },
    });
    expect(resp.status()).toBe(201);
    const op = await resp.json();
    operationId = op.id;
    expect(operationId).toBeTruthy();
  });

  // ──────────────────────────────────────────────
  // Step 2: Add 3 Targets
  // ──────────────────────────────────────────────

  test("02. Add target-a (10.99.1.1)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/targets`,
      {
        data: {
          hostname: "target-a",
          ip_address: "10.99.1.1",
          os: "Linux",
          role: "target",
          network_segment: "Internal",
        },
      },
    );
    expect(resp.status()).toBe(201);
    const target = await resp.json();
    targetAId = target.id;
    expect(target.ip_address).toBe("10.99.1.1");
  });

  test("02b. Add target-b (10.99.1.2)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/targets`,
      {
        data: {
          hostname: "target-b",
          ip_address: "10.99.1.2",
          os: "Windows",
          role: "target",
          network_segment: "DMZ",
        },
      },
    );
    expect(resp.status()).toBe(201);
    const target = await resp.json();
    targetBId = target.id;
    expect(target.ip_address).toBe("10.99.1.2");
  });

  test("02c. Add target-c (10.99.1.3)", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/targets`,
      {
        data: {
          hostname: "target-c",
          ip_address: "10.99.1.3",
          os: "Linux",
          role: "target",
          network_segment: "Internal",
        },
      },
    );
    expect(resp.status()).toBe(201);
    const target = await resp.json();
    targetCId = target.id;
    expect(target.ip_address).toBe("10.99.1.3");
  });

  // ──────────────────────────────────────────────
  // Step 3: Set target-a active, verify
  // ──────────────────────────────────────────────

  test("03. Set target-a active and verify", async ({ page }) => {
    const patchResp = await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetAId } },
    );
    expect(patchResp.status()).toBe(200);

    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets`,
    );
    expect(resp.status()).toBe(200);
    const targets = await resp.json();
    const a = targets.find((t: { id: string }) => t.id === targetAId);
    expect(a.is_active).toBe(true);
  });

  // ──────────────────────────────────────────────
  // Step 4: Set target-b active, verify switching
  // ──────────────────────────────────────────────

  test("04. Set target-b active — target-a becomes inactive", async ({ page }) => {
    const patchResp = await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetBId } },
    );
    expect(patchResp.status()).toBe(200);

    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets`,
    );
    expect(resp.status()).toBe(200);
    const targets = await resp.json();

    const a = targets.find((t: { id: string }) => t.id === targetAId);
    const b = targets.find((t: { id: string }) => t.id === targetBId);
    expect(a.is_active).toBe(false);
    expect(b.is_active).toBe(true);
  });

  // ──────────────────────────────────────────────
  // Step 5: Deactivate all targets
  // ──────────────────────────────────────────────

  test("05. Deactivate all targets", async ({ page }) => {
    const patchResp = await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: "" } },
    );
    expect(patchResp.status()).toBe(200);

    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets`,
    );
    expect(resp.status()).toBe(200);
    const targets = await resp.json();

    for (const t of targets) {
      expect(t.is_active).toBe(false);
    }
  });

  // ──────────────────────────────────────────────
  // Step 6: Set target-c active, verify
  // ──────────────────────────────────────────────

  test("06. Set target-c active and verify", async ({ page }) => {
    const patchResp = await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: targetCId } },
    );
    expect(patchResp.status()).toBe(200);

    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets`,
    );
    expect(resp.status()).toBe(200);
    const targets = await resp.json();
    const c = targets.find((t: { id: string }) => t.id === targetCId);
    expect(c.is_active).toBe(true);
  });

  // ──────────────────────────────────────────────
  // Step 7: Delete inactive target-a → 204
  // ──────────────────────────────────────────────

  test("07. Delete inactive target-a succeeds (204)", async ({ page }) => {
    const resp = await page.request.delete(
      `${API}/operations/${operationId}/targets/${targetAId}`,
    );
    expect(resp.status()).toBe(204);
  });

  // ──────────────────────────────────────────────
  // Step 8: Try delete active target-c → 400
  // ──────────────────────────────────────────────

  test("08. Delete active target-c fails (400)", async ({ page }) => {
    const resp = await page.request.delete(
      `${API}/operations/${operationId}/targets/${targetCId}`,
    );
    // Backend returns 400 or 409 for active target deletion
    expect([400, 409]).toContain(resp.status());
    const body = await resp.json();
    expect(JSON.stringify(body).toLowerCase()).toContain("active");
  });

  // ──────────────────────────────────────────────
  // Step 9: Verify 2 targets remain
  // ──────────────────────────────────────────────

  test("09. GET targets — 2 remain (target-b and target-c)", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets`,
    );
    expect(resp.status()).toBe(200);
    const targets = await resp.json();
    expect(targets).toHaveLength(2);

    const ids = targets.map((t: { id: string }) => t.id);
    expect(ids).toContain(targetBId);
    expect(ids).toContain(targetCId);
  });

  // ──────────────────────────────────────────────
  // Step 10: Deactivate target-c, delete it, verify only target-b remains
  // ──────────────────────────────────────────────

  test("10. Deactivate target-c, delete it, verify only target-b remains", async ({ page }) => {
    // Deactivate all
    const deactivateResp = await page.request.patch(
      `${API}/operations/${operationId}/targets/active`,
      { data: { target_id: "" } },
    );
    expect(deactivateResp.status()).toBe(200);

    // Delete target-c
    const deleteResp = await page.request.delete(
      `${API}/operations/${operationId}/targets/${targetCId}`,
    );
    expect(deleteResp.status()).toBe(204);

    // Verify only target-b remains
    const resp = await page.request.get(
      `${API}/operations/${operationId}/targets`,
    );
    expect(resp.status()).toBe(200);
    const targets = await resp.json();
    expect(targets).toHaveLength(1);
    expect(targets[0].id).toBe(targetBId);
  });
});
