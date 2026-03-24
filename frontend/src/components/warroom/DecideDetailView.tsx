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

interface DecideDetailViewProps {
  detail: PhaseDetail;
}

const ACTION_COLORS: Record<string, string> = {
  GO: "var(--color-success)",
  CAUTION: "var(--color-warning)",
  HOLD: "#F59E0B",
  ABORT: "#EF4444",
};

function ConfidenceBar({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  const pct = Math.round(value * 100);
  const filledBlocks = Math.round(pct / 10);
  const emptyBlocks = 10 - filledBlocks;

  const bar =
    "\u2588".repeat(filledBlocks) + "\u2591".repeat(emptyBlocks);

  return (
    <div className="flex items-center gap-2 text-xs font-mono">
      <span className="text-[var(--color-text-secondary)] min-w-[140px] text-right">
        {label}
      </span>
      <span className="text-[var(--color-accent)] tracking-tight">
        {bar}
      </span>
      <span className="text-[var(--color-text-primary)] font-bold min-w-[32px]">
        {pct}%
      </span>
    </div>
  );
}

export function DecideDetailView({ detail }: DecideDetailViewProps) {
  const t = useTranslations("WarRoom");

  const matrixAction = detail.matrixAction?.toUpperCase() ?? "GO";
  const actionColor =
    ACTION_COLORS[matrixAction] ?? "var(--color-text-tertiary)";
  const noiseLevel = detail.noiseLevel?.toUpperCase() ?? "-";
  const riskLevel = detail.riskLevel?.toUpperCase() ?? "-";

  const breakdown = detail.confidenceBreakdown ?? {};
  const breakdownEntries = Object.entries(breakdown);

  return (
    <div className="font-mono space-y-3">
      {/* Decision result header */}
      <div className="flex items-center gap-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
          {t("decisionResult")}:
        </h4>
        <span
          className="text-xs font-bold uppercase tracking-wider px-2 py-1 rounded-[var(--radius)] border"
          style={{
            color: actionColor,
            borderColor: `${actionColor}40`,
            backgroundColor: `${actionColor}12`,
          }}
        >
          {matrixAction}
        </span>
      </div>

      {/* Confidence breakdown */}
      {breakdownEntries.length > 0 && (
        <div>
          <h5 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-tertiary)] mb-2">
            {t("confidenceBreakdown")}
          </h5>
          <div className="space-y-1">
            {breakdownEntries.map(([key, value]) => (
              <ConfidenceBar key={key} label={key} value={value} />
            ))}
          </div>
        </div>
      )}

      {/* Noise x Risk matrix summary */}
      <div className="text-xs text-[var(--color-text-secondary)]">
        <span className="text-[var(--color-text-tertiary)]">Matrix: </span>
        <span className="text-[var(--color-text-primary)]">
          NOISE={noiseLevel}
        </span>
        <span className="text-[var(--color-text-tertiary)]"> x </span>
        <span className="text-[var(--color-text-primary)]">
          RISK={riskLevel}
        </span>
        <span className="text-[var(--color-text-tertiary)]"> -&gt; </span>
        <span style={{ color: actionColor }} className="font-bold">
          {matrixAction}
        </span>
      </div>

      {/* Reason */}
      {detail.reason && (
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
          {detail.reason}
        </p>
      )}
    </div>
  );
}
