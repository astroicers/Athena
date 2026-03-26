import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

test.describe.serial("SIT — Operations CRUD Lifecycle", () => {
  // Shared state across serial tests
  let baselineCount: number;
  let opId1: string;
  let opId2: string;
  let opId3: string;
  const timestamp = Date.now();

  const codenames = [
    `IRON-FALCON-${timestamp}`,
    `STEEL-VIPER-${timestamp}`,
    `DARK-CONDOR-${timestamp}`,
  ];

  test.setTimeout(60_000);

  // ──────────────────────────────────────────────
  // Step 1: Record initial count
  // ──────────────────────────────────────────────

  test("01. GET /operations — record initial count", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations`);
    expect(resp.status()).toBe(200);
    const operations = await resp.json();
    expect(Array.isArray(operations)).toBe(true);
    baselineCount = operations.length;
  });

  // ──────────────────────────────────────────────
  // Step 2: Create 3 new operations
  // ──────────────────────────────────────────────

  test("02. Create 3 new operations", async ({ page }) => {
    const payloads = [
      {
        code: `SIT-CRUD-A-${timestamp}`,
        name: "SIT CRUD Operation A",
        codename: codenames[0],
        strategic_intent: "Validate CRUD create path A",
        mission_profile: "SP",
      },
      {
        code: `SIT-CRUD-B-${timestamp}`,
        name: "SIT CRUD Operation B",
        codename: codenames[1],
        strategic_intent: "Validate CRUD create path B",
        mission_profile: "SP",
      },
      {
        code: `SIT-CRUD-C-${timestamp}`,
        name: "SIT CRUD Operation C",
        codename: codenames[2],
        strategic_intent: "Validate CRUD create path C",
        mission_profile: "SP",
      },
    ];

    const ids: string[] = [];

    for (const payload of payloads) {
      const resp = await page.request.post(`${API}/operations`, {
        data: payload,
      });
      expect(resp.status()).toBe(201);
      const op = await resp.json();
      expect(op.id).toBeTruthy();
      ids.push(op.id);
    }

    opId1 = ids[0];
    opId2 = ids[1];
    opId3 = ids[2];
  });

  // ──────────────────────────────────────────────
  // Step 3: Verify count increased by 3
  // ──────────────────────────────────────────────

  test("03. GET /operations — count increased by 3", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations`);
    expect(resp.status()).toBe(200);
    const operations = await resp.json();
    expect(operations.length).toBe(baselineCount + 3);
  });

  // ──────────────────────────────────────────────
  // Step 4: Operations page shows new cards
  // ──────────────────────────────────────────────

  test("04. Operations page shows new cards", async ({ page }) => {
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const mainContent = await page.locator("main").textContent();
    const found = codenames.some(
      (codename) => mainContent && mainContent.includes(codename),
    );
    expect(found).toBe(true);
  });

  // ──────────────────────────────────────────────
  // Step 5: PATCH operation updates strategic_intent
  // ──────────────────────────────────────────────

  test("05. PATCH operation updates risk_threshold", async ({ page }) => {
    const patchResp = await page.request.patch(
      `${API}/operations/${opId1}`,
      { data: { risk_threshold: "high" } },
    );
    expect(patchResp.status()).toBe(200);

    const getResp = await page.request.get(`${API}/operations/${opId1}`);
    expect(getResp.status()).toBe(200);
    const op = await getResp.json();
    expect(op.risk_threshold).toBe("high");
  });

  // ──────────────────────────────────────────────
  // Step 6: Operation detail API returns correct data
  // ──────────────────────────────────────────────

  test("06. Operation detail API returns correct data", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations/${opId2}`);
    expect(resp.status()).toBe(200);
    const op = await resp.json();
    expect(op.status).toBe("planning");
    expect(op.mission_profile).toBe("SP");
    expect(op.ooda_iteration_count).toBe(0);
  });

  // ──────────────────────────────────────────────
  // Step 7: Cleanup — operations still accessible
  // ──────────────────────────────────────────────

  test("07. Cleanup — operations still accessible", async ({ page }) => {
    for (const id of [opId1, opId2, opId3]) {
      const resp = await page.request.get(`${API}/operations/${id}`);
      expect(resp.status()).toBe(200);
    }
  });
});
