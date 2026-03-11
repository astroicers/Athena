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

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import type { AttackNode, AttackEdge } from "@/hooks/useAttackGraph";

interface AttackGraphCanvasProps {
  nodes: AttackNode[];
  edges: AttackEdge[];
  stats: { totalNodes: number; exploredNodes: number; coverageScore: number };
  onRebuild: () => void;
  rebuilding?: boolean;
}

/* ── Layout helpers ── */

const NODE_RADIUS = 20;
const PADDING = 60;

function layoutNodes(nodes: AttackNode[]) {
  // Simple grid layout: arrange nodes in rows
  const cols = Math.max(3, Math.ceil(Math.sqrt(nodes.length)));
  const spacingX = 120;
  const spacingY = 100;

  return nodes.map((node, i) => ({
    ...node,
    cx: PADDING + (i % cols) * spacingX + NODE_RADIUS,
    cy: PADDING + Math.floor(i / cols) * spacingY + NODE_RADIUS,
  }));
}

/* ── Status colors ── */

function statusColor(status: AttackNode["status"]): string {
  switch (status) {
    case "explored":
      return "var(--color-success, #22c55e)";
    case "pending":
      return "var(--color-warning, #eab308)";
    case "failed":
      return "var(--color-error, #ef4444)";
    case "unreachable":
      return "var(--color-text-secondary, #9ca3af)";
  }
}

function statusOpacity(status: AttackNode["status"]): number {
  return status === "unreachable" ? 0.4 : 1;
}

/* ── Edge styling ── */

function edgeStroke(type: AttackEdge["type"]): string {
  switch (type) {
    case "enables":
      return "#ffffff";
    case "alternative":
      return "#eab308";
    case "lateral":
      return "#06b6d4";
  }
}

function edgeDash(type: AttackEdge["type"]): string | undefined {
  switch (type) {
    case "enables":
      return undefined;
    case "alternative":
      return "6 4";
    case "lateral":
      return "2 4";
  }
}

export function AttackGraphCanvas({
  nodes,
  edges,
  stats,
  onRebuild,
  rebuilding = false,
}: AttackGraphCanvasProps) {
  const t = useTranslations("AttackGraph");

  const positioned = useMemo(() => layoutNodes(nodes), [nodes]);

  const posMap = useMemo(() => {
    const map = new Map<string, { cx: number; cy: number }>();
    for (const n of positioned) {
      map.set(n.id, { cx: n.cx, cy: n.cy });
    }
    return map;
  }, [positioned]);

  // Compute SVG dimensions to fit all nodes
  const svgWidth = useMemo(() => {
    if (positioned.length === 0) return 600;
    return Math.max(600, Math.max(...positioned.map((n) => n.cx)) + PADDING + NODE_RADIUS);
  }, [positioned]);

  const svgHeight = useMemo(() => {
    if (positioned.length === 0) return 400;
    return Math.max(400, Math.max(...positioned.map((n) => n.cy)) + PADDING + NODE_RADIUS);
  }, [positioned]);

  if (nodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-widest">
          {t("noData")}
        </span>
      </div>
    );
  }

  return (
    <div className="relative flex-1 overflow-auto">
      {/* Stats panel */}
      <div className="absolute top-3 right-3 z-10 bg-athena-bg-secondary border border-athena-border rounded px-3 py-2 font-mono text-xs space-y-1">
        <div className="flex justify-between gap-4">
          <span className="text-athena-text-secondary">{t("totalNodes")}</span>
          <span className="text-athena-text">{stats.totalNodes}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-athena-text-secondary">{t("exploredNodes")}</span>
          <span className="text-athena-text">{stats.exploredNodes}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-athena-text-secondary">{t("coverage")}</span>
          <span className="text-athena-text">{Math.round(stats.coverageScore * 100)}%</span>
        </div>
      </div>

      {/* Toolbar */}
      <div className="absolute top-3 left-3 z-10">
        <button
          onClick={onRebuild}
          disabled={rebuilding}
          className="px-3 py-1 text-xs font-mono uppercase tracking-wider
                     border border-athena-border rounded
                     bg-athena-bg-secondary text-athena-text
                     hover:bg-athena-accent/20 hover:border-athena-accent
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors"
        >
          {rebuilding ? t("rebuilding") : t("rebuild")}
        </button>
      </div>

      {/* SVG Canvas */}
      <svg
        width={svgWidth}
        height={svgHeight}
        className="block"
        style={{ minWidth: "100%", minHeight: "100%" }}
      >
        {/* Edges */}
        {edges.map((edge) => {
          const src = posMap.get(edge.source);
          const tgt = posMap.get(edge.target);
          if (!src || !tgt) return null;
          return (
            <line
              key={edge.id}
              x1={src.cx}
              y1={src.cy}
              x2={tgt.cx}
              y2={tgt.cy}
              stroke={edgeStroke(edge.type)}
              strokeWidth={1.5}
              strokeDasharray={edgeDash(edge.type)}
              opacity={0.6}
            />
          );
        })}

        {/* Nodes */}
        {positioned.map((node) => (
          <g key={node.id} opacity={statusOpacity(node.status)}>
            <circle
              cx={node.cx}
              cy={node.cy}
              r={NODE_RADIUS}
              fill={statusColor(node.status)}
              fillOpacity={0.2}
              stroke={statusColor(node.status)}
              strokeWidth={1.5}
            />
            <text
              x={node.cx}
              y={node.cy + NODE_RADIUS + 14}
              textAnchor="middle"
              className="text-[10px] font-mono"
              fill="var(--color-text-secondary, #9ca3af)"
            >
              {node.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
