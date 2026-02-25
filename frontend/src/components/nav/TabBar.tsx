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
                ? "bg-athena-accent text-black"
                : "text-athena-text-secondary hover:text-athena-text"
            }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
