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
  default: { text: "text-athena-accent", bg: "bg-athena-accent/10" },
  success: { text: "text-athena-success", bg: "bg-athena-success/10" },
  warning: { text: "text-athena-warning", bg: "bg-athena-warning-bg" },
  error: { text: "text-athena-error", bg: "bg-athena-error/10" },
  muted: { text: "text-athena-text-tertiary", bg: "bg-athena-text-tertiary/10" },
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
      className={`inline-flex items-center justify-center font-mono font-bold rounded-athena
        ${SIZE_MAP[size]} ${text} ${bg}`}
    >
      <span>{icon}</span>
    </div>
  );
}
