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

import { useState } from "react";
import { ProgressBar } from "@/components/atoms/ProgressBar";
import { Button } from "@/components/atoms/Button";
import type { OperationalConstraints } from "@/types/constraint";

interface ConstraintStatusPanelProps {
  constraints: OperationalConstraints | null;
  onOverride?: (domain: string) => void;
}

export function ConstraintStatusPanel({
  constraints,
  onOverride,
}: ConstraintStatusPanelProps) {
  const [overriding, setOverriding] = useState<string | null>(null);

  if (!constraints) {
    return (
      <div
        className="rounded-[var(--radius)] font-mono text-athena-floor text-center bg-[#ffffff0d] border border-[#ffffff10] text-[#ffffff25] px-3 py-2.5"
      >
        Waiting for constraint data...
      </div>
    );
  }

  const hasIssues =
    constraints.warnings.length > 0 || constraints.hardLimits.length > 0;

  async function handleOverride(domain: string) {
    if (!onOverride || overriding) return;
    setOverriding(domain);
    try {
      onOverride(domain);
    } finally {
      setTimeout(() => setOverriding(null), 1500);
    }
  }

  return (
    <div>
      <span
        className="font-mono text-athena-floor font-bold uppercase tracking-wider mb-2 block text-[#ffffff20]"
      >
        CONSTRAINT STATUS
      </span>

      {/* Mini indicators row */}
      <div className="flex gap-2 mb-2 flex-wrap">
        {/* Forced Mode */}
        {constraints.forcedMode && (
          <span
            className="font-mono text-athena-floor font-bold uppercase px-2 py-1 rounded-[var(--radius)] bg-athena-error-bg text-athena-error"
          >
            MODE: {constraints.forcedMode}
          </span>
        )}

        {/* Noise Budget */}
        <div
          className="flex items-center gap-1.5 px-2 py-0.5 rounded-[var(--radius)] bg-[#ffffff14]"
        >
          <span
            className="font-mono text-athena-floor text-[#ffffff20]"
          >
            NOISE
          </span>
          <div className="w-12">
            <ProgressBar
              value={constraints.noiseBudgetRemaining}
              variant={
                constraints.noiseBudgetRemaining > 30
                  ? "default"
                  : constraints.noiseBudgetRemaining > 10
                    ? "warning"
                    : "error"
              }
            />
          </div>
          <span
            className="font-mono text-athena-floor font-bold athena-tabular-nums text-[#ffffff50]"
          >
            {constraints.noiseBudgetRemaining}/50
          </span>
        </div>

        {/* Orient Options (only if reduced) */}
        {constraints.orientMaxOptions < 3 && (
          <span
            className="font-mono text-athena-floor font-bold px-2 py-1 rounded-[var(--radius)] bg-athena-warning-bg text-athena-warning"
          >
            OPTIONS: {constraints.orientMaxOptions}/3
          </span>
        )}

        {/* Blocked Targets */}
        {constraints.blockedTargets.length > 0 && (
          <span
            className="font-mono text-athena-floor font-bold px-2 py-1 rounded-[var(--radius)] bg-athena-error-bg text-athena-error"
          >
            BLOCKED: {constraints.blockedTargets.length}
          </span>
        )}

        {/* Active Overrides */}
        {constraints.activeOverrides.length > 0 && (
          <span
            className="font-mono text-athena-floor font-bold px-2 py-1 rounded-[var(--radius)] bg-athena-accent-bg text-athena-accent"
          >
            OVERRIDES: {constraints.activeOverrides.join(", ")}
          </span>
        )}
      </div>

      {/* Hard Limits */}
      {constraints.hardLimits.length > 0 && (
        <div className="flex flex-col gap-1.5 mb-2">
          {constraints.hardLimits.map((limit, i) => (
            <div
              key={i}
              className="rounded-[var(--radius)] flex items-center justify-between px-2.5 py-1.5 bg-athena-error-bg border border-[var(--color-error)]/20"
            >
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0 bg-athena-error-bg"
                />
                <span
                  className="font-mono text-athena-floor font-bold uppercase text-athena-error"
                >
                  {limit.domain}
                </span>
                <span
                  className="font-mono text-athena-floor text-[#ffffff50]"
                >
                  {limit.rule}
                </span>
              </div>
              {onOverride &&
                !constraints.activeOverrides.includes(limit.domain) && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleOverride(limit.domain)}
                    disabled={overriding === limit.domain}
                    className="text-athena-floor font-bold uppercase px-1.5 py-0.5 bg-[#ffffff1a] text-[#ffffff50]"
                  >
                    {overriding === limit.domain ? "..." : "OVERRIDE"}
                  </Button>
                )}
            </div>
          ))}
        </div>
      )}

      {/* Warnings */}
      {constraints.warnings.length > 0 && (
        <div className="flex flex-col gap-1">
          {constraints.warnings.map((warn, i) => (
            <div
              key={i}
              className="rounded-[var(--radius)] flex items-center gap-2 bg-athena-warning-bg border border-[var(--color-warning)]/15 py-[5px] px-2.5"
            >
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0 bg-athena-warning"
              />
              <span
                className="font-mono text-athena-floor font-bold uppercase text-athena-warning"
              >
                {warn.domain}
              </span>
              <span
                className="font-mono text-athena-floor text-[#ffffff60]"
              >
                {warn.message}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* All nominal */}
      {!hasIssues && (
        <div
          className="rounded-[var(--radius)] font-mono text-athena-floor text-center bg-athena-success-bg text-athena-success border border-[var(--color-success)]/15 py-2 px-3"
        >
          All domains nominal — no active constraints
        </div>
      )}
    </div>
  );
}
