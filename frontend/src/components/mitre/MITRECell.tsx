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

import { TechniqueStatus } from "@/types/enums";

const STATUS_COLORS: Record<string, string> = {
  [TechniqueStatus.SUCCESS]: "bg-[#22C55E20] text-[#22C55E] border border-[#22C55E]/50",
  [TechniqueStatus.RUNNING]: "bg-[#3b82f6]/60 text-white animate-pulse",
  [TechniqueStatus.FAILED]: "bg-[#EF444420]/80 text-white",
  [TechniqueStatus.QUEUED]: "bg-[#9ca3af]/30 text-[#9ca3af]",
  [TechniqueStatus.UNTESTED]: "bg-[#1f2937]/40 text-[#9ca3af]",
  [TechniqueStatus.PARTIAL]: "bg-[#FBBF2420] text-[#FBBF24] border border-[#FBBF24]/50",
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
      className={`w-full text-left p-1.5 rounded text-sm font-mono transition-all ${colorClass} ${
        isSelected ? "ring-1 ring-[#3b82f6]" : ""
      } hover:brightness-110 cursor-pointer`}
    >
      <div className="font-bold truncate">{mitreId}</div>
      {!compact && <div className="truncate opacity-80">{name}</div>}
    </button>
  );
}
