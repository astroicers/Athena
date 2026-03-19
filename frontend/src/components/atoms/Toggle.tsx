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

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
}

export function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <label className="inline-flex items-center gap-2 cursor-pointer">
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-[#3b82f6]
          ${checked ? "bg-[#3b82f6]" : "bg-athena-elevated"}`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 rounded-full bg-athena-bg transition-transform
            ${checked ? "translate-x-4" : "translate-x-0.5"}`}
        />
      </button>
      {label && (
        <span className="text-xs font-mono text-athena-text-tertiary">
          {label}
        </span>
      )}
    </label>
  );
}
