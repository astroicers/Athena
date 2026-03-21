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

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Button } from "@/components/atoms/Button";
import type { OrientRecommendation } from "@/types/recommendation";

/* ── Constants ── */

const POLL_MS = 30_000;

/* ── Noise x Risk matrix types ── */

type MatrixAction = "GO" | "CAUTION" | "HOLD" | "ABORT";

const NOISE_ROWS = ["HI", "MED", "LO"] as const;
const RISK_COLS = ["LOW", "MED", "HIGH", "CRIT"] as const;

/** Matrix[noise][risk] -- rows top-to-bottom: HI, MED, LO */
const MATRIX: MatrixAction[][] = [
  // HI noise
  ["CAUTION", "HOLD", "ABORT", "ABORT"],
  // MED noise
  ["GO", "CAUTION", "HOLD", "ABORT"],
  // LO noise
  ["GO", "GO", "CAUTION", "HOLD"],
];

function actionBg(a: MatrixAction): string {
  switch (a) {
    case "GO":
      return "bg-athena-success/[0.08]";
    case "CAUTION":
      return "bg-athena-warning-bg";
    case "HOLD":
      return "bg-athena-error/[0.14]";
    case "ABORT":
      return "bg-athena-error/25";
  }
}

function actionTextColor(a: MatrixAction): string {
  switch (a) {
    case "GO":
      return "var(--color-success)";
    case "CAUTION":
      return "var(--color-warning)";
    case "HOLD":
      return "var(--color-error)";
    case "ABORT":
      return "#991B1B";
  }
}

function actionBorderColor(a: MatrixAction): string {
  switch (a) {
    case "GO":
      return "var(--color-success)";
    case "CAUTION":
      return "var(--color-warning)";
    case "HOLD":
      return "var(--color-error)";
    case "ABORT":
      return "#991B1B";
  }
}

/* ── Map noise % and risk % to matrix cell indices ── */

function noiseToRow(noisePct: number): number {
  if (noisePct >= 66) return 0; // HI
  if (noisePct >= 33) return 1; // MED
  return 2; // LO
}

function riskToCol(riskPct: number): number {
  if (riskPct >= 75) return 3; // CRIT
  if (riskPct >= 50) return 2; // HIGH
  if (riskPct >= 25) return 1; // MED
  return 0; // LOW
}

/* ── Confidence helpers ── */

function confidenceColor(score: number): string {
  if (score >= 0.75) return "var(--color-success)";
  if (score >= 0.5) return "var(--color-warning)";
  return "var(--color-error)";
}

/* ── Dashboard response shape ── */

interface DashboardData {
  opsec: {
    noise10min: number;
    eventCount: number;
  };
  c5isr: Array<{
    domain: string;
    healthPct: number;
    status: string;
  }>;
  operation: {
    threatLevel?: number;
    successRate?: number;
    techniquesExecuted?: number;
  };
}

/* ── Confidence breakdown bar item ── */

interface BreakdownBar {
  label: string;
  value: number;
  color: string;
}

/* ── Progress Bar ── */

