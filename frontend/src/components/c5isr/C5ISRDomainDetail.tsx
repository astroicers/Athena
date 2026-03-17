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
import type { C5ISRStatus, DomainReport } from "@/types/c5isr";

function severityColor(severity: string): string {
  switch (severity) {
    case "CRIT":
      return "var(--color-error)";
    case "WARN":
      return "#FBBF24";
    default:
      return "var(--color-accent)";
  }
}

interface C5ISRDomainDetailProps {
  domain: C5ISRStatus;
  report: DomainReport | null;
  onClose: () => void;
}

export function C5ISRDomainDetail({ domain, report, onClose }: C5ISRDomainDetailProps) {

  return (
    <div
      className="rounded-athena-md flex flex-col gap-3 overflow-y-auto bg-[#111827] border border-[#1f2937]"
      style={{
        padding: 16,
        maxHeight: 400,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span
          className="font-mono text-xs font-bold uppercase text-[#e5e7eb]"
        >
          {domain.domain} REPORT
        </span>
        <button
          onClick={onClose}
          className="font-mono text-xs transition-colors text-[#ffffff30]"
          aria-label="Close detail"
        >
          x
        </button>
      </div>

      {/* Executive Summary */}
      {report?.executiveSummary && (
        <p
          className="font-mono text-[9px] leading-relaxed text-[#ffffff50]"
        >
          {report.executiveSummary}
        </p>
      )}

      {/* Metrics */}
      {report?.metrics && report.metrics.length > 0 && (
        <div>
          <span
            className="font-mono text-[8px] font-bold uppercase tracking-wider block mb-1 text-[#ffffff30]"
          >
            METRICS
          </span>
          <div className="flex flex-col gap-1.5">
            {report.metrics.map((m) => (
              <div key={m.name} className="flex items-center gap-2">
                <span
                  className="font-mono text-[8px] w-32 shrink-0 text-[#ffffff60]"
                >
                  {m.name}
                </span>
                <div className="flex-1">
                  <ProgressBar
                    value={m.value}
                    variant={
                      m.value >= 80
                        ? "success"
                        : m.value >= 50
                          ? "warning"
                          : "error"
                    }
                  />
                </div>
                <span
                  className="font-mono text-[8px] athena-tabular-nums w-16 text-right text-[#ffffff50]"
                >
                  {m.numerator != null && m.denominator != null
                    ? `${m.numerator}/${m.denominator}`
                    : `${Math.round(m.value)}%`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk Vectors */}
      {report?.riskVectors && report.riskVectors.length > 0 && (
        <div>
          <span
            className="font-mono text-[8px] font-bold uppercase tracking-wider block mb-1 text-[#ffffff30]"
          >
            RISK VECTORS
          </span>
          <div className="flex flex-col gap-1">
            {report.riskVectors.map((rv, i) => (
              <div key={i} className="flex items-center gap-2">
                <span
                  className="font-mono text-[7px] font-bold px-1 py-0.5 rounded-athena-sm"
                  style={{
                    backgroundColor: `color-mix(in srgb, ${severityColor(rv.severity)} 20%, transparent)`,
                    color: severityColor(rv.severity),
                  }}
                >
                  {rv.severity}
                </span>
                <span
                  className="font-mono text-[8px] text-[#ffffff60]"
                >
                  {rv.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Actions */}
      {report?.recommendedActions && report.recommendedActions.length > 0 && (
        <div>
          <span
            className="font-mono text-[8px] font-bold uppercase tracking-wider block mb-1 text-[#ffffff30]"
          >
            RECOMMENDED ACTIONS
          </span>
          <div className="flex flex-col gap-0.5">
            {report.recommendedActions.map((action, i) => (
              <p
                key={i}
                className="font-mono text-[8px] text-[#ffffff60]"
              >
                - {action}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Cross-Domain Impacts */}
      {report?.crossDomainImpacts &&
        report.crossDomainImpacts.length > 0 && (
          <div>
            <span
              className="font-mono text-[8px] font-bold uppercase tracking-wider block mb-1 text-[#ffffff30]"
            >
              CROSS-DOMAIN IMPACTS
            </span>
            <div className="flex flex-col gap-0.5">
              {report.crossDomainImpacts.map((impact, i) => (
                <p
                  key={i}
                  className="font-mono text-[8px] text-[#3b82f6]"
                >
                  {impact}
                </p>
              ))}
            </div>
          </div>
        )}
    </div>
  );
}
