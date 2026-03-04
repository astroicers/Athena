// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import type { TopologyData } from "@/types/api";
import { KillChainStage } from "@/types/enums";

const NODE_COLORS: Record<string, string> = {
  compromised: "#ff4444",
  secure: "#00ff88",
  target: "#ffaa00",
};

export const KILL_CHAIN_COLORS: Record<KillChainStage, string> = {
  [KillChainStage.RECON]:     "#4488ff",
  [KillChainStage.WEAPONIZE]: "#8855ff",
  [KillChainStage.DELIVER]:   "#aa44ff",
  [KillChainStage.EXPLOIT]:   "#ff8800",
  [KillChainStage.INSTALL]:   "#ffaa00",
  [KillChainStage.C2]:        "#ff4444",
  [KillChainStage.ACTION]:    "#ff0040",
};

const GRAPH_HEIGHT = 420;

/** Draw a small role icon inside a topology node using Canvas 2D API */
function drawRoleIcon(ctx: CanvasRenderingContext2D, x: number, y: number, role: string, size: number) {
  ctx.save();
  const s = Math.min(size * 0.55, 6); // icon scale relative to node size
  ctx.strokeStyle = "rgba(255,255,255,0.85)";
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.lineWidth = 0.8;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  const r = role.toLowerCase();

  if (r.includes("domain controller") || r === "dc") {
    // Crown / tower shape
    ctx.beginPath();
    ctx.moveTo(x - s, y + s * 0.6);
    ctx.lineTo(x - s, y - s * 0.3);
    ctx.lineTo(x - s * 0.5, y);
    ctx.lineTo(x, y - s * 0.7);
    ctx.lineTo(x + s * 0.5, y);
    ctx.lineTo(x + s, y - s * 0.3);
    ctx.lineTo(x + s, y + s * 0.6);
    ctx.closePath();
    ctx.stroke();
  } else if (r.includes("server")) {
    // Server rack: stacked rectangles
    const w = s * 0.9;
    const h = s * 0.35;
    for (let i = 0; i < 3; i++) {
      const ry = y - s * 0.6 + i * (h + 1);
      ctx.strokeRect(x - w, ry, w * 2, h);
      // Small dot on right side of each rack unit
      ctx.beginPath();
      ctx.arc(x + w * 0.6, ry + h / 2, 0.5, 0, 2 * Math.PI);
      ctx.fill();
    }
  } else if (r.includes("workstation") || r.includes("desktop") || r === "host") {
    // Monitor screen
    const w = s * 0.8;
    const h = s * 0.6;
    ctx.strokeRect(x - w, y - h, w * 2, h * 1.4);
    // Stand
    ctx.beginPath();
    ctx.moveTo(x, y + h * 0.4);
    ctx.lineTo(x, y + h * 0.8);
    ctx.moveTo(x - s * 0.4, y + h * 0.8);
    ctx.lineTo(x + s * 0.4, y + h * 0.8);
    ctx.stroke();
  } else if (r.includes("router") || r.includes("switch") || r.includes("gateway")) {
    // Network device: diamond/arrows
    ctx.beginPath();
    ctx.moveTo(x, y - s * 0.6);
    ctx.lineTo(x + s * 0.6, y);
    ctx.lineTo(x, y + s * 0.6);
    ctx.lineTo(x - s * 0.6, y);
    ctx.closePath();
    ctx.stroke();
    // 4 small arrows pointing outward
    const d = s * 0.3;
    ctx.beginPath();
    ctx.moveTo(x, y - s * 0.6 - d);
    ctx.lineTo(x, y - s * 0.6);
    ctx.moveTo(x + s * 0.6 + d, y);
    ctx.lineTo(x + s * 0.6, y);
    ctx.moveTo(x, y + s * 0.6 + d);
    ctx.lineTo(x, y + s * 0.6);
    ctx.moveTo(x - s * 0.6 - d, y);
    ctx.lineTo(x - s * 0.6, y);
    ctx.stroke();
  } else {
    // Default: simple circle dot
    ctx.beginPath();
    ctx.arc(x, y, s * 0.3, 0, 2 * Math.PI);
    ctx.fill();
  }
  ctx.restore();
}

