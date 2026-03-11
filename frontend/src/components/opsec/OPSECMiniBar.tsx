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
import { useOPSEC } from "@/hooks/useOPSEC";

/* ── Helpers ── */

function scoreColor(value: number): string {
  if (value < 40) return "var(--color-success)";
  if (value < 60) return "var(--color-warning)";
  return "var(--color-error)";
}

function budgetColor(remaining: number, total: number): string {
  if (total <= 0) return "var(--color-success)";
  const ratio = remaining / total;
  if (ratio > 0.5) return "var(--color-success)";
  if (ratio > 0.2) return "var(--color-warning)";
  return "var(--color-error)";
}

/* ── Sub-components ── */

function NoiseScoreRing({ value }: { value: number }) {
  const radius = 28;
  const stroke = 5;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  const color = scoreColor(value);

  return (
    <svg width={72} height={72} className="block mx-auto">
      <circle
        cx={36}
        cy={36}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        className="text-athena-border opacity-30"
      />
      <circle
        cx={36}
        cy={36}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 36 36)"
        className="transition-all duration-500"
      />
      <text
        x={36}
        y={36}
        textAnchor="middle"
        dominantBaseline="central"
        className="font-mono text-athena-text"
        style={{ fontSize: 16, fill: color }}
      >
        {value}
      </text>
    </svg>
  );
}

function DetectionRiskBar({ value }: { value: number }) {
  const color = scoreColor(value);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-3 rounded-full bg-athena-border/30 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(value, 100)}%`, backgroundColor: color }}
        />
      </div>
      <span className="font-mono text-sm" style={{ color, minWidth: 40 }}>
        {value}%
      </span>
    </div>
  );
}

function NoiseBudgetBar({
  remaining,
  total,
}: {
  remaining: number;
  total: number;
}) {
  const used = total - remaining;
  const pct = total > 0 ? (used / total) * 100 : 0;
  const color = budgetColor(remaining, total);

  return (
    <div>
      <div className="h-3 rounded-full bg-athena-border/30 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }}
        />
      </div>
      <p className="font-mono text-xs text-athena-text-secondary mt-1">
        {used} / {total}
      </p>
    </div>
  );
}

/* ── Main Component ── */

interface OPSECMiniBarProps {
  operationId: string;
}

export function OPSECMiniBar({ operationId }: OPSECMiniBarProps) {
  const t = useTranslations("OPSEC");
  const { opsec, loading, error } = useOPSEC(operationId);

  // Translation helper with fallback
  const label = (key: string, fallback: string): string => {
    try {
      return t(key);
    } catch {
      return fallback;
    }
  };

  if (error) {
    return (
      <div className="mx-4 my-2 px-3 py-2 rounded border border-athena-border bg-athena-surface text-athena-text-secondary font-mono text-xs">
        {label("errorLoading", "OPSEC unavailable")}
      </div>
    );
  }

  if (loading && !opsec) {
    return (
      <div className="mx-4 my-2 grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-24 rounded border border-athena-border bg-athena-surface animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (!opsec) return null;

  return (
    <div className="mx-4 my-2 grid grid-cols-4 gap-3">
      {/* Noise Score */}
      <div className="rounded border border-athena-border bg-athena-surface px-3 py-2">
        <p className="font-mono text-xs text-athena-text-secondary mb-1" style={{ minHeight: 16 }}>
          {label("noiseScore", "Noise Score")}
        </p>
        <NoiseScoreRing value={opsec.noiseScore} />
      </div>

      {/* Detection Risk */}
      <div className="rounded border border-athena-border bg-athena-surface px-3 py-2 flex flex-col justify-between">
        <p className="font-mono text-xs text-athena-text-secondary mb-1" style={{ minHeight: 16 }}>
          {label("detectionRisk", "Detection Risk")}
        </p>
        <DetectionRiskBar value={opsec.detectionRisk} />
      </div>

      {/* Exposure Count */}
      <div className="rounded border border-athena-border bg-athena-surface px-3 py-2 flex flex-col justify-between">
        <p className="font-mono text-xs text-athena-text-secondary mb-1" style={{ minHeight: 16 }}>
          {label("exposureCount", "Exposures")}
        </p>
        <p
          className="font-mono text-3xl text-athena-text"
          style={{ color: "var(--color-accent)" }}
        >
          {opsec.exposureCount}
        </p>
      </div>

      {/* Noise Budget */}
      <div className="rounded border border-athena-border bg-athena-surface px-3 py-2 flex flex-col justify-between">
        <p className="font-mono text-xs text-athena-text-secondary mb-1" style={{ minHeight: 16 }}>
          {label("noiseBudget", "Noise Budget")}
        </p>
        <NoiseBudgetBar
          remaining={opsec.noiseBudgetRemaining}
          total={opsec.noiseBudgetTotal}
        />
      </div>
    </div>
  );
}
