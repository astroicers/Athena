import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

test.describe.serial("SIT — Playbook CRUD", () => {
  // Shared state across serial tests
  let baselineCount: number;
  let playbookId: string;

  test.setTimeout(60_000);

  // ──────────────────────────────────────────────
  // Step 1: Record baseline count
  // ──────────────────────────────────────────────

  test("01. GET /playbooks — record baseline count", async ({ page }) => {
    const resp = await page.request.get(`${API}/playbooks`);
    expect(resp.status()).toBe(200);
    const playbooks = await resp.json();
    expect(Array.isArray(playbooks)).toBe(true);
    baselineCount = playbooks.length;
  });

  // ──────────────────────────────────────────────
  // Step 2: POST creates playbook
  // ──────────────────────────────────────────────

  test("02. POST creates playbook", async ({ page }) => {
    const resp = await page.request.post(`${API}/playbooks`, {
      data: {
        mitre_id: "T1021.004",
        platform: "linux",
        command: "ssh user@target whoami",
        tags: ["sit-test"],
      },
    });
    expect(resp.status()).toBe(201);
    const playbook = await resp.json();
    expect(playbook.id).toBeTruthy();
    expect(playbook.source).toBe("user");
    playbookId = playbook.id;
  });

  // ──────────────────────────────────────────────
  // Step 3: GET by id returns playbook
  // ──────────────────────────────────────────────

  test("03. GET by id returns playbook", async ({ page }) => {
    const resp = await page.request.get(`${API}/playbooks/${playbookId}`);
    expect(resp.status()).toBe(200);
    const playbook = await resp.json();
    expect(playbook.mitre_id).toBe("T1021.004");
    expect(playbook.platform).toBe("linux");
    expect(playbook.command).toBe("ssh user@target whoami");
  });

  // ──────────────────────────────────────────────
  // Step 4: PATCH updates command
  // ──────────────────────────────────────────────

  test("04. PATCH updates command", async ({ page }) => {
    const resp = await page.request.patch(`${API}/playbooks/${playbookId}`, {
      data: { command: "ssh root@target id" },
    });
    expect(resp.status()).toBe(200);
    const playbook = await resp.json();
    expect(playbook.command).toBe("ssh root@target id");
  });

  // ──────────────────────────────────────────────
  // Step 5: GET confirms update
  // ──────────────────────────────────────────────

  test("05. GET confirms update", async ({ page }) => {
    const resp = await page.request.get(`${API}/playbooks/${playbookId}`);
    expect(resp.status()).toBe(200);
    const playbook = await resp.json();
    expect(playbook.command).toBe("ssh root@target id");
  });

  // ──────────────────────────────────────────────
  // Step 6: DELETE removes playbook
  // ──────────────────────────────────────────────

  test("06. DELETE removes playbook", async ({ page }) => {
    const resp = await page.request.delete(`${API}/playbooks/${playbookId}`);
    expect(resp.status()).toBe(204);
  });

  // ──────────────────────────────────────────────
  // Step 7: GET /playbooks count back to baseline
  // ──────────────────────────────────────────────

  test("07. GET /playbooks count back to baseline", async ({ page }) => {
    const resp = await page.request.get(`${API}/playbooks`);
    expect(resp.status()).toBe(200);
    const playbooks = await resp.json();
    expect(playbooks.length).toBe(baselineCount);
  });

  // ──────────────────────────────────────────────
  // Step 8: Filter by mitre_id
  // ──────────────────────────────────────────────

  test("08. Filter by mitre_id", async ({ page }) => {
    const resp = await page.request.get(
      `${API}/playbooks?mitre_id=T1059.001`,
    );
    expect(resp.status()).toBe(200);
    const playbooks = await resp.json();
    expect(Array.isArray(playbooks)).toBe(true);
    for (const pb of playbooks) {
      expect(pb.mitre_id).toBe("T1059.001");
    }
  });

  // ──────────────────────────────────────────────
  // Step 9: Filter by platform
  // ──────────────────────────────────────────────

  test("09. Filter by platform", async ({ page }) => {
    const resp = await page.request.get(`${API}/playbooks?platform=linux`);
    expect(resp.status()).toBe(200);
    const playbooks = await resp.json();
    expect(Array.isArray(playbooks)).toBe(true);
    for (const pb of playbooks) {
      expect(pb.platform).toBe("linux");
    }
  });
});
