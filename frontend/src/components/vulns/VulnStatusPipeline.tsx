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
import type { VulnStatus } from "@/types/vulnerability";

const PIPELINE_STATUSES: VulnStatus[] = ["discovered", "confirmed", "exploited", "reported"];

const STATUS_COLORS: Record<VulnStatus, string> = {
  discovered: "#00d4ff",
  confirmed: "#ffaa00",
  exploited: "#ff0040",
  reported: "#00ff88",
  false_positive: "#8a8a9a",
};

interface VulnStatusPipelineProps {
  byStatus: Record<VulnStatus, number>;
}

function HexNode({
  label,
  count,
  color,
  cx,
  cy,
  isPeak,
}: {
  label: string;
  count: number;
  color: string;
  cx: number;
  cy: number;
  isPeak: boolean;
}) {
  const size = 28;
  const points = Array.from({ length: 6 }, (_, i) => {
    const angle = (Math.PI / 3) * i - Math.PI / 6;
    return `${cx + size * Math.cos(angle)},${cy + size * Math.sin(angle)}`;
  }).join(" ");

  return (
    <g>
      {isPeak && (
        <polygon
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="1"
          opacity="0.4"
        >
          <animate
            attributeName="opacity"
            values="0.2;0.6;0.2"
            dur="2s"
            repeatCount="indefinite"
          />
        </polygon>
      )}
      <polygon
        points={points}
        fill={color + "20"}
        stroke={color}
        strokeWidth="1.5"
      />
      <text
        x={cx}
        y={cy - 6}
        textAnchor="middle"
        fill={color}
        fontSize="12"
        fontFamily="var(--font-mono)"
        fontWeight="bold"
      >
        {count}
      </text>
      <text
        x={cx}
        y={cy + 10}
        textAnchor="middle"
        fill={color}
        fontSize="9"
        fontFamily="var(--font-mono)"
        fontWeight="bold"
        style={{ textTransform: "uppercase" }}
      >
        {label}
      </text>
    </g>
  );
}

export function VulnStatusPipeline({ byStatus }: VulnStatusPipelineProps) {
  const t = useTranslations("Vulns");

  const maxCount = Math.max(
    ...PIPELINE_STATUSES.map((s) => byStatus[s] || 0),
    1,
  );
  const peakStatus = PIPELINE_STATUSES.find(
    (s) => (byStatus[s] || 0) === maxCount,
  );

  const nodeSpacing = 140;
  const startX = 70;
  const centerY = 45;
  const svgWidth = startX * 2 + nodeSpacing * (PIPELINE_STATUSES.length - 1);
  const svgHeight = 130;

  const fpCount = byStatus.false_positive || 0;

  return (
    <div className="w-full overflow-x-auto">
      <svg
        width="100%"
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="min-w-[560px]"
      >
        {/* Connecting arrows between pipeline nodes */}
        {PIPELINE_STATUSES.slice(0, -1).map((_, i) => {
          const x1 = startX + i * nodeSpacing + 30;
          const x2 = startX + (i + 1) * nodeSpacing - 30;
          return (
            <g key={`arrow-${i}`}>
              <line
                x1={x1}
                y1={centerY}
                x2={x2}
                y2={centerY}
                stroke="#8a8a9a"
                strokeWidth="1"
                strokeDasharray="6 4"
              />
              <polygon
                points={`${x2},${centerY - 4} ${x2 + 6},${centerY} ${x2},${centerY + 4}`}
                fill="#8a8a9a"
              />
            </g>
          );
        })}

        {/* Pipeline nodes */}
        {PIPELINE_STATUSES.map((status, i) => (
          <HexNode
            key={status}
            label={t(`status.${status}`)}
            count={byStatus[status] || 0}
            color={STATUS_COLORS[status]}
            cx={startX + i * nodeSpacing}
            cy={centerY}
            isPeak={status === peakStatus}
          />
        ))}

        {/* False positive branch — drops down from "discovered" node */}
        {fpCount > 0 && (
          <g opacity="0.5">
            <line
              x1={startX}
              y1={centerY + 30}
              x2={startX}
              y2={centerY + 60}
              stroke="#8a8a9a"
              strokeWidth="1"
              strokeDasharray="4 3"
            />
            <polygon
              points={`${startX - 4},${centerY + 60} ${startX},${centerY + 66} ${startX + 4},${centerY + 60}`}
              fill="#8a8a9a"
            />
            <text
              x={startX + 8}
              y={centerY + 78}
              fill="#8a8a9a"
              fontSize="9"
              fontFamily="var(--font-mono)"
            >
              {t("status.false_positive")} ({fpCount})
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
