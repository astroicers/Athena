import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

async function findShadowStrike(request: any) {
  const ops = await (await request.get(`${API}/operations`)).json();
  return ops.find((o: any) => o.codename === "SHADOW-STRIKE");
}

test.describe("SIT -- Vulnerabilities, OPSEC, Constraints, Logs", () => {
  test.setTimeout(60_000);

  // ──────────────────────────────────────────────
  // Vulnerabilities
  // ──────────────────────────────────────────────

  test("GET vulnerabilities list", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/vulnerabilities`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.vulnerabilities)).toBeTruthy();
    expect(body.summary).toBeTruthy();
  });

  test("GET vulnerabilities summary", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/vulnerabilities/summary`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(typeof body.total).toBe("number");
  });

  test("Vulnerability status update (if vulns exist)", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const listRes = await page.request.get(
      `${API}/operations/${op.id}/vulnerabilities`,
    );
    expect(listRes.status()).toBe(200);
    const listBody = await listRes.json();

    const discovered = listBody.vulnerabilities.find(
      (v: any) => v.status === "discovered",
    );
    if (!discovered) {
      test.skip(true, "No vulnerabilities with status 'discovered'");
      return;
    }

    const res = await page.request.put(
      `${API}/operations/${op.id}/vulnerabilities/${discovered.id}/status`,
      { data: { status: "confirmed" } },
    );
    expect(res.status()).toBe(200);
  });

  // ──────────────────────────────────────────────
  // OPSEC
  // ──────────────────────────────────────────────

  test("GET opsec-status", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/opsec-status`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toBeTruthy();
  });

  test("GET threat-level", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/threat-level`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toBeTruthy();
  });

  // ──────────────────────────────────────────────
  // Constraints
  // ──────────────────────────────────────────────

  test("GET constraints", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/constraints`,
    );
    expect(res.status()).toBe(200);
  });

  test("POST constraint override", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.post(
      `${API}/operations/${op.id}/constraints/override`,
      { data: { domain: "cyber" } },
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBeTruthy();
    expect(body.event_id ?? body.id).toBeTruthy();
  });

  // ──────────────────────────────────────────────
  // Logs
  // ──────────────────────────────────────────────

  test("GET logs page 1", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/logs?page=1&page_size=10`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.items)).toBeTruthy();
    expect(typeof body.total).toBe("number");
    expect(body.page).toBe(1);
  });

  test("GET logs page_size limit", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/logs?page=1&page_size=5`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.items.length).toBeLessThanOrEqual(5);
  });

  test("GET logs page 2", async ({ page }) => {
    const op = await findShadowStrike(page.request);
    if (!op) {
      test.skip(true, "SHADOW-STRIKE not found");
      return;
    }

    const res = await page.request.get(
      `${API}/operations/${op.id}/logs?page=2&page_size=5`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();

    if (body.total > 5) {
      expect(Array.isArray(body.items)).toBeTruthy();
      expect(body.items.length).toBeGreaterThan(0);
    } else {
      expect(body.items).toEqual([]);
    }
  });
});
