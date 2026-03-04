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

import { useTranslations } from "next-intl";
import type { SituationStage } from "@/hooks/useSituationData";

interface SituationNodeProps {
  stage: SituationStage;
  x: number;
  y: number;
  isCurrentStage: boolean;
  color: string;
  label: string;
}

// Flat-top hexagon scaled to ~120x104
const HEX_W = 120;
const HEX_H = 104;

/** Generate flat-top hexagon points centred at (0,0) */
function hexPoints(w: number, h: number): string {
  const hw = w / 2;
  const hh = h / 2;
  const qw = w / 4;
  return [
    `${-qw},${-hh}`,
    `${qw},${-hh}`,
    `${hw},0`,
    `${qw},${hh}`,
    `${-qw},${hh}`,
    `${-hw},0`,
  ].join(" ");
}

/** Approximate perimeter for strokeDasharray progress */
function hexPerimeter(w: number, h: number): number {
  const hw = w / 2;
  const hh = h / 2;
  const qw = w / 4;
  const side = Math.sqrt((hw - qw) ** 2 + hh ** 2);
  const top = w / 2; // qw * 2
  return side * 4 + top * 2;
}

const POINTS = hexPoints(HEX_W, HEX_H);
const PERIMETER = hexPerimeter(HEX_W, HEX_H);

export function SituationNode({
  stage,
  x,
  y,
  isCurrentStage,
  color,
  label,
}: SituationNodeProps) {
  const t = useTranslations("Situation");
  const isInactive = stage.status === "inactive";
  const isActive = stage.status === "active";
  const opacity = isInactive ? 0.3 : 1;
  const progress =
    stage.totalCount > 0 ? stage.successCount / stage.totalCount : 0;
  const filled = progress * PERIMETER;

  // Unique IDs for gradients/filters (per node)
  const gradId = `grad-${label}`;
  const glowId = `nglow-${label}`;

  return (
    <g transform={`translate(${x}, ${y})`} opacity={opacity}>
      <defs>
        {/* Radial gradient fill — stage colour core fading to surface */}
        <radialGradient id={gradId} cx="50%" cy="50%" r="60%">
          <stop offset="0%" stopColor={color} stopOpacity="0.15" />
          <stop offset="100%" stopColor="#1a1a2e" stopOpacity="0.9" />
        </radialGradient>

        {/* Glow filter */}
        <filter id={glowId} x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur in="SourceGraphic" stdDeviation={isCurrentStage ? 6 : 3} result="b1" />
          <feGaussianBlur in="SourceGraphic" stdDeviation={isCurrentStage ? 12 : 6} result="b2" />
          <feMerge>
            <feMergeNode in="b2" />
            <feMergeNode in="b1" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Outer glow hex (blurred duplicate) */}
      {!isInactive && (
        <polygon
          points={POINTS}
          fill="none"
          stroke={color}
          strokeWidth={1}
          opacity={0.25}
          filter={`url(#${glowId})`}
          className={isActive ? "situation-node-pulse" : undefined}
        />
      )}

      {/* Background fill hex */}
      <polygon
        points={POINTS}
        fill={`url(#${gradId})`}
        stroke="none"
      />

      {/* Progress arc — hex outline via strokeDasharray */}
      <polygon
        points={POINTS}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeDasharray={`${filled} ${PERIMETER - filled}`}
        strokeLinecap="round"
        opacity={progress > 0 ? 0.9 : 0}
      />

      {/* Border hex */}
      <polygon
        points={POINTS}
        fill="none"
        stroke={color}
        strokeWidth={isCurrentStage ? 1.5 : 0.8}
        opacity={isInactive ? 0.3 : 0.5}
        className={isActive ? "situation-node-pulse" : undefined}
      />

      {/* Stage label */}
      <text
        y={-18}
        textAnchor="middle"
        fill={color}
        fontSize={11}
        fontFamily="var(--font-mono)"
        fontWeight="bold"
        letterSpacing="0.12em"
      >
        {label}
      </text>

      {/* Count text */}
      <text
        y={8}
        textAnchor="middle"
        fill="#e0e0f0"
        fontSize={16}
        fontFamily="var(--font-mono)"
        fontWeight="bold"
      >
        {stage.totalCount > 0
          ? `${stage.successCount}/${stage.totalCount}`
          : "\u2014"}
      </text>

      {/* Success check mark */}
      {stage.successCount > 0 && (
        <text
          y={8}
          x={38}
          textAnchor="middle"
          fill={color}
          fontSize={12}
          fontFamily="var(--font-mono)"
        >
          ✓
        </text>
      )}

      {/* Running indicator */}
      {stage.runningCount > 0 && (
        <text
          y={28}
          textAnchor="middle"
          fill="#00d4ff"
          fontSize={9}
          fontFamily="var(--font-mono)"
          className="situation-node-pulse"
        >
          {t("running", { count: stage.runningCount })}
        </text>
      )}
    </g>
  );
}
