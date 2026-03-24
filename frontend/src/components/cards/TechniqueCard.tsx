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

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/atoms/Badge";
import type { TechniqueWithStatus } from "@/types/technique";
import type { ToolRegistryEntry } from "@/types/tool";
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

const TOOL_RISK_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  low: "success",
  medium: "warning",
  high: "error",
  critical: "error",
};

interface TechniqueCardProps {
  technique: TechniqueWithStatus;
  relatedTools?: ToolRegistryEntry[];
}

export function TechniqueCard({ technique, relatedTools }: TechniqueCardProps) {
  const t = useTranslations("TechniqueCard");
  const tStatus = useTranslations("Status");
  const tRisk = useTranslations("Risk");

  return (
    <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] p-4">
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
      <h3 className="text-sm font-mono font-bold text-athena-text-light mb-2">
        {technique.name}
      </h3>
      {technique.description && (
        <p className="text-xs font-mono text-athena-text-tertiary mb-3 line-clamp-3">
          {technique.description}
        </p>
      )}
      <div className="flex items-center gap-3 text-sm font-mono text-athena-text-tertiary">
        <span>{t("tactic")} {technique.tactic}</span>
        <Badge variant={RISK_VARIANT[technique.riskLevel] || "info"}>
          {tRisk(technique.riskLevel as any)}
        </Badge>
      </div>

      {relatedTools && relatedTools.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
          <span className="text-sm font-mono text-athena-text-tertiary uppercase tracking-wider">
            {t("relatedTools")}
          </span>
          <div className="mt-1.5 space-y-1">
            {relatedTools.map((tool) => (
              <Link
                key={tool.toolId}
                href={`/tools#${tool.toolId}`}
                className="flex items-center justify-between gap-2 px-2 py-1 rounded-[var(--radius)] hover:bg-athena-elevated transition-colors group"
              >
                <div className="flex items-center gap-1.5 min-w-0">
                  <span
                    className={`w-2.5 h-2.5 rounded-full shrink-0 ${tool.enabled ? "bg-athena-success-bg" : "bg-athena-text-tertiary/40"}`}
                  />
                  <span className="text-xs font-mono text-athena-text-light truncate group-hover:text-athena-accent transition-colors">
                    {tool.name}
                  </span>
                </div>
                <Badge variant={TOOL_RISK_VARIANT[tool.riskLevel] || "info"}>
                  {tool.riskLevel}
                </Badge>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
