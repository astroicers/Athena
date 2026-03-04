// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/atoms/Badge";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import type { OODATimelineEntry } from "@/types/ooda";

const PHASE_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  observe: "info",
  orient: "warning",
  decide: "success",
  act: "error",
};

const PHASE_LABELS = ["observe", "orient", "decide", "act"];
const SUMMARY_TRUNCATE = 150;
const DEFAULT_SHOW_ITERATIONS = 3;

interface OODATimelineProps {
  entries: OODATimelineEntry[];
  defaultExpandLatest?: number;
}

export function OODATimeline({ entries, defaultExpandLatest = 1 }: OODATimelineProps) {
  const t = useTranslations("OODA");
  const tHints = useTranslations("Hints");
  const [phaseFilter, setPhaseFilter] = useState<string[]>([]);
  const [showAll, setShowAll] = useState(false);
  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(new Set());

  // Group entries by iteration number
  const iterationMap = useMemo(() => {
    const map = new Map<number, OODATimelineEntry[]>();
    for (const e of entries) {
      const list = map.get(e.iterationNumber) ?? [];
      list.push(e);
      map.set(e.iterationNumber, list);
    }
    return map;
  }, [entries]);

  const allIterationNumbers = useMemo(
    () => Array.from(iterationMap.keys()).sort((a, b) => b - a), // newest first
    [iterationMap],
  );

  const maxIteration = allIterationNumbers[0] ?? 0;

  // Default: expand the latest `defaultExpandLatest` iterations
  const [expandedIterations, setExpandedIterations] = useState<Set<number>>(
    () => new Set(allIterationNumbers.slice(0, defaultExpandLatest)),
  );

  const visibleIterations = showAll
    ? allIterationNumbers
    : allIterationNumbers.slice(0, DEFAULT_SHOW_ITERATIONS);

  function toggleIteration(num: number) {
    setExpandedIterations((prev) => {
      const next = new Set(prev);
      if (next.has(num)) next.delete(num);
      else next.add(num);
      return next;
    });
  }

  function toggleEntry(key: string) {
    setExpandedEntries((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function togglePhaseFilter(phase: string) {
    setPhaseFilter((prev) =>
      prev.includes(phase) ? prev.filter((p) => p !== phase) : [...prev, phase],
    );
  }

  if (entries.length === 0) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-6 text-center">
        <span className="text-xs font-mono text-athena-text-secondary">{t("noIterations")}</span>
      </div>
    );
  }

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
      {/* Header + filter bar */}
      <SectionHeader
        level="card"
        className="mb-3 flex-wrap gap-2"
        title={tHints("oodaTimeline")}
        trailing={
          <div className="flex items-center gap-1 flex-wrap">
            {/* Phase filter chips */}
            <button
              onClick={() => setPhaseFilter([])}
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded border transition-colors ${
                phaseFilter.length === 0
                  ? "border-athena-accent text-athena-accent bg-athena-accent/10"
                  : "border-athena-border text-athena-text-secondary hover:border-athena-accent/50"
              }`}
            >
              {t("all")}
            </button>
            {PHASE_LABELS.map((p) => (
              <button
                key={p}
                onClick={() => togglePhaseFilter(p)}
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border transition-colors ${
                  phaseFilter.includes(p)
                    ? "border-athena-accent text-athena-accent bg-athena-accent/10"
                    : "border-athena-border text-athena-text-secondary hover:border-athena-accent/50"
                }`}
              >
                {p.slice(0, 3).toUpperCase()}
              </button>
            ))}
          </div>
        }
      >
        {t("timeline")}
      </SectionHeader>

      {/* Iteration groups */}
      <div className="space-y-2">
        {visibleIterations.map((iterNum) => {
          const iterEntries = iterationMap.get(iterNum) ?? [];
          const filtered = phaseFilter.length === 0
            ? iterEntries
            : iterEntries.filter((e) => phaseFilter.includes(e.phase));
          if (filtered.length === 0) return null;

          const isExpanded = expandedIterations.has(iterNum);
          const actEntry = iterEntries.find((e) => e.phase === "act");
          const actTime = actEntry?.timestamp.split("T")[1]?.slice(0, 8) ?? "";

          return (
            <div
              key={iterNum}
              className="border border-athena-border/60 rounded-athena-sm overflow-hidden"
            >
              {/* Iteration header */}
              <button
                onClick={() => toggleIteration(iterNum)}
                className="w-full flex items-center justify-between px-3 py-2 bg-athena-bg hover:bg-athena-border/20 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-athena-text-secondary">
                    {isExpanded ? "▼" : "►"}
                  </span>
                  <span className="text-xs font-mono text-athena-accent font-bold">
                    {t("iteration", { number: iterNum })}
                  </span>
                  {iterNum === maxIteration && (
                    <span className="text-[10px] font-mono text-athena-success bg-athena-success/10 px-1 rounded">
                      {t("latest")}
                    </span>
                  )}
                </div>
                {!isExpanded && actEntry && (
                  <span className="text-[10px] font-mono text-athena-text-secondary/70 truncate max-w-[200px]">
                    {actTime} · {actEntry.summary.slice(0, 60)}{actEntry.summary.length > 60 ? "..." : ""}
                  </span>
                )}
              </button>

              {/* Expanded entries */}
              {isExpanded && (
                <div className="px-3 py-2 space-y-2">
                  {filtered.map((entry, i) => {
                    const time = entry.timestamp.split("T")[1]?.slice(0, 8) || entry.timestamp;
                    const entryKey = `${iterNum}-${entry.phase}`;
                    const isEntryExpanded = expandedEntries.has(entryKey);
                    const needsTruncate = entry.summary.length > SUMMARY_TRUNCATE;
                    const displaySummary =
                      needsTruncate && !isEntryExpanded
                        ? entry.summary.slice(0, SUMMARY_TRUNCATE) + "..."
                        : entry.summary;

                    return (
                      <div key={i} className="flex items-start gap-3">
                        <div className="flex flex-col items-center shrink-0">
                          <div className="w-1.5 h-1.5 rounded-full bg-athena-accent mt-1.5" />
                          {i < filtered.length - 1 && (
                            <div className="w-px flex-1 bg-athena-border/50 mt-1 min-h-[12px]" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0 pb-1">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="text-[10px] font-mono text-athena-text-secondary/70">
                              {time}
                            </span>
                            <Badge variant={PHASE_VARIANT[entry.phase] || "info"}>
                              {entry.phase.toUpperCase()}
                            </Badge>
                          </div>
                          <p className="text-xs font-mono text-athena-text leading-relaxed">
                            {displaySummary}
                            {needsTruncate && (
                              <button
                                onClick={() => toggleEntry(entryKey)}
                                className="ml-1 text-[10px] font-mono text-athena-accent hover:underline"
                              >
                                {isEntryExpanded ? t("collapse") : t("expand")}
                              </button>
                            )}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Show more / less */}
      {allIterationNumbers.length > DEFAULT_SHOW_ITERATIONS && (
        <button
          onClick={() => setShowAll((v) => !v)}
          className="mt-3 w-full text-[10px] font-mono text-athena-text-secondary hover:text-athena-accent transition-colors py-1 border-t border-athena-border/50"
        >
          {showAll
            ? t("showLatest", { count: DEFAULT_SHOW_ITERATIONS })
            : t("showAll", { count: allIterationNumbers.length })}
        </button>
      )}
    </div>
  );
}
