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
        className="rounded-athena-md font-mono text-[9px] text-center bg-[#ffffff0d] border border-[#ffffff10] text-[#ffffff25]"
        style={{
          padding: "10px 12px",
        }}
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
        className="font-mono text-[10px] font-bold uppercase tracking-wider mb-2 block text-[#ffffff20]"
      >
        CONSTRAINT STATUS
      </span>

      {/* Mini indicators row */}
      <div className="flex gap-2 mb-2 flex-wrap">
        {/* Forced Mode */}
        {constraints.forcedMode && (
          <span
            className="font-mono text-[8px] font-bold uppercase px-2 py-0.5 rounded-athena-sm bg-[#EF444420] text-[#EF4444]"
          >
            MODE: {constraints.forcedMode}
          </span>
        )}

        {/* Noise Budget */}
        <div
          className="flex items-center gap-1.5 px-2 py-0.5 rounded-athena-sm bg-[#ffffff14]"
        >
          <span
            className="font-mono text-[8px] text-[#ffffff20]"
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
            className="font-mono text-[8px] font-bold athena-tabular-nums text-[#ffffff50]"
          >
            {constraints.noiseBudgetRemaining}/50
          </span>
        </div>

        {/* Orient Options (only if reduced) */}
        {constraints.orientMaxOptions < 3 && (
          <span
            className="font-mono text-[8px] font-bold px-2 py-0.5 rounded-athena-sm bg-[#FBBF2420]"
            style={{ color: "#FBBF24" }}
          >
            OPTIONS: {constraints.orientMaxOptions}/3
          </span>
        )}

        {/* Blocked Targets */}
        {constraints.blockedTargets.length > 0 && (
          <span
            className="font-mono text-[8px] font-bold px-2 py-0.5 rounded-athena-sm bg-[#EF444420] text-[#EF4444]"
          >
            BLOCKED: {constraints.blockedTargets.length}
          </span>
        )}

        {/* Active Overrides */}
        {constraints.activeOverrides.length > 0 && (
          <span
            className="font-mono text-[8px] font-bold px-2 py-0.5 rounded-athena-sm bg-[#3b82f620] text-[#3b82f6]"
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
              className="rounded-athena-sm flex items-center justify-between"
              style={{
                backgroundColor: "var(--color-error-bg)",
                border: "1px solid color-mix(in srgb, var(--color-error) 20%, transparent)",
                padding: "6px 10px",
              }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0 bg-[#EF444420]"
                />
                <span
                  className="font-mono text-[8px] font-bold uppercase text-[#EF4444]"
                >
                  {limit.domain}
                </span>
                <span
                  className="font-mono text-[8px] text-[#ffffff50]"
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
                    className="text-[7px] font-bold uppercase px-1.5 py-0.5 bg-[#ffffff1a] text-[#ffffff50]"
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
              className="rounded-athena-sm flex items-center gap-2"
              style={{
                backgroundColor: "var(--color-warning-bg)",
                border: "1px solid color-mix(in srgb, #FBBF24 15%, transparent)",
                padding: "5px 10px",
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{ backgroundColor: "#FBBF24" }}
              />
              <span
                className="font-mono text-[8px] font-bold uppercase"
                style={{ color: "#FBBF24" }}
              >
                {warn.domain}
              </span>
              <span
                className="font-mono text-[8px] text-[#ffffff60]"
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
          className="rounded-athena-sm font-mono text-[9px] text-center bg-[#22C55E20] text-[#22C55E]"
          style={{
            border: "1px solid color-mix(in srgb, var(--color-success) 15%, transparent)",
            padding: "8px 12px",
          }}
        >
          All domains nominal — no active constraints
        </div>
      )}
    </div>
  );
}
