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

interface PageHeaderProps {
  title: string;
  operationCode?: string;
  trailing?: React.ReactNode;
}

export function PageHeader({
  title,
  operationCode,
  trailing,
}: PageHeaderProps) {
  return (
    <header
      className="px-4 flex items-center justify-between border-b border-[#1f2937] h-12"
      style={{ backgroundColor: "#111827" }}
    >
      <div className="flex items-center gap-3">
        <h2
          className="font-mono font-bold tracking-wider"
          style={{ fontSize: 13, color: "#e5e7eb", letterSpacing: 1 }}
        >
          {title}
        </h2>
        {operationCode && (
          <span
            className="font-mono text-[10px] rounded-athena-sm"
            style={{
              color: "#3b82f6",
              backgroundColor: "#3b82f620",
              padding: "2px 8px",
            }}
          >
            {operationCode}
          </span>
        )}
      </div>
      {trailing && <div className="flex items-center gap-2">{trailing}</div>}
    </header>
  );
}
