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

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";

interface RecommendedTechnique {
  technique_id: string;
  name: string;
  rationale: string;
}

interface TargetSummaryData {
  target_id: string;
  hostname: string;
  summary: string;
  attack_surface: string[];
  recommended_techniques: RecommendedTechnique[];
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
    <div className="bg-athena-surface border border-athena-border rounded-athena-sm p-4 font-mono text-xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-athena-accent uppercase tracking-wider font-bold">
          {t("aiSummary")} — {hostname}
        </span>
        <button
          onClick={onClose}
          className="text-athena-text-secondary hover:text-athena-text transition-colors leading-none"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-athena-border/40 rounded w-full" />
          <div className="h-3 bg-athena-border/40 rounded w-5/6" />
          <div className="h-3 bg-athena-border/40 rounded w-4/6" />
          <p className="text-athena-text-secondary pt-1">{t("loadingSummary")}</p>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <p className="text-athena-error">{t("noSummary")}</p>
      )}

      {/* Content */}
      {!loading && !error && data && (
        <>
          {/* Summary text */}
          {data.summary ? (
            <p className="text-athena-text leading-relaxed whitespace-pre-wrap">
              {data.summary}
            </p>
          ) : (
            <p className="text-athena-text-secondary">{t("noSummary")}</p>
          )}

          {/* Attack Surface */}
          {data.attack_surface && data.attack_surface.length > 0 && (
            <div>
              <p className="text-athena-text-secondary uppercase tracking-wider mb-1">
                {t("attackSurface")}
              </p>
              <ul className="space-y-0.5 pl-2">
                {data.attack_surface.map((item, idx) => (
                  <li key={idx} className="text-athena-text before:content-['>_'] before:text-athena-accent/60">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommended Techniques */}
          {data.recommended_techniques && data.recommended_techniques.length > 0 && (
            <div>
              <p className="text-athena-text-secondary uppercase tracking-wider mb-1">
                {t("recommendedTechniques")}
              </p>
              <div className="space-y-2">
                {data.recommended_techniques.map((tech) => (
                  <div
                    key={tech.technique_id}
                    className="border border-athena-border/50 rounded-athena-sm p-2 space-y-0.5"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-athena-accent">{tech.technique_id}</span>
                      <span className="text-athena-text font-semibold">{tech.name}</span>
                    </div>
                    {tech.rationale && (
                      <p className="text-athena-text-secondary pl-1">{tech.rationale}</p>
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
