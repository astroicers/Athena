// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TopologyData } from "@/types/api";

const NODE_COLORS: Record<string, string> = {
  compromised: "#ff4444",
  secure: "#00ff88",
  target: "#ffaa00",
};

const GRAPH_HEIGHT = 420;

interface NetworkTopologyProps {
  data: TopologyData | null;
}

export function NetworkTopology({ data }: NetworkTopologyProps) {
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
    return {
      nodes: data.nodes.map((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
        role: (n.data?.role as string) || "host",
        isCompromised: !!n.data?.isCompromised,
        color: n.data?.isCompromised ? NODE_COLORS.compromised : NODE_COLORS.secure,
        nodeSize: (n.data?.role as string) === "Domain Controller" ? 16
          : n.data?.isCompromised ? 12 : 8,
      })),
      links: data.edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
      })),
    };
  }, [data]);

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

    // Outer glow (3 layers for smooth falloff)
    for (let i = 3; i >= 1; i--) {
      ctx.beginPath();
      ctx.arc(x, y, size + i * 6, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.04 * i;
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

  if (!data || data.nodes.length === 0) {
    return (
      <div ref={wrapperRef} className="bg-athena-surface border border-athena-border rounded-athena-md p-6 flex items-center justify-center" style={{ height: GRAPH_HEIGHT }}>
        <span className="text-xs font-mono text-athena-text-secondary">
          No topology data available
        </span>
      </div>
    );
  }

  if (!mounted || !ForceGraph2DComp || containerWidth === 0) {
    return (
      <div ref={wrapperRef} className="bg-[#060612] rounded-athena-md border border-athena-border flex items-center justify-center" style={{ height: GRAPH_HEIGHT }}>
        <span className="text-xs font-mono text-athena-text-secondary animate-pulse">
          Loading topology...
        </span>
      </div>
    );
  }

  return (
    <div
      ref={wrapperRef}
      className="bg-[#060612] rounded-athena-md overflow-hidden border border-athena-border relative"
      style={{ height: GRAPH_HEIGHT }}
    >
      {/* Reset view button */}
      <button
        onClick={handleReset}
        className="absolute top-2 right-2 z-10 px-2 py-1 rounded border border-athena-border bg-athena-surface/80 hover:bg-athena-surface text-[10px] font-mono text-athena-text-secondary hover:text-athena-text-primary transition-colors backdrop-blur-sm"
        title="Reset view"
      >
        &#x25CE; Reset
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
        linkColor={() => "rgba(0, 255, 136, 0.5)"}
        linkWidth={1.5}
        linkDirectionalParticles={3}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleWidth={3}
        linkDirectionalParticleColor={() => "#00ff88"}
        linkCurvature={0.2}
        backgroundColor="#060612"
        width={containerWidth}
        height={GRAPH_HEIGHT}
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