interface NetworkTopologyProps {
  data: TopologyData | null;
  nodeKillChainMap?: Record<string, KillChainStage>;
  /** Multiplier applied to all node sizes (default 1). Use >1 for larger full-page views. */
  nodeSizeMultiplier?: number;
  /** Called with node id when user clicks a node */
  onNodeClick?: (nodeId: string) => void;
  /** Override graph height in pixels */
  height?: number;
}

export function NetworkTopology({
  data,
  nodeKillChainMap,
  nodeSizeMultiplier = 1,
  onNodeClick,
  height = GRAPH_HEIGHT,
}: NetworkTopologyProps) {
  const t = useTranslations("Topology");
  // Outer wrapper ref — always mounted, used for width measurement
  const wrapperRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line
  const fgRef = useRef<any>(null);
  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line
  const [ForceGraph2DComp, setForceGraph2DComp] = useState<any>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const fitted = useRef(false);

  // Client-side: load ForceGraph2D component
  useEffect(() => {
    setMounted(true);
    import("react-force-graph-2d").then((mod) => {
      setForceGraph2DComp(() => mod.default || mod);
    });
  }, []);

  // Measure wrapper width — wrapper is always mounted so width is stable
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.getBoundingClientRect().width;
      if (w > 0) setContainerWidth(Math.floor(w));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Auto zoomToFit after graph settles
  useEffect(() => {
    if (!data || data.nodes.length === 0 || !ForceGraph2DComp) return;
    fitted.current = false;
    const timers = [500, 1200, 2500].map((ms) =>
      setTimeout(() => {
        try { fgRef.current?.zoomToFit(400, 30); } catch { /* not ready */ }
      }, ms),
    );
    return () => timers.forEach(clearTimeout);
  }, [data, ForceGraph2DComp]);

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    const m = nodeSizeMultiplier;
    return {
      nodes: data.nodes.map((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
        role: (n.data?.role as string) || "host",
        isCompromised: !!n.data?.isCompromised,
        color: n.data?.isCompromised ? NODE_COLORS.compromised : NODE_COLORS.secure,
        nodeSize: ((n.data?.role as string) === "Domain Controller" ? 3
          : n.data?.isCompromised ? 2 : 1.5) * m,
        killChainStage: nodeKillChainMap?.[n.id] ?? null,
      })),
      links: data.edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
      })),
    };
  }, [data, nodeKillChainMap, nodeSizeMultiplier]);

  // Configure d3 forces for proper node spreading
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    try {
      fg.d3Force("charge")?.strength(-400);
      fg.d3Force("link")?.distance(80);
    } catch { /* not ready */ }
  }, [graphData, ForceGraph2DComp]);

  // Custom 2D node rendering: glowing circle + label
  const handleNodeCanvasObject = useCallback((
    node: Record<string, unknown>,
    ctx: CanvasRenderingContext2D,
    globalScale: number,
  ) => {
    const x = (node.x as number) || 0;
    const y = (node.y as number) || 0;
    const color = (node.color as string) || "#00ff88";
    const size = (node.nodeSize as number) || 8;
    const label = String(node.label || node.id);

    // Outer glow (2 layers for smooth falloff)
    for (let i = 2; i >= 1; i--) {
      ctx.beginPath();
      ctx.arc(x, y, size + i * 3, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.05 * i;
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Core circle with radial gradient
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
    gradient.addColorStop(0, color);
    gradient.addColorStop(0.7, color);
    gradient.addColorStop(1, "rgba(0,0,0,0.3)");
    ctx.beginPath();
    ctx.arc(x, y, size, 0, 2 * Math.PI);
    ctx.fillStyle = gradient;
    ctx.fill();

    // Bright center highlight
    ctx.beginPath();
    ctx.arc(x - size * 0.2, y - size * 0.2, size * 0.3, 0, 2 * Math.PI);
    ctx.fillStyle = "rgba(255,255,255,0.25)";
    ctx.fill();

    // Role icon
    const role = (node.role as string) || "host";
    drawRoleIcon(ctx, x, y, role, size);

    // Kill Chain stage ring
    const kcStage = node.killChainStage as KillChainStage | null;
    if (kcStage && KILL_CHAIN_COLORS[kcStage]) {
      ctx.beginPath();
      ctx.arc(x, y, size + 2, 0, 2 * Math.PI);
      ctx.strokeStyle = KILL_CHAIN_COLORS[kcStage];
      ctx.lineWidth = 2.5;
      ctx.globalAlpha = 0.9;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Single-line label
    const fontSize = Math.max(11 / globalScale, 2.5);
    ctx.font = `bold ${fontSize}px monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = "#ffffff";
    ctx.fillText(label, x, y + size + 3);
  }, []);

  const handleEngineStop = useCallback(() => {
    if (!fitted.current && fgRef.current) {
      fitted.current = true;
      try { fgRef.current.zoomToFit(400, 30); } catch { /* ignore */ }
    }
  }, []);

  const handleReset = useCallback(() => {
    try { fgRef.current?.zoomToFit(400, 30); } catch { /* ignore */ }
  }, []);

  const handleNodeClickInternal = useCallback((node: Record<string, unknown>) => {
    onNodeClick?.(node.id as string);
  }, [onNodeClick]);

  if (!data || data.nodes.length === 0) {
    return (
      <div ref={wrapperRef} className="bg-athena-surface border border-athena-border rounded-athena-md p-6 flex items-center justify-center" style={{ height }}>
        <span className="text-xs font-mono text-athena-text-secondary">
          {t("noData")}
        </span>
      </div>
    );
  }

  if (!mounted || !ForceGraph2DComp || containerWidth === 0) {
    return (
      <div ref={wrapperRef} className="bg-athena-bg rounded-athena-md border border-athena-border flex items-center justify-center" style={{ height }}>
        <span className="text-xs font-mono text-athena-text-secondary animate-pulse">
          {t("loading")}
        </span>
      </div>
    );
  }

  return (
    <div
      ref={wrapperRef}
      className="bg-athena-bg rounded-athena-md overflow-hidden border border-athena-border relative"
      style={{ height }}
    >
      {/* Reset view button */}
      <button
        onClick={handleReset}
        className="absolute top-2 right-2 z-10 px-2 py-1 rounded border border-athena-border bg-athena-surface/80 hover:bg-athena-surface text-[10px] font-mono text-athena-text-secondary hover:text-athena-text-primary transition-colors backdrop-blur-sm"
        title={t("resetView")}
      >
        &#x25CE; {t("reset")}
      </button>
      <ForceGraph2DComp
        ref={(el: unknown) => { fgRef.current = el; }}
        graphData={graphData}
        nodeCanvasObject={handleNodeCanvasObject}
        nodePointerAreaPaint={(node: Record<string, unknown>, color: string, ctx: CanvasRenderingContext2D) => {
          const size = (node.nodeSize as number) || 8;
          ctx.beginPath();
          ctx.arc((node.x as number) || 0, (node.y as number) || 0, size + 4, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        onNodeClick={handleNodeClickInternal}
        linkColor={() => "rgba(0, 255, 136, 0.5)"}
        linkWidth={1.5}
        linkDirectionalParticles={3}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleWidth={3}
        linkDirectionalParticleColor={() => "#00ff88"}
        linkCurvature={0.2}
        backgroundColor="#0a0a1a"
        width={containerWidth}
        height={height}
        d3AlphaDecay={0.03}
        d3VelocityDecay={0.3}
        warmupTicks={100}
        cooldownTicks={200}
        cooldownTime={5000}
        onEngineStop={handleEngineStop}
      />
    </div>
  );
}
