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

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/atoms/Badge";
import { ProgressBar } from "@/components/atoms/ProgressBar";
import { C5ISRDomainStatus } from "@/types/enums";
import type { C5ISRStatus, RiskSeverity } from "@/types/c5isr";

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

const SEVERITY_COLOR: Record<RiskSeverity, string> = {
  CRIT: "text-athena-error",
  WARN: "text-athena-warning",
  INFO: "text-athena-info",
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
  const [expanded, setExpanded] = useState(false);
  const report = domain.report;
  const canExpand = report !== null && report !== undefined;

  const handleClick = () => {
    if (canExpand) setExpanded((prev) => !prev);
  };

  return (
    <div
      className={`bg-athena-surface border ${borderClass} rounded-athena-md p-3 ${canExpand ? "cursor-pointer" : ""}`}
      onClick={handleClick}
    >
      <div className="flex items-start gap-3">
        {/* Hex health gauge */}
        <HexGauge value={domain.healthPct} color={color} />

        {/* Existing card content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs font-mono font-bold text-athena-text truncate">
              {t(("domain" + domain.domain.charAt(0).toUpperCase() + domain.domain.slice(1)) as any)}
            </span>
            <div className="flex items-center gap-1">
              <Badge variant={STATUS_VARIANT[domain.status] || "info"}>
                {tStatus(domain.status as any)}
              </Badge>
              {canExpand && (
                <span className="text-sm font-mono text-athena-text-secondary ml-1">
                  {expanded ? "\u25B2" : "\u25BC"}
                </span>
              )}
            </div>
          </div>
          <ProgressBar value={domain.healthPct} max={100} variant={healthVariant(domain.healthPct)} />
          <div className="flex items-center justify-between mt-2">
            <span className="text-sm font-mono text-athena-text-secondary">
              {domain.detail}
            </span>
            <span className="text-sm font-mono text-athena-text-secondary">
              {domain.healthPct}%
            </span>
          </div>
        </div>
      </div>

      {/* Expanded report sections */}
      {expanded && report && (
        <div className="mt-3 border-t border-athena-border pt-3 space-y-3" onClick={(e) => e.stopPropagation()}>
          {/* Metrics table */}
          {report.metrics.length > 0 && (
            <div>
              <h4 className="text-sm font-mono font-bold text-athena-text-secondary mb-1 uppercase">
                {t("reportMetrics" as any)}
              </h4>
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-athena-text-secondary">
                    <th className="text-left pr-2">{t("reportMetricName" as any)}</th>
                    <th className="text-right pr-2">{t("reportMetricValue" as any)}</th>
                    <th className="text-right pr-2">{t("reportMetricWeight" as any)}</th>
                    <th className="text-left w-1/3"></th>
                  </tr>
                </thead>
                <tbody>
                  {report.metrics.map((m) => (
                    <tr key={m.name} className="text-athena-text">
                      <td className="pr-2">{m.name}</td>
                      <td className="text-right pr-2">
                        {m.value.toFixed(1)}
                        {m.numerator !== null && m.denominator !== null && (
                          <span className="text-athena-text-secondary ml-1">
                            ({m.numerator}/{m.denominator})
                          </span>
                        )}
                      </td>
                      <td className="text-right pr-2">{m.weight}</td>
                      <td>
                        <div className="h-1 bg-athena-border rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.min(100, m.value)}%`,
                              backgroundColor: healthColor(m.value),
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Asset roster */}
          {report.asset_roster.length > 0 && (
            <div>
              <h4 className="text-sm font-mono font-bold text-athena-text-secondary mb-1 uppercase">
                {t("reportAssetRoster" as any)}
              </h4>
              <div className="max-h-32 overflow-y-auto">
                {report.asset_roster.slice(0, 10).map((asset, i) => (
                  <div key={i} className="text-sm font-mono text-athena-text py-0.5 border-b border-athena-border/30 last:border-0">
                    {Object.entries(asset)
                      .filter(([k]) => k !== "type")
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(" | ")}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tactical assessment */}
          {report.tactical_assessment && (
            <div>
              <h4 className="text-sm font-mono font-bold text-athena-text-secondary mb-1 uppercase">
                {t("reportTacticalAssessment" as any)}
              </h4>
              <p className="text-sm font-mono text-athena-text bg-athena-bg/50 rounded p-2">
                {report.tactical_assessment}
              </p>
            </div>
          )}

          {/* Risk vectors */}
          {report.risk_vectors.length > 0 && (
            <div>
              <h4 className="text-sm font-mono font-bold text-athena-text-secondary mb-1 uppercase">
                {t("reportRiskVectors" as any)}
              </h4>
              <ul className="space-y-0.5">
                {report.risk_vectors.map((rv, i) => (
                  <li
                    key={i}
                    className={`text-sm font-mono ${SEVERITY_COLOR[rv.severity]}`}
                  >
                    [{rv.severity}] {rv.message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommended actions */}
          {report.recommended_actions.length > 0 && (
            <div>
              <h4 className="text-sm font-mono font-bold text-athena-text-secondary mb-1 uppercase">
                {t("reportRecommendedActions" as any)}
              </h4>
              <ol className="list-decimal list-inside space-y-0.5">
                {report.recommended_actions.map((action, i) => (
                  <li key={i} className="text-sm font-mono text-athena-text">
                    {action}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Cross-domain impacts */}
          {report.cross_domain_impacts.length > 0 && (
            <div>
              <h4 className="text-sm font-mono font-bold text-athena-text-secondary mb-1 uppercase">
                {t("reportCrossDomainImpacts" as any)}
              </h4>
              <ul className="list-disc list-inside space-y-0.5">
                {report.cross_domain_impacts.map((impact, i) => (
                  <li key={i} className="text-sm font-mono text-athena-text">
                    {impact}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
