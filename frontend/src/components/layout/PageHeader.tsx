"use client";

import { Toggle } from "@/components/atoms/Toggle";

interface PageHeaderProps {
  title: string;
  operationCode?: string;
  automationMode?: string;
  onModeToggle?: (checked: boolean) => void;
}

export function PageHeader({
  title,
  operationCode,
  automationMode,
  onModeToggle,
}: PageHeaderProps) {
  const isSemiAuto = automationMode === "semi_auto";

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

      {onModeToggle && (
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-athena-text-secondary">
            {isSemiAuto ? "SEMI-AUTO" : "MANUAL"}
          </span>
          <Toggle
            checked={isSemiAuto}
            onChange={onModeToggle}
          />
        </div>
      )}
    </header>
  );
}
