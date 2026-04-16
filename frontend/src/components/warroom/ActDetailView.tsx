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

interface ActDetailViewProps {
  detail: PhaseDetail;
}

const STATUS_COLORS: Record<string, string> = {
  SUCCESS: "var(--color-success)",
  FAILED: "#EF4444",
  RUNNING: "var(--color-accent)",
  PARTIAL: "var(--color-warning)",
};

export function ActDetailView({ detail }: ActDetailViewProps) {
  const t = useTranslations("WarRoom");

  if (!detail) return null;

  const status = detail.status?.toUpperCase() ?? "RUNNING";
  const statusColor =
    STATUS_COLORS[status] ?? "var(--color-text-tertiary)";
  const isFailed = status === "FAILED";

  return (
    <div className="font-mono space-y-3">
      {/* Execution result header */}
      <div className="flex items-center gap-2">
        <h4 className="text-athena-floor font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
          {t("executionResult")}:
        </h4>
        <span
          className="text-athena-floor font-bold uppercase tracking-wider px-2 py-1 rounded-[var(--radius)] border"
          style={{
            color: statusColor,
            borderColor: `${statusColor}40`,
            backgroundColor: `${statusColor}12`,
          }}
        >
          {status}
        </span>
        {detail.failureCategory && isFailed && (
          <span className="text-xs font-mono px-1.5 py-0.5 rounded-[var(--radius)] bg-[var(--color-error)]/[0.08] border border-[var(--color-error)]/[0.15] text-[var(--color-error)]">
            [{detail.failureCategory}]
          </span>
        )}
      </div>

      {/* Technique + Engine info */}
      {(detail.techniqueId || detail.engine) && (
        <div className="text-athena-floor text-[var(--color-text-secondary)]">
          {detail.techniqueId && (
            <span>
              <span className="text-[var(--color-text-tertiary)]">
                Technique:{" "}
              </span>
              <span className="text-[var(--color-text-primary)] font-bold">
                {detail.techniqueId}
              </span>
            </span>
          )}
          {detail.techniqueId && detail.engine && (
            <span className="text-[var(--color-text-tertiary)]">
              {" "}
              via{" "}
            </span>
          )}
          {detail.engine && (
            <span className="text-[var(--color-text-primary)]">
              {detail.engine}
            </span>
          )}
        </div>
      )}

      {/* Facts collected */}
      {detail.factsCollectedCount !== undefined &&
        detail.factsCollectedCount > 0 && (
          <div className="text-athena-floor text-[var(--color-text-secondary)]">
            <span className="text-[var(--color-text-tertiary)]">
              {t("factsCollected")}:{" "}
            </span>
            <span className="text-[var(--color-text-primary)] font-bold">
              {detail.factsCollectedCount}
            </span>
          </div>
        )}

      {/* Result summary (success case) */}
      {!isFailed && detail.resultSummary && (
        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border-subtle)] rounded-[var(--radius)] p-2">
          <p className="text-athena-floor text-[var(--color-text-secondary)] leading-relaxed">
            {detail.resultSummary}
          </p>
        </div>
      )}

      {/* Error message (failure case) */}
      {isFailed && detail.errorMessage && (
        <div className="bg-[#EF4444]/[0.08] border border-[#EF4444]/[0.25] rounded-[var(--radius)] p-2">
          <p className="text-athena-floor text-[#EF4444] leading-relaxed">
            {detail.errorMessage}
          </p>
        </div>
      )}
    </div>
  );
}
