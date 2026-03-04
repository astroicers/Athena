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

import { useTranslations } from "next-intl";
import { TechniqueStatus } from "@/types/enums";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import type { AttackPathEntry, AttackPathResponse } from "@/types/attackPath";

// ─── Tactic metadata ──────────────────────────────────────────────────────────

const TACTIC_ORDER_IDS = [
  "TA0043","TA0042","TA0001","TA0002","TA0003","TA0004","TA0005",
  "TA0006","TA0007","TA0008","TA0009","TA0011","TA0010","TA0040",
];


const TACTIC_TO_COLOR: Record<string, string> = {
  TA0043: "#4488ff", TA0042: "#8855ff",
  TA0001: "#aa44ff", TA0002: "#ff8800",
  TA0003: "#ff8800", TA0004: "#ff8800",
  TA0005: "#ffaa00", TA0006: "#ffaa00",
  TA0007: "#ffaa00", TA0008: "#ff4444",
  TA0009: "#ff4444", TA0011: "#ff4444",
  TA0010: "#ff0040", TA0040: "#ff0040",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDuration(sec: number | null): string {
  if (sec === null) return "—";
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}m ${s}s`;
}

function StatusDot({ status }: { status: TechniqueStatus }) {
  switch (status) {
    case TechniqueStatus.SUCCESS:
      return <span className="text-athena-success font-bold">●</span>;
    case TechniqueStatus.FAILED:
      return <span className="text-athena-error font-bold">✗</span>;
    case TechniqueStatus.RUNNING:
    case TechniqueStatus.QUEUED:
      return <span className="text-athena-accent font-bold animate-pulse">⟳</span>;
    case TechniqueStatus.PARTIAL:
      return <span className="text-athena-warning font-bold">◑</span>;
    default:
      return <span className="text-athena-text-secondary">○</span>;
  }
}

function pillBg(status: TechniqueStatus): string {
  switch (status) {
    case TechniqueStatus.SUCCESS:
      return "bg-athena-success/10 border border-athena-success/40";
    case TechniqueStatus.FAILED:
      return "bg-athena-error/10 border border-athena-error/40";
    case TechniqueStatus.RUNNING:
      return "bg-athena-accent/10 border border-athena-accent/40 animate-pulse";
    case TechniqueStatus.QUEUED:
      return "bg-athena-accent/5 border border-athena-accent/20";
    case TechniqueStatus.PARTIAL:
      return "bg-athena-warning/10 border border-athena-warning/40";
    default:
      return "border border-athena-border/40";
  }
}

// ─── Technique pill ───────────────────────────────────────────────────────────

function TechniquePill({ entry }: { entry: AttackPathEntry }) {
  const tooltipLines = [
    entry.techniqueName,
    `Engine: ${entry.engine}`,
    `Duration: ${formatDuration(entry.durationSec)}`,
    entry.targetIp ? `Target: ${entry.targetIp}` : null,
    entry.resultSummary ? `Result: ${entry.resultSummary}` : null,
    entry.errorMessage ? `Error: ${entry.errorMessage}` : null,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <div className="relative group">
      <div
        className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono cursor-default ${pillBg(entry.status)}`}
        title={tooltipLines}
      >
        <StatusDot status={entry.status} />
        <span className="text-athena-text-primary truncate">{entry.mitreId}</span>
      </div>
      {/* CSS hover tooltip */}
      <div
        className={
          "absolute z-50 left-0 top-full mt-1 min-w-[180px] max-w-[240px] " +
          "bg-athena-elevated border border-athena-border rounded-athena-sm p-2 " +
          "text-[10px] font-mono text-athena-text-primary shadow-lg " +
          "invisible opacity-0 group-hover:visible group-hover:opacity-100 " +
          "transition-opacity duration-150 pointer-events-none whitespace-pre-wrap"
        }
      >
        {tooltipLines}
      </div>
    </div>
  );
}

// ─── Skeleton shimmer ─────────────────────────────────────────────────────────

function SkeletonColumn() {
  return (
    <div className="w-24 shrink-0 space-y-1">
      {/* header shimmer */}
      <div className="h-3 bg-athena-border/40 rounded animate-pulse mb-2" />
      {/* pill shimmers */}
      {[1, 2].map((i) => (
        <div
          key={i}
          className="h-5 bg-athena-border/30 rounded animate-pulse"
          style={{ animationDelay: `${i * 80}ms` }}
        />
      ))}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface AttackPathTimelineProps {
  data: AttackPathResponse | null;
  loading: boolean;
}

export function AttackPathTimeline({ data, loading }: AttackPathTimelineProps) {
  const tNav = useTranslations("Navigator");
  const tHints = useTranslations("Hints");
  const tTactic = useTranslations("Tactic");
  // Build tactic → entries map
  const tacticMap = new Map<string, AttackPathEntry[]>();
  if (data) {
    for (const entry of data.entries) {
      const tid = entry.tacticId;
      if (!tacticMap.has(tid)) tacticMap.set(tid, []);
      tacticMap.get(tid)!.push(entry);
    }
  }

  const highestTacticId = data
    ? TACTIC_ORDER_IDS[data.highestTacticIdx] ?? null
    : null;

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-3">
      {/* Section header */}
      <SectionHeader className="mb-3" title={tHints("attackPath")}>
        {tNav("attackPath")}
      </SectionHeader>

      {/* Horizontal scroll container */}
      <div className="overflow-x-auto">
        <div className="flex gap-2 min-w-max">
          {loading
            ? TACTIC_ORDER_IDS.map((tid) => <SkeletonColumn key={tid} />)
            : TACTIC_ORDER_IDS.map((tid, idx) => {
                const entries = tacticMap.get(tid) || [];
                const isEmpty = entries.length === 0;
                const isHighest = tid === highestTacticId;
                const accentColor = TACTIC_TO_COLOR[tid] ?? "#4488ff";

                return (
                  <div
                    key={tid}
                    className={[
                      "w-24 shrink-0 rounded-athena-sm p-1.5",
                      isHighest
                        ? "border-b-2 border-athena-accent bg-athena-accent/5"
                        : isEmpty
                          ? "border border-dashed border-athena-border/30"
                          : "border border-athena-border/20",
                    ].join(" ")}
                    style={
                      isHighest
                        ? { borderBottomColor: accentColor }
                        : undefined
                    }
                  >
                    {/* Tactic header */}
                    <div className="mb-1.5">
                      <div
                        className="text-[10px] font-mono font-bold uppercase truncate"
                        style={{ color: accentColor }}
                      >
                        {tTactic(tid as any)}
                      </div>
                      <div className="text-[10px] font-mono text-athena-text-secondary opacity-60">
                        {tid}
                      </div>
                    </div>

                    {/* Technique pills */}
                    <div className="space-y-1">
                      {isEmpty ? (
                        <div className="text-[10px] font-mono text-athena-text-secondary/40 italic">
                          —
                        </div>
                      ) : (
                        entries.map((entry) => (
                          <TechniquePill key={`${entry.executionId}-${idx}`} entry={entry} />
                        ))
                      )}
                    </div>

                    {/* Coverage badge */}
                    {data && data.tacticCoverage[tid] !== undefined && data.tacticCoverage[tid] > 0 && (
                      <div className="mt-1 text-[10px] font-mono text-athena-text-secondary opacity-60 text-right">
                        {data.tacticCoverage[tid]}%
                      </div>
                    )}
                  </div>
                );
              })}
        </div>
      </div>
    </div>
  );
}
