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
import { Badge } from "@/components/atoms/Badge";
import { ProgressBar } from "@/components/atoms/ProgressBar";
import { C5ISRDomainStatus } from "@/types/enums";
import type { C5ISRStatus } from "@/types/c5isr";

const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [C5ISRDomainStatus.OPERATIONAL]: "success",
  [C5ISRDomainStatus.ACTIVE]: "success",
  [C5ISRDomainStatus.NOMINAL]: "success",
  [C5ISRDomainStatus.ENGAGED]: "info",
  [C5ISRDomainStatus.SCANNING]: "info",
  [C5ISRDomainStatus.DEGRADED]: "warning",
  [C5ISRDomainStatus.OFFLINE]: "error",
  [C5ISRDomainStatus.CRITICAL]: "error",
};

function healthVariant(pct: number): "success" | "warning" | "error" | "default" {
  if (pct >= 80) return "success";
  if (pct >= 60) return "warning";
  return "error";
}

function healthColor(pct: number): string {
  if (pct >= 80) return "var(--color-success)";
  if (pct >= 50) return "var(--color-warning)";
  return "var(--color-error)";
}

function healthBorderClass(pct: number): string {
  if (pct >= 80) return "border-[var(--color-success)]/30";
  if (pct >= 50) return "border-[var(--color-warning)]/30";
  return "border-[var(--color-error)]/30";
}

/* ------------------------------------------------------------------ */
/*  HexGauge — SVG hexagonal health indicator                         */
/* ------------------------------------------------------------------ */
function HexGauge({ value, color }: { value: number; color: string }) {
  // Hexagon vertices for a 36x40 viewBox (flat-top)
  const points = "18,1 33,10 33,30 18,39 3,30 3,10";
  // Approximate perimeter of this hexagon ~= 108
  const perimeter = 108;
  const filled = (Math.min(100, Math.max(0, value)) / 100) * perimeter;

  return (
    <svg width="36" height="40" viewBox="0 0 36 40" className="shrink-0">
      {/* Background hex */}
      <polygon
        points={points}
        fill="none"
        stroke="var(--color-border)"
        strokeWidth="1.5"
      />
      {/* Foreground hex — filled arc proportional to health % */}
      <polygon
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeDasharray={`${filled} ${perimeter - filled}`}
        strokeLinecap="round"
      />
      {/* Percentage label */}
      <text
        x="18"
        y="22"
        textAnchor="middle"
        dominantBaseline="central"
        fill={color}
        fontFamily="var(--font-mono)"
        fontSize="10"
        fontWeight="700"
      >
        {value}
      </text>
    </svg>
  );
}

interface DomainCardProps {
  domain: C5ISRStatus;
}

export function DomainCard({ domain }: DomainCardProps) {
  const t = useTranslations("C5ISR");
  const tStatus = useTranslations("Status");
  const color = healthColor(domain.healthPct);
  const borderClass = healthBorderClass(domain.healthPct);

  return (
    <div className={`bg-athena-surface border ${borderClass} rounded-athena-md p-3 flex items-start gap-3`}>
      {/* Hex health gauge */}
      <HexGauge value={domain.healthPct} color={color} />

      {/* Existing card content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-mono font-bold text-athena-text">
            {t(("domain" + domain.domain.charAt(0).toUpperCase() + domain.domain.slice(1)) as any)}
          </span>
          <Badge variant={STATUS_VARIANT[domain.status] || "info"}>
            {tStatus(domain.status as any)}
          </Badge>
        </div>
        <ProgressBar value={domain.healthPct} max={100} variant={healthVariant(domain.healthPct)} />
        <div className="flex items-center justify-between mt-2">
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {domain.detail}
          </span>
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {domain.healthPct}%
          </span>
        </div>
      </div>
    </div>
  );
}
