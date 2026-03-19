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
    <div className="flex items-center h-10 px-4 bg-[#0f1729] border-b border-athena-border">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`relative h-full px-4 text-xs font-mono transition-colors flex items-center
            ${
              activeTab === tab.id
                ? "text-athena-accent font-semibold"
                : "text-athena-text-secondary hover:text-athena-text-tertiary"
            }`}
        >
          {tab.label}
          {activeTab === tab.id && (
            <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-[#3b82f6]" />
          )}
        </button>
      ))}
    </div>
  );
}
