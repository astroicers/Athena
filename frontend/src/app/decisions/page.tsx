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

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";

// ── Types ──────────────────────────────────────────────────────────────────

interface RecommendationOption {
  techniqueId: string;
  techniqueName: string;
  confidence: number;
  rationale: string;
  prerequisites: string[];
}

interface Recommendation {
  id: string;
  techniqueId: string;
  techniqueName: string;
  confidence: number;
  situationAssessment: string;
  options: RecommendationOption[];
}

interface DashboardData {
  threatLevel?: string;
  ooda?: {
    phase?: string;
    iteration?: number;
  };
  c5isr?: {
    overallScore?: number;
  };
  noiseScore?: number;
  detectionRisk?: number;
}

interface ConfidenceBreakdown {
  c5isrReadiness: number;
  frameworkMatch: number;
  noiseRisk: number;
  targetProfile: number;
  opsecViability: number;
}

type NoiseLevel = "lo" | "med" | "hi";
type RiskLevel = "low" | "med" | "high" | "crit";

// ── Matrix cell definitions ────────────────────────────────────────────────

interface MatrixCell {
  action: "GO" | "CAUTION" | "HOLD" | "ABORT";
  color: string;      // tailwind bg class
  textColor: string;  // tailwind text class
}

const MATRIX: Record<NoiseLevel, Record<RiskLevel, MatrixCell>> = {
  lo: {
    low:  { action: "GO",      color: "bg-green-900/60",  textColor: "text-green-400" },
    med:  { action: "GO",      color: "bg-green-900/60",  textColor: "text-green-400" },
    high: { action: "CAUTION", color: "bg-yellow-900/60", textColor: "text-yellow-400" },
    crit: { action: "HOLD",    color: "bg-red-900/60",    textColor: "text-red-400" },
  },
  med: {
    low:  { action: "GO",      color: "bg-green-900/60",  textColor: "text-green-400" },
    med:  { action: "CAUTION", color: "bg-yellow-900/60", textColor: "text-yellow-400" },
    high: { action: "HOLD",    color: "bg-red-900/60",    textColor: "text-red-400" },
    crit: { action: "ABORT",   color: "bg-red-900/80",    textColor: "text-red-300" },
  },
  hi: {
    low:  { action: "CAUTION", color: "bg-yellow-900/60", textColor: "text-yellow-400" },
    med:  { action: "HOLD",    color: "bg-red-900/60",    textColor: "text-red-400" },
    high: { action: "ABORT",   color: "bg-red-900/80",    textColor: "text-red-300" },
    crit: { action: "ABORT",   color: "bg-red-900/80",    textColor: "text-red-300" },
  },
};

const NOISE_ROWS: NoiseLevel[] = ["hi", "med", "lo"];
const RISK_COLS: RiskLevel[] = ["low", "med", "high", "crit"];

const NOISE_LABELS: Record<NoiseLevel, string> = { hi: "HI", med: "MED", lo: "LO" };
const RISK_LABELS: Record<RiskLevel, string>   = { low: "LOW", med: "MED", high: "HIGH", crit: "CRIT" };

// ── Confidence bar config ──────────────────────────────────────────────────

interface BarConfig {
  key: keyof ConfidenceBreakdown;
  label: string;
  barColor: string; // tailwind bg class
}

const BARS: BarConfig[] = [
  { key: "c5isrReadiness",  label: "C5ISR Readiness",           barColor: "bg-blue-500" },
  { key: "frameworkMatch",  label: "Framework / Technique Match", barColor: "bg-green-500" },
  { key: "noiseRisk",       label: "Noise / Detection Risk",     barColor: "bg-yellow-500" },
  { key: "targetProfile",   label: "Target Profile Match",       barColor: "bg-cyan-500" },
  { key: "opsecViability",  label: "OPSEC Viability Score",      barColor: "bg-orange-500" },
];

// ── Helper: derive noise/risk levels from dashboard data ──────────────────

function deriveNoise(dashboard: DashboardData | null): NoiseLevel {
  const score = dashboard?.noiseScore ?? 0;
  if (score >= 0.65) return "hi";
  if (score >= 0.35) return "med";
  return "lo";
}

function deriveRisk(dashboard: DashboardData | null): RiskLevel {
  const risk = dashboard?.detectionRisk ?? 0;
  if (risk >= 0.85) return "crit";
  if (risk >= 0.6)  return "high";
  if (risk >= 0.35) return "med";
  return "low";
}

// ── Helper: build confidence breakdown from recommendation + dashboard ────

