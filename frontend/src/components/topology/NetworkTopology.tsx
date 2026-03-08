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
// @ts-expect-error — d3-force-3d has no type declarations; it is a transitive dep of react-force-graph-2d
import { forceCollide, forceX } from "d3-force-3d";
import { useTranslations } from "next-intl";
import type { TopologyData } from "@/types/api";
import { KillChainStage } from "@/types/enums";
import { TopologyLegend } from "./TopologyLegend";
import { FloatingCardLayer } from "./FloatingCardLayer";
import { PHASE_COLORS, KILL_CHAIN_COLORS } from "./topologyColors";

export { PHASE_COLORS, KILL_CHAIN_COLORS };

const GRAPH_HEIGHT = 420;

/** Draw a small role icon inside a topology node using Canvas 2D API */
function drawRoleIcon(ctx: CanvasRenderingContext2D, x: number, y: number, role: string, size: number) {
  ctx.save();
  const s = Math.min(size * 0.55, 6);
  ctx.strokeStyle = "rgba(255,255,255,0.85)";
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.lineWidth = 0.8;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  const r = role.toLowerCase();

  if (r === "c2") {
    // Crosshair / command centre
    const arm = s * 0.7;
    ctx.beginPath();
    ctx.moveTo(x - arm, y); ctx.lineTo(x + arm, y);
    ctx.moveTo(x, y - arm); ctx.lineTo(x, y + arm);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x, y, s * 0.4, 0, 2 * Math.PI);
    ctx.stroke();
  } else if (r.includes("domain controller") || r === "dc") {
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
    const w = s * 0.9;
    const h = s * 0.35;
    for (let i = 0; i < 3; i++) {
      const ry = y - s * 0.6 + i * (h + 1);
      ctx.strokeRect(x - w, ry, w * 2, h);
      ctx.beginPath();
      ctx.arc(x + w * 0.6, ry + h / 2, 0.5, 0, 2 * Math.PI);
      ctx.fill();
    }
  } else if (r.includes("workstation") || r.includes("desktop") || r === "host") {
    const w = s * 0.8;
    const h = s * 0.6;
    ctx.strokeRect(x - w, y - h, w * 2, h * 1.4);
    ctx.beginPath();
    ctx.moveTo(x, y + h * 0.4);
    ctx.lineTo(x, y + h * 0.8);
    ctx.moveTo(x - s * 0.4, y + h * 0.8);
    ctx.lineTo(x + s * 0.4, y + h * 0.8);
    ctx.stroke();
  } else if (r.includes("router") || r.includes("switch") || r.includes("gateway")) {
    ctx.beginPath();
    ctx.moveTo(x, y - s * 0.6);
    ctx.lineTo(x + s * 0.6, y);
    ctx.lineTo(x, y + s * 0.6);
    ctx.lineTo(x - s * 0.6, y);
    ctx.closePath();
    ctx.stroke();
    const d = s * 0.3;
    ctx.beginPath();
    ctx.moveTo(x, y - s * 0.6 - d); ctx.lineTo(x, y - s * 0.6);
    ctx.moveTo(x + s * 0.6 + d, y); ctx.lineTo(x + s * 0.6, y);
    ctx.moveTo(x, y + s * 0.6 + d); ctx.lineTo(x, y + s * 0.6);
    ctx.moveTo(x - s * 0.6 - d, y); ctx.lineTo(x - s * 0.6, y);
    ctx.stroke();
  } else {
    ctx.beginPath();
    ctx.arc(x, y, s * 0.3, 0, 2 * Math.PI);
    ctx.fill();
  }
  ctx.restore();
}

/** Draw a hexagon path centred at (x,y) with given radius */
function hexPath(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    const px = x + radius * Math.cos(angle);
    const py = y + radius * Math.sin(angle);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.closePath();
}

// ── Status badge drawing helpers ──

const BADGE_OFFSETS = {
  topLeft:     { dx: -1, dy: -1 },
  topRight:    { dx:  1, dy: -1 },
  bottomLeft:  { dx: -1, dy:  1 },
  bottomRight: { dx:  1, dy:  1 },
} as const;

