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
