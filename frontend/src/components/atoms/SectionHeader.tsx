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

interface SectionHeaderProps extends React.HTMLAttributes<HTMLElement> {
  /** "page" = text-xs (12px), "card" = text-xs (12px) */
  level?: "page" | "card";
  /** The header text content */
  children: React.ReactNode;
  /** Optional right-side content (buttons, toggles, etc.) */
  trailing?: React.ReactNode;
  /** Additional className for margin customization */
  className?: string;
}

export function SectionHeader({
  level = "page",
  children,
  trailing,
  className = "",
  ...rest
}: SectionHeaderProps) {
  const Tag = level === "page" ? "h2" : "h3";
  const colorClass = level === "page" ? "text-[#e5e7eb]" : "text-[#e5e7eb]";

  if (trailing) {
    return (
      <div className={`flex items-center justify-between ${className}`}>
        <Tag
          className={`text-xs font-mono font-bold ${colorClass} uppercase tracking-wider`}
          {...rest}
        >
          {children}
        </Tag>
        {trailing}
      </div>
    );
  }

  return (
    <Tag
      className={`text-xs font-mono font-bold ${colorClass} uppercase tracking-wider ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}
