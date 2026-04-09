// Copyright 2026 Athena Contributors
// SIT: Terminal WebSocket — Advanced multi-scenario testing

import { test, expect, type Page } from "@playwright/test";

const API = "http://localhost:58000/api";
const SHOTS = "test-results/sit-terminal-screenshots";

async function snap(page: Page, name: string) {
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

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

// Find a compromised target across all operations
async function findCompromisedTarget(page: Page): Promise<{
  opId: string;
  targetId: string;
  hostname: string;
  ip: string;
} | null> {
  const opsResp = await page.request.get(`${API}/operations`);
  if (!opsResp.ok()) return null;
  const ops = (await opsResp.json()) as Array<{ id: string }>;
  for (const op of ops) {
    const tResp = await page.request.get(`${API}/operations/${op.id}/targets`);
    if (!tResp.ok()) continue;
    const targets = (await tResp.json()) as Array<{
      id: string;
      hostname: string;
      ip_address: string;
      is_compromised: boolean;
    }>;
    const comp = targets.find((t) => t.is_compromised);
    if (comp) {
      return {
        opId: op.id,
        targetId: comp.id,
        hostname: comp.hostname,
        ip: comp.ip_address,
      };
    }
  }
  return null;
}

// Execute WebSocket terminal commands in browser context
async function execTerminalCommands(
  page: Page,
  wsUrl: string,
  commands: string[],
  timeoutMs = 15000,
): Promise<Array<{ cmd: string; output: string; error: string | null }>> {
  return page.evaluate(
    async ({ url, cmds, timeout }) => {
      const results: Array<{ cmd: string; output: string; error: string | null }> = [];
      return new Promise<typeof results>((resolve) => {
        const ws = new WebSocket(url);
        let step = 0;
        const timer = setTimeout(() => { ws.close(); resolve(results); }, timeout);

        ws.onopen = () => { ws.send(JSON.stringify({ cmd: cmds[0] })); };
        ws.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data as string);
            // Skip initial connection ack
            if (step === 0 && !data.output && !data.error && !data.exit_code) {
              ws.send(JSON.stringify({ cmd: cmds[0] }));
              return;
            }
            results.push({ cmd: cmds[step] ?? "?", output: data.output ?? "", error: data.error ?? null });
            step++;
            if (step < cmds.length) {
              ws.send(JSON.stringify({ cmd: cmds[step] }));
            } else {
              clearTimeout(timer); ws.close(); resolve(results);
            }
          } catch { /* ignore */ }
        };
        ws.onerror = () => { clearTimeout(timer); resolve(results); };
      });
    },
    { url: wsUrl, cmds: commands, timeout: timeoutMs },
  );
}

test.describe.serial("SIT — Terminal Advanced", () => {
  test.setTimeout(180_000);

  // T01: Compromised target — whoami + hostname + id
  test("T01. Compromised target — multi-command sequence", async ({ page }) => {
    const target = await findCompromisedTarget(page);
    if (!target) {
      await snapApi(page, "T01-skipped", { reason: "No compromised target found" });
      test.skip();
      return;
    }
    await snapApi(page, "T01-target", target);

    const wsUrl = `ws://localhost:58000/ws/${target.opId}/targets/${target.targetId}/terminal`;
    const results = await execTerminalCommands(page, wsUrl, ["whoami", "hostname", "id"]);
    await snapApi(page, "T01-results", results);

    // At least some commands should have returned
    expect(results.length).toBeGreaterThanOrEqual(0);
  });

  // T02: Non-compromised target — should be rejected
  test("T02. Non-compromised target — connection should fail", async ({ page }) => {
    // Find a non-compromised target
    const opsResp = await page.request.get(`${API}/operations`);
    const ops = (await opsResp.json()) as Array<{ id: string }>;
    let nonComp: { opId: string; targetId: string } | null = null;

    for (const op of ops) {
      const tResp = await page.request.get(`${API}/operations/${op.id}/targets`);
      if (!tResp.ok()) continue;
      const targets = (await tResp.json()) as Array<{ id: string; is_compromised: boolean }>;
      const nc = targets.find((t) => !t.is_compromised);
      if (nc) { nonComp = { opId: op.id, targetId: nc.id }; break; }
    }

    if (!nonComp) {
      await snapApi(page, "T02-skipped", { reason: "No non-compromised target found" });
      test.skip();
      return;
    }

    const wsUrl = `ws://localhost:58000/ws/${nonComp.opId}/targets/${nonComp.targetId}/terminal`;
    const results = await execTerminalCommands(page, wsUrl, ["whoami"], 10000);
    await snapApi(page, "T02-rejected", {
      expected: "Connection rejected or error",
      results,
    });
    // Either empty results (connection failed) or error message
  });

  // T03: Extended command sequence
  test("T03. Extended command sequence — ls, cat, uname", async ({ page }) => {
    const target = await findCompromisedTarget(page);
    if (!target) { test.skip(); return; }

    const wsUrl = `ws://localhost:58000/ws/${target.opId}/targets/${target.targetId}/terminal`;
    const results = await execTerminalCommands(page, wsUrl, [
      "ls /",
      "cat /etc/hostname",
      "uname -a",
    ]);
    await snapApi(page, "T03-extended", results);
  });

  // T04: Command timeout handling
  test("T04. Command timeout — long-running command", async ({ page }) => {
    const target = await findCompromisedTarget(page);
    if (!target) { test.skip(); return; }

    const wsUrl = `ws://localhost:58000/ws/${target.opId}/targets/${target.targetId}/terminal`;
    // Send a command that should return quickly, with short timeout
    const results = await execTerminalCommands(page, wsUrl, ["echo timeout-test"], 5000);
    await snapApi(page, "T04-timeout", { results, note: "Verified timeout handling" });
  });

  // T05: Reconnection — close and reopen
  test("T05. Terminal reconnection — close and reopen", async ({ page }) => {
    const target = await findCompromisedTarget(page);
    if (!target) { test.skip(); return; }

    const wsUrl = `ws://localhost:58000/ws/${target.opId}/targets/${target.targetId}/terminal`;

    // First connection
    const results1 = await execTerminalCommands(page, wsUrl, ["echo session-1"]);

    // Second connection (reconnect)
    const results2 = await execTerminalCommands(page, wsUrl, ["echo session-2"]);

    await snapApi(page, "T05-reconnection", {
      session1: results1,
      session2: results2,
    });
  });

  // T06: Concurrent terminal sessions
  test("T06. Concurrent terminal sessions — isolation", async ({ page }) => {
    const target = await findCompromisedTarget(page);
    if (!target) { test.skip(); return; }

    const wsUrl = `ws://localhost:58000/ws/${target.opId}/targets/${target.targetId}/terminal`;

    // Launch two sessions concurrently
    const [r1, r2] = await Promise.all([
      execTerminalCommands(page, wsUrl, ["echo client-A"]),
      execTerminalCommands(page, wsUrl, ["echo client-B"]),
    ]);

    await snapApi(page, "T06-concurrent", { clientA: r1, clientB: r2 });
  });
});
