// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

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
