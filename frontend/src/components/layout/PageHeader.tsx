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
    <header className="px-6 flex items-center justify-between border-b border-athena-border h-12 bg-athena-surface">
      <div className="flex items-center gap-3">
        <h2 className="font-mono text-[13px] font-bold tracking-wider text-athena-text">
          {title}
        </h2>
        {operationCode && (
          <span className="font-mono text-[10px] rounded-athena text-athena-accent bg-athena-accent-bg px-2 py-0.5">
            {operationCode}
          </span>
        )}
      </div>
      {trailing && <div className="flex items-center gap-2">{trailing}</div>}
    </header>
  );
}
