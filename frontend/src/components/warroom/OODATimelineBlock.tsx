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

import { OODAPhase } from "@/types/enums";
import type { C5ISRStatus } from "@/types/c5isr";
import type { OperationalConstraints } from "@/types/constraint";
import { C5ISRInlineSnapshot } from "./C5ISRInlineSnapshot";

interface IterationLike {
  id: string;
  iterationNumber: number;
  phase: string;
  observeSummary?: string | null;
  orientSummary?: string | null;
  decideSummary?: string | null;
  actSummary?: string | null;
  completedAt?: string | null;
}

interface OODATimelineBlockProps {
  iteration: IterationLike;
  c5isrDomains?: C5ISRStatus[];
  constraints?: OperationalConstraints;
  isCurrent?: boolean;
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

const PHASE_LABELS: Record<OODAPhase, string> = {
  [OODAPhase.OBSERVE]: "OBSERVE",
  [OODAPhase.ORIENT]: "ORIENT",
  [OODAPhase.DECIDE]: "DECIDE",
  [OODAPhase.ACT]: "ACT",
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
}: OODATimelineBlockProps) {
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
            OODA #{iteration.iterationNumber}
          </span>
        </div>
        <span
          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-[var(--radius)] ${
            isCompleted
              ? "bg-athena-success/[0.12] border border-[var(--color-success)]/[0.25] text-athena-success"
              : "bg-athena-accent/[0.12] border border-[var(--color-accent)]/[0.25] text-athena-accent"
          }`}
        >
          {isCompleted ? "COMPLETED" : "IN PROGRESS"}
        </span>
      </div>

      {/* Phase rows */}
      <div className="flex flex-col divide-y divide-athena-border">
        {PHASE_ORDER.map((phase) => {
          const status = getPhaseStatus(iteration, phase);
          const summary = getSummary(iteration, phase);
          const color = PHASE_COLORS[phase];
          const isActive = status === "active";
          const isPending = status === "pending";
          const dotSize = isActive ? 8 : 6;

          return (
            <div key={phase} className="px-3 py-2">
              <div className="flex items-start gap-2">
                {/* Phase dot */}
                <span className="mt-1 shrink-0">
                  <svg
                    width={dotSize}
                    height={dotSize}
                    viewBox={`0 0 ${dotSize} ${dotSize}`}
                  >
                    <circle
                      cx={dotSize / 2}
                      cy={dotSize / 2}
                      r={dotSize / 2}
                      fill={isPending ? "var(--color-text-tertiary)" : color}
                      opacity={isPending ? 0.4 : 1}
                    />
                  </svg>
                </span>

                {/* Phase content */}
                <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className="text-xs font-bold uppercase tracking-wider"
                      style={{
                        color: isPending
                          ? "var(--color-text-tertiary)"
                          : color,
                      }}
                    >
                      {PHASE_LABELS[phase]}
                    </span>
                    {isActive && (
                      <span className="text-[10px] font-bold uppercase tracking-wider text-athena-accent bg-athena-accent/[0.12] border border-[var(--color-accent)]/[0.25] px-1.5 py-0.5 rounded-[var(--radius)]">
                        ACTIVE
                      </span>
                    )}
                  </div>

                  {isPending ? (
                    <span className="text-xs text-athena-text-tertiary italic">
                      (pending)
                    </span>
                  ) : summary ? (
                    <span className="text-xs text-athena-text-secondary">
                      {summary}
                    </span>
                  ) : null}
                </div>
              </div>

              {/* C5ISR inline snapshot in ORIENT phase */}
              {phase === OODAPhase.ORIENT &&
                c5isrDomains &&
                c5isrDomains.length > 0 &&
                status !== "pending" && (
                  <C5ISRInlineSnapshot
                    domains={c5isrDomains}
                    constraints={constraints}
                  />
                )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
