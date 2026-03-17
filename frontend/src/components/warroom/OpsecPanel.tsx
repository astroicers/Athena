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
import { useOPSEC } from "@/hooks/useOPSEC";
import { api } from "@/lib/api";
import { Button } from "@/components/atoms/Button";
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
  if (score >= 80) return "#ef4444"; // critical red
  if (score >= 50) return "#f59e0b"; // warning orange
  return "#22c55e"; // success green
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
  if (risk >= 70) return "#ef4444";
  if (risk >= 40) return "#f59e0b";
  return "#22c55e";
}

function severityDotColor(severity: string): string {
  switch (severity) {
    case "critical":
      return "#ef4444";
    case "error":
      return "#f59e0b";
    case "warning":
      return "#eab308";
    case "success":
      return "#22c55e";
    default:
      return "#6b7280";
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
      className="flex-1 min-w-0 rounded-athena-md p-4 flex flex-col gap-1 bg-[#111827] border border-[#1f2937]"
      style={{
        height: 120,
      }}
    >
      <span
        className="font-mono text-2xl font-bold athena-tabular-nums leading-tight"
        style={{ color }}
      >
        {value}
      </span>
      <span className="font-mono text-xs uppercase font-semibold text-[#9ca3af]" style={{ letterSpacing: "1px" }}>
        {label}
      </span>
      {subLabel && (
        <span className="font-mono text-[10px] text-[#9ca3af]">
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

/* ── OpsecPanel ── */

export function OpsecPanel({ operationId }: { operationId: string }) {
  const t = useTranslations("OPSEC");
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
        color: "#f59e0b",
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
        <p className="text-sm font-mono text-[#9ca3af]">
          {t("title")}...
        </p>
      </div>
    );
  }

  // -- Error state --
  if (error && !opsec) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-[#EF4444]">
          {t("errorLoading")}
        </p>
      </div>
    );
  }

  // -- No data state --
  if (!opsec) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-[#9ca3af]">
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
    <section className="flex flex-col gap-4">
      {/* Section label */}
      <h2
        className="font-mono uppercase"
        style={{ color: "#6b7280", fontSize: 10, fontWeight: 600, letterSpacing: "2px" }}
      >
        OPERATIONAL SECURITY STATUS
      </h2>

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
          color={opsec.exposureCount > 0 ? "#f59e0b" : "#22c55e"}
        />
        <MetricCard
          label={t("noiseBudget")}
          value={`${budgetPct}%`}
          subLabel={t("remainingBudget")}
          color={budgetPct < 20 ? "#ef4444" : budgetPct < 50 ? "#f59e0b" : "#22c55e"}
          progressValue={opsec.noiseBudgetRemaining}
          progressMax={opsec.noiseBudgetTotal}
        />
      </div>

      {/* Noise Trend Chart */}
      <div
        className="rounded-athena-md p-4 flex flex-col gap-2 bg-[#111827] border border-[#1f2937]"
        style={{
          height: 220,
        }}
      >
        <div className="flex items-center justify-between">
          <span
            className="font-mono uppercase font-semibold"
            style={{ color: "#e5e7eb", fontSize: 11, letterSpacing: "1px" }}
          >
            NOISE SCORE TREND
          </span>
          <span
            className="font-mono"
            style={{ color: "#6b7280", fontSize: 10 }}
          >
            Last 6 hours
          </span>
        </div>
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
        className="rounded-athena-md flex flex-col flex-1 min-h-[200px] bg-[#111827] border border-[#1f2937]"
      >
        {/* Header */}
        <div className="flex items-center gap-2" style={{ height: 40, padding: "0 16px" }}>
          <span
            className="font-mono uppercase font-semibold"
            style={{ color: "#e5e7eb", fontSize: 11, letterSpacing: "1px" }}
          >
            OPSEC EVENTS
          </span>
          <span
            className="font-mono text-[10px]"
            style={{ color: "#ef4444", backgroundColor: "#ef444420", borderRadius: 3, padding: "2px 8px" }}
          >
            {t("eventCount", { count: events.length })}
          </span>
        </div>

        {/* Event list */}
        <div className="flex-1 overflow-y-auto">
          {events.length === 0 ? (
            <p className="text-xs font-mono py-4 text-center text-[#9ca3af]">
              {t("noEvents")}
            </p>
          ) : (
            events.map((event) => (
              <div
                key={event.id}
                className="flex items-center gap-3"
                style={{ height: 36, padding: "0 16px", borderBottom: "1px solid #1f2937" }}
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
                  className="font-mono text-[11px] shrink-0 athena-tabular-nums text-[#9ca3af]"
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
                  className="font-mono text-xs truncate flex-1 text-[#6b7280]"
                >
                  {event.message}
                </span>
                {/* View button */}
                <Button
                  variant="secondary"
                  size="sm"
                  className="text-[10px] px-2 py-0.5 shrink-0 text-[#f59e0b]"
                >
                  {t("view")}
                </Button>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
