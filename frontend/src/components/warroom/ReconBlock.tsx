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
import type { OODATimelineEntry } from "@/types/ooda";

interface ReconBlockProps {
  entries: OODATimelineEntry[];
}

export function ReconBlock({ entries }: ReconBlockProps) {
  const t = useTranslations("WarRoom");
  const reconEntries = entries.filter((e) => e.iterationNumber === 0);

  return (
    <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] p-3 font-mono">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="bg-athena-accent/[0.12] border border-[var(--color-accent)]/[0.25] text-athena-accent text-athena-floor font-bold uppercase tracking-wider px-2 py-1 rounded-[var(--radius)]">
          {t("recon")}
        </span>
      </div>

      {/* Entries */}
      {reconEntries.length === 0 ? (
        <p className="text-athena-floor text-athena-text-tertiary">
          {t("noReconData")}
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {reconEntries.map((entry, idx) => (
            <div key={idx} className="flex items-start gap-2">
              {/* Dot */}
              <span className="mt-1.5 shrink-0">
                <svg
                  width="6"
                  height="6"
                  viewBox="0 0 6 6"
                  className="fill-athena-accent"
                >
                  <circle cx="3" cy="3" r="3" />
                </svg>
              </span>

              {/* Content */}
              <div className="flex flex-col gap-0.5 min-w-0">
                <span className="text-athena-floor text-athena-text-tertiary athena-tabular-nums">
                  {new Date(entry.timestamp).toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: false,
                  })}
                </span>
                <span className="text-athena-floor text-athena-text-secondary">
                  {entry.summary}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
