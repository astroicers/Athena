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
    <header className="px-6 flex items-center justify-between border-b border-[var(--color-border)] h-12 bg-[var(--color-bg-surface)]">
      <div className="flex items-center gap-3">
        <h2 className="font-mono text-[13px] font-bold tracking-wider text-[var(--color-text-primary)]">
          {title}
        </h2>
        {operationCode && (
          <span className="font-mono text-xs font-semibold rounded-[var(--radius)] text-[var(--color-accent)] bg-[var(--color-accent)]/[0.12] border border-[var(--color-accent)]/[0.25] px-2 py-1">
            {operationCode}
          </span>
        )}
      </div>
      {trailing && <div className="flex items-center gap-2">{trailing}</div>}
    </header>
  );
}
