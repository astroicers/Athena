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
  success: "bg-athena-success-bg text-athena-success border-athena-success/25",
  warning: "bg-athena-warning-bg text-athena-warning border-athena-warning/25",
  error: "bg-athena-error-bg text-athena-error border-athena-error/25",
  info: "bg-athena-accent-bg text-athena-accent border-athena-accent/25",
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
