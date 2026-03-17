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

import { ReactNode } from "react";

const VARIANT_STYLES = {
  success: "bg-[#22C55E20] text-[#22C55E] border-[#22C55E40]",
  warning: "bg-[#FBBF2420] text-[#FBBF24] border-[#FBBF2440]",
  error: "bg-[#EF444420] text-[#EF4444] border-[#EF444440]",
  info: "bg-[#3b82f620] text-[#3b82f6] border-[#3b82f640]",
} as const;

interface BadgeProps {
  variant?: keyof typeof VARIANT_STYLES;
  children: ReactNode;
}

export function Badge({ variant = "info", children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center shrink-0 whitespace-nowrap px-3 py-1 rounded-full text-xs font-mono border
        ${VARIANT_STYLES[variant]}`}
    >
      {children}
    </span>
  );
}
