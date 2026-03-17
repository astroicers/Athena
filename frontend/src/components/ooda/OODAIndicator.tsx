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
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { OODAPhase } from "@/types/enums";

const PHASE_KEYS: { key: OODAPhase; tKey: "observe" | "orient" | "decide" | "act" }[] = [
  { key: OODAPhase.OBSERVE, tKey: "observe" },
  { key: OODAPhase.ORIENT, tKey: "orient" },
  { key: OODAPhase.DECIDE, tKey: "decide" },
  { key: OODAPhase.ACT, tKey: "act" },
];

interface OODAIndicatorProps {
  currentPhase: OODAPhase | string | null;
}

export function OODAIndicator({ currentPhase }: OODAIndicatorProps) {
  const t = useTranslations("OODA");
  const tHints = useTranslations("Hints");

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-athena-md p-4">
      <SectionHeader level="card" className="mb-1">
        {t("cycle")}
      </SectionHeader>
      <p className="text-sm font-mono text-[#9ca3af] mb-3">{tHints("oodaCycle")}</p>
      <div className="flex items-center gap-1">
        {PHASE_KEYS.map((phase, i) => {
          const isActive = currentPhase === phase.key;
          const isPast =
            currentPhase != null &&
            PHASE_KEYS.findIndex((p) => p.key === currentPhase) > i;
          return (
            <div key={phase.key} className="flex items-center gap-1 flex-1">
              <div
                className={`flex flex-col items-center justify-center w-full py-2 rounded-athena-sm text-sm font-mono font-bold transition-all ${
                  isActive
                    ? "bg-[#3b82f620] text-[#3b82f6] border border-[#3b82f6]"
                    : isPast
                      ? "bg-[#3b82f620] text-[#3b82f6]"
                      : "bg-[#1f2937]/30 text-[#9ca3af]"
                }`}
              >
                {t(phase.tKey)}
              </div>
              {i < PHASE_KEYS.length - 1 && (
                <span className="text-[#9ca3af] text-xs shrink-0">→</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
