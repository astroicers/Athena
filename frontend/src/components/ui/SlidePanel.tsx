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

import { useEffect, useCallback, useRef } from "react";

interface SlidePanelProps {
  open: boolean;
  onClose: () => void;
  title: string;
  width?: "sm" | "md" | "lg";
  children: React.ReactNode;
}

export function SlidePanel({ open, onClose, title, width = "md", children }: SlidePanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Escape key handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [open, handleKeyDown]);

  // Width classes — explicit pixel widths for predictability
  const widthClass = width === "sm" ? "w-80" : width === "lg" ? "w-[640px]" : "w-[480px]";

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-athena-bg/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`relative ${widthClass} h-full bg-athena-surface border-l border-athena-border flex flex-col`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-athena-border shrink-0">
          <h2 className="text-xs font-mono text-athena-text-tertiary uppercase tracking-wider font-bold">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="text-athena-text-tertiary hover:text-athena-text-light transition-colors p-1"
            aria-label="Close panel"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Body — scrollable */}
        <div className="flex-1 overflow-y-auto p-4">
          {children}
        </div>
      </div>
    </div>
  );
}