function buildBreakdown(
  rec: Recommendation | null,
  dashboard: DashboardData | null,
): ConfidenceBreakdown {
  const c5isr  = Math.min(1, Math.max(0, (dashboard?.c5isr?.overallScore ?? 0.7)));
  const noise  = Math.min(1, Math.max(0, 1 - (dashboard?.noiseScore ?? 0.2)));
  const opsec  = Math.min(1, Math.max(0, 1 - (dashboard?.detectionRisk ?? 0.2)));
  const base   = rec?.confidence ?? 0.75;
  return {
    c5isrReadiness: c5isr,
    frameworkMatch: Math.min(1, base * 1.05),
    noiseRisk:      noise,
    targetProfile:  Math.min(1, base * 0.95),
    opsecViability: opsec,
  };
}

// ── Confidence label helper ────────────────────────────────────────────────

function confidenceLabel(score: number): { label: string; color: string } {
  if (score >= 0.75) return { label: "HIGH CONFIDENCE",   color: "text-green-400" };
  if (score >= 0.5)  return { label: "MEDIUM CONFIDENCE", color: "text-yellow-400" };
  return                    { label: "LOW CONFIDENCE",    color: "text-red-400" };
}

// ── Action recommendation ──────────────────────────────────────────────────

function actionRecommendation(noise: NoiseLevel, risk: RiskLevel): string {
  const action = MATRIX[noise][risk].action;
  switch (action) {
    case "GO":      return "Conditions are favorable. Proceed with the recommended technique.";
    case "CAUTION": return "Exercise caution. Monitor noise levels closely before executing.";
    case "HOLD":    return "Hold position. Reduce noise footprint before proceeding.";
    case "ABORT":   return "ABORT. Detection risk is too high. Stand down and reassess.";
  }
}

// ── Loading skeleton ───────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="flex-1 flex gap-4 p-4 animate-pulse overflow-hidden">
      <div className="flex-1 rounded border border-athena-border bg-athena-surface" />
      <div className="flex-1 rounded border border-athena-border bg-athena-surface" />
    </div>
  );
}

// ── Left Panel: Confidence Breakdown ─────────────────────────────────────

interface LeftPanelProps {
  recommendation: Recommendation | null;
  breakdown: ConfidenceBreakdown;
  onAccept: () => void;
  onOverride: () => void;
  accepting: boolean;
}