function drawBadgeCircle(
  ctx: CanvasRenderingContext2D,
  cx: number, cy: number, r: number, color: string,
) {
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, 2 * Math.PI);
  ctx.fillStyle = color + "40"; // 25% alpha
  ctx.fill();
  ctx.strokeStyle = color;
  ctx.lineWidth = 0.8;
  ctx.stroke();
}

function drawReconBadge(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  drawBadgeCircle(ctx, cx, cy, r, "#4488ff");
  const s = r * 0.5;
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 0.7;
  // Lens
  ctx.beginPath();
  ctx.arc(cx - s * 0.15, cy - s * 0.15, s * 0.55, 0, 2 * Math.PI);
  ctx.stroke();
  // Handle
  ctx.beginPath();
  ctx.moveTo(cx + s * 0.25, cy + s * 0.25);
  ctx.lineTo(cx + s * 0.7, cy + s * 0.7);
  ctx.stroke();
}

function drawSkullBadge(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  drawBadgeCircle(ctx, cx, cy, r, "#ff4444");
  const s = r * 0.5;
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 0.7;
  // Cranium
  ctx.beginPath();
  ctx.arc(cx, cy - s * 0.15, s * 0.55, Math.PI, 0);
  ctx.stroke();
  // Eyes
  ctx.fillStyle = "#fff";
  ctx.fillRect(cx - s * 0.3, cy - s * 0.15, s * 0.2, s * 0.2);
  ctx.fillRect(cx + s * 0.1, cy - s * 0.15, s * 0.2, s * 0.2);
  // Jaw
  ctx.beginPath();
  ctx.moveTo(cx - s * 0.35, cy + s * 0.2);
  ctx.lineTo(cx + s * 0.35, cy + s * 0.2);
  ctx.stroke();
}

function drawShieldBadge(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number, level: string) {
  const levelColor = level === "SYSTEM" ? "#ff4444"
    : (level === "Admin" || level === "sudo" || level === "root") ? "#eab308"
    : "#22c55e";
  drawBadgeCircle(ctx, cx, cy, r, levelColor);
  const s = r * 0.5;
  ctx.beginPath();
  ctx.moveTo(cx, cy - s * 0.6);
  ctx.lineTo(cx - s * 0.5, cy - s * 0.25);
  ctx.lineTo(cx - s * 0.5, cy + s * 0.15);
  ctx.quadraticCurveTo(cx, cy + s * 0.65, cx, cy + s * 0.65);
  ctx.quadraticCurveTo(cx, cy + s * 0.65, cx + s * 0.5, cy + s * 0.15);
  ctx.lineTo(cx + s * 0.5, cy - s * 0.25);
  ctx.closePath();
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 0.7;
  ctx.stroke();
}

function drawChainBadge(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  drawBadgeCircle(ctx, cx, cy, r, "#ffaa00");
  const s = r * 0.4;
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 0.7;
  ctx.beginPath();
  ctx.ellipse(cx - s * 0.2, cy, s * 0.45, s * 0.3, 0, 0, 2 * Math.PI);
  ctx.stroke();
  ctx.beginPath();
  ctx.ellipse(cx + s * 0.2, cy, s * 0.45, s * 0.3, 0, 0, 2 * Math.PI);
  ctx.stroke();
}

function drawStatusBadges(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, size: number,
  node: Record<string, unknown>,
) {
  const r = Math.max(size * 0.35, 3);
  const offset = r + Math.max(size * 0.5, 1); // SPEC-035: offset from centre to four corners

  // Top-left: Recon complete
  if ((node.scanCount as number) > 0) {
    const bx = x + BADGE_OFFSETS.topLeft.dx * offset;
    const by = y + BADGE_OFFSETS.topLeft.dy * offset;
    drawReconBadge(ctx, bx, by, r);
  }

  // Top-right: Compromised
  if (node.isCompromised) {
    const bx = x + BADGE_OFFSETS.topRight.dx * offset;
    const by = y + BADGE_OFFSETS.topRight.dy * offset;
    drawSkullBadge(ctx, bx, by, r);
  }

  // Bottom-left: Privilege level
  if (node.privilegeLevel) {
    const bx = x + BADGE_OFFSETS.bottomLeft.dx * offset;
    const by = y + BADGE_OFFSETS.bottomLeft.dy * offset;
    drawShieldBadge(ctx, bx, by, r, node.privilegeLevel as string);
  }

  // Bottom-right: Persistence / lateral
  if ((node.persistenceCount as number) > 0) {
    const bx = x + BADGE_OFFSETS.bottomRight.dx * offset;
    const by = y + BADGE_OFFSETS.bottomRight.dy * offset;
    drawChainBadge(ctx, bx, by, r);
  }
}

