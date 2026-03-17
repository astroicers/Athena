// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use client";

import { useMemo } from "react";

/* ── Types ── */

export interface TimeSeriesDataPoint {
  timestamp: string; // ISO 8601
  value: number;
}

export interface TimeSeriesLine {
  id: string;
  label: string;
  data: TimeSeriesDataPoint[];
  color: string; // CSS color
}

interface TimeSeriesChartProps {
  lines: TimeSeriesLine[];
  height?: number; // default 120
  yMin?: number; // default 0
  yMax?: number; // default auto from data
  showGrid?: boolean; // default true
}

/* ── Constants ── */

const PADDING = { top: 8, right: 12, bottom: 20, left: 36 };
const VIEW_WIDTH = 400;

/* ── Helpers ── */

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

/* ── Component ── */

export function TimeSeriesChart({
  lines,
  height = 120,
  yMin = 0,
  yMax: yMaxProp,
  showGrid = true,
}: TimeSeriesChartProps) {
  const allPoints = useMemo(
    () => lines.flatMap((l) => l.data),
    [lines],
  );

  const hasData = allPoints.length > 0;

  const yMax = useMemo(() => {
    if (yMaxProp !== undefined) return yMaxProp;
    if (!hasData) return 100;
    const max = Math.max(...allPoints.map((p) => p.value));
    // Add 10% headroom, minimum 1
    return Math.max(max * 1.1, yMin + 1);
  }, [yMaxProp, allPoints, hasData, yMin]);

  const plotW = VIEW_WIDTH - PADDING.left - PADDING.right;
  const plotH = height - PADDING.top - PADDING.bottom;

  // Collect all timestamps across all lines for x-domain
  const allTimestamps = useMemo(() => {
    const set = new Set<string>();
    for (const line of lines) {
      for (const pt of line.data) set.add(pt.timestamp);
    }
    return Array.from(set).sort();
  }, [lines]);

  const tMin = allTimestamps.length > 0 ? new Date(allTimestamps[0]).getTime() : 0;
  const tMax =
    allTimestamps.length > 1
      ? new Date(allTimestamps[allTimestamps.length - 1]).getTime()
      : tMin + 1;

  function xOf(iso: string): number {
    const t = new Date(iso).getTime();
    const ratio = tMax === tMin ? 0.5 : (t - tMin) / (tMax - tMin);
    return PADDING.left + ratio * plotW;
  }

  function yOf(v: number): number {
    const ratio = yMax === yMin ? 0 : (v - yMin) / (yMax - yMin);
    return PADDING.top + plotH - ratio * plotH;
  }

  // Grid lines at yMin, midpoint, yMax
  const gridValues = [yMin, yMin + (yMax - yMin) / 2, yMax];

  if (!hasData) {
    return (
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${VIEW_WIDTH} ${height}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Time series chart - no data"
      >
        <text
          x={VIEW_WIDTH / 2}
          y={height / 2}
          textAnchor="middle"
          dominantBaseline="central"
          className="font-mono"
          style={{ fontSize: 12, fill: "var(--color-text-secondary)" }}
        >
          No data
        </text>
      </svg>
    );
  }

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${VIEW_WIDTH} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Time series chart"
    >
      {/* Grid lines */}
      {showGrid &&
        gridValues.map((v) => {
          const y = yOf(v);
          return (
            <g key={`grid-${v}`}>
              <line
                x1={PADDING.left}
                y1={y}
                x2={VIEW_WIDTH - PADDING.right}
                y2={y}
                stroke="var(--color-border)"
                strokeWidth={0.5}
                strokeDasharray="4 3"
              />
              <text
                x={PADDING.left - 4}
                y={y}
                textAnchor="end"
                dominantBaseline="central"
                className="font-mono"
                style={{ fontSize: 9, fill: "var(--color-text-secondary)" }}
              >
                {Math.round(v)}
              </text>
            </g>
          );
        })}

      {/* X-axis labels: start and end */}
      {allTimestamps.length >= 1 && (
        <text
          x={PADDING.left}
          y={height - 4}
          textAnchor="start"
          className="font-mono"
          style={{ fontSize: 9, fill: "var(--color-text-secondary)" }}
        >
          {formatTimestamp(allTimestamps[0])}
        </text>
      )}
      {allTimestamps.length >= 2 && (
        <text
          x={VIEW_WIDTH - PADDING.right}
          y={height - 4}
          textAnchor="end"
          className="font-mono"
          style={{ fontSize: 9, fill: "var(--color-text-secondary)" }}
        >
          {formatTimestamp(allTimestamps[allTimestamps.length - 1])}
        </text>
      )}

      {/* Lines + fill areas */}
      {lines.map((line) => {
        if (line.data.length === 0) return null;

        const sorted = [...line.data].sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
        );

        // Build polyline points string
        const pts = sorted.map((p) => `${xOf(p.timestamp)},${yOf(p.value)}`).join(" ");

        // Fill polygon: line points + bottom-right + bottom-left
        const firstX = xOf(sorted[0].timestamp);
        const lastX = xOf(sorted[sorted.length - 1].timestamp);
        const bottomY = yOf(yMin);
        const fillPts = `${pts} ${lastX},${bottomY} ${firstX},${bottomY}`;

        // For single-point lines, render a circle instead
        if (sorted.length === 1) {
          const cx = xOf(sorted[0].timestamp);
          const cy = yOf(sorted[0].value);
          return (
            <g key={line.id}>
              <circle cx={cx} cy={cy} r={3} fill={line.color} />
            </g>
          );
        }

        return (
          <g key={line.id}>
            <polygon
              points={fillPts}
              fill={line.color}
              fillOpacity={0.1}
            />
            <polyline
              points={pts}
              fill="none"
              stroke={line.color}
              strokeWidth={1.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </g>
        );
      })}
    </svg>
  );
}
