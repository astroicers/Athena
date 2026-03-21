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

import type { C5ISRStatus } from "@/types/c5isr";
import type { OperationalConstraints } from "@/types/constraint";

interface C5ISRInlineSnapshotProps {
  domains: C5ISRStatus[];
  constraints?: OperationalConstraints;
}

function healthColor(pct: number): string {
  if (pct >= 80) return "var(--color-success)";
  if (pct >= 50) return "var(--color-warning)";
  return "var(--color-error)";
}

function domainLabel(domain: string): string {
  return domain.slice(0, 4).toUpperCase();
}

export function C5ISRInlineSnapshot({
  domains,
  constraints,
}: C5ISRInlineSnapshotProps) {
  return (
    <div className="bg-athena-bg rounded-[var(--radius)] p-2 mt-2 font-mono">
      <div className="flex flex-col gap-1.5">
        {domains.map((d) => {
          const color = healthColor(d.healthPct);
          const hardLimit = constraints?.hardLimits.find(
            (hl) => hl.domain === d.domain,
          );
          const warning = constraints?.warnings.find(
            (w) => w.domain === d.domain,
          );

          return (
            <div key={d.id} className="flex flex-col gap-0.5">
              <div className="flex items-center gap-2">
                {/* Domain label */}
                <span className="text-[10px] text-athena-text-tertiary w-10 shrink-0 uppercase tracking-wider">
                  {domainLabel(d.domain)}
                </span>

                {/* Mini progress bar */}
                <div className="flex-1 h-1 rounded-full bg-athena-elevated overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(100, Math.max(0, d.healthPct))}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>

                {/* Health % */}
                <span
                  className="text-[10px] athena-tabular-nums w-8 text-right shrink-0"
                  style={{ color }}
                >
                  {Math.round(d.healthPct)}%
                </span>

                {/* Status text */}
                <span className="text-[10px] text-athena-text-tertiary w-16 shrink-0 truncate">
                  {d.status}
                </span>
              </div>

              {/* Hard limit tag */}
              {hardLimit && (
                <span className="text-[10px] text-athena-error bg-athena-error/[0.08] border border-[var(--color-error)]/[0.25] rounded-[var(--radius)] px-1.5 py-0.5 ml-12 w-fit">
                  {hardLimit.rule}
                </span>
              )}

              {/* Warning tag */}
              {warning && !hardLimit && (
                <span className="text-[10px] text-athena-warning bg-athena-warning/[0.08] border border-[var(--color-warning)]/[0.25] rounded-[var(--radius)] px-1.5 py-0.5 ml-12 w-fit">
                  {warning.message}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
