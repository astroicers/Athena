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
import { useOPSEC } from "@/hooks/useOPSEC";
import { api } from "@/lib/api";
import {
  TimeSeriesChart,
  type TimeSeriesLine,
  type TimeSeriesDataPoint,
} from "@/components/ui/TimeSeriesChart";
import type { LogEntry } from "@/types/log";

/* ── Constants ── */

const EVENTS_POLL_MS = 30_000;
const TREND_POLL_MS = 30_000;
const EVENTS_PAGE_SIZE = 20;

/* ── Color helpers ── */

function noiseScoreColor(score: number): string {
  if (score >= 80) return "#EF4444"; // critical red
  if (score >= 50) return "#FFA500"; // warning orange
  return "#22C55E"; // success green
}

function noiseScoreLabel(
  score: number,
  t: (key: string) => string,
): string {
  if (score >= 80) return t("critical");
  if (score >= 50) return t("high");
  if (score >= 30) return t("moderate");
  return t("low");
}

function detectionRiskColor(risk: number): string {
  if (risk >= 70) return "#EF4444";
  if (risk >= 40) return "#FFA500";
  return "#22C55E";
}

function severityDotColor(severity: string): string {
  switch (severity) {
    case "critical":
      return "#EF4444";
    case "error":
      return "#FFA500";
    case "warning":
      return "#EAB308";
    case "success":
      return "#22C55E";
    default:
      return "#6B7280";
  }
}

/* ── Progress Bar ── */

