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

import { useTranslations } from "next-intl";
import type { C5ISRStatus } from "@/types/c5isr";

interface TargetStat {
  id: string;
  hostname: string;
  ipAddress: string;
  isCompromised: boolean;
  privilegeLevel: string;
  iterationCount: number;
}

interface StatusPanelProps {
  c5isrDomains: C5ISRStatus[];
  noiseLevel: number;
  riskLevel: string;
  matrixAction: string;
  confidence: number;
  targets?: TargetStat[];
}

function healthColor(pct: number): string {
  if (pct >= 80) return "var(--color-success)";
  if (pct >= 50) return "var(--color-warning)";
  return "var(--color-error)";
}

function noiseColor(pct: number): string {
  if (pct <= 33) return "var(--color-success)";
  if (pct <= 66) return "var(--color-warning)";
  return "var(--color-error)";
}

function riskColor(level: string): string {
  switch (level.toUpperCase()) {
    case "LOW":
      return "var(--color-success)";
    case "MED":
      return "var(--color-warning)";
    case "HIGH":
    case "CRIT":
      return "var(--color-error)";
    default:
      return "var(--color-text-secondary)";
  }
}

function actionStyle(action: string): { bg: string; text: string } {
  switch (action.toUpperCase()) {
    case "GO":
      return {
        bg: "bg-athena-success/[0.12]",
        text: "text-athena-success",
      };
    case "CAUTION":
      return {
        bg: "bg-athena-warning/[0.12]",
        text: "text-athena-warning",
      };
    case "HOLD":
      return {
        bg: "bg-athena-accent/[0.12]",
        text: "text-athena-accent",
      };
    case "ABORT":
      return {
        bg: "bg-athena-error/[0.12]",
        text: "text-athena-error",
      };
    default:
      return {
        bg: "bg-athena-surface",
        text: "text-athena-text-secondary",
      };
  }
}

function domainLabel(domain: string): string {
  return domain.slice(0, 4).toUpperCase();
}

export function StatusPanel({
  c5isrDomains,
  noiseLevel,
  riskLevel,
  matrixAction,
  confidence,
  targets,
}: StatusPanelProps) {
  const t = useTranslations("WarRoom");
  const action = actionStyle(matrixAction);

  return (
    <div className="w-[260px] bg-athena-surface border-l border-[var(--color-border)] p-3 flex flex-col gap-0 font-mono h-full overflow-y-auto">
      {/* Section 0: TARGETS */}
      {targets && targets.length > 0 && (
        <>
          <div className="flex flex-col gap-2">
            <span className="text-athena-floor font-bold tracking-[2px] text-[var(--color-text-secondary)]">
              {t("targets")} ({targets.length})
            </span>
            {targets.map((tgt) => (
              <div key={tgt.id} className="flex items-center gap-2">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    tgt.isCompromised
                      ? "bg-[var(--color-success)]"
                      : "bg-[var(--color-text-tertiary)]"
                  }`}
                />
                <span className="text-athena-floor font-mono text-[var(--color-text-primary)] flex-1 truncate">
                  {tgt.ipAddress}
                </span>
                <span className="text-athena-floor font-mono text-[var(--color-text-tertiary)]">
                  {tgt.privilegeLevel}
                </span>
                <span className="text-athena-floor font-mono text-[var(--color-text-tertiary)]">
                  {tgt.iterationCount}x
                </span>
              </div>
            ))}
          </div>
          <div className="h-px bg-[var(--color-border)] my-3" />
        </>
      )}

      {/* Section 1: C5ISR HEALTH */}
      <div className="flex flex-col gap-2">
        <span className="text-athena-floor text-athena-text-tertiary uppercase tracking-wider font-semibold">
          {t("c5isrHealth")}
        </span>

        <div className="flex flex-col gap-1.5">
          {c5isrDomains.map((d) => {
            const color = healthColor(d.healthPct);
            return (
              <div key={d.id} className="flex items-center gap-2">
                <span className="text-athena-floor text-athena-text-tertiary w-10 shrink-0 uppercase tracking-wider">
                  {domainLabel(d.domain)}
                </span>
                <div className="flex-1 h-1 rounded-full bg-athena-elevated overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(100, Math.max(0, d.healthPct))}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
                <span
                  className="text-athena-floor athena-tabular-nums w-8 text-right shrink-0"
                  style={{ color }}
                >
                  {Math.round(d.healthPct)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border)] my-3" />

      {/* Section 2: TACTICAL STATUS */}
      <div className="flex flex-col gap-2">
        <span className="text-athena-floor text-athena-text-tertiary uppercase tracking-wider font-semibold">
          {t("tacticalStatus")}
        </span>

        <div className="flex gap-2">
          {/* Noise box */}
          <div className="flex-1 bg-athena-bg rounded-[var(--radius)] p-2 flex flex-col items-center gap-0.5">
            <span className="text-athena-floor text-athena-text-tertiary uppercase tracking-wider">
              {t("noise")}
            </span>
            <span
              className="text-athena-heading-section font-bold athena-tabular-nums"
              style={{ color: noiseColor(noiseLevel) }}
            >
              {Math.round(noiseLevel)}%
            </span>
          </div>

          {/* Risk box */}
          <div className="flex-1 bg-athena-bg rounded-[var(--radius)] p-2 flex flex-col items-center gap-0.5">
            <span className="text-athena-floor text-athena-text-tertiary uppercase tracking-wider">
              {t("risk")}
            </span>
            <span
              className="text-athena-heading-section font-bold uppercase"
              style={{ color: riskColor(riskLevel) }}
            >
              {riskLevel}
            </span>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border)] my-3" />

      {/* Section 3: DECISION */}
      <div className="flex flex-col gap-2">
        <span className="text-athena-floor text-athena-text-tertiary uppercase tracking-wider font-semibold">
          {t("decision")}
        </span>

        <div
          className={`${action.bg} rounded-[var(--radius)] p-3 flex items-center justify-center`}
        >
          <span className={`text-2xl font-bold uppercase ${action.text}`}>
            {matrixAction}
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border)] my-3" />

      {/* Section 4: CONFIDENCE */}
      <div className="flex flex-col gap-2">
        <span className="text-athena-floor text-athena-text-tertiary uppercase tracking-wider font-semibold">
          {t("confidence")}
        </span>

        <div className="flex items-center justify-center py-1">
          <span className="text-3xl font-bold text-athena-accent athena-tabular-nums">
            {(confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
}
