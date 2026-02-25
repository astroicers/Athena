"use client";

import { OODAPhase } from "@/types/enums";

const PHASES: { key: OODAPhase; label: string }[] = [
  { key: OODAPhase.OBSERVE, label: "OBSERVE" },
  { key: OODAPhase.ORIENT, label: "ORIENT" },
  { key: OODAPhase.DECIDE, label: "DECIDE" },
  { key: OODAPhase.ACT, label: "ACT" },
];

interface OODAIndicatorProps {
  currentPhase: OODAPhase | string | null;
}

export function OODAIndicator({ currentPhase }: OODAIndicatorProps) {
  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
      <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-3">
        OODA Cycle
      </h3>
      <div className="flex items-center gap-2">
        {PHASES.map((phase, i) => {
          const isActive = currentPhase === phase.key;
          const isPast =
            currentPhase != null &&
            PHASES.findIndex((p) => p.key === currentPhase) > i;
          return (
            <div key={phase.key} className="flex items-center gap-2 flex-1">
              <div
                className={`flex items-center justify-center w-full py-2 rounded-athena-sm text-[10px] font-mono font-bold transition-all ${
                  isActive
                    ? "bg-athena-accent text-black"
                    : isPast
                      ? "bg-athena-accent/20 text-athena-accent"
                      : "bg-athena-border/30 text-athena-text-secondary"
                }`}
              >
                {phase.label}
              </div>
              {i < PHASES.length - 1 && (
                <span className="text-athena-text-secondary text-xs shrink-0">→</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
