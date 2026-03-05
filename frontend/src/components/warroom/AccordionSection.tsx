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

interface AccordionSectionProps {
  id: string;
  title: string;
  summary: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

export function AccordionSection({
  title,
  summary,
  isOpen,
  onToggle,
  children,
}: AccordionSectionProps) {
  return (
    <div className="border-b border-athena-border/50">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-athena-border/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {isOpen ? "▼" : "►"}
          </span>
          <span className="text-xs font-mono font-bold text-athena-text">
            {title}
          </span>
        </div>
        {!isOpen && (
          <span className="text-[10px] font-mono text-athena-text-secondary truncate max-w-[160px]">
            {summary}
          </span>
        )}
      </button>
      <div
        className={`overflow-hidden transition-all duration-200 ${
          isOpen ? "max-h-[60vh] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="px-3 py-2 overflow-y-auto max-h-[58vh]">
          {children}
        </div>
      </div>
    </div>
  );
}
