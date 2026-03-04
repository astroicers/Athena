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

import { OODAPhase } from "@/types/enums";

interface OODARingProps {
  cx: number;
  cy: number;
  phase: OODAPhase | null;
}

const PHASES: { phase: OODAPhase; label: string; startAngle: number }[] = [
  { phase: OODAPhase.OBSERVE, label: "O", startAngle: -90 },
  { phase: OODAPhase.ORIENT, label: "O", startAngle: 0 },
  { phase: OODAPhase.DECIDE, label: "D", startAngle: 90 },
  { phase: OODAPhase.ACT, label: "A", startAngle: 180 },
];

const RADIUS = 55;
const ARC_WIDTH = 4;
const GAP_DEG = 8; // gap between arcs in degrees
const ARC_DEG = 90 - GAP_DEG; // each arc spans this many degrees

function polarToCartesian(
  cx: number,
  cy: number,
  radius: number,
  angleDeg: number,
): { x: number; y: number } {
  const rad = (angleDeg * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad),
  };
}

function describeArc(
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number,
): string {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

export function OODARing({ cx, cy, phase }: OODARingProps) {
  if (!phase) return null;

  return (
    <g>
      {PHASES.map(({ phase: p, label, startAngle }) => {
        const isActive = p === phase;
        const endAngle = startAngle + ARC_DEG;
        const midAngle = startAngle + ARC_DEG / 2;
        const labelPos = polarToCartesian(cx, cy, RADIUS + 12, midAngle);
        const arcPath = describeArc(cx, cy, RADIUS, startAngle + GAP_DEG / 2, endAngle + GAP_DEG / 2);

        return (
          <g key={p}>
            <path
              d={arcPath}
              fill="none"
              stroke={isActive ? "#00d4ff" : "#2a2a4a"}
              strokeWidth={ARC_WIDTH}
              strokeLinecap="round"
              opacity={isActive ? 1 : 0.5}
            />
            <text
              x={labelPos.x}
              y={labelPos.y}
              textAnchor="middle"
              dominantBaseline="central"
              fill={isActive ? "#00d4ff" : "#4a4a6a"}
              fontSize={9}
              fontFamily="monospace"
              fontWeight={isActive ? "bold" : "normal"}
            >
              {label}
            </text>
          </g>
        );
      })}
    </g>
  );
}
