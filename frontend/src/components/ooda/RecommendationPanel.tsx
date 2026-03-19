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

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/atoms/Badge";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import type { OrientRecommendation, TacticalOption } from "@/types/recommendation";
import { RiskLevel } from "@/types/enums";

const RISK_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [RiskLevel.LOW]: "success",
  [RiskLevel.MEDIUM]: "warning",
  [RiskLevel.HIGH]: "error",
  [RiskLevel.CRITICAL]: "error",
};

interface RecommendationPanelProps {
  recommendation: OrientRecommendation | null;
}

function OptionCard({ option, index }: { option: TacticalOption; index: number }) {
  const t = useTranslations("Recommendation");
  const tRisk = useTranslations("Risk");
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`bg-athena-bg border rounded-athena p-3 cursor-pointer transition-colors ${
        index === 0 ? "border-athena-accent/50" : "border-athena-border"
      }`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="text-athena-accent text-xs font-mono font-bold">
            {option.techniqueId}
          </span>
          {index === 0 && (
            <span className="text-sm font-mono text-athena-accent bg-[#3b82f610] px-1.5 py-0.5 rounded-athena">
              {t("recommended")}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={RISK_VARIANT[option.riskLevel] || "info"}>
            {tRisk(option.riskLevel as any)}
          </Badge>
          <span className="text-sm font-mono text-athena-text-tertiary">
            {(option.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      <p className="text-xs font-mono text-athena-text-tertiary">{option.techniqueName}</p>
      <p className="text-sm font-mono text-athena-text-tertiary mt-1">
        {t("engine", { name: option.recommendedEngine.toUpperCase() })}
      </p>

      {expanded && (
        <div className="mt-2 pt-2 border-t border-athena-border/50 space-y-2">
          <p className="text-xs font-mono text-athena-text-tertiary leading-relaxed">
            {option.reasoning}
          </p>
          {option.prerequisites.length > 0 && (
            <div>
              <span className="text-sm font-mono text-athena-text-tertiary uppercase">
                {t("prerequisites")}
              </span>
              <ul className="mt-1 space-y-0.5">
                {option.prerequisites.map((p, i) => (
                  <li key={i} className="text-sm font-mono text-athena-text-tertiary">
                    &bull; {p}
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

export function RecommendationPanel({
  recommendation,
}: RecommendationPanelProps) {
  const t = useTranslations("Recommendation");
  const tHints = useTranslations("Hints");

  if (!recommendation) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena p-4">
        <SectionHeader level="card" className="mb-3" title={tHints("recommendation")}>
          {t("title")}
        </SectionHeader>
        <div className="text-center py-4">
          <span className="text-xs font-mono text-athena-text-tertiary">
            {t("noRecommendation")}
          </span>
        </div>
      </div>
    );
  }

  const isDecided = recommendation.accepted !== null;

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena p-4">
      <SectionHeader
        level="card"
        className="mb-3"
        title={tHints("recommendation")}
        trailing={
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-athena-text-tertiary">
              {t("confidence", { value: (recommendation.confidence * 100).toFixed(0) })}
            </span>
            {isDecided && (
              <Badge variant={recommendation.accepted ? "success" : "error"}>
                {recommendation.accepted ? t("accepted") : t("rejected")}
              </Badge>
            )}
          </div>
        }
      >
        {t("title")}
      </SectionHeader>

      {/* Situation Assessment */}
      <div className="bg-athena-bg border border-athena-border/50 rounded-athena p-3 mb-3">
        <span className="text-sm font-mono text-athena-text-tertiary uppercase tracking-wider">
          {t("situationAssessment")}
        </span>
        <p className="text-xs font-mono text-athena-text-light leading-relaxed mt-1">
          {recommendation.situationAssessment}
        </p>
      </div>

      {/* Tactical Options */}
      <div className="space-y-2 mb-3">
        <span className="text-sm font-mono text-athena-text-tertiary uppercase tracking-wider">
          {t("tacticalOptions", { count: recommendation.options.length })}
        </span>
        {recommendation.options.map((opt, i) => (
          <OptionCard key={opt.techniqueId} option={opt} index={i} />
        ))}
      </div>

    </div>
  );
}
