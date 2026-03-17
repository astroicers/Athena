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
    "bg-[#3b82f6] text-white font-bold border border-[#3b82f6] hover:bg-[#2563eb]",
  secondary:
    "bg-[#111827] text-[#e5e7eb] border border-[#374151] hover:bg-[#1f2937]",
  danger:
    "bg-[#EF444420] text-[#EF4444] border border-[#EF444440] hover:bg-[#EF444430]",
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
  variant = "primary",
  size = "md",
  disabled,
  className = "",
  icon,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 font-mono font-semibold rounded transition-colors
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
