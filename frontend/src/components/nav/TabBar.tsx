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

interface Tab {
  id: string;
  label: string;
}

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabId: string) => void;
}

export function TabBar({ tabs, activeTab, onChange }: TabBarProps) {
  return (
    <div className="flex gap-1 bg-athena-surface rounded-athena-md p-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`px-4 py-1.5 text-xs font-mono rounded-athena-sm transition-colors
            ${
              activeTab === tab.id
                ? "bg-athena-accent/20 text-athena-accent border border-athena-accent"
                : "text-athena-text-secondary hover:text-athena-text"
            }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
