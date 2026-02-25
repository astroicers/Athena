"use client";

import { TechniqueStatus } from "@/types/enums";

const STATUS_COLORS: Record<string, string> = {
  [TechniqueStatus.SUCCESS]: "bg-athena-success/80 text-black",
  [TechniqueStatus.RUNNING]: "bg-athena-accent/60 text-white animate-pulse",
  [TechniqueStatus.FAILED]: "bg-athena-error/80 text-white",
  [TechniqueStatus.QUEUED]: "bg-athena-text-secondary/30 text-athena-text-secondary",
  [TechniqueStatus.UNTESTED]: "bg-athena-border/40 text-athena-text-secondary/60",
  [TechniqueStatus.PARTIAL]: "bg-athena-warning/60 text-black",
};

interface MITRECellProps {
  mitreId: string;
  name: string;
  status: TechniqueStatus | null;
  isSelected?: boolean;
  onClick?: () => void;
}

export function MITRECell({ mitreId, name, status, isSelected, onClick }: MITRECellProps) {
  const colorClass = STATUS_COLORS[status || TechniqueStatus.UNTESTED] || STATUS_COLORS[TechniqueStatus.UNTESTED];

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-1.5 rounded-athena-sm text-[10px] font-mono transition-all ${colorClass} ${
        isSelected ? "ring-1 ring-athena-accent" : ""
      } hover:brightness-110 cursor-pointer`}
    >
      <div className="font-bold truncate">{mitreId}</div>
      <div className="truncate opacity-80">{name}</div>
    </button>
  );
}
