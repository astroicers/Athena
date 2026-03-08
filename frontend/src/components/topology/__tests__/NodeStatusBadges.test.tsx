// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

/**
 * SPEC-035: Node Status Badge System
 *
 * Tests badge data mapping, drawing trigger conditions, privilege-level
 * colour logic, globalScale visibility gating, and i18n completeness.
 *
 * NOTE: The individual badge drawing helpers (drawReconBadge, drawSkullBadge,
 * drawShieldBadge, drawChainBadge, drawStatusBadges) are module-private
 * functions inside NetworkTopology.tsx and cannot be imported directly.
 * We test their behaviour indirectly through the component's canvas callback
 * and by verifying the data pipeline that feeds them.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import type { TopologyData } from "@/types/api";
import en from "../../../../messages/en.json";
import zhTW from "../../../../messages/zh-TW.json";

// ── Mock react-force-graph-2d to capture nodeCanvasObject callback ──

let capturedNodeCanvasObject: ((
  node: Record<string, unknown>,
  ctx: CanvasRenderingContext2D,
  globalScale: number,
) => void) | null = null;

let capturedGraphData: { nodes: Record<string, unknown>[]; links: unknown[] } | null = null;

vi.mock("react-force-graph-2d", () => {
  const { forwardRef } = require("react");
  const MockForceGraph = forwardRef(function MockForceGraph(
    props: Record<string, unknown>,
    ref: React.Ref<unknown>,
  ) {
    // Capture the callback & graphData so tests can invoke them
    capturedNodeCanvasObject = props.nodeCanvasObject as typeof capturedNodeCanvasObject;
    capturedGraphData = props.graphData as typeof capturedGraphData;

    if (typeof ref === "function") {
      ref({
        d3Force: () => ({ strength: () => {}, distance: () => {} }),
        zoomToFit: () => {},
        zoom: () => {},
      });
    } else if (ref && typeof ref === "object") {
      (ref as React.MutableRefObject<unknown>).current = {
        d3Force: () => ({ strength: () => {}, distance: () => {} }),
        zoomToFit: () => {},
        zoom: () => {},
      };
    }
    return <div data-testid="force-graph" />;
  });
  MockForceGraph.displayName = "MockForceGraph";
  return { default: MockForceGraph, __esModule: true };
});

// Stub ResizeObserver + getBoundingClientRect for jsdom
beforeEach(() => {
  capturedNodeCanvasObject = null;
  capturedGraphData = null;

  // The component calls el.getBoundingClientRect() inside the ResizeObserver callback.
  // In jsdom all elements return {width:0, height:0} by default, so we patch it.
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue({
    width: 800, height: 600,
    top: 0, left: 0, bottom: 600, right: 800,
    x: 0, y: 0, toJSON: () => {},
  });

  globalThis.ResizeObserver = class {
    cb: ResizeObserverCallback;
    constructor(cb: ResizeObserverCallback) { this.cb = cb; }
    observe() {
      // Fire immediately so the component sets containerWidth > 0
      this.cb(
        [{ contentRect: { width: 800, height: 600 } } as unknown as ResizeObserverEntry],
        this,
      );
    }
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

// Lazy-import after mock
const { NetworkTopology } = await import("../NetworkTopology");
const { TopologyLegend } = await import("../TopologyLegend");

/**
 * Render NetworkTopology and wait for the async dynamic import of
 * react-force-graph-2d to resolve so the ForceGraph mock captures props.
 */
async function renderAndWait(data: TopologyData, extraProps: Record<string, unknown> = {}) {
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <NetworkTopology data={data} {...extraProps} />,
      { wrapper: IntlWrapper },
    );
    // Flush the dynamic import() microtask and subsequent setState.
    // Two ticks: one for the import resolution, one for the state batch.
    await new Promise((r) => setTimeout(r, 20));
  });
  // Second act pass to ensure all state updates from effects are flushed
  await act(async () => {
    await new Promise((r) => setTimeout(r, 0));
  });
  return result;
}

// ── Test data factories ──

