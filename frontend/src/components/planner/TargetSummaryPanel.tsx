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

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";

interface RecommendedTechnique {
  techniqueId: string;
  name: string;
  rationale: string;
}

interface TargetSummaryData {
  targetId: string;
  hostname: string;
  summary: string;
  attackSurface: string[];
  recommendedTechniques: RecommendedTechnique[];
}

interface TargetSummaryPanelProps {
  operationId: string;
  targetId: string;
  hostname: string;
  onClose: () => void;
}

export function TargetSummaryPanel({
  operationId,
  targetId,
  hostname,
  onClose,
}: TargetSummaryPanelProps) {
  const t = useTranslations("Planner");
  const [data, setData] = useState<TargetSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    setData(null);
    api
      .get<TargetSummaryData>(
        `/operations/${operationId}/targets/${targetId}/summary`,
      )
      .then((res) => {
        setData(res);
      })
      .catch(() => {
        setError(true);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [operationId, targetId]);

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius)] p-4 font-mono text-athena-floor space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-[var(--color-accent)] uppercase tracking-wider font-bold">
          {t("aiSummary")} — {hostname}
        </span>
        <button
          onClick={onClose}
          className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition-colors leading-none"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-[var(--color-bg-elevated)]/40 rounded-[var(--radius)] w-full" />
          <div className="h-3 bg-[var(--color-bg-elevated)]/40 rounded-[var(--radius)] w-5/6" />
          <div className="h-3 bg-[var(--color-bg-elevated)]/40 rounded-[var(--radius)] w-4/6" />
          <p className="text-[var(--color-text-tertiary)] pt-1">{t("loadingSummary")}</p>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <p className="text-[var(--color-error)]">{t("noSummary")}</p>
      )}

      {/* Content */}
      {!loading && !error && data && (
        <>
          {/* Summary text */}
          {data.summary ? (
            <p className="text-[var(--color-text-primary)] leading-relaxed whitespace-pre-wrap">
              {data.summary}
            </p>
          ) : (
            <p className="text-[var(--color-text-tertiary)]">{t("noSummary")}</p>
          )}

          {/* Attack Surface */}
          {data.attackSurface && data.attackSurface.length > 0 && (
            <div>
              <p className="text-[var(--color-text-tertiary)] uppercase tracking-wider mb-1">
                {t("attackSurface")}
              </p>
              <ul className="space-y-0.5 pl-2">
                {data.attackSurface.map((item, idx) => (
                  <li key={idx} className="text-[var(--color-text-primary)] before:content-['>_'] before:text-[var(--color-accent)]/60">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommended Techniques */}
          {data.recommendedTechniques && data.recommendedTechniques.length > 0 && (
            <div>
              <p className="text-[var(--color-text-tertiary)] uppercase tracking-wider mb-1">
                {t("recommendedTechniques")}
              </p>
              <div className="space-y-2">
                {data.recommendedTechniques.map((tech) => (
                  <div
                    key={tech.techniqueId}
                    className="border border-[var(--color-border)]/50 rounded-[var(--radius)] p-2 space-y-0.5"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--color-accent)]">{tech.techniqueId}</span>
                      <span className="text-[var(--color-text-primary)] font-semibold">{tech.name}</span>
                    </div>
                    {tech.rationale && (
                      <p className="text-[var(--color-text-tertiary)] pl-1">{tech.rationale}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
