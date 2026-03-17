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

import { ProgressBar } from "@/components/atoms/ProgressBar";
import type { C5ISRStatus } from "@/types/c5isr";

function healthVariant(pct: number): "success" | "warning" | "error" {
  if (pct >= 80) return "success";
  if (pct >= 50) return "warning";
  return "error";
}

function healthColor(pct: number): string {
  if (pct >= 80) return "var(--color-success)";
  if (pct >= 50) return "#FBBF24";
  return "var(--color-error)";
}

interface C5ISRDomainCardProps {
  domain: C5ISRStatus;
  onClick?: () => void;
}

export function C5ISRDomainCard({ domain, onClick }: C5ISRDomainCardProps) {
  const pct = Math.round(domain.healthPct);
  const variant = healthVariant(pct);
  const color = healthColor(pct);

  return (
    <button
      onClick={onClick}
      className="rounded-athena-md flex flex-col gap-1.5 text-left transition-colors bg-[#ffffff0d] border border-[#ffffff10] hover:border-[#3b82f640] px-3 py-2.5"
    >
      <div className="flex items-center justify-between w-full">
        <span
          className="font-mono text-[9px] font-bold uppercase tracking-wider text-[#ffffff20]"
        >
          {domain.domain}
        </span>
        <span
          className="font-mono text-[9px] font-bold uppercase tracking-wider rounded-athena-sm"
          style={{
            color,
            backgroundColor: `${color}15`,
            padding: "1px 5px",
          }}
        >
          {domain.status}
        </span>
      </div>

      <span
        className="font-mono text-lg font-bold"
        style={{ color }}
      >
        {pct}%
      </span>

      <ProgressBar value={pct} variant={variant} />

      {domain.metricLabel && (
        <span
          className="font-mono text-[8px] text-[#ffffff30]"
        >
          {domain.numerator != null && domain.denominator != null
            ? `${domain.numerator}/${domain.denominator} `
            : ""}
          {domain.metricLabel}
        </span>
      )}
    </button>
  );
}
