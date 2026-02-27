// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// tech-debt: test-pending (SPEC-018)

"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import type { PentestGPTRecommendation, TacticalOption } from "@/types/recommendation";
import { RiskLevel } from "@/types/enums";

const RISK_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [RiskLevel.LOW]: "success",
  [RiskLevel.MEDIUM]: "warning",
  [RiskLevel.HIGH]: "error",
  [RiskLevel.CRITICAL]: "error",
};

interface RecommendationPanelProps {
  recommendation: PentestGPTRecommendation | null;
  operationId: string;
  onAccepted?: () => void;
}

function OptionCard({ option, index }: { option: TacticalOption; index: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`bg-athena-bg border rounded-athena-sm p-3 cursor-pointer transition-colors ${
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
            <span className="text-[9px] font-mono text-athena-accent bg-athena-accent/10 px-1.5 py-0.5 rounded">
              RECOMMENDED
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={RISK_VARIANT[option.riskLevel] || "info"}>
            {option.riskLevel.toUpperCase()}
          </Badge>
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {(option.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      <p className="text-xs font-mono text-athena-text-secondary">{option.techniqueName}</p>
      <p className="text-[10px] font-mono text-athena-text-secondary/70 mt-1">
        Engine: {option.recommendedEngine.toUpperCase()}
      </p>

      {expanded && (
        <div className="mt-2 pt-2 border-t border-athena-border/50 space-y-2">
          <p className="text-xs font-mono text-athena-text-secondary leading-relaxed">
            {option.reasoning}
          </p>
          {option.prerequisites.length > 0 && (
            <div>
              <span className="text-[9px] font-mono text-athena-text-secondary uppercase">
                Prerequisites:
              </span>
              <ul className="mt-1 space-y-0.5">
                {option.prerequisites.map((p, i) => (
                  <li key={i} className="text-[10px] font-mono text-athena-text-secondary/70">
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
  operationId,
  onAccepted,
}: RecommendationPanelProps) {
  const [accepting, setAccepting] = useState(false);
  const { addToast } = useToast();

  if (!recommendation) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
        <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-3">
          PentestGPT Recommendation
        </h3>
        <div className="text-center py-4">
          <span className="text-xs font-mono text-athena-text-secondary">
            No recommendation available. Trigger an OODA cycle to generate one.
          </span>
        </div>
      </div>
    );
  }

  const isDecided = recommendation.accepted !== null;

  async function handleAccept() {
    setAccepting(true);
    try {
      await api.post(
        `/operations/${operationId}/recommendations/${recommendation!.id}/accept`,
      );
      onAccepted?.();
    } catch {
      addToast("Failed to accept recommendation", "error");
    } finally {
      setAccepting(false);
    }
  }

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
          PentestGPT Recommendation
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-athena-text-secondary">
            Confidence: {(recommendation.confidence * 100).toFixed(0)}%
          </span>
          {isDecided && (
            <Badge variant={recommendation.accepted ? "success" : "error"}>
              {recommendation.accepted ? "ACCEPTED" : "REJECTED"}
            </Badge>
          )}
        </div>
      </div>

      {/* Situation Assessment */}
      <div className="bg-athena-bg border border-athena-border/50 rounded-athena-sm p-3 mb-3">
        <span className="text-[9px] font-mono text-athena-text-secondary uppercase tracking-wider">
          Situation Assessment
        </span>
        <p className="text-xs font-mono text-athena-text leading-relaxed mt-1">
          {recommendation.situationAssessment}
        </p>
      </div>

      {/* Tactical Options */}
      <div className="space-y-2 mb-3">
        <span className="text-[9px] font-mono text-athena-text-secondary uppercase tracking-wider">
          Tactical Options ({recommendation.options.length})
        </span>
        {recommendation.options.map((opt, i) => (
          <OptionCard key={opt.techniqueId} option={opt} index={i} />
        ))}
      </div>

      {/* Accept button */}
      {!isDecided && (
        <div className="flex justify-end gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={handleAccept}
            disabled={accepting}
          >
            {accepting ? "ACCEPTING..." : "ACCEPT RECOMMENDATION"}
          </Button>
        </div>
      )}
    </div>
  );
}
