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
  default: { text: "text-[#3b82f6]", bg: "bg-[#3b82f610]" },
  success: { text: "text-[#22C55E]", bg: "bg-[#22C55E10]" },
  warning: { text: "text-[#FBBF24]", bg: "bg-[#FBBF2410]" },
  error: { text: "text-[#EF4444]", bg: "bg-[#EF444410]" },
  muted: { text: "text-[#9ca3af]", bg: "bg-[#9ca3af]/10" },
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
      className={`inline-flex items-center justify-center font-mono font-bold rounded-athena-md
        ${SIZE_MAP[size]} ${text} ${bg}`}
    >
      <span>{icon}</span>
    </div>
  );
}
