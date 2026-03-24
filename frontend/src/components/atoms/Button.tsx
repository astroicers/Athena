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
    "bg-[var(--color-accent)] text-[var(--color-text-primary)] font-bold border border-[var(--color-accent)] hover:bg-[var(--color-accent-hover)]",
  secondary:
    "bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] border border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-elevated)]",
  danger:
    "bg-[var(--color-error)]/[0.12] text-[var(--color-error)] border border-[var(--color-error)]/[0.25] hover:bg-[var(--color-error)]/20",
} as const;

const SIZE_STYLES = {
  sm: "px-3 py-1 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
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
