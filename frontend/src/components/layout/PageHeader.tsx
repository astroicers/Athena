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

interface PageHeaderProps {
  title: string;
  operationCode?: string;
}

export function PageHeader({
  title,
  operationCode,
}: PageHeaderProps) {
  return (
    <header className="h-12 px-4 flex items-center justify-between bg-athena-surface border-b border-athena-border">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-mono font-bold text-athena-text">
          {title}
        </h2>
        {operationCode && (
          <span className="text-xs font-mono text-athena-accent bg-athena-accent/10 px-2 py-0.5 rounded">
            {operationCode}
          </span>
        )}
      </div>
    </header>
  );
}
