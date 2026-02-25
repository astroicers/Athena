"use client";

import { ButtonHTMLAttributes } from "react";

const VARIANT_STYLES = {
  primary:
    "bg-athena-accent text-black hover:bg-athena-accent-hover",
  secondary:
    "bg-athena-surface text-athena-text border border-athena-border hover:bg-athena-elevated",
  danger:
    "bg-athena-error text-white hover:brightness-110",
} as const;

const SIZE_STYLES = {
  sm: "px-3 py-1 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof VARIANT_STYLES;
  size?: keyof typeof SIZE_STYLES;
}

export function Button({
  variant = "primary",
  size = "md",
  disabled,
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center font-mono font-semibold rounded-athena-md transition-colors
        ${VARIANT_STYLES[variant]} ${SIZE_STYLES[size]}
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
