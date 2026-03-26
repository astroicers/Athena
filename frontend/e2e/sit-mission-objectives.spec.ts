import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

test.describe.serial("SIT — Mission Steps & Objectives", () => {
  let operationId: string;
  let targetId: string;
  let stepId1: string;
  let stepId2: string;
  let objectiveId: string;
  const stepBase = Math.floor(Date.now() / 1000) % 10000;

  test.setTimeout(60_000);

  // ──────────────────────────────────────────────
  // Step 1: Find SHADOW-STRIKE operation and target
  // ──────────────────────────────────────────────

  test("01. Find SHADOW-STRIKE operation and target", async ({ page }) => {
    const resp = await page.request.get(`${API}/operations`);
    expect(resp.status()).toBe(200);
    const ops = await resp.json();

    const op = ops.find((o: { codename: string }) => o.codename === "SHADOW-STRIKE");
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    operationId = op.id;
    expect(operationId).toBeTruthy();

    const targetsResp = await page.request.get(`${API}/operations/${op.id}/targets`);
    expect(targetsResp.status()).toBe(200);
    const targets = await targetsResp.json();
    targetId = targets[0]?.id ?? "unknown";
  });

  // ──────────────────────────────────────────────
  // Mission Steps
  // ──────────────────────────────────────────────

  let baselineStepCount: number;

  test("02. GET /mission/steps — record baseline", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/mission/steps`,
    );
    expect(resp.status()).toBe(200);
    const steps = await resp.json();
    baselineStepCount = steps.length;
  });

  test("03. POST step 1 — Exploit vsftpd", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/mission/steps`,
      {
        data: {
          step_number: stepBase,
          technique_id: "T1190",
          technique_name: "Exploit vsftpd 2.3.4",
          target_id: targetId,
          target_label: "metasploitable2",
          engine: "metasploit",
        },
      },
    );
    expect(resp.status()).toBe(201);
    const body = await resp.json();
    stepId1 = body.id;
    expect(stepId1).toBeTruthy();
  });

  test("04. POST step 2 — SSH Lateral", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/mission/steps`,
      {
        data: {
          step_number: stepBase + 1,
          technique_id: "T1021.004",
          technique_name: "SSH Lateral Movement",
          target_id: targetId,
          target_label: "metasploitable2",
          engine: "ssh",
        },
      },
    );
    expect(resp.status()).toBe(201);
    const body = await resp.json();
    stepId2 = body.id;
    expect(stepId2).toBeTruthy();
  });

  test("05. GET steps — count increased", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/mission/steps`,
    );
    expect(resp.status()).toBe(200);
    const steps = await resp.json();
    expect(steps.length).toBe(baselineStepCount + 2);
  });

  test("06. PATCH step 1 → running", async ({ page }) => {
    const url = `${API}/operations/${operationId}/mission/steps/${stepId1}`;
    // Verify step exists first
    const check = await page.request.get(
      `${API}/operations/${operationId}/mission/steps`,
    );
    const steps = await check.json();
    const found = steps.find((s: { id: string }) => s.id === stepId1);
    expect(found).toBeTruthy();

    const resp = await page.request.patch(url, {
      data: { status: "running" },
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("running");
  });

  test("07. PATCH step 1 → completed", async ({ page }) => {
    const resp = await page.request.patch(
      `${API}/operations/${operationId}/mission/steps/${stepId1}`,
      { data: { status: "completed" } },
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("completed");
  });

  test("08. PATCH step 2 → skipped", async ({ page }) => {
    const resp = await page.request.patch(
      `${API}/operations/${operationId}/mission/steps/${stepId2}`,
      { data: { status: "skipped" } },
    );
    expect(resp.status()).toBe(200);
  });

  // ──────────────────────────────────────────────
  // Objectives
  // ──────────────────────────────────────────────

  test("09. POST objective", async ({ page }) => {
    const resp = await page.request.post(
      `${API}/operations/${operationId}/objectives`,
      {
        data: {
          objective: "Obtain root access on metasploitable2",
          category: "tactical",
          priority: 1,
        },
      },
    );
    expect(resp.status()).toBe(201);
    const body = await resp.json();
    objectiveId = body.id;
    expect(objectiveId).toBeTruthy();
  });

  test("10. GET objectives includes new", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/operations/${operationId}/objectives`,
    );
    expect(resp.status()).toBe(200);
    const objectives = await resp.json();
    const ours = objectives.find((o: { id: string }) => o.id === objectiveId);
    expect(ours).toBeTruthy();
    expect(ours.status).toBe("pending");
  });

  test("11. PATCH objective → achieved", async ({ page }) => {
    const patchResp = await page.request.patch(
      `${API}/operations/${operationId}/objectives/${objectiveId}`,
      { data: { status: "achieved" } },
    );
    expect(patchResp.status()).toBe(200);

    const getResp = await page.request.get(
      `${API}/operations/${operationId}/objectives`,
    );
    expect(getResp.status()).toBe(200);
    const objectives = await getResp.json();
    const ours = objectives.find((o: { id: string }) => o.id === objectiveId);
    expect(ours).toBeTruthy();
    expect(ours.status).toBe("achieved");
  });
});
