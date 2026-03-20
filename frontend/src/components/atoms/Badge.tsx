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
  success: "bg-athena-success/[0.12] text-athena-success border-athena-success/[0.25]",
  warning: "bg-athena-warning/[0.12] text-athena-warning border-athena-warning/[0.25]",
  error: "bg-athena-error/[0.12] text-athena-error border-athena-error/[0.25]",
  info: "bg-athena-accent/[0.12] text-athena-accent border-athena-accent/[0.25]",
} as const;

interface BadgeProps {
  variant?: keyof typeof VARIANT_STYLES;
  children: ReactNode;
}

export function Badge({ variant = "info", children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center shrink-0 whitespace-nowrap px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold border
        ${VARIANT_STYLES[variant]}`}
    >
      {children}
    </span>
  );
}
