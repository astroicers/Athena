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

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  accentColor?: string;
  trend?: "up" | "down" | "stable";
  trendLabel?: string;
  gauge?: { value: number; max: number };
}

function TrendArrow({ trend }: { trend: "up" | "down" | "stable" }) {
  const colorClass =
    trend === "up"
      ? "text-[var(--color-success)]"
      : trend === "down"
        ? "text-[var(--color-error)]"
        : "text-athena-text-secondary";

  const path =
    trend === "up"
      ? "M6 9V3M3 5.5L6 3L9 5.5"
      : trend === "down"
        ? "M6 3V9M3 6.5L6 9L9 6.5"
        : "M2 6H10";

  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={colorClass}
    >
      <path d={path} />
    </svg>
  );
}

function MiniGauge({
  value,
  max,
  color,
}: {
  value: number;
  max: number;
  color?: string;
}) {
  const r = 12;
  const circumference = 2 * Math.PI * r;
  const pct = max > 0 ? Math.min(value / max, 1) : 0;
  const dashOffset = circumference * (1 - pct);

  return (
    <svg width="32" height="32" viewBox="0 0 32 32" className="shrink-0">
      <circle
        cx="16"
        cy="16"
        r={r}
        fill="none"
        stroke="var(--color-border)"
        strokeWidth={2.5}
      />
      <circle
        cx="16"
        cy="16"
        r={r}
        fill="none"
        stroke={color || "var(--color-accent)"}
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        transform="rotate(-90 16 16)"
      />
    </svg>
  );
}

export function MetricCard({
  title,
  value,
  subtitle,
  accentColor,
  trend,
  trendLabel,
  gauge,
}: MetricCardProps) {
  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 flex items-start justify-between gap-2">
      <div className="flex flex-col gap-1 flex-1">
        <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
          {title}
        </span>
        <div className="flex items-center gap-2">
          <span
            className="text-2xl font-mono font-bold"
            style={accentColor ? { color: accentColor } : undefined}
          >
            {value}
          </span>
          {trend && <TrendArrow trend={trend} />}
        </div>
        {trendLabel && (
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {trendLabel}
          </span>
        )}
        {subtitle && !trendLabel && (
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {subtitle}
          </span>
        )}
      </div>
      {gauge && (
        <MiniGauge value={gauge.value} max={gauge.max} color={accentColor} />
      )}
    </div>
  );
}
