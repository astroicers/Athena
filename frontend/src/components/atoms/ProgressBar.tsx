// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

"use client";

const VARIANT_COLORS = {
  default: "bg-athena-accent",
  success: "bg-athena-success",
  warning: "bg-athena-warning",
  error: "bg-athena-error",
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
    <div className="w-full h-1.5 bg-athena-border rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all ${VARIANT_COLORS[variant]}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
