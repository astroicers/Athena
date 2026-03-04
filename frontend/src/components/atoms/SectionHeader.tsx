// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

"use client";

interface SectionHeaderProps extends React.HTMLAttributes<HTMLElement> {
  /** "page" = text-xs (12px), "card" = text-[11px] */
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
  const sizeClass = level === "page" ? "text-xs" : "text-[11px]";

  if (trailing) {
    return (
      <div className={`flex items-center justify-between ${className}`}>
        <Tag
          className={`${sizeClass} font-mono text-athena-text-secondary uppercase tracking-wider`}
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
      className={`${sizeClass} font-mono text-athena-text-secondary uppercase tracking-wider ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}
