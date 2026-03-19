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
import { Badge } from "@/components/atoms/Badge";
import type { OrientRecommendation } from "@/types/recommendation";
import { RiskLevel } from "@/types/enums";

const RISK_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [RiskLevel.LOW]: "success",
  [RiskLevel.MEDIUM]: "warning",
  [RiskLevel.HIGH]: "error",
  [RiskLevel.CRITICAL]: "error",
};

interface RecommendCardProps {
  recommendation: OrientRecommendation | null;
}

export function RecommendCard({ recommendation }: RecommendCardProps) {
  const t = useTranslations("Recommendation");
  const tUI = useTranslations("UI");
  const tRisk = useTranslations("Risk");

  if (!recommendation) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena p-4">
        <span className="text-xs font-mono text-athena-text-tertiary">
          {t("noRecommendation")}
        </span>
      </div>
    );
  }

  return (
    <div className="bg-athena-surface border border-athena-accent/30 rounded-athena p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-mono text-athena-accent uppercase tracking-wider">
          {t("title")}
        </span>
        <span className="text-xs font-mono text-athena-accent font-bold">
          {tUI("confidence", { value: Math.round(recommendation.confidence * 100) })}
        </span>
      </div>
      <p className="text-xs font-mono text-athena-text-tertiary mb-3">
        {recommendation.situationAssessment}
      </p>
      <div className="space-y-2">
        {recommendation.options.map((opt, i) => (
          <div
            key={opt.techniqueId}
            className={`flex items-center gap-2 p-2 rounded-athena text-xs font-mono ${
              opt.techniqueId === recommendation.recommendedTechniqueId
                ? "bg-[#3b82f610] border border-athena-accent/30"
                : "bg-athena-elevated/50"
            }`}
          >
            <span className="text-athena-text-tertiary w-4">{i + 1}.</span>
            <span className="text-athena-accent">{opt.techniqueId}</span>
            <span className="text-athena-text-light flex-1">{opt.techniqueName}</span>
            <Badge variant={RISK_VARIANT[opt.riskLevel] || "info"}>
              {tRisk(opt.riskLevel as any)}
            </Badge>
            <span className="text-athena-text-tertiary">
              {opt.recommendedEngine.toUpperCase()}
            </span>
          </div>
        ))}
      </div>
      <p className="text-sm font-mono text-athena-text-tertiary mt-3">
        {recommendation.reasoningText}
      </p>
    </div>
  );
}