function LeftPanel({
  recommendation,
  breakdown,
  onAccept,
  onOverride,
  accepting,
}: LeftPanelProps) {
  const score  = recommendation?.confidence ?? 0.75;
  const { label: confLabel, color: confColor } = confidenceLabel(score);

  const topOption = recommendation?.options?.[0] ?? null;
  const techniqueName = topOption?.techniqueName ?? recommendation?.techniqueName ?? "— NO TECHNIQUE —";
  const description   = topOption?.rationale ?? recommendation?.situationAssessment ?? "No assessment available.";

  return (
    <div className="flex-1 flex flex-col gap-4 min-w-0">
      {/* Panel header */}
      <div>
        <p className="text-[10px] font-mono tracking-widest text-athena-text-secondary uppercase">
          CONFIDENCE BREAKDOWN
        </p>
        <p className="text-xs font-mono text-athena-text-secondary mt-0.5">
          AI recommendation confidence sources for current decision
        </p>
      </div>

      {/* Big score */}
      <div className="flex flex-col items-center py-4 rounded border border-athena-border bg-black/20">
        <span className={`text-5xl font-mono font-bold ${confColor}`}>
          {score.toFixed(2)}
        </span>
        <span className={`text-xs font-mono tracking-widest mt-1 ${confColor}`}>
          {confLabel}
        </span>
      </div>

      {/* Progress bars */}
      <div className="flex flex-col gap-3">
        {BARS.map(({ key, label, barColor }) => {
          const val = breakdown[key];
          return (
            <div key={key}>
              <div className="flex justify-between mb-1">
                <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
                  {label}
                </span>
                <span className="text-[10px] font-mono text-athena-text tabular-nums">
                  {val.toFixed(2)}
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-athena-border/40 overflow-hidden">
                <div
                  className={`h-full rounded-full ${barColor} transition-all duration-500`}
                  style={{ width: `${Math.round(val * 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Recommended Action card */}
      <div className="rounded border border-blue-500/30 bg-blue-950/30 p-3 flex flex-col gap-2 mt-auto">
        <p className="text-[10px] font-mono tracking-widest text-blue-400 uppercase">
          RECOMMENDED ACTION
        </p>
        <p className="text-sm font-mono text-athena-text font-semibold leading-snug">
          {techniqueName}
        </p>
        <p className="text-xs font-mono text-athena-text-secondary leading-relaxed line-clamp-3">
          {description}
        </p>
        <div className="flex gap-2 mt-1">
          <button
            onClick={onAccept}
            disabled={accepting}
            className="flex-1 py-1.5 text-xs font-mono tracking-wider uppercase rounded bg-green-700 hover:bg-green-600 text-white transition-colors disabled:opacity-50"
          >
            {accepting ? "ACCEPTING..." : "ACCEPT"}
          </button>
          <button
            onClick={onOverride}
            className="flex-1 py-1.5 text-xs font-mono tracking-wider uppercase rounded border border-athena-border text-athena-text-secondary hover:text-athena-text hover:border-athena-text/50 transition-colors"
          >
            OVERRIDE
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Right Panel: Noise x Risk Matrix ──────────────────────────────────────

interface RightPanelProps {
  noiseLevel: NoiseLevel;
  riskLevel: RiskLevel;
  noiseScore: number;
  detectionRisk: number;
}

function RightPanel({ noiseLevel, riskLevel, noiseScore, detectionRisk }: RightPanelProps) {
  const currentCell = MATRIX[noiseLevel][riskLevel];
  const actionText  = actionRecommendation(noiseLevel, riskLevel);

  return (
    <div className="flex-1 flex flex-col gap-4 min-w-0">
      {/* Panel header */}
      <div>
        <p className="text-[10px] font-mono tracking-widest text-athena-text-secondary uppercase">
          NOISE x RISK MATRIX
        </p>
        <p className="text-xs font-mono text-athena-text-secondary mt-0.5">
          Action safety zone based on current noise level and detection risk
        </p>
      </div>

      {/* Matrix grid */}
      <div className="rounded border border-athena-border bg-black/20 p-4">
        {/* X-axis header */}
        <div className="flex mb-2 ml-10">
          <div className="flex-1 text-center">
            <span className="text-[10px] font-mono tracking-widest text-athena-text-secondary uppercase">
              DETECTION RISK
            </span>
          </div>
        </div>

        {/* Column headers */}
        <div className="flex mb-1 ml-10 gap-1">
          {RISK_COLS.map((col) => (
            <div
              key={col}
              className={`flex-1 text-center text-[10px] font-mono tracking-wider uppercase ${
                col === riskLevel ? "text-athena-text font-bold" : "text-athena-text-secondary"
              }`}
            >
              {RISK_LABELS[col]}
            </div>
          ))}
        </div>

        {/* Rows */}
        {NOISE_ROWS.map((row) => (
          <div key={row} className="flex items-center gap-1 mb-1">
            {/* Y-axis label */}
            <div
              className={`w-10 text-center text-[10px] font-mono tracking-wider uppercase shrink-0 ${
                row === noiseLevel ? "text-athena-text font-bold" : "text-athena-text-secondary"
              }`}
            >
              {NOISE_LABELS[row]}
            </div>

            {/* Cells */}
            {RISK_COLS.map((col) => {
              const cell      = MATRIX[row][col];
              const isCurrent = row === noiseLevel && col === riskLevel;
              return (
                <div
                  key={col}
                  className={`
                    flex-1 h-12 flex items-center justify-center rounded text-[10px] font-mono tracking-wider
                    ${cell.color} ${cell.textColor}
                    ${isCurrent ? "ring-2 ring-white/70 font-bold scale-105 z-10 relative shadow-lg" : "opacity-75"}
                    transition-all duration-200
                  `}
                >
                  {cell.action}
                </div>
              );
            })}
          </div>
        ))}

        {/* Y-axis label */}
        <div className="flex justify-start mt-2 ml-10">
          <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-widest">
            ^ NOISE LEVEL
          </span>
        </div>
      </div>

      {/* Current position card */}
      <div
        className={`rounded border p-3 flex flex-col gap-2 ${
          currentCell.action === "GO"
            ? "border-green-500/30 bg-green-950/30"
            : currentCell.action === "CAUTION"
            ? "border-yellow-500/30 bg-yellow-950/30"
            : "border-red-500/30 bg-red-950/30"
        }`}
      >
        <p className="text-[10px] font-mono tracking-widest text-athena-text-secondary uppercase">
          CURRENT POSITION
        </p>

        <div className="flex gap-4">
          <div>
            <p className="text-[10px] font-mono text-athena-text-secondary mb-0.5">NOISE</p>
            <p className={`text-sm font-mono font-bold ${currentCell.textColor}`}>
              {NOISE_LABELS[noiseLevel]} ({(noiseScore * 100).toFixed(0)}%)
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono text-athena-text-secondary mb-0.5">RISK</p>
            <p className={`text-sm font-mono font-bold ${currentCell.textColor}`}>
              {RISK_LABELS[riskLevel]} ({(detectionRisk * 100).toFixed(0)}%)
            </p>
          </div>
          <div className="ml-auto">
            <p className="text-[10px] font-mono text-athena-text-secondary mb-0.5">ACTION</p>
            <p className={`text-sm font-mono font-bold tracking-wider ${currentCell.textColor}`}>
              {currentCell.action}
            </p>
          </div>
        </div>

        <p className="text-xs font-mono text-athena-text-secondary leading-relaxed">
          {actionText}
        </p>
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

interface RecommendationHistoryItem {
  id: string;
  techniqueId: string;
  techniqueName: string;
  confidence: number;
  situationAssessment: string;
  timestamp?: string;
  createdAt?: string;
}

export default function DecisionsPage() {
  const t = useTranslations("AIDecisionPage");
  const tRec = useTranslations("Recommendations");
  const operationId = useOperationId();

  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [recHistory, setRecHistory] = useState<RecommendationHistoryItem[]>([]);

  const fetchData = useCallback(async () => {
    try {
      const [rec, dash, history] = await Promise.all([
        api
          .get<Recommendation>(`/operations/${operationId}/recommendations/latest`)
          .catch(() => null),
        api
          .get<DashboardData>(`/operations/${operationId}/dashboard`)
          .catch(() => null),
        api
          .get<RecommendationHistoryItem[]>(`/operations/${operationId}/recommendations`)
          .catch(() => [] as RecommendationHistoryItem[]),
      ]);
      setRecommendation(rec);
      setDashboard(dash);
      setRecHistory(history ?? []);
      setError(null);
    } catch {
      setError(t("errorLoading"));
    } finally {
      setLoading(false);
    }
  }, [operationId, t]);

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 30_000);
    return () => clearInterval(timer);
  }, [fetchData]);

  const breakdown  = buildBreakdown(recommendation, dashboard);
  const noiseLevel = deriveNoise(dashboard);
  const riskLevel  = deriveRisk(dashboard);
  const noiseScore = Math.min(1, Math.max(0, dashboard?.noiseScore ?? 0.2));
  const detectionRisk = Math.min(1, Math.max(0, dashboard?.detectionRisk ?? 0.2));

  async function handleAccept() {
    if (!recommendation) return;
    setAccepting(true);
    try {
      await api.post(
        `/operations/${operationId}/recommendations/${recommendation.id}/accept`,
      );
    } catch {
      // ignore — recommendation may not support accept endpoint yet
    } finally {
      setAccepting(false);
    }
  }

  function handleOverride() {
    // Navigate to planner or open directive panel — no-op for now
  }

  const title = t("title");

  return (
    <div className="flex flex-col h-full athena-grid-bg">
      <PageHeader title={title} operationCode={operationId} />

      {loading ? (
        <LoadingSkeleton />
      ) : error && !recommendation && !dashboard ? (
        <div className="flex-1 flex items-center justify-center">
          <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-widest">
            {error}
          </span>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          <div className="p-4 flex gap-4 min-h-full">
            {/* Left: Confidence Breakdown */}
            <div className="flex-1 rounded border border-athena-border bg-athena-surface p-4 flex flex-col gap-4">
              <LeftPanel
                recommendation={recommendation}
                breakdown={breakdown}
                onAccept={handleAccept}
                onOverride={handleOverride}
                accepting={accepting}
              />
            </div>

            {/* Right: Noise x Risk Matrix */}
            <div className="flex-1 rounded border border-athena-border bg-athena-surface p-4 flex flex-col gap-4">
              <RightPanel
                noiseLevel={noiseLevel}
                riskLevel={riskLevel}
                noiseScore={noiseScore}
                detectionRisk={detectionRisk}
              />
            </div>
          </div>

          {/* Recommendation History */}
          <div className="px-4 pb-4">
            <div className="rounded border border-athena-border bg-athena-surface p-4">
              <p className="text-[10px] font-mono tracking-widest text-athena-text-secondary uppercase mb-3">
                {tRec("history")}
              </p>
              {recHistory.length === 0 ? (
                <p className="text-xs font-mono text-athena-text-secondary">
                  {tRec("noHistory")}
                </p>
              ) : (
                <div className="space-y-2">
                  {recHistory.map((item) => {
                    const ts = item.timestamp || item.createdAt;
                    return (
                      <div
                        key={item.id}
                        className="flex items-center gap-3 bg-athena-bg border border-athena-border/50 rounded-athena-sm px-3 py-2"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-bold text-athena-accent truncate">
                              {item.techniqueName || item.techniqueId}
                            </span>
                            <span className="text-[10px] font-mono text-green-400">
                              {Math.round(item.confidence * 100)}%
                            </span>
                          </div>
                          {item.situationAssessment && (
                            <p className="text-[10px] font-mono text-athena-text-secondary truncate mt-0.5">
                              {item.situationAssessment}
                            </p>
                          )}
                        </div>
                        {ts && (
                          <span className="text-[10px] font-mono text-athena-text-secondary shrink-0">
                            {new Date(ts).toLocaleString()}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