function makeTopology(overrides: {
  scanCount?: number;
  isCompromised?: boolean;
  privilegeLevel?: string | null;
  persistenceCount?: number;
} = {}): TopologyData {
  return {
    nodes: [
      {
        id: "athena-c2",
        label: "Athena C2",
        type: "c2",
        data: { role: "C2" },
      },
      {
        id: "target-001",
        label: "web-srv",
        type: "host",
        data: {
          role: "Web Server",
          attackPhase: "idle",
          isCompromised: overrides.isCompromised ?? false,
          scanCount: overrides.scanCount ?? 0,
          privilegeLevel: overrides.privilegeLevel ?? null,
          persistenceCount: overrides.persistenceCount ?? 0,
        },
      },
    ],
    edges: [
      { source: "athena-c2", target: "target-001", label: "c2-link", data: { phase: "idle" } },
    ],
  };
}

/**
 * Create a minimal mock CanvasRenderingContext2D that records calls via Proxy.
 */
function createMockCtx() {
  const calls: { method: string; args: unknown[] }[] = [];
  const props: Record<string, unknown> = {};

  const handler: ProxyHandler<Record<string, unknown>> = {
    get(_target, prop: string) {
      if (prop === "__calls") return calls;
      if (prop === "__props") return props;
      if (prop in props) return props[prop];
      return (...args: unknown[]) => {
        calls.push({ method: prop, args });
        if (prop === "createRadialGradient") {
          return { addColorStop: () => {} };
        }
      };
    },
    set(_target, prop: string, value: unknown) {
      props[prop] = value;
      calls.push({ method: `set:${prop}`, args: [value] });
      return true;
    },
  };

  return new Proxy({} as Record<string, unknown>, handler) as unknown as CanvasRenderingContext2D & {
    __calls: typeof calls;
    __props: typeof props;
  };
}

/** Extract fillStyle values from mock ctx calls */
function getFillStyles(ctx: ReturnType<typeof createMockCtx>): string[] {
  return ctx.__calls
    .filter((c) => c.method === "set:fillStyle" && typeof c.args[0] === "string")
    .map((c) => c.args[0] as string);
}

/** Badge background colours (25% alpha suffix "40") */
const BADGE_BG = {
  recon: "4488ff40",
  skull: "ff444440",
  shieldGold: "eab30840",
  shieldRed: "ff444440",
  shieldGreen: "22c55e40",
  chain: "ffaa0040",
};

