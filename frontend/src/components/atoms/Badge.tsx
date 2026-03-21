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
  success: "bg-[var(--color-success)]/[0.12] text-[var(--color-success)] border-[var(--color-success)]/[0.25]",
  warning: "bg-[var(--color-warning)]/[0.12] text-[var(--color-warning)] border-[var(--color-warning)]/[0.25]",
  error: "bg-[var(--color-error)]/[0.12] text-[var(--color-error)] border-[var(--color-error)]/[0.25]",
  info: "bg-[var(--color-accent)]/[0.12] text-[var(--color-accent)] border-[var(--color-accent)]/[0.25]",
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
