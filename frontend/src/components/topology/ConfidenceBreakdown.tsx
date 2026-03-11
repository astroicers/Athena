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

export interface ConfidenceSource {
  key: "llm" | "historical" | "graph" | "target" | "opsec";
  label: string;
  score: number; // 0-1
  weight: number; // 0-1, all weights sum to 1
}

interface ConfidenceBreakdownProps {
  sources: ConfidenceSource[];
  totalConfidence: number; // 0-1
}

const colorMap: Record<ConfidenceSource["key"], string> = {
  llm: "bg-athena-accent",
  historical: "bg-athena-success",
  graph: "bg-athena-info",
  target: "bg-athena-warning",
  opsec: "bg-athena-error",
};

const dotColorMap: Record<ConfidenceSource["key"], string> = {
  llm: "bg-athena-accent",
  historical: "bg-athena-success",
  graph: "bg-athena-info",
  target: "bg-athena-warning",
  opsec: "bg-athena-error",
};

export function ConfidenceBreakdown({
  sources,
  totalConfidence,
}: ConfidenceBreakdownProps) {
  const t = useTranslations("AIDecision" as any);

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-mono tracking-widest text-athena-text-secondary uppercase">
        {t("confidenceBreakdown")}
      </h4>

      {/* Stacked bar */}
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-athena-border/30">
        {sources.map((source) => {
          const widthPercent = source.weight * source.score * 100 / totalConfidence;
          if (widthPercent <= 0) return null;
          return (
            <div
              key={source.key}
              className={`${colorMap[source.key]} h-full`}
              style={{ width: `${widthPercent}%` }}
            />
          );
        })}
      </div>

      {/* Source list */}
      <ul className="space-y-1">
        {sources.map((source) => (
          <li key={source.key} className="flex items-center gap-2">
            <span
              className={`${dotColorMap[source.key]} w-2 h-2 rounded-full shrink-0`}
            />
            <span className="text-xs font-mono text-athena-text">
              {source.label}
            </span>
            <span className="ml-auto text-xs font-mono text-athena-text-secondary">
              {Math.round(source.score * 100)}%
            </span>
            <span className="text-xs font-mono text-athena-text-tertiary">
              ({Math.round(source.weight * 100)}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