function ProgressBar({ value, color }: { value: number; color: string }) {
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <div className="w-full h-1.5 rounded-full bg-athena-elevated overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

/* ── DecisionPanel ── */

export function DecisionPanel({ operationId }: { operationId: string }) {
  const t = useTranslations("AIDecisionPage");
  const tRec = useTranslations("Recommendations");

  /* State */
  const [recommendation, setRecommendation] =
    useState<OrientRecommendation | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [history, setHistory] = useState<OrientRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* Fetch all data */
  const fetchData = useCallback(async () => {
    if (!operationId) return;
    try {
      const [rec, dash, hist] = await Promise.all([
        api
          .get<OrientRecommendation | null>(
            `/operations/${operationId}/recommendations/latest`,
          )
          .catch(() => null),
        api
          .get<DashboardData>(`/operations/${operationId}/dashboard`)
          .catch(() => null),
        api
          .get<OrientRecommendation[]>(
            `/operations/${operationId}/recommendations?limit=20`,
          )
          .catch(() => []),
      ]);
      setRecommendation(rec);
      setDashboard(dash);
      setHistory(hist ?? []);
      setError(null);
    } catch {
      setError(t("errorLoading"));
    } finally {
      setLoading(false);
    }
  }, [operationId, t]);

  useEffect(() => {
    fetchData();
    timerRef.current = setInterval(fetchData, POLL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchData]);

  /* Accept handler */
  const handleAccept = useCallback(async () => {
    if (!recommendation || !operationId) return;
    setAccepting(true);
    try {
      const updated = await api.post<OrientRecommendation>(
        `/operations/${operationId}/recommendations/${recommendation.id}/accept`,
      );
      setRecommendation(updated);
    } catch {
      // silently fail
    } finally {
      setAccepting(false);
    }
  }, [recommendation, operationId]);

  /* Derived: confidence score */
  const confidence = recommendation?.confidence ?? 0;
  const confColor = confidenceColor(confidence);
  const confLabel =
    confidence >= 0.75
      ? t("highConfidence")
      : confidence >= 0.5
        ? t("mediumConfidence")
        : t("lowConfidence");

  /* Derived: recommended technique name */
  const recTechnique = useMemo(() => {
    if (!recommendation?.options?.length) return null;
    return recommendation.options.find(
      (o) => o.techniqueId === recommendation.recommendedTechniqueId,
    );
  }, [recommendation]);

  /* Derived: confidence breakdown bars */
  const breakdownBars: BreakdownBar[] = useMemo(() => {
    // C5ISR Readiness: average C5ISR health across domains
    const c5isrAvg =
      dashboard?.c5isr && dashboard.c5isr.length > 0
        ? dashboard.c5isr.reduce((s, d) => s + (d.healthPct ?? 0), 0) /
          dashboard.c5isr.length /
          100
        : 0.5;

    // Framework/Technique Match: use recommendation confidence as proxy
    const frameworkMatch = recommendation?.confidence ?? 0.5;

    // Noise/Detection Risk: inversely proportional to noise
    const noiseRaw = dashboard?.opsec?.noise10min ?? 0;
    const noiseScore = Math.max(0, 1 - noiseRaw / 100);

    // Target Profile Match: use success rate from dashboard operation
    const targetMatch = (dashboard?.operation?.successRate ?? 50) / 100;

    // OPSEC Viability: derived from detection risk (inverse of noise risk)
    const opsecViability = Math.max(
      0,
      1 - (dashboard?.opsec?.eventCount ?? 0) / 50,
    );

    return [
      { label: "C5ISR READINESS", value: c5isrAvg, color: "var(--color-accent)" },
      {
        label: "FRAMEWORK / TECHNIQUE MATCH",
        value: frameworkMatch,
        color: "var(--color-success)",
      },
      {
        label: "NOISE / DETECTION RISK",
        value: noiseScore,
        color: "var(--color-warning)",
      },
      {
        label: "TARGET PROFILE MATCH",
        value: targetMatch,
        color: "#06B6D4",
      },
      {
        label: "OPSEC VIABILITY SCORE",
        value: opsecViability,
        color: "#F97316",
      },
    ];
  }, [dashboard, recommendation]);

  /* Derived: noise & risk for matrix */
  const noisePct = dashboard?.opsec?.noise10min ?? 0;
  const riskPct = (dashboard?.operation?.threatLevel ?? 0) * 10; // 0-10 -> 0-100
  const curRow = noiseToRow(noisePct);
  const curCol = riskToCol(riskPct);
  const curAction = MATRIX[curRow][curCol];

  /* Loading state */
  if (loading && !recommendation && !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-athena-text-tertiary">
          {t("title")}...
        </p>
      </div>
    );
  }

  /* Error state */
  if (error && !recommendation && !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-athena-error">
          {t("errorLoading")}
        </p>
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-4">
      {/* Section label */}
      <h2
        className="font-mono uppercase text-athena-text-secondary text-[10px] font-semibold tracking-widest"
      >
        AI DECISION ENGINE
      </h2>

      {/* Two-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Column: Confidence Breakdown */}
        <div
          className="rounded-[var(--radius)] flex flex-col gap-5 bg-athena-surface border border-[#FFFFFF08] px-6 py-5"
        >
          {/* Header */}
          <div className="flex flex-col gap-1">
            <span
              className="font-mono uppercase tracking-widest text-athena-text-tertiary text-[10px]"
            >
              {t("confidenceBreakdown")}
            </span>
            <span
              className="font-mono text-athena-text-tertiary text-[11px]"
            >
              {t("confidenceSubtitle")}
            </span>
          </div>

          {/* Big score */}
          <div className="flex flex-col items-center gap-1 py-4">
            <span
              className="font-mono athena-tabular-nums text-4xl font-bold"
              style={{ color: confColor }}
            >
              {confidence.toFixed(2)}
            </span>
            <span
              className="font-mono text-xs uppercase tracking-wider"
              style={{ color: confColor }}
            >
              {confLabel}
            </span>
          </div>

          {/* 5 Progress bars */}
          <div className="flex flex-col gap-3">
            {breakdownBars.map((bar) => (
              <div key={bar.label} className="flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span
                    className="font-mono uppercase tracking-widest text-athena-text-tertiary text-[10px]"
                  >
                    {bar.label}
                  </span>
                  <span
                    className="font-mono text-xs athena-tabular-nums"
                    style={{ color: bar.color }}
                  >
                    {bar.value.toFixed(2)}
                  </span>
                </div>
                <ProgressBar value={bar.value} color={bar.color} />
              </div>
            ))}
          </div>

          {/* Recommended Action card */}
          <div
            className="flex flex-col gap-2 mt-auto rounded-[var(--radius)] px-4 py-3 bg-athena-accent-bg border border-[var(--color-accent)]/20"
          >
            <span
              className="font-mono uppercase tracking-widest text-athena-text-tertiary text-[10px]"
            >
              {t("recommendedAction")}
            </span>
            <span className="font-mono text-sm font-semibold text-athena-text-light">
              {recTechnique?.techniqueName ?? t("noTechnique")}
            </span>
            <span className="font-mono text-xs text-athena-text-secondary">
              {recTechnique?.reasoning ??
                recommendation?.situationAssessment ??
                t("noAssessment")}
            </span>
            {/* Buttons */}
            <div className="flex gap-2 mt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleAccept}
                disabled={
                  accepting || recommendation?.accepted === true
                }
                className="uppercase tracking-wider"
              >
                {accepting ? t("accepting") : t("accept")}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                className="uppercase tracking-wider text-athena-text-secondary"
              >
                {t("override")}
              </Button>
            </div>
          </div>
        </div>

        {/* Right Column: Noise x Risk Matrix */}
        <div
          className="rounded-[var(--radius)] flex flex-col gap-5 bg-athena-surface border border-[#FFFFFF08] px-6 py-5"
        >
          {/* Header */}
          <div className="flex flex-col gap-1">
            <span
              className="font-mono uppercase tracking-widest text-athena-text-tertiary text-[10px]"
            >
              {t("noiseRiskMatrix")}
            </span>
            <span
              className="font-mono text-athena-text-tertiary text-[11px]"
            >
              {t("matrixSubtitle")}
            </span>
          </div>

          {/* Matrix grid */}
          <div className="flex gap-2">
            {/* Y-axis label */}
            <div className="flex flex-col items-center justify-center mr-1">
              <span
                className="font-mono uppercase tracking-widest text-athena-text-tertiary text-[9px]"
                style={{
                  writingMode: "vertical-lr",
                  transform: "rotate(180deg)",
                }}
              >
                {t("noiseAxisLabel")}
              </span>
            </div>

            <div className="flex flex-col gap-1 flex-1">
              {/* Column headers */}
              <div className="grid grid-cols-[40px_repeat(4,1fr)] gap-1">
                <div /> {/* spacer for row label column */}
                {RISK_COLS.map((col) => (
                  <div
                    key={col}
                    className="flex items-center justify-center"
                  >
                    <span
                      className="font-mono uppercase tracking-wider text-athena-text-tertiary text-[9px]"
                    >
                      {col}
                    </span>
                  </div>
                ))}
              </div>

              {/* Matrix rows */}
              {NOISE_ROWS.map((rowLabel, rowIdx) => (
                <div
                  key={rowLabel}
                  className="grid grid-cols-[40px_repeat(4,1fr)] gap-1"
                >
                  {/* Row label */}
                  <div className="flex items-center justify-center">
                    <span
                      className="font-mono uppercase tracking-wider text-athena-text-tertiary text-[9px]"
                    >
                      {rowLabel}
                    </span>
                  </div>

                  {/* Cells */}
                  {RISK_COLS.map((_, colIdx) => {
                    const action = MATRIX[rowIdx][colIdx];
                    const isCurrent =
                      rowIdx === curRow && colIdx === curCol;
                    return (
                      <div
                        key={colIdx}
                        className={`
                          flex items-center justify-center rounded-[var(--radius)] py-3
                          ${actionBg(action)}
                          ${isCurrent ? "ring-2 ring-white/70 scale-105 shadow-lg z-10" : ""}
                          transition-all duration-300
                        `}
                      >
                        <span
                          className="font-mono text-xs font-bold uppercase"
                          style={{
                            color: actionTextColor(action),
                          }}
                        >
                          {action}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ))}

              {/* X-axis label */}
              <div className="flex justify-center mt-1">
                <span
                  className="font-mono uppercase tracking-widest text-athena-text-tertiary text-[9px]"
                >
                  {t("riskAxisLabel")}
                </span>
              </div>
            </div>
          </div>

          {/* Current Position card */}
          <div
            className="rounded-[var(--radius)] p-4 flex flex-col gap-2 mt-auto bg-black/20"
            style={{
              border: `1px solid ${actionBorderColor(curAction)}`,
            }}
          >
            <span
              className="font-mono uppercase tracking-widest text-athena-text-tertiary text-[10px]"
            >
              {t("currentPosition")}
            </span>
            <div className="flex gap-4">
              <div className="flex flex-col gap-0.5">
                <span
                  className="font-mono uppercase tracking-wider text-athena-text-tertiary text-[9px]"
                >
                  {t("noiseLabel")}
                </span>
                <span className="font-mono text-sm athena-tabular-nums text-athena-text-light">
                  {noisePct.toFixed(0)}%
                </span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span
                  className="font-mono uppercase tracking-wider text-athena-text-tertiary text-[9px]"
                >
                  {t("riskLabel")}
                </span>
                <span className="font-mono text-sm athena-tabular-nums text-athena-text-light">
                  {riskPct.toFixed(0)}%
                </span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span
                  className="font-mono uppercase tracking-wider text-athena-text-tertiary text-[9px]"
                >
                  {t("actionLabel")}
                </span>
                <span
                  className="font-mono text-sm font-bold"
                  style={{ color: actionTextColor(curAction) }}
                >
                  {curAction}
                </span>
              </div>
            </div>
            <span className="font-mono text-xs text-athena-text-secondary">
              {curAction === "GO"
                ? "Safe to proceed with current technique."
                : curAction === "CAUTION"
                  ? "Proceed with increased monitoring."
                  : curAction === "HOLD"
                    ? "Pause operations and reassess."
                    : "Abort current operation immediately."}
            </span>
          </div>
        </div>
      </div>

      {/* Recommendation History */}
      {history.length > 0 && (
        <div
          className="rounded-[var(--radius)] flex flex-col gap-3 bg-athena-surface border border-[#FFFFFF08] px-6 py-5"
        >
          <span
            className="font-mono uppercase tracking-widest text-athena-text-tertiary text-[10px]"
          >
            {tRec("history")}
          </span>
          <div className="flex flex-col gap-1 max-h-[240px] overflow-y-auto">
            {history.map((rec) => {
              const topOption = rec.options?.[0];
              const cColor = confidenceColor(rec.confidence);
              return (
                <div
                  key={rec.id}
                  className="flex items-center gap-3 px-3 py-2 rounded-[var(--radius)] hover:bg-athena-elevated transition-colors"
                >
                  {/* Confidence dot */}
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: cColor }}
                  />
                  {/* Timestamp */}
                  <span
                    className="font-mono text-[11px] shrink-0 athena-tabular-nums text-athena-text-tertiary"
                  >
                    {new Date(rec.createdAt).toLocaleTimeString("en-US", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                      hour12: false,
                    })}
                  </span>
                  {/* Technique */}
                  <span
                    className="font-mono text-xs truncate flex-1 text-athena-text-secondary"
                  >
                    {topOption?.techniqueName ??
                      rec.recommendedTechniqueId}
                  </span>
                  {/* Confidence */}
                  <span
                    className="font-mono text-xs shrink-0 athena-tabular-nums"
                    style={{ color: cColor }}
                  >
                    {rec.confidence.toFixed(2)}
                  </span>
                  {/* Accepted badge */}
                  {rec.accepted === true && (
                    <span
                      className="font-mono text-[10px] px-2 py-0.5 rounded-[var(--radius)] shrink-0 bg-athena-success-bg text-athena-success"
                    >
                      ACCEPTED
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty history state */}
      {history.length === 0 && !loading && (
        <div
          className="rounded-[var(--radius)] flex items-center justify-center bg-athena-surface border border-[#FFFFFF08] px-6 py-5"
        >
          <span className="font-mono text-xs text-athena-text-tertiary">
            {tRec("noHistory")}
          </span>
        </div>
      )}
    </section>
  );
}
