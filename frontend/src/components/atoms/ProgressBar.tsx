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

const VARIANT_COLORS = {
  default: "bg-[#3b82f6]",
  success: "bg-athena-success-bg",
  warning: "bg-athena-warning-bg",
  error: "bg-athena-error-bg",
} as const;

interface ProgressBarProps {
  value: number;
  max?: number;
  variant?: keyof typeof VARIANT_COLORS;
}

export function ProgressBar({
  value,
  max = 100,
  variant = "default",
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="w-full h-1.5 bg-athena-elevated rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all ${VARIANT_COLORS[variant]}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
