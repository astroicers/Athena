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

import type { SituationStage } from "@/hooks/useSituationData";

interface SituationNodeProps {
  stage: SituationStage;
  x: number;
  y: number;
  isCurrentStage: boolean;
  color: string;
  label: string;
}

const NODE_WIDTH = 140;
const NODE_HEIGHT = 70;

export function SituationNode({
  stage,
  x,
  y,
  isCurrentStage,
  color,
  label,
}: SituationNodeProps) {
  const isInactive = stage.status === "inactive";
  const isActive = stage.status === "active";
  const opacity = isInactive ? 0.4 : 1;
  const strokeWidth = isCurrentStage ? 2.5 : 1.5;
  const strokeColor = isCurrentStage ? color : `${color}99`;
  const filterAttr = isCurrentStage ? "url(#glow)" : undefined;

  return (
    <g
      transform={`translate(${x - NODE_WIDTH / 2}, ${y - NODE_HEIGHT / 2})`}
      opacity={opacity}
    >
      {/* Background rect */}
      <rect
        width={NODE_WIDTH}
        height={NODE_HEIGHT}
        rx={8}
        ry={8}
        fill="#1a1a2e"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        filter={filterAttr}
        className={isActive ? "situation-node-pulse" : undefined}
      />

      {/* Stage label */}
      <text
        x={NODE_WIDTH / 2}
        y={24}
        textAnchor="middle"
        fill={color}
        fontSize={10}
        fontFamily="monospace"
        fontWeight="bold"
        letterSpacing="0.1em"
      >
        {label}
      </text>

      {/* Count text */}
      <text
        x={NODE_WIDTH / 2}
        y={46}
        textAnchor="middle"
        fill="#a0a0b0"
        fontSize={12}
        fontFamily="monospace"
      >
        {stage.totalCount > 0
          ? `${stage.successCount}/${stage.totalCount} \u2713`
          : "\u2014"}
      </text>

      {/* Running indicator */}
      {stage.runningCount > 0 && (
        <text
          x={NODE_WIDTH / 2}
          y={60}
          textAnchor="middle"
          fill="#00d4ff"
          fontSize={9}
          fontFamily="monospace"
        >
          {stage.runningCount} running
        </text>
      )}
    </g>
  );
}
