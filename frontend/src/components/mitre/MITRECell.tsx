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

import { TechniqueStatus } from "@/types/enums";

const STATUS_COLORS: Record<string, string> = {
  [TechniqueStatus.SUCCESS]: "bg-athena-success/20 text-athena-success border border-athena-success/50",
  [TechniqueStatus.RUNNING]: "bg-athena-accent/60 text-white animate-pulse",
  [TechniqueStatus.FAILED]: "bg-athena-error/80 text-white",
  [TechniqueStatus.QUEUED]: "bg-athena-text-secondary/30 text-athena-text-secondary",
  [TechniqueStatus.UNTESTED]: "bg-athena-border/40 text-athena-text-secondary/60",
  [TechniqueStatus.PARTIAL]: "bg-athena-warning/20 text-athena-warning border border-athena-warning/50",
};

interface MITRECellProps {
  mitreId: string;
  name: string;
  status: TechniqueStatus | null;
  isSelected?: boolean;
  onClick?: () => void;
  compact?: boolean;
}

export function MITRECell({ mitreId, name, status, isSelected, onClick, compact = false }: MITRECellProps) {
  const colorClass = STATUS_COLORS[status || TechniqueStatus.UNTESTED] || STATUS_COLORS[TechniqueStatus.UNTESTED];

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-1.5 rounded-athena-sm text-[10px] font-mono transition-all ${colorClass} ${
        isSelected ? "ring-1 ring-athena-accent" : ""
      } hover:brightness-110 cursor-pointer`}
    >
      <div className="font-bold truncate">{mitreId}</div>
      {!compact && <div className="truncate opacity-80">{name}</div>}
    </button>
  );
}