export const OODA_PHASE_COLORS: Record<string, string> = {
  observe: "#4488ff",
  orient: "#ffaa00",
  decide: "#00ff88",
  act: "#ff4444",
};

interface NetworkTopologyProps {
  data: TopologyData | null;
  nodeKillChainMap?: Record<string, KillChainStage>;
  nodeSizeMultiplier?: number;
  onNodeClick?: (nodeId: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
  activeTargetId?: string;
  oodaPhase?: string | null;
  height?: number | "auto";
  graphRef?: React.MutableRefObject<any>;
  onZoomChange?: () => void;
  onEngineRunningChange?: (running: boolean) => void;
  openNodeIds?: string[];
  operationId?: string;
  onCloseNode?: (nodeId: string) => void;
  onReconScan?: (targetId: string) => void;
  onInitialAccess?: (targetId: string) => void;
  /** SPEC-042: Attack graph recommended path — attack graph node ID array */
  recommendedPath?: string[];
}

export function NetworkTopology({
  data,
  nodeKillChainMap,
  nodeSizeMultiplier = 1,
  onNodeClick,
  onNodeHover,
  activeTargetId,
  oodaPhase,
  height = GRAPH_HEIGHT,
  graphRef,
  onZoomChange,
  onEngineRunningChange,
  openNodeIds,
  operationId,
  onCloseNode,
  onReconScan,
  onInitialAccess,
  recommendedPath,
}: NetworkTopologyProps) {
  const t = useTranslations("Topology");
  const wrapperRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line
  const fgRef = useRef<any>(null);
  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line
  const [ForceGraph2DComp, setForceGraph2DComp] = useState<any>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);
  const fitted = useRef(false);
  // SPEC-042: pulse animation phase for attack path edges
  const animPhase = useRef(0);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [zoomLocked, setZoomLocked] = useState(false);
  const [viewTick, setViewTick] = useState(0);