function ProgressBar({
  value,
  max = 100,
  color,
}: {
  value: number;
  max?: number;
  color: string;
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="w-full h-1.5 rounded-full bg-[#1f2937] overflow-hidden mt-2">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

/* ── Metric Card ── */

function MetricCard({
  label,
  value,
  subLabel,
  color,
  progressValue,
  progressMax,
}: {
  label: string;
  value: string;
  subLabel?: string;
  color: string;
  progressValue?: number;
  progressMax?: number;
}) {
  return (
    <div
      className="flex-1 min-w-0 rounded-md p-4 flex flex-col gap-1"
      style={{
        backgroundColor: "#111827",
        border: "1px solid #1f2937",
        height: 120,
      }}
    >
      <span
        className="font-mono text-2xl font-bold athena-tabular-nums leading-tight"
        style={{ color }}
      >
        {value}
      </span>
      <span
        className="font-mono text-xs uppercase tracking-wider"
        style={{ color: "#6B7280" }}
      >
        {label}
      </span>
      {subLabel && (
        <span
          className="font-mono text-[10px]"
          style={{ color: "#6B7280" }}
        >
          {subLabel}
        </span>
      )}
      {progressValue !== undefined && (
        <ProgressBar
          value={progressValue}
          max={progressMax}
          color={color}
        />
      )}
    </div>
  );
}

/* ── Main Page Content (uses hooks that need context) ── */

function OpsecContent() {
  const t = useTranslations("OPSEC");
  const operationId = useOperationId();
  const { opsec, loading, error } = useOPSEC(operationId);

  // -- Noise trend time series --
  const [trendData, setTrendData] = useState<TimeSeriesDataPoint[]>([]);
  const trendTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTrend = useCallback(async () => {
    if (!operationId) return;
    try {
      const raw = await api.get<Array<{ ts: string; totalNoise: number }>>(
        `/operations/${operationId}/metrics/time-series?metric=opsec&granularity=1min`,
      );
      if (Array.isArray(raw)) {
        setTrendData(raw.map((r) => ({ timestamp: r.ts, value: r.totalNoise })));
      }
    } catch {
      // Silently fail -- trend chart simply stays empty
    }
  }, [operationId]);

  useEffect(() => {
    fetchTrend();
    trendTimerRef.current = setInterval(fetchTrend, TREND_POLL_MS);
    return () => {
      if (trendTimerRef.current) clearInterval(trendTimerRef.current);
    };
  }, [fetchTrend]);

  const trendLines: TimeSeriesLine[] = useMemo(
    () => [
      {
        id: "noise",
        label: t("noiseScore"),
        data: trendData,
        color: "#FFA500",
      },
    ],
    [trendData, t],
  );

  // -- OPSEC events --
  const [events, setEvents] = useState<LogEntry[]>([]);
  const eventsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchEvents = useCallback(async () => {
    if (!operationId) return;
    try {
      const resp = await api.get<{ items: LogEntry[] }>(
        `/operations/${operationId}/logs?page_size=${EVENTS_PAGE_SIZE}`,
      );
      const data = resp?.items ?? [];
      if (data.length > 0) {
        // Filter for OPSEC-related events
        const opsecEvents = data.filter(
          (e) =>
            e.source?.toLowerCase().includes("opsec") ||
            e.message?.toLowerCase().includes("opsec") ||
            e.message?.toLowerCase().includes("noise") ||
            e.message?.toLowerCase().includes("detection") ||
            e.message?.toLowerCase().includes("exposure"),
        );
        setEvents(opsecEvents.length > 0 ? opsecEvents : data);
      }
    } catch {
      // Silently fail
    }
  }, [operationId]);

  useEffect(() => {
    fetchEvents();
    eventsTimerRef.current = setInterval(fetchEvents, EVENTS_POLL_MS);
    return () => {
      if (eventsTimerRef.current) clearInterval(eventsTimerRef.current);
    };
  }, [fetchEvents]);

  // -- Loading state --
  if (loading && !opsec) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
          {t("title")}...
        </p>
      </div>
    );
  }

  // -- Error state --
  if (error && !opsec) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono" style={{ color: "#EF4444" }}>
          {t("errorLoading")}
        </p>
      </div>
    );
  }

  // -- No data state --
  if (!opsec) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
          {t("noData")}
        </p>
      </div>
    );
  }

  const budgetPct =
    opsec.noiseBudgetTotal > 0
      ? Math.round(
          (opsec.noiseBudgetRemaining / opsec.noiseBudgetTotal) * 100,
        )
      : 0;

  const noiseColor = noiseScoreColor(opsec.noiseScore);
  const riskColor = detectionRiskColor(opsec.detectionRisk);

  return (
    <div className="flex flex-col h-full athena-grid-bg overflow-y-auto">
      <div className="flex flex-col gap-4 p-4 max-w-[1440px] w-full mx-auto">
        {/* Section label */}
        <h1
          className="font-mono uppercase tracking-[2px]"
          style={{ fontSize: 10, color: "#6B7280" }}
        >
          OPERATIONAL SECURITY STATUS
        </h1>

        {/* 4 Metric Cards */}
        <div className="flex gap-4">
          <MetricCard
            label={t("noiseScore")}
            value={String(Math.round(opsec.noiseScore))}
            subLabel={noiseScoreLabel(opsec.noiseScore, t)}
            color={noiseColor}
            progressValue={opsec.noiseScore}
            progressMax={100}
          />
          <MetricCard
            label={t("detectionRisk")}
            value={opsec.detectionRisk.toFixed(1)}
            subLabel={
              opsec.detectionRisk >= 50
                ? t("aboveThreshold")
                : t("belowThreshold")
            }
            color={riskColor}
            progressValue={opsec.detectionRisk}
            progressMax={100}
          />
          <MetricCard
            label={t("exposureCount")}
            value={String(opsec.exposureCount)}
            subLabel={t("activeExposures")}
            color={opsec.exposureCount > 0 ? "#FFA500" : "#22C55E"}
          />
          <MetricCard
            label={t("noiseBudget")}
            value={`${budgetPct}%`}
            subLabel={t("remainingBudget")}
            color={budgetPct < 20 ? "#EF4444" : budgetPct < 50 ? "#FFA500" : "#22C55E"}
            progressValue={opsec.noiseBudgetRemaining}
            progressMax={opsec.noiseBudgetTotal}
          />
        </div>

        {/* Noise Trend Chart */}
        <div
          className="rounded-md p-3 flex flex-col gap-2"
          style={{
            backgroundColor: "#111827",
            border: "1px solid #1f2937",
            height: 220,
          }}
        >
          <span
            className="font-mono uppercase tracking-wider"
            style={{ fontSize: 10, color: "#6B7280" }}
          >
            {t("noiseTrend")}
          </span>
          <div className="flex-1 min-h-0">
            <TimeSeriesChart
              lines={trendLines}
              height={180}
              yMin={0}
              yMax={100}
            />
          </div>
        </div>

        {/* OPSEC Events */}
        <div
          className="rounded-md p-3 flex flex-col gap-2 flex-1 min-h-[200px]"
          style={{
            backgroundColor: "#111827",
            border: "1px solid #1f2937",
          }}
        >
          {/* Header */}
          <div className="flex items-center gap-2">
            <span
              className="font-mono uppercase tracking-wider"
              style={{ fontSize: 10, color: "#6B7280" }}
            >
              {t("events")}
            </span>
            <span
              className="font-mono text-[10px] px-2 py-0.5 rounded"
              style={{
                backgroundColor: "#1f2937",
                color: "#FFA500",
              }}
            >
              {t("eventCount", { count: events.length })}
            </span>
          </div>

          {/* Event list */}
          <div className="flex-1 overflow-y-auto space-y-1">
            {events.length === 0 ? (
              <p
                className="text-xs font-mono py-4 text-center"
                style={{ color: "#6B7280" }}
              >
                {t("noEvents")}
              </p>
            ) : (
              events.map((event) => (
                <div
                  key={event.id}
                  className="flex items-center gap-3 px-2 py-1.5 rounded hover:bg-[#1f2937] transition-colors"
                >
                  {/* Severity dot */}
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{
                      backgroundColor: severityDotColor(event.severity),
                    }}
                  />
                  {/* Timestamp */}
                  <span
                    className="font-mono text-[11px] shrink-0 athena-tabular-nums"
                    style={{ color: "#6B7280" }}
                  >
                    {new Date(event.timestamp).toLocaleTimeString("en-US", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                      hour12: false,
                    })}
                  </span>
                  {/* Message */}
                  <span
                    className="font-mono text-xs truncate flex-1"
                    style={{ color: "#9CA3AF" }}
                  >
                    {event.message}
                  </span>
                  {/* View button */}
                  <button
                    className="font-mono text-[10px] px-2 py-0.5 rounded shrink-0 hover:bg-[#374151] transition-colors"
                    style={{
                      color: "#FFA500",
                      border: "1px solid #374151",
                    }}
                  >
                    {t("view")}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Page wrapper with Suspense ── */

export default function OpsecPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
            Loading OPSEC...
          </p>
        </div>
      }
    >
      <OpsecContent />
    </Suspense>
  );
}
