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

interface TargetPivotMarkerProps {
  fromTarget: string;
  toTarget: string;
  reason?: string;
}

export function TargetPivotMarker({
  fromTarget,
  toTarget,
  reason,
}: TargetPivotMarkerProps) {
  return (
    <div className="bg-athena-warning/[0.06] border border-[var(--color-warning)]/[0.25] rounded-[var(--radius)] px-3 py-1.5 font-mono">
      <div className="flex items-center gap-1.5">
        {/* Triangle alert icon */}
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          className="shrink-0"
        >
          <path
            d="M5.134 1.866a1 1 0 0 1 1.732 0l3.83 6.635A1 1 0 0 1 9.83 10H2.17a1 1 0 0 1-.866-1.5l3.83-6.634Z"
            stroke="var(--color-warning)"
            strokeWidth="1"
            fill="none"
          />
          <line
            x1="6"
            y1="4.5"
            x2="6"
            y2="6.5"
            stroke="var(--color-warning)"
            strokeWidth="1"
            strokeLinecap="round"
          />
          <circle cx="6" cy="8" r="0.5" fill="var(--color-warning)" />
        </svg>

        <span className="text-athena-floor font-bold text-athena-warning">
          TARGET PIVOT: {fromTarget} -&gt; {toTarget}
        </span>
      </div>

      {reason && (
        <p className="text-athena-floor text-athena-text-tertiary mt-1 ml-[18px]">
          {reason}
        </p>
      )}
    </div>
  );
}