  useEffect(() => {
    setMounted(true);
    import("react-force-graph-2d").then((mod) => {
      setForceGraph2DComp(() => mod.default || mod);
    });
  }, []);

  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const measure = () => {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0) setContainerWidth(Math.floor(rect.width));
      if (rect.height > 0) setContainerHeight(Math.floor(rect.height));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!data || data.nodes.length === 0 || !ForceGraph2DComp) return;
    onEngineRunningChange?.(true);
    fitted.current = false;
    const timers = [500, 1200, 2500].map((ms) =>
      setTimeout(() => {
        try { fgRef.current?.zoomToFit(400, 30); } catch { /* not ready */ }
      }, ms),
    );
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, ForceGraph2DComp]);

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    const m = nodeSizeMultiplier;
    return {
      nodes: data.nodes.map((n) => {
        const phase = (n.data?.attackPhase as string) || "idle";
        const isC2 = n.type === "c2";
        const role = (n.data?.role as string) || "host";
        let color: string;
        let nodeSize: number;

        if (isC2) {
          color = PHASE_COLORS.c2;
          nodeSize = 3.5 * m;
        } else {
          color = PHASE_COLORS[phase] || PHASE_COLORS.idle;
          nodeSize = (role === "Domain Controller" ? 3 : phase === "session" ? 2 : 1.5) * m;
        }

        return {
          id: n.id,
          label: n.label,
          type: n.type,
          role,
          phase,
          isCompromised: !!n.data?.isCompromised,
          color,
          nodeSize,
          killChainStage: nodeKillChainMap?.[n.id] ?? null,
          // SPEC-042: subnet grouping
          networkSegment: (n.data?.network_segment as string) || null,
          // Status badge data
          scanCount: (n.data?.scanCount as number) || 0,
          privilegeLevel: (n.data?.privilegeLevel as string) || null,
          persistenceCount: (n.data?.persistenceCount as number) || 0,
        };
      }),
      links: data.edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
        phase: (e.data?.phase as string) || "idle",
      })),
    };
  }, [data, nodeKillChainMap, nodeSizeMultiplier]);

  // SPEC-042: pulse animation for attack path edges
  useEffect(() => {
    let raf: number;
    const tick = () => {
      animPhase.current = (Date.now() % 1500) / 1500; // 0 -> 1 cycle 1.5s
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  // SPEC-042: convert recommendedPath node IDs to topology edge pairs
  const attackPathEdges = useMemo(() => {
    if (!recommendedPath || recommendedPath.length < 2) return new Set<string>();
    const edges = new Set<string>();
    for (let i = 0; i < recommendedPath.length - 1; i++) {
      const srcTargetId = recommendedPath[i].split("::")[1];
      const tgtTargetId = recommendedPath[i + 1].split("::")[1];
      if (srcTargetId && tgtTargetId && srcTargetId !== tgtTargetId) {
        // Cross-target lateral movement edge
        edges.add(`${srcTargetId}\u2192${tgtTargetId}`);
      }
    }
    // Mark path-involved targets for C2->target edge highlighting
    const pathTargetIds = new Set(
      recommendedPath.map((nid) => nid.split("::")[1]).filter(Boolean)
    );
    pathTargetIds.forEach((tid) => edges.add(`athena-c2\u2192${tid}`));
    return edges;
  }, [recommendedPath]);

  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    try {
      fg.d3Force("charge")?.strength(-400);
      fg.d3Force("link")?.distance(100);
      // SPEC-042: collision detection to prevent node overlap
      fg.d3Force("collide", forceCollide()
        .radius((node: Record<string, unknown>) => ((node.nodeSize as number) || 8) + 5)
        .strength(0.8)
      );
      // SPEC-042: subnet grouping via forceX
      const segments = [...new Set(
        graphData.nodes
          .map((n) => (n as Record<string, unknown>).networkSegment as string | null)
          .filter(Boolean)
      )].sort() as string[];

      if (segments.length > 1) {
        const segmentIndex = new Map(segments.map((s, i) => [s, i]));
        const centerOffset = ((segments.length - 1) * 200) / 2;
        fg.d3Force("subnetX", forceX()
          .x((node: Record<string, unknown>) => {
            const seg = node.networkSegment as string | null;
            if (!seg) return 0;
            const idx = segmentIndex.get(seg) ?? 0;
            return idx * 200 - centerOffset;
          })
          .strength(0.15)
        );
      } else {
        // Remove subnetX force if only one or zero segments
        fg.d3Force("subnetX", null);
      }
    } catch { /* not ready */ }
  }, [graphData, ForceGraph2DComp]);

  // Custom 2D node rendering
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
    const isC2 = node.type === "c2";

    // Outer glow
    for (let i = 2; i >= 1; i--) {
      ctx.globalAlpha = 0.05 * i;
      if (isC2) {
        hexPath(ctx, x, y, size + i * 4);
      } else {
        ctx.beginPath();
        ctx.arc(x, y, size + i * 3, 0, 2 * Math.PI);
      }
      ctx.fillStyle = color;
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Core shape
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
    gradient.addColorStop(0, color);
    gradient.addColorStop(0.7, color);
    gradient.addColorStop(1, "rgba(0,0,0,0.3)");

    if (isC2) {
      hexPath(ctx, x, y, size);
      ctx.fillStyle = gradient;
      ctx.fill();
      // Hex border
      hexPath(ctx, x, y, size);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fillStyle = gradient;
      ctx.fill();
    }

    // Bright center highlight
    ctx.beginPath();
    ctx.arc(x - size * 0.2, y - size * 0.2, size * 0.3, 0, 2 * Math.PI);
    ctx.fillStyle = "rgba(255,255,255,0.25)";
    ctx.fill();

    // Role icon
    const role = (node.role as string) || "host";
    drawRoleIcon(ctx, x, y, role, size);

    // Kill Chain stage ring (host nodes only)
    if (!isC2) {
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
    }

    // OODA phase indicator (active target node)
    if (activeTargetId && node.id === activeTargetId && oodaPhase) {
      const phaseColor = OODA_PHASE_COLORS[oodaPhase] || "#ffffff";
      const indicatorR = size + 5;
      ctx.beginPath();
      ctx.arc(x, y, indicatorR, 0, 2 * Math.PI);
      ctx.strokeStyle = phaseColor;
      ctx.lineWidth = 2;
      ctx.setLineDash([3, 3]);
      ctx.globalAlpha = 0.8;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    // ── Status badges (4-corner) ──
    if (!isC2 && globalScale > 0.4) {
      drawStatusBadges(ctx, x, y, size, node);
    }

    // Label — hide when FloatingNodeCard is open for this node
    const isCardOpen = openNodeIds?.includes(node.id as string);
    if (!isCardOpen) {
      const fontSize = Math.max(14 / globalScale, 3);
      ctx.font = `bold ${fontSize}px monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#ffffff";
      const badgeR = Math.max(size * 0.35, 3);
      ctx.fillText(label, x, y + size + badgeR + 6);
    }
  }, [activeTargetId, oodaPhase, openNodeIds]);

  const handleEngineStop = useCallback(() => {
    if (!fitted.current && fgRef.current) {
      fitted.current = true;
      try { fgRef.current.zoomToFit(400, 30); } catch { /* ignore */ }
    }
    onEngineRunningChange?.(false);
    onZoomChange?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleReset = useCallback(() => {
    try { fgRef.current?.zoomToFit(400, 30); } catch { /* ignore */ }
  }, []);

  const handleNodeClickInternal = useCallback((node: Record<string, unknown>) => {
    onNodeClick?.(node.id as string);
  }, [onNodeClick]);

  const handleNodeHoverInternal = useCallback((node: Record<string, unknown> | null) => {
    onNodeHover?.(node ? (node.id as string) : null);
  }, [onNodeHover]);

  // SPEC-042: helper to check if a link is on the attack path
  const isAttackPathLink = useCallback((link: Record<string, unknown>) => {
    if (attackPathEdges.size === 0) return false;
    const src = typeof link.source === "object"
      ? (link.source as Record<string, unknown>).id as string
      : link.source as string;
    const tgt = typeof link.target === "object"
      ? (link.target as Record<string, unknown>).id as string
      : link.target as string;
    return attackPathEdges.has(`${src}\u2192${tgt}`) || attackPathEdges.has(`${tgt}\u2192${src}`);
  }, [attackPathEdges]);

  // Edge colour based on phase
  const getLinkColor = useCallback((link: Record<string, unknown>) => {
    // SPEC-042: attack path edges are red
    if (isAttackPathLink(link)) return "#ff2222";
    const phase = (link.phase as string) || "idle";
    if (phase === "session") return "rgba(255, 68, 68, 0.7)";
    if (phase === "attacking") return "rgba(255, 136, 0, 0.7)";
    if (phase === "scanning") return "rgba(68, 136, 255, 0.7)";
    if (phase === "lateral") return "rgba(255, 170, 0, 0.7)";
    if (phase === "attempted") return "rgba(255, 255, 255, 0.15)";
    return "rgba(0, 255, 136, 0.3)";
  }, [isAttackPathLink]);

  // Edge width based on phase
  const getLinkWidth = useCallback((link: Record<string, unknown>) => {
    // SPEC-042: attack path edges pulse between 1.8-3px
    if (isAttackPathLink(link)) {
      const pulse = 0.6 + 0.4 * Math.sin(animPhase.current * Math.PI * 2);
      return 3 * pulse;
    }
    const phase = (link.phase as string) || "idle";
    if (phase === "session") return 2.5;
    if (phase === "attacking" || phase === "scanning") return 2;
    if (phase === "lateral") return 2;
    return 0.8;
  }, [isAttackPathLink]);

  // Dashed lines for scanning/attacking
  const getLinkDash = useCallback((link: Record<string, unknown>) => {
    const phase = (link.phase as string) || "idle";
    if (phase === "scanning" || phase === "attacking") return [4, 4];
    if (phase === "lateral") return [6, 3];
    return null;
  }, []);

  // Particles only for active states
  const getLinkParticles = useCallback((link: Record<string, unknown>) => {
    // SPEC-042: attack path edges get 4 particles
    if (isAttackPathLink(link)) return 4;
    const phase = (link.phase as string) || "idle";
    if (phase === "session" || phase === "attacking" || phase === "scanning") return 3;
    if (phase === "lateral") return 2;
    return 0;
  }, [isAttackPathLink]);

  const getLinkParticleColor = useCallback((link: Record<string, unknown>) => {
    // SPEC-042: attack path particle color
    if (isAttackPathLink(link)) return "#ff2222";
    const phase = (link.phase as string) || "idle";
    if (phase === "session") return "#ff4444";
    if (phase === "attacking") return "#ff8800";
    if (phase === "scanning") return "#4488ff";
    if (phase === "lateral") return "#ffaa00";
    return "#00ff88";
  }, [isAttackPathLink]);

  const isAutoHeight = height === "auto";
  const effectiveHeight = isAutoHeight ? (containerHeight || GRAPH_HEIGHT) : height;
  const wrapperStyle = isAutoHeight ? undefined : { height: effectiveHeight };
  const wrapperClass = isAutoHeight ? "h-full" : "";

  if (!data || data.nodes.length === 0) {
    return (
      <div ref={wrapperRef} className={`bg-athena-surface border border-athena-border rounded-athena-md p-6 flex items-center justify-center ${wrapperClass}`} style={wrapperStyle}>
        <span className="text-xs font-mono text-athena-text-secondary">
          {t("noData")}
        </span>
      </div>
    );
  }

  if (data.nodes.length <= 1) {
    return (
      <div ref={wrapperRef} className={`bg-athena-bg border border-athena-border rounded-athena-md flex flex-col items-center justify-center gap-3 ${wrapperClass}`} style={wrapperStyle}>
        <span className="text-athena-accent text-3xl">&#x25CE;</span>
        <span className="text-xs font-mono text-athena-text-secondary">
          {t("addTargetsToBegin")}
        </span>
      </div>
    );
  }

  if (!mounted || !ForceGraph2DComp || containerWidth === 0) {
    return (
      <div ref={wrapperRef} className={`bg-athena-bg rounded-athena-md border border-athena-border flex items-center justify-center ${wrapperClass}`} style={wrapperStyle}>
        <span className="text-xs font-mono text-athena-text-secondary animate-pulse">
          {t("loading")}
        </span>
      </div>
    );
  }

  return (
    <div
      ref={wrapperRef}
      className={`bg-athena-bg rounded-athena-md overflow-hidden border border-athena-border relative ${wrapperClass}`}
      style={wrapperStyle}
    >
      <TopologyLegend />
      <button
        onClick={handleReset}
        className="absolute top-2 right-2 z-10 px-2 py-1 rounded border border-athena-border bg-athena-surface hover:bg-athena-elevated text-sm font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
        title={t("resetView")}
      >
        &#x25CE; {t("reset")}
      </button>
      <ForceGraph2DComp
        ref={(el: unknown) => { fgRef.current = el; if (graphRef) graphRef.current = el; }}
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
        onNodeHover={onNodeHover ? handleNodeHoverInternal : undefined}
        linkColor={getLinkColor}
        linkWidth={getLinkWidth}
        linkLineDash={getLinkDash}
        linkDirectionalParticles={getLinkParticles}
        linkDirectionalParticleSpeed={(link: Record<string, unknown>) => isAttackPathLink(link) ? 0.008 : 0.005}
        linkDirectionalParticleWidth={3}
        linkDirectionalParticleColor={getLinkParticleColor}
        linkCurvature={0.2}
        onRenderFramePost={(ctx: CanvasRenderingContext2D) => {
          // SPEC-042: draw subnet bounding boxes
          const segGroups = new Map<string, { xs: number[]; ys: number[]; sizes: number[] }>();
          for (const node of graphData.nodes) {
            const seg = (node as Record<string, unknown>).networkSegment as string | null;
            if (!seg) continue;
            const x = (node as Record<string, unknown>).x as number | undefined;
            const y = (node as Record<string, unknown>).y as number | undefined;
            const size = (node as Record<string, unknown>).nodeSize as number || 8;
            if (x == null || y == null) continue;
            if (!segGroups.has(seg)) segGroups.set(seg, { xs: [], ys: [], sizes: [] });
            const g = segGroups.get(seg)!;
            g.xs.push(x);
            g.ys.push(y);
            g.sizes.push(size);
          }
          if (segGroups.size <= 1) return; // no boxes for single subnet
          const pad = 30;
          ctx.save();
          for (const [seg, g] of segGroups) {
            const maxR = Math.max(...g.sizes);
            const minX = Math.min(...g.xs) - maxR - pad;
            const minY = Math.min(...g.ys) - maxR - pad;
            const maxX = Math.max(...g.xs) + maxR + pad;
            const maxY = Math.max(...g.ys) + maxR + pad;
            ctx.strokeStyle = "rgba(255,255,255,0.15)";
            ctx.lineWidth = 1;
            ctx.setLineDash([6, 4]);
            ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);
            ctx.setLineDash([]);
            // Subnet label
            ctx.font = "13px monospace";
            ctx.fillStyle = "rgba(255,255,255,0.55)";
            ctx.textAlign = "left";
            ctx.textBaseline = "top";
            ctx.fillText(seg, minX + 4, minY + 4);
          }
          ctx.restore();
        }}
        backgroundColor="#0a0a1a"
        width={containerWidth}
        height={effectiveHeight}
        d3AlphaDecay={0.08}
        d3VelocityDecay={0.5}
        warmupTicks={100}
        cooldownTicks={200}
        cooldownTime={3000}
        onEngineStop={handleEngineStop}
        onZoom={(transform: { k: number }) => { setZoomLevel(transform.k); setViewTick((v) => v + 1); onZoomChange?.(); }}
        enableZoomInteraction={!zoomLocked}
        enablePanInteraction={!zoomLocked}
      />
      {openNodeIds && openNodeIds.length > 0 && operationId && onCloseNode && (
        <FloatingCardLayer
          openNodeIds={openNodeIds}
          fgRef={fgRef}
          graphData={graphData}
          topologyData={data}
          nodeKillChainMap={nodeKillChainMap ?? {}}
          operationId={operationId}
          containerWidth={containerWidth}
          containerHeight={containerHeight}
          onCloseNode={onCloseNode}
          viewTick={viewTick}
          onReconScan={onReconScan}
          onInitialAccess={onInitialAccess}
        />
      )}
      {/* Zoom Toolbar */}
      <div className="absolute bottom-2 left-2 z-10 flex items-center gap-1 bg-athena-surface border border-athena-border rounded px-1.5 py-1">
        <button
          onClick={() => {
            const s = Math.max(0.1, zoomLevel * 0.8);
            fgRef.current?.zoom(s, 300);
          }}
          className="w-6 h-6 flex items-center justify-center rounded hover:bg-athena-elevated text-athena-text-secondary hover:text-athena-text text-sm font-mono transition-colors"
          title={t("zoomOut")}
        >
          &minus;
        </button>
        <input
          type="number"
          value={Math.round(zoomLevel * 100)}
          onChange={(e) => {
            const v = Number(e.target.value);
            if (v > 0 && v <= 500) fgRef.current?.zoom(v / 100, 300);
          }}
          className="w-12 h-6 text-center text-sm font-mono text-athena-text bg-transparent border border-athena-border rounded appearance-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          min={10}
          max={500}
          step={10}
        />
        <span className="text-sm font-mono text-athena-text-secondary">%</span>
        <button
          onClick={() => {
            const s = Math.min(5, zoomLevel * 1.25);
            fgRef.current?.zoom(s, 300);
          }}
          className="w-6 h-6 flex items-center justify-center rounded hover:bg-athena-elevated text-athena-text-secondary hover:text-athena-text text-sm font-mono transition-colors"
          title={t("zoomIn")}
        >
          +
        </button>
        <div className="w-px h-4 bg-athena-border mx-0.5" />
        <button
          onClick={() => setZoomLocked((v) => !v)}
          className={`w-6 h-6 flex items-center justify-center rounded text-sm font-mono transition-colors ${
            zoomLocked
              ? "bg-athena-accent/20 text-athena-accent"
              : "hover:bg-athena-elevated text-athena-text-secondary hover:text-athena-text"
          }`}
          title={zoomLocked ? t("unlockZoom") : t("lockZoom")}
        >
          {zoomLocked ? (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 9.9-1" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
