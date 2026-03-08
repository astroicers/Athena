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
import type { VulnSeverity } from "@/types/vulnerability";

const SEVERITY_COLORS: Record<VulnSeverity, string> = {
  critical: "#ff0040",
  high: "#ff4444",
  medium: "#ffaa00",
  low: "#00d4ff",
  info: "#8a8a9a",
};

const SEVERITY_ORDER: VulnSeverity[] = ["critical", "high", "medium", "low", "info"];

interface SeverityHeatStripProps {
  bySeverity: Record<VulnSeverity, number>;
  total: number;
}

export function SeverityHeatStrip({ bySeverity, total }: SeverityHeatStripProps) {
  const t = useTranslations("Vulns");
  if (total === 0) return null;

  return (
    <div className="w-full flex h-10 rounded-athena-sm overflow-hidden">
      {SEVERITY_ORDER.map((sev) => {
        const count = bySeverity[sev] || 0;
        if (count === 0) return null;
        const pct = (count / total) * 100;
        return (
          <div
            key={sev}
            className={`flex items-center justify-center gap-1 transition-all ${sev === "critical" ? "animate-pulse" : ""}`}
            style={{
              width: `${pct}%`,
              backgroundColor: SEVERITY_COLORS[sev] + "30",
              borderBottom: `3px solid ${SEVERITY_COLORS[sev]}`,
            }}
          >
            <span
              className="text-xs font-mono font-bold uppercase"
              style={{ color: SEVERITY_COLORS[sev] }}
            >
              {t(`severity.${sev}`)}
            </span>
            <span
              className="text-xs font-mono font-bold"
              style={{ color: SEVERITY_COLORS[sev] }}
            >
              {count}
            </span>
          </div>
        );
      })}
    </div>
  );
}
