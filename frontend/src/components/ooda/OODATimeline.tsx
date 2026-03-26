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
  recon: "info",
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

  // Split entries: OODA iterations (≥1) vs recon scans (0 sentinel)
  const oodaEntries = useMemo(
    () => entries.filter((e) => e.iterationNumber > 0),
    [entries],
  );
  const reconEntries = useMemo(
    () => entries.filter((e) => e.iterationNumber === 0),
    [entries],
  );

  // Group OODA entries by iteration number
  const iterationMap = useMemo(() => {
    const map = new Map<number, OODATimelineEntry[]>();
    for (const e of oodaEntries) {
      const list = map.get(e.iterationNumber) ?? [];
      list.push(e);
      map.set(e.iterationNumber, list);
    }
    return map;
  }, [oodaEntries]);

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

  if (oodaEntries.length === 0 && reconEntries.length === 0) {
    return (
      <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius)] p-6 text-center">
        <span className="text-athena-floor font-mono text-[var(--color-text-tertiary)]">{t("noIterations")}</span>
      </div>
    );
  }

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius)] p-4">
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
              className={`text-athena-body font-mono px-1.5 py-0.5 rounded-[var(--radius)] border transition-colors ${
                phaseFilter.length === 0
                  ? "border-[var(--color-accent)] text-[var(--color-accent)] bg-[var(--color-accent)]/10"
                  : "border-[var(--color-border)] text-[var(--color-text-tertiary)] hover:border-[var(--color-accent)]/50"
              }`}
            >
              {t("all")}
            </button>
            {PHASE_LABELS.map((p) => (
              <button
                key={p}
                onClick={() => togglePhaseFilter(p)}
                className={`text-athena-body font-mono px-1.5 py-0.5 rounded-[var(--radius)] border transition-colors ${
                  phaseFilter.includes(p)
                    ? "border-[var(--color-accent)] text-[var(--color-accent)] bg-[var(--color-accent)]/10"
                    : "border-[var(--color-border)] text-[var(--color-text-tertiary)] hover:border-[var(--color-accent)]/50"
                }`}
              >
                {t(p as "observe" | "orient" | "decide" | "act")}
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
              className="border border-[var(--color-border)] rounded-[var(--radius)] overflow-hidden"
            >
              {/* Iteration header */}
              <button
                onClick={() => toggleIteration(iterNum)}
                className="w-full flex items-center justify-between px-3 py-2 bg-[var(--color-bg-primary)] hover:bg-[var(--color-bg-elevated)] transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-athena-body font-mono text-[var(--color-text-tertiary)]">
                    {isExpanded ? "▼" : "►"}
                  </span>
                  <span className="text-athena-floor font-mono text-[var(--color-accent)] font-bold">
                    {t("iteration", { number: iterNum })}
                  </span>
                  {iterNum === maxIteration && (
                    <span className="text-athena-body font-mono text-[var(--color-success)] bg-[var(--color-success)]/10 px-1 rounded-[var(--radius)]">
                      {t("latest")}
                    </span>
                  )}
                </div>
                {!isExpanded && actEntry && (
                  <span className="text-athena-body font-mono text-[var(--color-text-tertiary)] truncate max-w-[200px]">
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
                          <div className="w-2.5 h-2.5 rounded-full bg-[var(--color-accent)] mt-1.5" />
                          {i < filtered.length - 1 && (
                            <div className="w-px flex-1 bg-[var(--color-border)]/50 mt-1 min-h-[12px]" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0 pb-1">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="text-athena-body font-mono text-[var(--color-text-tertiary)]">
                              {time}
                            </span>
                            <Badge variant={PHASE_VARIANT[entry.phase] || "info"}>
                              {t(entry.phase as "observe" | "orient" | "decide" | "act")}
                            </Badge>
                          </div>
                          <p className="text-athena-floor font-mono text-[var(--color-text-primary)] leading-relaxed">
                            {displaySummary}
                            {needsTruncate && (
                              <button
                                onClick={() => toggleEntry(entryKey)}
                                className="ml-1 text-athena-body font-mono text-[var(--color-accent)] hover:underline"
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

      {/* Recon Activity Log */}
      {reconEntries.length > 0 && (
        <div className={oodaEntries.length > 0 ? "mt-3 pt-3 border-t border-[var(--color-border)]/50" : ""}>
          <span className="text-athena-body font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider">
            {t("reconActivity")}
          </span>
          <div className="mt-2 space-y-2">
            {reconEntries.map((entry, i) => {
              const time = entry.timestamp.split("T")[1]?.slice(0, 8) || entry.timestamp;
              return (
                <div key={`recon-${i}`} className="flex items-start gap-3">
                  <div className="flex flex-col items-center shrink-0">
                    <div className="w-2.5 h-2.5 rounded-full bg-[var(--color-accent)] mt-1.5" />
                    {i < reconEntries.length - 1 && (
                      <div className="w-px flex-1 bg-[var(--color-border)]/50 mt-1 min-h-[12px]" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0 pb-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-athena-body font-mono text-[var(--color-text-tertiary)]">
                        {time}
                      </span>
                      <Badge variant="info">{t("recon")}</Badge>
                    </div>
                    <p className="text-athena-floor font-mono text-[var(--color-text-primary)] leading-relaxed">
                      {entry.summary}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Show more / less */}
      {allIterationNumbers.length > DEFAULT_SHOW_ITERATIONS && (
        <button
          onClick={() => setShowAll((v) => !v)}
          className="mt-3 w-full text-athena-body font-mono text-[var(--color-text-tertiary)] hover:text-[var(--color-accent)] transition-colors py-1 border-t border-[var(--color-border)]/50"
        >
          {showAll
            ? t("showLatest", { count: DEFAULT_SHOW_ITERATIONS })
            : t("showAll", { count: allIterationNumbers.length })}
        </button>
      )}
    </div>
  );
}
