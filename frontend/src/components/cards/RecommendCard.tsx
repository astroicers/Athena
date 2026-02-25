"use client";

import { Badge } from "@/components/atoms/Badge";
import type { PentestGPTRecommendation } from "@/types/recommendation";
import { RiskLevel } from "@/types/enums";

const RISK_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [RiskLevel.LOW]: "success",
  [RiskLevel.MEDIUM]: "warning",
  [RiskLevel.HIGH]: "error",
  [RiskLevel.CRITICAL]: "error",
};

interface RecommendCardProps {
  recommendation: PentestGPTRecommendation | null;
}

export function RecommendCard({ recommendation }: RecommendCardProps) {
  if (!recommendation) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
        <span className="text-xs font-mono text-athena-text-secondary">
          No recommendation available
        </span>
      </div>
    );
  }

  return (
    <div className="bg-athena-surface border border-athena-accent/30 rounded-athena-md p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-mono text-athena-accent uppercase tracking-wider">
          PentestGPT Recommendation
        </span>
        <span className="text-xs font-mono text-athena-accent font-bold">
          {Math.round(recommendation.confidence * 100)}% confidence
        </span>
      </div>
      <p className="text-xs font-mono text-athena-text-secondary mb-3">
        {recommendation.situationAssessment}
      </p>
      <div className="space-y-2">
        {recommendation.options.map((opt, i) => (
          <div
            key={opt.techniqueId}
            className={`flex items-center gap-2 p-2 rounded-athena-sm text-xs font-mono ${
              opt.techniqueId === recommendation.recommendedTechniqueId
                ? "bg-athena-accent/10 border border-athena-accent/30"
                : "bg-athena-elevated/50"
            }`}
          >
            <span className="text-athena-text-secondary w-4">{i + 1}.</span>
            <span className="text-athena-accent">{opt.techniqueId}</span>
            <span className="text-athena-text flex-1">{opt.techniqueName}</span>
            <Badge variant={RISK_VARIANT[opt.riskLevel] || "info"}>
              {opt.riskLevel.toUpperCase()}
            </Badge>
            <span className="text-athena-text-secondary">
              {opt.recommendedEngine.toUpperCase()}
            </span>
          </div>
        ))}
      </div>
      <p className="text-[10px] font-mono text-athena-text-secondary mt-3">
        {recommendation.reasoningText}
      </p>
    </div>
  );
}
