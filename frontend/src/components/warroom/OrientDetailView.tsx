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
import type { PhaseDetail } from "@/types/ooda";

interface OrientDetailViewProps {
  detail: PhaseDetail;
}

const RISK_COLORS: Record<string, string> = {
  LOW: "var(--color-success)",
  MEDIUM: "var(--color-warning)",
  HIGH: "#EF4444",
  CRITICAL: "#DC2626",
};

export function OrientDetailView({ detail }: OrientDetailViewProps) {
  const t = useTranslations("WarRoom");

  if (!detail) return null;

  const options = detail.options ?? [];

  return (
    <div className="font-mono space-y-3">
      {/* Header */}
      <h4 className="text-athena-floor font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
        {t("attackPathAnalysis")}
      </h4>

      {/* Situation assessment */}
      {detail.situationAssessment && (
        <div>
          <h5 className="text-athena-floor font-bold uppercase tracking-wider text-[var(--color-text-tertiary)] mb-1">
            {t("situationAssessment")}
          </h5>
          <p className="text-athena-floor text-[var(--color-text-secondary)] leading-relaxed">
            {detail.situationAssessment}
          </p>
        </div>
      )}

      {/* Recommended techniques */}
      {options.length > 0 && (
        <div>
          <h5 className="text-athena-floor font-bold uppercase tracking-wider text-[var(--color-text-tertiary)] mb-2">
            {t("recommendedTechniques")} ({options.length})
          </h5>
          <div className="space-y-2">
            {options.map((option, idx) => {
              const riskColor =
                RISK_COLORS[option.riskLevel.toUpperCase()] ??
                "var(--color-text-tertiary)";
              const isRecommended =
                detail.recommendedTechniqueId === option.techniqueId;
              const confidencePct = Math.round(option.confidence * 100);

              return (
                <div
                  key={idx}
                  className={`border rounded-[var(--radius)] p-2 ${
                    isRecommended
                      ? "border-[var(--color-accent)] bg-[var(--color-accent)]/[0.04]"
                      : "border-[var(--color-border-subtle)]"
                  }`}
                >
                  {/* Option header */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-athena-floor text-[var(--color-text-tertiary)]">
                      #{idx + 1}
                    </span>
                    <span className="text-athena-floor font-bold text-[var(--color-text-primary)]">
                      {option.techniqueId}
                    </span>
                    <span className="text-athena-floor text-[var(--color-text-secondary)]">
                      {option.techniqueName}
                    </span>
                    <span className="text-athena-floor text-[var(--color-accent)] bg-[var(--color-accent)]/[0.12] px-2 py-1 rounded-[var(--radius)]">
                      {confidencePct}%
                    </span>
                    {isRecommended && (
                      <span className="text-athena-floor font-bold text-[var(--color-success)] bg-[var(--color-success)]/[0.12] border border-[var(--color-success)]/[0.25] px-2 py-1 rounded-[var(--radius)] uppercase tracking-wider">
                        REC
                      </span>
                    )}
                  </div>

                  {/* Risk + Engine badges */}
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className="text-athena-floor font-bold uppercase tracking-wider px-2 py-1 rounded-[var(--radius)] border"
                      style={{
                        color: riskColor,
                        borderColor: `${riskColor}40`,
                        backgroundColor: `${riskColor}12`,
                      }}
                    >
                      {option.riskLevel.toUpperCase()}
                    </span>
                    <span className="text-athena-floor text-[var(--color-text-tertiary)] bg-[var(--color-bg-secondary)] px-2 py-1 rounded-[var(--radius)] border border-[var(--color-border-subtle)] uppercase">
                      {option.recommendedEngine}
                    </span>
                  </div>

                  {/* Reasoning */}
                  {option.reasoning && (
                    <p className="text-athena-floor text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
                      {option.reasoning}
                    </p>
                  )}

                  {/* Prerequisites */}
                  {option.prerequisites.length > 0 && (
                    <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                      <span className="text-athena-floor text-[var(--color-text-tertiary)] font-bold uppercase tracking-wider">
                        {t("prerequisite")}:
                      </span>
                      {option.prerequisites.map((prereq, pidx) => (
                        <span
                          key={pidx}
                          className="text-athena-floor text-[var(--color-success)] flex items-center gap-0.5"
                        >
                          <span>+</span>
                          <span>{prereq}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
