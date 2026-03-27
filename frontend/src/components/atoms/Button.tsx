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

import React, { ButtonHTMLAttributes } from "react";

const VARIANT_STYLES = {
  primary:
    "bg-athena-accent text-athena-text font-bold border border-athena-accent hover:bg-athena-accent-hover",
  secondary:
    "bg-athena-surface text-athena-text border border-[var(--color-border-subtle)] hover:bg-athena-elevated",
  danger:
    "bg-athena-error-bg text-athena-error border border-athena-error/25 hover:bg-athena-error/20",
} as const;

const SIZE_STYLES = {
  sm: "px-3 py-1 text-athena-floor",
  md: "px-4 py-2 text-athena-body",
  lg: "px-6 py-3 text-athena-heading-panel",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof VARIANT_STYLES;
  size?: keyof typeof SIZE_STYLES;
  icon?: React.ReactNode;
}

export function Button({
  variant = "secondary",
  size = "md",
  disabled,
  className = "",
  icon,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 font-mono font-semibold rounded-[var(--radius)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]
        ${VARIANT_STYLES[variant]} ${SIZE_STYLES[size]}
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        ${className}`}
      disabled={disabled}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </button>
  );
}
