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

interface SituationEdgeProps {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  status: "completed" | "active" | "pending";
  fromColor: string;
  toColor: string;
  index: number;
}

export function SituationEdge({
  fromX,
  fromY,
  toX,
  toY,
  status,
  fromColor,
  toColor,
  index,
}: SituationEdgeProps) {
  const gradId = `edge-grad-${index}`;
  const pathId = `edge-path-${index}`;

  const isPending = status === "pending";
  const isCompleted = status === "completed";

  // Cubic bezier with a subtle upward curve
  const midX = (fromX + toX) / 2;
  const curveY = fromY - 18;
  const d = `M ${fromX} ${fromY} C ${midX} ${curveY}, ${midX} ${curveY}, ${toX} ${toY}`;

  const opacity = isCompleted ? 0.9 : status === "active" ? 0.7 : 0.25;
  const strokeWidth = isCompleted ? 2 : 1.5;

  // Number of animated particles
  const particleCount = isCompleted ? 3 : status === "active" ? 1 : 0;

  const particles = useMemo(() => {
    if (particleCount === 0) return [];
    return Array.from({ length: particleCount }, (_, i) => {
      const delay = (i / particleCount) * 3; // stagger evenly across duration
      return { key: `p-${index}-${i}`, delay };
    });
  }, [particleCount, index]);

  return (
    <g>
      <defs>
        {/* Gradient from source → target stage colour */}
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={isPending ? "#2a2a4a" : fromColor} stopOpacity={opacity} />
          <stop offset="100%" stopColor={isPending ? "#2a2a4a" : toColor} stopOpacity={opacity} />
        </linearGradient>
      </defs>

      {/* Invisible reference path for animateMotion */}
      <path id={pathId} d={d} fill="none" stroke="none" />

      {/* Visible edge path */}
      <path
        d={d}
        fill="none"
        stroke={`url(#${gradId})`}
        strokeWidth={strokeWidth}
        strokeDasharray={isPending ? "4 6" : isCompleted ? undefined : "8 4"}
        strokeLinecap="round"
        className={status === "active" ? "situation-edge-flow" : undefined}
      />

      {/* Arrow head at end */}
      {!isPending && (
        <circle
          cx={toX}
          cy={toY}
          r={3}
          fill={toColor}
          opacity={opacity}
        />
      )}

      {/* Animated particles along the path */}
      {particles.map(({ key, delay }) => (
        <circle key={key} r={2.5} fill="#00d4ff" opacity={0.9}>
          <animateMotion
            dur="3s"
            repeatCount="indefinite"
            begin={`${delay}s`}
          >
            <mpath xlinkHref={`#${pathId}`} />
          </animateMotion>
        </circle>
      ))}
    </g>
  );
}
