"use client";

import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { api } from "@/lib/api";
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
      return "bg-green-900/60";
    case "CAUTION":
      return "bg-yellow-900/60";
    case "HOLD":
      return "bg-red-900/60";
    case "ABORT":
      return "bg-red-900/80";
  }
}

function actionTextColor(a: MatrixAction): string {
  switch (a) {
    case "GO":
      return "#22C55E";
    case "CAUTION":
      return "#EAB308";
    case "HOLD":
      return "#EF4444";
    case "ABORT":
      return "#991B1B";
  }
}

function actionBorderColor(a: MatrixAction): string {
  switch (a) {
    case "GO":
      return "#22C55E";
    case "CAUTION":
      return "#EAB308";
    case "HOLD":
      return "#EF4444";
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
  if (score >= 0.75) return "#22C55E";
  if (score >= 0.5) return "#EAB308";
  return "#EF4444";
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
    <div className="w-full h-1.5 rounded-full bg-[#1f2937] overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

/* ── Main Content ── */

function DecisionsContent() {
  const t = useTranslations("AIDecisionPage");
  const tRec = useTranslations("Recommendations");
  const operationId = useOperationId();

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
      { label: "C5ISR READINESS", value: c5isrAvg, color: "#3B82F6" },
      {
        label: "FRAMEWORK / TECHNIQUE MATCH",
        value: frameworkMatch,
        color: "#22C55E",
      },
      {
        label: "NOISE / DETECTION RISK",
        value: noiseScore,
        color: "#EAB308",
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
        <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
          {t("title")}...
        </p>
      </div>
    );
  }

  /* Error state */
  if (error && !recommendation && !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono" style={{ color: "#EF4444" }}>
          {t("errorLoading")}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full athena-grid-bg overflow-y-auto">
      <div className="flex flex-col gap-4 p-4 max-w-[1440px] w-full mx-auto">
        {/* Page title */}
        <h1
          className="font-mono uppercase tracking-[2px]"
          style={{ fontSize: 10, color: "#6B7280" }}
        >
          {t("title")}
        </h1>

        {/* Two-column grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* ─── Left Column: Confidence Breakdown ─── */}
          <div
            className="rounded-lg p-6 flex flex-col gap-5"
            style={{
              backgroundColor: "#111827",
              border: "1px solid rgba(255,255,255,0.03)",
            }}
          >
            {/* Header */}
            <div className="flex flex-col gap-1">
              <span
                className="font-mono uppercase tracking-widest"
                style={{ fontSize: 10, color: "#6B7280" }}
              >
                {t("confidenceBreakdown")}
              </span>
              <span
                className="font-mono"
                style={{ fontSize: 11, color: "#6B7280" }}
              >
                {t("confidenceSubtitle")}
              </span>
            </div>

            {/* Big score */}
            <div className="flex flex-col items-center gap-1 py-4">
              <span
                className="font-mono text-5xl font-bold athena-tabular-nums"
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
                      className="font-mono uppercase tracking-widest"
                      style={{ fontSize: 10, color: "#6B7280" }}
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
              className="rounded-md p-4 flex flex-col gap-2 mt-auto"
              style={{
                border: "1px solid #3B82F6",
                backgroundColor: "rgba(59,130,246,0.05)",
              }}
            >
              <span
                className="font-mono uppercase tracking-widest"
                style={{ fontSize: 10, color: "#6B7280" }}
              >
                {t("recommendedAction")}
              </span>
              <span
                className="font-mono text-sm font-semibold"
                style={{ color: "#FFFFFF" }}
              >
                {recTechnique?.techniqueName ?? t("noTechnique")}
              </span>
              <span
                className="font-mono text-xs"
                style={{ color: "#9CA3AF" }}
              >
                {recTechnique?.reasoning ??
                  recommendation?.situationAssessment ??
                  t("noAssessment")}
              </span>
              {/* Buttons */}
              <div className="flex gap-2 mt-2">
                <button
                  onClick={handleAccept}
                  disabled={
                    accepting || recommendation?.accepted === true
                  }
                  className="font-mono text-xs uppercase tracking-wider px-4 py-1.5 rounded transition-colors disabled:opacity-50"
                  style={{
                    backgroundColor: "#3B82F6",
                    color: "#FFFFFF",
                  }}
                >
                  {accepting ? t("accepting") : t("accept")}
                </button>
                <button
                  className="font-mono text-xs uppercase tracking-wider px-4 py-1.5 rounded transition-colors hover:bg-[#1f2937]"
                  style={{
                    border: "1px solid #374151",
                    color: "#9CA3AF",
                  }}
                >
                  {t("override")}
                </button>
              </div>
            </div>
          </div>

          {/* ─── Right Column: Noise x Risk Matrix ─── */}
          <div
            className="rounded-lg p-6 flex flex-col gap-5"
            style={{
              backgroundColor: "#111827",
              border: "1px solid rgba(255,255,255,0.03)",
            }}
          >
            {/* Header */}
            <div className="flex flex-col gap-1">
              <span
                className="font-mono uppercase tracking-widest"
                style={{ fontSize: 10, color: "#6B7280" }}
              >
                {t("noiseRiskMatrix")}
              </span>
              <span
                className="font-mono"
                style={{ fontSize: 11, color: "#6B7280" }}
              >
                {t("matrixSubtitle")}
              </span>
            </div>

            {/* Matrix grid */}
            <div className="flex gap-2">
              {/* Y-axis label */}
              <div className="flex flex-col items-center justify-center mr-1">
                <span
                  className="font-mono uppercase tracking-widest"
                  style={{
                    fontSize: 9,
                    color: "#6B7280",
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
                        className="font-mono uppercase tracking-wider"
                        style={{ fontSize: 9, color: "#6B7280" }}
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
                        className="font-mono uppercase tracking-wider"
                        style={{ fontSize: 9, color: "#6B7280" }}
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
                            flex items-center justify-center rounded-md py-3
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
                    className="font-mono uppercase tracking-widest"
                    style={{ fontSize: 9, color: "#6B7280" }}
                  >
                    {t("riskAxisLabel")}
                  </span>
                </div>
              </div>
            </div>

            {/* Current Position card */}
            <div
              className="rounded-md p-4 flex flex-col gap-2 mt-auto"
              style={{
                border: `1px solid ${actionBorderColor(curAction)}`,
                backgroundColor: "rgba(0,0,0,0.2)",
              }}
            >
              <span
                className="font-mono uppercase tracking-widest"
                style={{ fontSize: 10, color: "#6B7280" }}
              >
                {t("currentPosition")}
              </span>
              <div className="flex gap-4">
                <div className="flex flex-col gap-0.5">
                  <span
                    className="font-mono uppercase tracking-wider"
                    style={{ fontSize: 9, color: "#6B7280" }}
                  >
                    {t("noiseLabel")}
                  </span>
                  <span
                    className="font-mono text-sm athena-tabular-nums"
                    style={{ color: "#FFFFFF" }}
                  >
                    {noisePct.toFixed(0)}%
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span
                    className="font-mono uppercase tracking-wider"
                    style={{ fontSize: 9, color: "#6B7280" }}
                  >
                    {t("riskLabel")}
                  </span>
                  <span
                    className="font-mono text-sm athena-tabular-nums"
                    style={{ color: "#FFFFFF" }}
                  >
                    {riskPct.toFixed(0)}%
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span
                    className="font-mono uppercase tracking-wider"
                    style={{ fontSize: 9, color: "#6B7280" }}
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
              <span
                className="font-mono text-xs"
                style={{ color: "#9CA3AF" }}
              >
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

        {/* ─── Recommendation History ─── */}
        {history.length > 0 && (
          <div
            className="rounded-lg p-6 flex flex-col gap-3"
            style={{
              backgroundColor: "#111827",
              border: "1px solid rgba(255,255,255,0.03)",
            }}
          >
            <span
              className="font-mono uppercase tracking-widest"
              style={{ fontSize: 10, color: "#6B7280" }}
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
                    className="flex items-center gap-3 px-3 py-2 rounded hover:bg-[#1f2937] transition-colors"
                  >
                    {/* Confidence dot */}
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: cColor }}
                    />
                    {/* Timestamp */}
                    <span
                      className="font-mono text-[11px] shrink-0 athena-tabular-nums"
                      style={{ color: "#6B7280" }}
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
                      className="font-mono text-xs truncate flex-1"
                      style={{ color: "#9CA3AF" }}
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
                        className="font-mono text-[10px] px-2 py-0.5 rounded shrink-0"
                        style={{
                          backgroundColor: "rgba(34,197,94,0.15)",
                          color: "#22C55E",
                        }}
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
            className="rounded-lg p-6 flex items-center justify-center"
            style={{
              backgroundColor: "#111827",
              border: "1px solid rgba(255,255,255,0.03)",
            }}
          >
            <span
              className="font-mono text-xs"
              style={{ color: "#6B7280" }}
            >
              {tRec("noHistory")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Page wrapper with Suspense ── */

export default function DecisionsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
            Loading AI Decision Breakdown...
          </p>
        </div>
      }
    >
      <DecisionsContent />
    </Suspense>
  );
}
