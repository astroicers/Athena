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
import { SectionHeader } from "@/components/atoms/SectionHeader";

interface ThreatBreakdown {
  noise: number;
  auth_failures: number;
  detection_events: number;
  dwell: number;
}

interface ThreatLevelGaugeProps {
  level: number;
  breakdown?: ThreatBreakdown;
}

const BREAKDOWN_FACTORS = [
  { key: "noise" as const, color: "var(--color-warning)", fallback: "Noise" },
  { key: "auth_failures" as const, color: "var(--color-error)", fallback: "Auth Failures" },
  { key: "detection_events" as const, color: "var(--color-critical)", fallback: "Detection" },
  { key: "dwell" as const, color: "var(--color-accent)", fallback: "Dwell" },
] as const;

export function ThreatLevelGauge({ level, breakdown }: ThreatLevelGaugeProps) {
  const t = useTranslations("C5ISR");
  const tThreat = useTranslations("Threat");

  const clamped = Math.max(0, Math.min(10, level));
  // Needle angle: 0 → left (180° in math), 10 → right (0° in math)
  // In SVG coords (Y-down): angle in radians from center (100,100)
  const needleRad = Math.PI * (1 - clamped / 10);
  const color =
    clamped >= 8 ? "var(--color-critical)" :
    clamped >= 6 ? "var(--color-error)" :
    clamped >= 4 ? "var(--color-warning)" :
    "var(--color-success)";

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 flex flex-col items-center">
      <SectionHeader level="card" className="mb-3 self-start">
        {t("threatLevel")}
      </SectionHeader>
      <svg viewBox="0 0 200 120" className="w-full max-w-[200px]">
        {/* Background arc */}
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="12"
          strokeLinecap="round"
        />
        {/* Colored arc */}
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${(clamped / 10) * 251.2} 251.2`}
        />
        {/* Needle */}
        <line
          x1="100"
          y1="100"
          x2={100 + 60 * Math.cos(needleRad)}
          y2={100 - 60 * Math.sin(needleRad)}
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
        />
        <circle cx="100" cy="100" r="4" fill={color} />
        {/* Value */}
        <text
          x="100"
          y="90"
          textAnchor="middle"
          className="text-2xl font-mono font-bold"
          fill={color}
          fontSize="28"
          fontFamily="var(--font-mono)"
          fontWeight="bold"
        >
          {level.toFixed(1)}
        </text>
        {/* Labels */}
        <text x="20" y="116" textAnchor="middle" fill="var(--color-text-secondary)" fontSize="9" fontFamily="var(--font-mono)">0</text>
        <text x="100" y="20" textAnchor="middle" fill="var(--color-text-secondary)" fontSize="9" fontFamily="var(--font-mono)">5</text>
        <text x="180" y="116" textAnchor="middle" fill="var(--color-text-secondary)" fontSize="9" fontFamily="var(--font-mono)">10</text>
      </svg>

      {breakdown && (() => {
        const total = breakdown.noise + breakdown.auth_failures + breakdown.detection_events + breakdown.dwell;
        if (total === 0) return null;
        return (
          <div className="w-full mt-3">
            {/* Stacked horizontal bar */}
            <div className="flex w-full h-3 rounded-athena-sm overflow-hidden">
              {BREAKDOWN_FACTORS.map(({ key, color }) => {
                const pct = (breakdown[key] / total) * 100;
                if (pct <= 0) return null;
                return (
                  <div
                    key={key}
                    style={{ width: `${pct}%`, backgroundColor: color }}
                  />
                );
              })}
            </div>
            {/* Labels */}
            <div className="flex justify-between mt-1.5 gap-1">
              {BREAKDOWN_FACTORS.map(({ key, color, fallback }) => {
                const pct = (breakdown[key] / total) * 100;
                let label: string;
                try {
                  label = tThreat(key);
                } catch {
                  label = fallback;
                }
                return (
                  <div key={key} className="flex flex-col items-center flex-1 min-w-0">
                    <span
                      className="font-mono text-xs truncate"
                      style={{ color }}
                    >
                      {label}
                    </span>
                    <span className="font-mono text-xs text-athena-text-secondary">
                      {pct.toFixed(0)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
