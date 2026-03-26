import { test, expect } from "@playwright/test";

const API = "http://localhost:58000/api";

/**
 * Find the SHADOW-STRIKE operation and its compromised target (192.168.0.26).
 * Returns { opId, targetId } or null if not found.
 */
async function findCompromisedTarget(
  request: import("@playwright/test").APIRequestContext,
) {
  const ops = await (await request.get(`${API}/operations`)).json();
  const op = ops.find(
    (o: { codename: string; status: string }) =>
      o.codename === "SHADOW-STRIKE" && o.status === "active",
  );
  if (!op) return null;
  const targets = await (
    await request.get(`${API}/operations/${op.id}/targets`)
  ).json();
  const target = targets.find(
    (t: { is_compromised: boolean; ip_address: string }) =>
      t.is_compromised && t.ip_address === "192.168.0.26",
  );
  return target ? { opId: op.id, targetId: target.id } : null;
}

test.describe("Terminal WebSocket SIT", () => {
  test.setTimeout(60_000);

  // ──────────────────────────────────────────────
  // 1. Basic command execution
  // ──────────────────────────────────────────────

  test("connects and executes basic commands", async ({ page, request }) => {
    const found = await findCompromisedTarget(request);
    if (!found) {
      test.skip(true, "No active SHADOW-STRIKE operation with compromised 192.168.0.26 target");
      return;
    }

    const wsUrl = `ws://localhost:58000/ws/${found.opId}/targets/${found.targetId}/terminal`;
    const commands = ["whoami", "id", "uname -a"];

    const result = await page.evaluate(
      async ({ wsUrl, commands }) => {
        return new Promise<
          Array<{
            type: string;
            cmd?: string;
            output?: string;
            error?: string;
            exit_code?: number;
          }>
        >((resolve, reject) => {
          const ws = new WebSocket(wsUrl);
          const results: Array<{
            type: string;
            cmd?: string;
            output?: string;
            error?: string;
            exit_code?: number;
          }> = [];
          let step = 0;
          const timeout = setTimeout(
            () => reject(new Error("WS timeout")),
            15000,
          );

          ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (step === 0) {
              // initial connection
              if (data.error) {
                reject(new Error(data.error));
                return;
              }
              results.push({ type: "connect", output: data.output });
            } else {
              results.push({
                type: "cmd",
                cmd: commands[step - 1],
                output: data.output,
                error: data.error,
                exit_code: data.exit_code,
              });
            }
            step++;
            if (step <= commands.length) {
              ws.send(JSON.stringify({ cmd: commands[step - 1] }));
            } else {
              clearTimeout(timeout);
              ws.close();
              resolve(results);
            }
          };

          ws.onerror = () => {
            clearTimeout(timeout);
            reject(new Error("WS error"));
          };
        });
      },
      { wsUrl, commands },
    );

    // Verify connection message
    expect(result[0].type).toBe("connect");
    expect(result[0].output).toBeTruthy();

    // whoami should return "service"
    const whoamiResult = result.find((r) => r.cmd === "whoami");
    expect(whoamiResult).toBeTruthy();
    expect(whoamiResult!.output?.trim()).toBe("service");

    // id should contain "uid="
    const idResult = result.find((r) => r.cmd === "id");
    expect(idResult).toBeTruthy();
    expect(idResult!.output).toContain("uid=");

    // uname -a should contain "Linux"
    const unameResult = result.find((r) => r.cmd === "uname -a");
    expect(unameResult).toBeTruthy();
    expect(unameResult!.output).toContain("Linux");
  });

  // ──────────────────────────────────────────────
  // 2. Dangerous command rejection
  // ──────────────────────────────────────────────

  test("rejects dangerous commands", async ({ page, request }) => {
    const found = await findCompromisedTarget(request);
    if (!found) {
      test.skip(true, "No active SHADOW-STRIKE operation with compromised 192.168.0.26 target");
      return;
    }

    const wsUrl = `ws://localhost:58000/ws/${found.opId}/targets/${found.targetId}/terminal`;
    const commands = ["rm -rf /"];

    const result = await page.evaluate(
      async ({ wsUrl, commands }) => {
        return new Promise<
          Array<{
            type: string;
            cmd?: string;
            output?: string;
            error?: string;
            exit_code?: number;
          }>
        >((resolve, reject) => {
          const ws = new WebSocket(wsUrl);
          const results: Array<{
            type: string;
            cmd?: string;
            output?: string;
            error?: string;
            exit_code?: number;
          }> = [];
          let step = 0;
          const timeout = setTimeout(
            () => reject(new Error("WS timeout")),
            15000,
          );

          ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (step === 0) {
              if (data.error) {
                reject(new Error(data.error));
                return;
              }
              results.push({ type: "connect", output: data.output });
            } else {
              results.push({
                type: "cmd",
                cmd: commands[step - 1],
                output: data.output,
                error: data.error,
                exit_code: data.exit_code,
              });
            }
            step++;
            if (step <= commands.length) {
              ws.send(JSON.stringify({ cmd: commands[step - 1] }));
            } else {
              clearTimeout(timeout);
              ws.close();
              resolve(results);
            }
          };

          ws.onerror = () => {
            clearTimeout(timeout);
            reject(new Error("WS error"));
          };
        });
      },
      { wsUrl, commands },
    );

    const dangerousResult = result.find((r) => r.cmd === "rm -rf /");
    expect(dangerousResult).toBeTruthy();
    expect(dangerousResult!.error).toBeTruthy();
    expect(dangerousResult!.error).toMatch(/refused|destructive/i);
  });

  // ──────────────────────────────────────────────
  // 3. Oversized command rejection
  // ──────────────────────────────────────────────

  test("rejects oversized commands", async ({ page, request }) => {
    const found = await findCompromisedTarget(request);
    if (!found) {
      test.skip(true, "No active SHADOW-STRIKE operation with compromised 192.168.0.26 target");
      return;
    }

    const wsUrl = `ws://localhost:58000/ws/${found.opId}/targets/${found.targetId}/terminal`;
    // Generate a command that exceeds 1024 chars
    const oversizedCmd = "A".repeat(1025);
    const commands = [oversizedCmd];

    const result = await page.evaluate(
      async ({ wsUrl, commands }) => {
        return new Promise<
          Array<{
            type: string;
            cmd?: string;
            output?: string;
            error?: string;
            exit_code?: number;
          }>
        >((resolve, reject) => {
          const ws = new WebSocket(wsUrl);
          const results: Array<{
            type: string;
            cmd?: string;
            output?: string;
            error?: string;
            exit_code?: number;
          }> = [];
          let step = 0;
          const timeout = setTimeout(
            () => reject(new Error("WS timeout")),
            15000,
          );

          ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (step === 0) {
              if (data.error) {
                reject(new Error(data.error));
                return;
              }
              results.push({ type: "connect", output: data.output });
            } else {
              results.push({
                type: "cmd",
                cmd: commands[step - 1],
                output: data.output,
                error: data.error,
                exit_code: data.exit_code,
              });
            }
            step++;
            if (step <= commands.length) {
              ws.send(JSON.stringify({ cmd: commands[step - 1] }));
            } else {
              clearTimeout(timeout);
              ws.close();
              resolve(results);
            }
          };

          ws.onerror = () => {
            clearTimeout(timeout);
            reject(new Error("WS error"));
          };
        });
      },
      { wsUrl, commands },
    );

    const oversizedResult = result.find((r) => r.cmd === oversizedCmd);
    expect(oversizedResult).toBeTruthy();
    expect(oversizedResult!.error).toBeTruthy();
    expect(oversizedResult!.error).toMatch(/too long|1024/i);
  });

  // ──────────────────────────────────────────────
  // 4. Non-compromised target rejection
  // ──────────────────────────────────────────────

  test("rejects terminal for non-compromised target", async ({
    page,
    request,
  }) => {
    // Create a temporary operation
    const opResp = await request.post(`${API}/operations`, {
      data: {
        code: `TERM-TEST-${Date.now()}`,
        name: "Terminal Reject Test",
        codename: `term-reject-${Date.now()}`,
        strategic_intent: "E2E test: verify terminal rejects non-compromised target",
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
          hostname: "uncompromised-host",
          ip_address: "10.99.99.99",
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
      return new Promise<{ error: string | null; output: string | null }>(
        (resolve, reject) => {
          const ws = new WebSocket(url);
          const timeout = setTimeout(
            () => reject(new Error("WS timeout")),
            15000,
          );

          ws.onmessage = (e) => {
            clearTimeout(timeout);
            const data = JSON.parse(e.data);
            ws.close();
            resolve({ error: data.error || null, output: data.output || null });
          };

          ws.onerror = () => {
            clearTimeout(timeout);
            reject(new Error("WS error"));
          };
        },
      );
    }, wsUrl);

    expect(result.error).toBeTruthy();
    expect(result.error).toMatch(/not compromised/i);
  });
});
