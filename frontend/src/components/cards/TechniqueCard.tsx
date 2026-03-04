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
  const t = useTranslations("TechniqueCard");
  const tStatus = useTranslations("Status");
  const tRisk = useTranslations("Risk");

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-athena-accent">
          {technique.mitreId}
        </span>
        {technique.latestStatus && (
          <Badge variant={STATUS_VARIANT[technique.latestStatus] || "info"}>
            {tStatus(technique.latestStatus as any)}
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
        <span>{t("tactic")} {technique.tactic}</span>
        <Badge variant={RISK_VARIANT[technique.riskLevel] || "info"}>
          {tRisk(technique.riskLevel as any)}
        </Badge>
      </div>
    </div>
  );
}
