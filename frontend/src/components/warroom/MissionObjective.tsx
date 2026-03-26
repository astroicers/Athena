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

interface MissionObjectiveProps {
  objective: string;
  targetsCompromised: number;
  targetsTotal: number;
}

export function MissionObjective({
  objective,
  targetsCompromised,
  targetsTotal,
}: MissionObjectiveProps) {
  const t = useTranslations("WarRoom");
  const pct =
    targetsTotal > 0
      ? Math.round((targetsCompromised / targetsTotal) * 100)
      : 0;

  return (
    <div className="border-2 border-[var(--color-accent)] rounded-[var(--radius)] p-3 font-mono">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        {/* Crosshair icon */}
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          className="shrink-0"
        >
          <circle
            cx="8"
            cy="8"
            r="5"
            stroke="var(--color-accent)"
            strokeWidth="1.5"
            fill="none"
          />
          <line
            x1="8"
            y1="1"
            x2="8"
            y2="4"
            stroke="var(--color-accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <line
            x1="8"
            y1="12"
            x2="8"
            y2="15"
            stroke="var(--color-accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <line
            x1="1"
            y1="8"
            x2="4"
            y2="8"
            stroke="var(--color-accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <line
            x1="12"
            y1="8"
            x2="15"
            y2="8"
            stroke="var(--color-accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>

        <span className="text-athena-body font-bold text-athena-text-light">
          {t("objective", { name: objective })}
        </span>
      </div>

      {/* Progress bar */}
      <div className="flex flex-col gap-1.5">
        <div className="w-full h-2 rounded-full bg-athena-elevated overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500 bg-athena-accent"
            style={{ width: `${pct}%` }}
          />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-athena-floor text-athena-text-tertiary athena-tabular-nums">
            {t("targetsProgress", { current: targetsCompromised, total: targetsTotal })}
          </span>
          <span className="text-athena-floor text-athena-accent font-bold athena-tabular-nums">
            {pct}%
          </span>
        </div>
      </div>
    </div>
  );
}
