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

interface NoiseRiskMatrixProps {
  noiseLevel: "low" | "medium" | "high";
  riskLevel: "low" | "medium" | "high" | "critical";
  currentAction?: string;
}

type ActionType = "go" | "caution" | "hold" | "abort";

const MATRIX: Record<string, Record<string, ActionType>> = {
  low: { low: "go", medium: "go", high: "caution", critical: "hold" },
  medium: { low: "go", medium: "caution", high: "hold", critical: "abort" },
  high: { low: "caution", medium: "hold", high: "abort", critical: "abort" },
};

const ACTION_COLORS: Record<ActionType, string> = {
  go: "var(--color-success)",
  caution: "var(--color-warning)",
  hold: "var(--color-warning)",
  abort: "var(--color-error)",
};

const ACTION_I18N_KEYS: Record<ActionType, string> = {
  go: "actionGo",
  caution: "actionCaution",
  hold: "actionHold",
  abort: "actionAbort",
};

const NOISE_LEVELS = ["low", "medium", "high"] as const;
const RISK_LEVELS = ["low", "medium", "high", "critical"] as const;

const NOISE_I18N_KEYS: Record<string, string> = {
  low: "noiseLow",
  medium: "noiseMedium",
  high: "noiseHigh",
};

const RISK_I18N_KEYS: Record<string, string> = {
  low: "riskLow",
  medium: "riskMedium",
  high: "riskHigh",
  critical: "riskCritical",
};

export function NoiseRiskMatrix({
  noiseLevel,
  riskLevel,
}: NoiseRiskMatrixProps) {
  const t = useTranslations("AIDecision");

  return (
    <div>
      <h3 className="text-xs font-mono text-athena-foreground-muted mb-2 tracking-wider">
        {(t as any)("noiseRiskMatrix")}
      </h3>

      <div
        className="grid gap-px text-xs font-mono"
        style={{
          gridTemplateColumns: "auto repeat(3, 1fr)",
          gridTemplateRows: "auto repeat(4, 1fr)",
        }}
      >
        {/* Top-left empty corner */}
        <div />

        {/* Column headers (noise levels) */}
        {NOISE_LEVELS.map((n) => (
          <div
            key={`col-${n}`}
            className="text-center text-athena-foreground-muted py-1"
          >
            {(t as any)(NOISE_I18N_KEYS[n])}
          </div>
        ))}

        {/* Rows */}
        {RISK_LEVELS.map((r) => (
          <>
            {/* Row header */}
            <div
              key={`row-${r}`}
              className="text-athena-foreground-muted pr-2 py-1 text-right"
            >
              {(t as any)(RISK_I18N_KEYS[r])}
            </div>

            {/* Cells */}
            {NOISE_LEVELS.map((n) => {
              const action = MATRIX[n][r];
              const color = ACTION_COLORS[action];
              const isActive = n === noiseLevel && r === riskLevel;

              return (
                <div
                  key={`${n}-${r}`}
                  className="text-center py-1 px-1 rounded-sm"
                  style={{
                    color,
                    backgroundColor: `color-mix(in srgb, ${color} 10%, transparent)`,
                    ...(isActive
                      ? {
                          border: `1px solid ${color}`,
                          boxShadow: `0 0 6px ${color}`,
                        }
                      : {
                          border: "1px solid transparent",
                        }),
                  }}
                >
                  {(t as any)(ACTION_I18N_KEYS[action])}
                </div>
              );
            })}
          </>
        ))}
      </div>
    </div>
  );
}
