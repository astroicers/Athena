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
import type { CredentialNode, CredentialEdge } from "@/hooks/useAttackGraph";

interface CredentialGraphCanvasProps {
  nodes: CredentialNode[];
  edges: CredentialEdge[];
}

/* ── Layout ── */

const RECT_W = 140;
const RECT_H = 44;
const PADDING = 60;

function layoutCredNodes(nodes: CredentialNode[]) {
  const cols = Math.max(3, Math.ceil(Math.sqrt(nodes.length)));
  const spacingX = 180;
  const spacingY = 90;

  return nodes.map((node, i) => ({
    ...node,
    x: PADDING + (i % cols) * spacingX,
    y: PADDING + Math.floor(i / cols) * spacingY,
  }));
}

export function CredentialGraphCanvas({
  nodes,
  edges,
}: CredentialGraphCanvasProps) {
  const t = useTranslations("AttackGraph");

  const positioned = useMemo(() => layoutCredNodes(nodes), [nodes]);

  const posMap = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    for (const n of positioned) {
      map.set(n.id, { x: n.x, y: n.y });
    }
    return map;
  }, [positioned]);

  const svgWidth = useMemo(() => {
    if (positioned.length === 0) return 600;
    return Math.max(600, Math.max(...positioned.map((n) => n.x)) + RECT_W + PADDING);
  }, [positioned]);

  const svgHeight = useMemo(() => {
    if (positioned.length === 0) return 400;
    return Math.max(400, Math.max(...positioned.map((n) => n.y)) + RECT_H + PADDING);
  }, [positioned]);

  if (nodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-widest">
          {t("noCredentials")}
        </span>
      </div>
    );
  }

  return (
    <div className="relative flex-1 overflow-auto">
      <svg
        width={svgWidth}
        height={svgHeight}
        className="block"
        style={{ minWidth: "100%", minHeight: "100%" }}
      >
        {/* Edges as curved lines */}
        {edges.map((edge) => {
          const src = posMap.get(edge.source);
          const tgt = posMap.get(edge.target);
          if (!src || !tgt) return null;

          const sx = src.x + RECT_W / 2;
          const sy = src.y + RECT_H / 2;
          const tx = tgt.x + RECT_W / 2;
          const ty = tgt.y + RECT_H / 2;
          const mx = (sx + tx) / 2;
          const my = (sy + ty) / 2 - 30;

          return (
            <path
              key={edge.id}
              d={`M ${sx} ${sy} Q ${mx} ${my} ${tx} ${ty}`}
              fill="none"
              stroke="var(--color-warning, #eab308)"
              strokeWidth={1.5}
              opacity={0.6}
            />
          );
        })}

        {/* Credential nodes as rounded rectangles */}
        {positioned.map((node) => (
          <g key={node.id}>
            <rect
              x={node.x}
              y={node.y}
              width={RECT_W}
              height={RECT_H}
              rx={6}
              ry={6}
              fill="var(--color-accent, #6366f1)"
              fillOpacity={0.15}
              stroke="var(--color-accent, #6366f1)"
              strokeWidth={1.5}
            />
            <text
              x={node.x + RECT_W / 2}
              y={node.y + 18}
              textAnchor="middle"
              className="text-[11px] font-mono"
              fill="var(--color-text, #e5e7eb)"
            >
              {node.username}
            </text>
            <text
              x={node.x + RECT_W / 2}
              y={node.y + 34}
              textAnchor="middle"
              className="text-[9px] font-mono"
              fill="var(--color-text-secondary, #9ca3af)"
            >
              {node.credentialType}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
