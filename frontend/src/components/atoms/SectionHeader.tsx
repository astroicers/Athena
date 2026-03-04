// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

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
