"use client";

import { Badge } from "@/components/atoms/Badge";
import type { TechniqueWithStatus } from "@/types/technique";
import { RiskLevel, TechniqueStatus } from "@/types/enums";

const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [TechniqueStatus.SUCCESS]: "success",
  [TechniqueStatus.RUNNING]: "info",
  [TechniqueStatus.FAILED]: "error",
  [TechniqueStatus.PARTIAL]: "warning",
  [TechniqueStatus.QUEUED]: "info",
  [TechniqueStatus.UNTESTED]: "info",
};

const RISK_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [RiskLevel.LOW]: "success",
  [RiskLevel.MEDIUM]: "warning",
  [RiskLevel.HIGH]: "error",
  [RiskLevel.CRITICAL]: "error",
};

interface TechniqueCardProps {
  technique: TechniqueWithStatus;
}

export function TechniqueCard({ technique }: TechniqueCardProps) {
  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-athena-accent">
          {technique.mitreId}
        </span>
        {technique.latestStatus && (
          <Badge variant={STATUS_VARIANT[technique.latestStatus] || "info"}>
            {technique.latestStatus.toUpperCase()}
          </Badge>
        )}
      </div>
      <h3 className="text-sm font-mono font-bold text-athena-text mb-2">
        {technique.name}
      </h3>
      {technique.description && (
        <p className="text-xs font-mono text-athena-text-secondary mb-3 line-clamp-3">
          {technique.description}
        </p>
      )}
      <div className="flex items-center gap-3 text-[10px] font-mono text-athena-text-secondary">
        <span>Tactic: {technique.tactic}</span>
        <Badge variant={RISK_VARIANT[technique.riskLevel] || "info"}>
          {technique.riskLevel.toUpperCase()}
        </Badge>
      </div>
    </div>
  );
}
