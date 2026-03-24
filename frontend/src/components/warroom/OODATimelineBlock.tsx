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
import { OODAPhase } from "@/types/enums";
import type { C5ISRStatus } from "@/types/c5isr";
import type { OperationalConstraints } from "@/types/constraint";
import type { OODATimelineEntry } from "@/types/ooda";
import { C5ISRInlineSnapshot } from "./C5ISRInlineSnapshot";
import { PhaseExpandable } from "./PhaseExpandable";

interface IterationLike {
  id: string;
  iterationNumber: number;
  phase: string;
  observeSummary?: string | null;
  orientSummary?: string | null;
  decideSummary?: string | null;
  actSummary?: string | null;
  completedAt?: string | null;
  targetHostname?: string;
  targetIp?: string;
}

interface OODATimelineBlockProps {
  iteration: IterationLike;
  c5isrDomains?: C5ISRStatus[];
  constraints?: OperationalConstraints;
  isCurrent?: boolean;
  timelineEntries?: OODATimelineEntry[];
}

const PHASE_ORDER: OODAPhase[] = [
  OODAPhase.OBSERVE,
  OODAPhase.ORIENT,
  OODAPhase.DECIDE,
  OODAPhase.ACT,
];

const PHASE_COLORS: Record<OODAPhase, string> = {
  [OODAPhase.OBSERVE]: "var(--color-accent)",
  [OODAPhase.ORIENT]: "#7C3AED",
  [OODAPhase.DECIDE]: "var(--color-warning)",
  [OODAPhase.ACT]: "var(--color-success)",
};

const PHASE_KEYS: Record<OODAPhase, string> = {
  [OODAPhase.OBSERVE]: "observe",
  [OODAPhase.ORIENT]: "orient",
  [OODAPhase.DECIDE]: "decide",
  [OODAPhase.ACT]: "act",
};

function getSummary(
  iteration: IterationLike,
  phase: OODAPhase,
): string | null {
  switch (phase) {
    case OODAPhase.OBSERVE:
      return iteration.observeSummary ?? null;
    case OODAPhase.ORIENT:
      return iteration.orientSummary ?? null;
    case OODAPhase.DECIDE:
      return iteration.decideSummary ?? null;
    case OODAPhase.ACT:
      return iteration.actSummary ?? null;
  }
}

function getPhaseStatus(
  iteration: IterationLike,
  phase: OODAPhase,
): "completed" | "active" | "pending" {
  const currentIdx = PHASE_ORDER.indexOf(iteration.phase as OODAPhase);
  const phaseIdx = PHASE_ORDER.indexOf(phase);

  if (iteration.completedAt) return "completed";
  if (phaseIdx < currentIdx) return "completed";
  if (phaseIdx === currentIdx) return "active";
  return "pending";
}

export function OODATimelineBlock({
  iteration,
  c5isrDomains,
  constraints,
  isCurrent = false,
  timelineEntries,
}: OODATimelineBlockProps) {
  const t = useTranslations("WarRoom");
  const isCompleted = iteration.completedAt !== null;

  return (
    <div
      className={`bg-athena-surface rounded-[var(--radius)] font-mono ${
        isCurrent
          ? "border-2 border-[var(--color-accent)]"
          : "border border-[var(--color-border)]"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-athena-text-light">
            {t("oodaIteration", { num: iteration.iterationNumber })}
          </span>
          {iteration.targetHostname && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-[var(--radius)] bg-[var(--color-accent)]/[0.12] border border-[var(--color-accent)]/[0.25] text-[var(--color-accent)]">
              [{iteration.targetIp}] {iteration.targetHostname}
            </span>
          )}
        </div>
        <span
          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-[var(--radius)] ${
            isCompleted
              ? "bg-athena-success/[0.12] border border-[var(--color-success)]/[0.25] text-athena-success"
              : "bg-athena-accent/[0.12] border border-[var(--color-accent)]/[0.25] text-athena-accent"
          }`}
        >
          {isCompleted ? t("completed") : t("inProgress")}
        </span>
      </div>

      {/* Phase rows */}
      <div className="flex flex-col divide-y divide-athena-border">
        {PHASE_ORDER.map((phase) => {
          const status = getPhaseStatus(iteration, phase);
          const summary = getSummary(iteration, phase);
          const isActive = status === "active";
          const isPending = status === "pending";

          // Find the detail for this phase from timeline entries
          const entry = timelineEntries?.find(
            (e) =>
              e.iterationNumber === iteration.iterationNumber &&
              e.phase === PHASE_KEYS[phase],
          );

          return (
            <div key={phase}>
              <PhaseExpandable
                phase={PHASE_KEYS[phase]}
                summary={summary}
                detail={entry?.detail}
                isActive={isActive}
                isPending={isPending}
                phaseColor={PHASE_COLORS[phase]}
              />

              {/* C5ISR inline snapshot in ORIENT phase */}
              {phase === OODAPhase.ORIENT &&
                c5isrDomains &&
                c5isrDomains.length > 0 &&
                status !== "pending" && (
                  <div className="px-3 pb-2">
                    <C5ISRInlineSnapshot
                      domains={c5isrDomains}
                      constraints={constraints}
                    />
                  </div>
                )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
