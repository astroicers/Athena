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
  default: { text: "text-athena-accent", bg: "bg-athena-accent/10" },
  success: { text: "text-athena-success", bg: "bg-athena-success/10" },
  warning: { text: "text-athena-warning", bg: "bg-athena-warning/10" },
  error: { text: "text-athena-error", bg: "bg-athena-error/10" },
  muted: { text: "text-athena-text-secondary", bg: "bg-athena-text-secondary/10" },
} as const;

const SIZE_MAP = {
  sm: "w-6 h-6 text-xs",
  md: "w-8 h-8 text-sm",
  lg: "w-10 h-10 text-base",
} as const;

interface HexIconProps {
  icon: string;
  size?: keyof typeof SIZE_MAP;
  variant?: keyof typeof VARIANT_COLORS;
}

export function HexIcon({
  icon,
  size = "md",
  variant = "default",
}: HexIconProps) {
  const { text, bg } = VARIANT_COLORS[variant];
  return (
    <div
      className={`inline-flex items-center justify-center font-mono font-bold rounded-lg
        ${SIZE_MAP[size]} ${text} ${bg}`}
    >
      <span>{icon}</span>
    </div>
  );
}