function makeHostNode(overrides: Record<string, unknown> = {}) {
  return {
    x: 100, y: 100,
    color: "#00ff88", nodeSize: 8, label: "test", id: "target-001",
    type: "host", role: "host",
    scanCount: 0, isCompromised: false, privilegeLevel: null, persistenceCount: 0,
    killChainStage: null,
    ...overrides,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. Badge data mapping in graphData useMemo
// ─────────────────────────────────────────────────────────────────────────────

describe("SPEC-035: Badge data mapping", () => {
  it("maps scanCount from node.data into graphData node", async () => {
    await renderAndWait(makeTopology({ scanCount: 3 }));
    expect(capturedGraphData).not.toBeNull();
    const host = capturedGraphData!.nodes.find((n) => n.id === "target-001");
    expect(host).toBeDefined();
    expect(host!.scanCount).toBe(3);
  });

  it("maps isCompromised from node.data into graphData node", async () => {
    await renderAndWait(makeTopology({ isCompromised: true }));
    const host = capturedGraphData!.nodes.find((n) => n.id === "target-001");
    expect(host!.isCompromised).toBe(true);
  });

  it("maps isCompromised=false correctly", async () => {
    await renderAndWait(makeTopology({ isCompromised: false }));
    const host = capturedGraphData!.nodes.find((n) => n.id === "target-001");
    expect(host!.isCompromised).toBe(false);
  });

  it("maps privilegeLevel from node.data into graphData node", async () => {
    await renderAndWait(makeTopology({ privilegeLevel: "root" }));
    const host = capturedGraphData!.nodes.find((n) => n.id === "target-001");
    expect(host!.privilegeLevel).toBe("root");
  });

  it("maps null privilegeLevel as null", async () => {
    await renderAndWait(makeTopology({ privilegeLevel: null }));
    const host = capturedGraphData!.nodes.find((n) => n.id === "target-001");
    expect(host!.privilegeLevel).toBeNull();
  });

  it("maps persistenceCount from node.data into graphData node", async () => {
    await renderAndWait(makeTopology({ persistenceCount: 2 }));
    const host = capturedGraphData!.nodes.find((n) => n.id === "target-001");
    expect(host!.persistenceCount).toBe(2);
  });

  it("defaults persistenceCount to 0 when absent", async () => {
    const data: TopologyData = {
      nodes: [
        { id: "athena-c2", label: "C2", type: "c2", data: { role: "C2" } },
        { id: "t1", label: "Host", type: "host", data: { role: "host", attackPhase: "idle" } },
      ],
      edges: [{ source: "athena-c2", target: "t1", label: "link", data: { phase: "idle" } }],
    };
    await renderAndWait(data);
    const host = capturedGraphData!.nodes.find((n) => n.id === "t1");
    expect(host!.persistenceCount).toBe(0);
  });

  it("defaults scanCount to 0 when absent", async () => {
    const data: TopologyData = {
      nodes: [
        { id: "athena-c2", label: "C2", type: "c2", data: { role: "C2" } },
        { id: "t1", label: "Host", type: "host", data: { role: "host", attackPhase: "idle" } },
      ],
      edges: [{ source: "athena-c2", target: "t1", label: "link", data: { phase: "idle" } }],
    };
    await renderAndWait(data);
    const host = capturedGraphData!.nodes.find((n) => n.id === "t1");
    expect(host!.scanCount).toBe(0);
  });

  it("C2 node has default badge fields (0/null) — badges skipped at draw time", async () => {
    await renderAndWait(makeTopology({ scanCount: 5 }));
    const c2 = capturedGraphData!.nodes.find((n) => n.id === "athena-c2");
    expect(c2).toBeDefined();
    expect(c2!.scanCount).toBe(0);
    expect(c2!.persistenceCount).toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Canvas callback — badge drawing trigger conditions
// ─────────────────────────────────────────────────────────────────────────────

describe("SPEC-035: Canvas badge drawing triggers", () => {
  it("draws recon badge when scanCount > 0 and globalScale > 0.4", async () => {
    await renderAndWait(makeTopology({ scanCount: 1 }));
    expect(capturedNodeCanvasObject).not.toBeNull();

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(makeHostNode({ scanCount: 1 }), ctx, 1.0);

    const fills = getFillStyles(ctx);
    expect(fills.some((s) => s.includes(BADGE_BG.recon))).toBe(true);
  });

  it("does NOT draw badges when globalScale <= 0.4", async () => {
    await renderAndWait(makeTopology({ scanCount: 1, isCompromised: true, privilegeLevel: "root", persistenceCount: 1 }));
    expect(capturedNodeCanvasObject).not.toBeNull();

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(
      makeHostNode({ scanCount: 1, isCompromised: true, privilegeLevel: "root", persistenceCount: 1 }),
      ctx, 0.3,
    );

    const fills = getFillStyles(ctx);
    const allBadgeBgs = [BADGE_BG.recon, BADGE_BG.skull, BADGE_BG.shieldGold, BADGE_BG.chain];
    const badgeHits = fills.filter((s) => allBadgeBgs.some((bg) => s.includes(bg)));
    expect(badgeHits.length).toBe(0);
  });

  it("does NOT draw badges on C2 nodes even with globalScale > 0.4", async () => {
    await renderAndWait(makeTopology());
    expect(capturedNodeCanvasObject).not.toBeNull();

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(
      { ...makeHostNode({ scanCount: 5, isCompromised: true, privilegeLevel: "SYSTEM", persistenceCount: 3 }),
        type: "c2", role: "C2", id: "athena-c2" },
      ctx, 1.0,
    );

    const fills = getFillStyles(ctx);
    const allBadgeBgs = [BADGE_BG.recon, BADGE_BG.shieldGold, BADGE_BG.shieldGreen, BADGE_BG.chain];
    const badgeHits = fills.filter((s) => allBadgeBgs.some((bg) => s.includes(bg)));
    expect(badgeHits.length).toBe(0);
  });

  it("draws skull badge when isCompromised is true", async () => {
    await renderAndWait(makeTopology({ isCompromised: true }));

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(makeHostNode({ isCompromised: true }), ctx, 1.0);

    const fills = getFillStyles(ctx);
    expect(fills.some((s) => s.includes(BADGE_BG.skull))).toBe(true);
  });

  it("draws chain badge when persistenceCount > 0", async () => {
    await renderAndWait(makeTopology({ persistenceCount: 2 }));

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(makeHostNode({ persistenceCount: 2 }), ctx, 1.0);

    const fills = getFillStyles(ctx);
    expect(fills.some((s) => s.includes(BADGE_BG.chain))).toBe(true);
  });

  it("does NOT draw recon badge when scanCount === 0", async () => {
    await renderAndWait(makeTopology({ scanCount: 0 }));

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(makeHostNode(), ctx, 1.0);

    const fills = getFillStyles(ctx);
    expect(fills.some((s) => s.includes(BADGE_BG.recon))).toBe(false);
  });

  it("does NOT draw skull badge when isCompromised is false", async () => {
    await renderAndWait(makeTopology({ isCompromised: false }));

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(makeHostNode(), ctx, 1.0);

    // The skull badge bg is #ff444440 — but the node core gradient also uses colors.
    // We check specifically for the 25%-alpha badge background.
    const fills = getFillStyles(ctx);
    expect(fills.filter((s) => s === "#ff444440").length).toBe(0);
  });

  it("does NOT draw chain badge when persistenceCount === 0", async () => {
    await renderAndWait(makeTopology({ persistenceCount: 0 }));

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(makeHostNode(), ctx, 1.0);

    const fills = getFillStyles(ctx);
    expect(fills.filter((s) => s === "#ffaa0040").length).toBe(0);
  });

  it("draws all four badges when all conditions are met", async () => {
    await renderAndWait(makeTopology({
      scanCount: 2, isCompromised: true, privilegeLevel: "root", persistenceCount: 1,
    }));

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(
      makeHostNode({ scanCount: 2, isCompromised: true, privilegeLevel: "root", persistenceCount: 1 }),
      ctx, 1.0,
    );

    const fills = getFillStyles(ctx);
    expect(fills.some((s) => s.includes(BADGE_BG.recon))).toBe(true);
    expect(fills.some((s) => s.includes(BADGE_BG.skull))).toBe(true);
    expect(fills.some((s) => s.includes(BADGE_BG.shieldGold))).toBe(true);
    expect(fills.some((s) => s.includes(BADGE_BG.chain))).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Shield badge colour logic (privilege level mapping)
// ─────────────────────────────────────────────────────────────────────────────

describe("SPEC-035: Shield badge privilege-level colours", () => {
  // drawShieldBadge colour mapping:
  //   SYSTEM           -> #ff4444 (red)
  //   Admin/sudo/root  -> #eab308 (gold)
  //   User/other       -> #22c55e (green)

  async function assertShieldColor(level: string, expectedBg: string) {
    await renderAndWait(makeTopology({ privilegeLevel: level }));
    const ctx = createMockCtx();
    capturedNodeCanvasObject!(makeHostNode({ privilegeLevel: level }), ctx, 1.0);
    const fills = getFillStyles(ctx);
    expect(fills.some((s) => s.includes(expectedBg))).toBe(true);
  }

  it('shield colour for "SYSTEM" privilege: red (#ff4444)', async () => {
    await assertShieldColor("SYSTEM", "ff444440");
  });

  it('shield colour for "Admin" privilege: gold (#eab308)', async () => {
    await assertShieldColor("Admin", "eab30840");
  });

  it('shield colour for "sudo" privilege: gold (#eab308)', async () => {
    await assertShieldColor("sudo", "eab30840");
  });

  it('shield colour for "root" privilege: gold (#eab308)', async () => {
    await assertShieldColor("root", "eab30840");
  });

  it('shield colour for "User" privilege: green (#22c55e)', async () => {
    await assertShieldColor("User", "22c55e40");
  });

  it('shield colour for "guest" privilege: green (#22c55e) — unknown level defaults to green', async () => {
    await assertShieldColor("guest", "22c55e40");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. TopologyLegend — Status Badges section
// ─────────────────────────────────────────────────────────────────────────────

describe("SPEC-035: TopologyLegend badge entries", () => {
  it("shows STATUS BADGES section header when expanded", () => {
    render(<TopologyLegend />, { wrapper: IntlWrapper });
    fireEvent.click(screen.getByText(/LEGEND/i));
    expect(screen.getByText(/STATUS BADGES/i)).toBeTruthy();
  });

  it("shows all four badge labels when expanded", () => {
    render(<TopologyLegend />, { wrapper: IntlWrapper });
    fireEvent.click(screen.getByText(/LEGEND/i));
    expect(screen.getByText("Recon Complete")).toBeTruthy();
    expect(screen.getByText("Compromised")).toBeTruthy();
    expect(screen.getByText("Privilege Level")).toBeTruthy();
    expect(screen.getByText("Persistence / Lateral")).toBeTruthy();
  });

  it("renders four badge SVG icons (14x14 viewBox) in the badge section", () => {
    const { container } = render(<TopologyLegend />, { wrapper: IntlWrapper });
    fireEvent.click(screen.getByText(/LEGEND/i));

    const svgs = container.querySelectorAll('svg[viewBox="0 0 14 14"]');
    expect(svgs.length).toBe(4);
  });

  it("uses correct colours for badge icons — recon (#4488ff), skull (#ff4444), shield (#eab308), chain (#ffaa00)", () => {
    const { container } = render(<TopologyLegend />, { wrapper: IntlWrapper });
    fireEvent.click(screen.getByText(/LEGEND/i));

    const svgs = container.querySelectorAll('svg[viewBox="0 0 14 14"]');
    const strokes = Array.from(svgs).map((svg) => {
      const circle = svg.querySelector("circle");
      return circle?.getAttribute("stroke");
    });

    expect(strokes).toContain("#4488ff");
    expect(strokes).toContain("#ff4444");
    expect(strokes).toContain("#eab308");
    expect(strokes).toContain("#ffaa00");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. i18n — badge label keys exist in both locales
// ─────────────────────────────────────────────────────────────────────────────

describe("SPEC-035: i18n badge labels", () => {
  const requiredLegendKeys = ["statusBadges", "recon", "compromised", "privilege", "persistence"];

  for (const key of requiredLegendKeys) {
    it(`en.json Legend.${key} exists and is non-empty`, () => {
      const legend = en.Legend as Record<string, string>;
      expect(legend).toHaveProperty(key);
      expect(legend[key].length).toBeGreaterThan(0);
    });

    it(`zh-TW.json Legend.${key} exists and is non-empty`, () => {
      const legend = zhTW.Legend as Record<string, string>;
      expect(legend).toHaveProperty(key);
      expect(legend[key].length).toBeGreaterThan(0);
    });
  }

  it("en and zh-TW badge labels differ (translated, not copy-pasted)", () => {
    const enLegend = en.Legend as Record<string, string>;
    const zhLegend = zhTW.Legend as Record<string, string>;

    expect(enLegend.statusBadges).not.toBe(zhLegend.statusBadges);
    expect(enLegend.persistence).not.toBe(zhLegend.persistence);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. Acceptance criteria quick-check (SPEC-035 table)
// ─────────────────────────────────────────────────────────────────────────────

describe("SPEC-035: Acceptance criteria coverage", () => {
  it("AC-1: unscanned node has no badge draws", async () => {
    await renderAndWait(makeTopology());

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(makeHostNode(), ctx, 1.0);

    const fills = getFillStyles(ctx);
    const allBadgeBgs = [BADGE_BG.recon, BADGE_BG.skull, BADGE_BG.shieldGold, BADGE_BG.shieldGreen, BADGE_BG.chain];
    const badgeHits = fills.filter((s) => allBadgeBgs.some((bg) => s.includes(bg)));
    expect(badgeHits.length).toBe(0);
  });

  it("AC-2: after recon scan (scanCount > 0), blue recon badge drawn", async () => {
    await renderAndWait(makeTopology({ scanCount: 1 }));

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(makeHostNode({ scanCount: 1 }), ctx, 1.0);

    const fills = getFillStyles(ctx);
    expect(fills.some((s) => s.includes(BADGE_BG.recon))).toBe(true);
  });

  it("AC-8: globalScale < 0.4 hides all badges", async () => {
    await renderAndWait(makeTopology({
      scanCount: 5, isCompromised: true, privilegeLevel: "SYSTEM", persistenceCount: 3,
    }));

    const ctx = createMockCtx();
    capturedNodeCanvasObject!(
      makeHostNode({ scanCount: 5, isCompromised: true, privilegeLevel: "SYSTEM", persistenceCount: 3 }),
      ctx, 0.2,
    );

    const fills = getFillStyles(ctx);
    const allBadgeBgs = [BADGE_BG.recon, BADGE_BG.shieldGold, BADGE_BG.shieldGreen, BADGE_BG.shieldRed, BADGE_BG.chain];
    const badgeHits = fills.filter((s) => allBadgeBgs.some((bg) => s.includes(bg)));
    expect(badgeHits.length).toBe(0);
  });
});
