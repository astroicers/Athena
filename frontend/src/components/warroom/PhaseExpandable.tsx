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

import { useState, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import type { PhaseDetail } from "@/types/ooda";
import { ObserveDetailView } from "./ObserveDetailView";
import { OrientDetailView } from "./OrientDetailView";
import { DecideDetailView } from "./DecideDetailView";
import { ActDetailView } from "./ActDetailView";

interface PhaseExpandableProps {
  phase: string;
  summary: string | null;
  detail?: PhaseDetail;
  isActive?: boolean;
  isPending?: boolean;
  phaseColor: string;
}

function PhaseDetailRouter({
  phase,
  detail,
}: {
  phase: string;
  detail: PhaseDetail;
}) {
  switch (phase) {
    case "observe":
      return <ObserveDetailView detail={detail} />;
    case "orient":
      return <OrientDetailView detail={detail} />;
    case "decide":
      return <DecideDetailView detail={detail} />;
    case "act":
      return <ActDetailView detail={detail} />;
    default:
      return null;
  }
}

export function PhaseExpandable({
  phase,
  summary,
  detail,
  isActive = false,
  isPending = false,
  phaseColor,
}: PhaseExpandableProps) {
  const t = useTranslations("WarRoom");
  const tOoda = useTranslations("OODA");
  const [expanded, setExpanded] = useState(false);
  const [rawExpanded, setRawExpanded] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState(0);

  useEffect(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, [expanded, rawExpanded, detail]);

  const hasDetail = detail != null;
  const canExpand = hasDetail && !isPending;

  const dotSize = isActive ? 14 : 12;

  const phaseKeys: Record<string, string> = {
    observe: "observe",
    orient: "orient",
    decide: "decide",
    act: "act",
  };

  const truncatedSummary =
    summary && summary.length > 80
      ? summary.slice(0, 80) + "..."
      : summary;

  return (
    <div className="font-mono">
      {/* Collapsed row */}
      <button
        type="button"
        className={`w-full h-10 px-3 flex items-center gap-2 transition-colors ${
          canExpand
            ? "cursor-pointer hover:bg-[var(--color-bg-secondary)]"
            : "cursor-default"
        }`}
        onClick={() => {
          if (canExpand) setExpanded((prev) => !prev);
        }}
        disabled={!canExpand}
      >
        {/* Expand arrow */}
        {canExpand && (
          <span className="text-athena-floor text-[var(--color-text-tertiary)] shrink-0 w-3">
            {expanded ? "\u25BE" : "\u25B8"}
          </span>
        )}
        {!canExpand && <span className="w-3 shrink-0" />}

        {/* Phase dot */}
        <span className="shrink-0">
          <svg
            width={dotSize}
            height={dotSize}
            viewBox={`0 0 ${dotSize} ${dotSize}`}
          >
            <circle
              cx={dotSize / 2}
              cy={dotSize / 2}
              r={dotSize / 2}
              fill={isPending ? "var(--color-text-tertiary)" : phaseColor}
              opacity={isPending ? 0.4 : 1}
            >
              {isActive && (
                <animate
                  attributeName="opacity"
                  values="1;0.4;1"
                  dur="2s"
                  repeatCount="indefinite"
                />
              )}
            </circle>
          </svg>
        </span>

        {/* Phase label */}
        <span
          className="text-athena-floor font-bold uppercase tracking-wider shrink-0"
          style={{
            color: isPending ? "var(--color-text-tertiary)" : phaseColor,
          }}
        >
          {tOoda(phaseKeys[phase] ?? phase)}
        </span>

        {/* Summary text */}
        {!expanded && (
          <span className="text-athena-floor text-[var(--color-text-secondary)] truncate min-w-0">
            {isPending ? "(pending)" : truncatedSummary}
          </span>
        )}
      </button>

      {/* Expanded area */}
      {expanded && detail && (
        <div
          ref={contentRef}
          className="bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-[var(--radius)] p-3 mt-1 mb-2 mx-3"
        >
          {/* Structured detail */}
          <PhaseDetailRouter phase={phase} detail={detail} />

          {/* Raw data toggle */}
          {detail.rawSummary && (
            <div className="mt-3">
              <button
                type="button"
                className="text-athena-floor text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] transition-colors flex items-center gap-1 font-mono"
                onClick={(e) => {
                  e.stopPropagation();
                  setRawExpanded((prev) => !prev);
                }}
              >
                <span>{rawExpanded ? "\u25BE" : "\u25B8"}</span>
                <span>
                  {rawExpanded
                    ? t("collapseRawData")
                    : t("viewRawData")}
                </span>
              </button>

              {rawExpanded && (
                <div className="bg-[var(--color-bg-primary)] border border-[var(--color-border-subtle)] rounded-[var(--radius)] p-3 font-mono text-athena-floor text-[var(--color-text-tertiary)] whitespace-pre-wrap max-h-[400px] overflow-y-auto mt-2">
                  {detail.rawSummary}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
