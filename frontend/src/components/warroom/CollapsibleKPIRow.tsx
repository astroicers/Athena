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

import { useState } from "react";
import { useTranslations } from "next-intl";
import { MetricCard } from "@/components/cards/MetricCard";
import type { OODAPhase } from "@/types/enums";

interface CollapsibleKPIRowProps {
  activeAgents: number | string;
  successRate: number | string;
  techniquesExecuted: number;
  techniquesTotal: number;
  threatLevel: number;
  isOpen: boolean;
  onToggle: () => void;
  operationId: string;
  currentOodaPhase: OODAPhase | null;
  onDirectiveSubmit: (directive: string) => Promise<void>;
}

function InlineDirective({
  currentOodaPhase,
  onSubmit,
}: {
  currentOodaPhase: OODAPhase | null;
  onSubmit: (directive: string) => Promise<void>;
}) {
  const t = useTranslations("WarRoom");
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const isCycleIdle = currentOodaPhase === null;

  async function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || sending) return;
    setSending(true);
    try {
      await onSubmit(trimmed);
      setValue("");
    } finally {
      setSending(false);
    }
  }

  return (
    <div
      className={`flex items-center gap-1.5 border rounded px-1.5 py-0.5 transition-colors ${
        isCycleIdle
          ? "border-athena-accent/60 animate-pulse"
          : "border-athena-border"
      }`}
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={t("directivePlaceholder")}
        className="bg-transparent text-sm font-mono text-athena-text w-48 outline-none placeholder:text-athena-text-secondary/40"
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            handleSubmit();
          }
        }}
      />
      <button
        onClick={handleSubmit}
        disabled={!value.trim() || sending}
        className="text-xs font-mono uppercase tracking-wider text-athena-accent hover:text-athena-accent-hover disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {t("directiveSend")}
      </button>
    </div>
  );
}

export function CollapsibleKPIRow({
  activeAgents,
  successRate,
  techniquesExecuted,
  techniquesTotal,
  threatLevel,
  isOpen,
  onToggle,
  currentOodaPhase,
  onDirectiveSubmit,
}: CollapsibleKPIRowProps) {
  const t = useTranslations("WarRoom");

  if (!isOpen) {
    return (
      <div className="flex items-center gap-4 px-3 py-1 bg-athena-surface border-b border-athena-border shrink-0">
        <button
          onClick={onToggle}
          className="text-sm font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
        >
          ►
        </button>
        <span className="text-sm font-mono text-athena-text-secondary">
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
          className="text-sm font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
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
      <div className="px-3 pb-2">
        <InlineDirective
          currentOodaPhase={currentOodaPhase}
          onSubmit={onDirectiveSubmit}
        />
      </div>
    </div>
  );
}
