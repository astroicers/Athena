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
import { MetricCard } from "@/components/cards/MetricCard";

interface CollapsibleKPIRowProps {
  activeAgents: number | string;
  successRate: number | string;
  techniquesExecuted: number;
  techniquesTotal: number;
  threatLevel: number;
  isOpen: boolean;
  onToggle: () => void;
}

export function CollapsibleKPIRow({
  activeAgents,
  successRate,
  techniquesExecuted,
  techniquesTotal,
  threatLevel,
  isOpen,
  onToggle,
}: CollapsibleKPIRowProps) {
  const t = useTranslations("WarRoom");

  if (!isOpen) {
    return (
      <div className="flex items-center gap-4 px-3 py-1 bg-athena-surface border-b border-athena-border shrink-0">
        <button
          onClick={onToggle}
          className="text-[10px] font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
        >
          ►
        </button>
        <span className="text-[10px] font-mono text-athena-text-secondary">
          Agents: {activeAgents} | Success: {successRate}% | Executed: {techniquesExecuted}/{techniquesTotal} | Threat: {typeof threatLevel === "number" ? threatLevel.toFixed(1) : threatLevel}
        </span>
      </div>
    );
  }

  return (
    <div className="shrink-0 border-b border-athena-border">
      <div className="flex items-center px-3 py-1 bg-athena-surface">
        <button
          onClick={onToggle}
          className="text-[10px] font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
        >
          ▼ {t("kpiCollapse")}
        </button>
      </div>
      <div className="grid grid-cols-4 gap-3 p-3 bg-athena-surface">
        <MetricCard
          title="Active Agents"
          value={activeAgents}
          accentColor="var(--color-accent)"
        />
        <MetricCard
          title="Success Rate"
          value={`${successRate}%`}
          accentColor={Number(successRate) < 50 ? "var(--color-warning)" : "var(--color-success)"}
        />
        <MetricCard
          title="Techniques"
          value={techniquesExecuted}
          subtitle={`/ ${techniquesTotal}`}
        />
        <MetricCard
          title="Threat Level"
          value={typeof threatLevel === "number" ? threatLevel.toFixed(1) : "—"}
          accentColor="var(--color-error)"
        />
      </div>
    </div>
  );
}
