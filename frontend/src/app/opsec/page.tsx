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

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { useOPSEC } from "@/hooks/useOPSEC";
import { api } from "@/lib/api";
import {
  TimeSeriesChart,
  type TimeSeriesLine,
} from "@/components/ui/TimeSeriesChart";
import { PageHeader } from "@/components/layout/PageHeader";

/* ── Types ── */

interface OpsecTimeSeriesPoint {
  ts: string;
  totalNoise: number;
  eventCount: number;
}

type LogSeverity = "info" | "success" | "warning" | "error" | "critical";

interface LogEntry {
  id: string;
  timestamp: string;
  severity: LogSeverity;
  source: string;
  message: string;
  operation_id: string | null;
  technique_id: string | null;
}

interface PaginatedLogs {
  items: LogEntry[];
  total: number;
  page: number;
  page_size: number;
}

/* ── Color helpers ── */

function noiseScoreColor(value: number): string {
  if (value > 70) return "#ef4444"; // red
  if (value >= 40) return "#eab308"; // yellow
  return "#22c55e"; // green
}

function noiseScoreLabel(value: number, t: ReturnType<typeof useTranslations<"OPSEC">>): string {
  if (value > 70) return t("high");
  if (value >= 40) return t("moderate");
  return t("low");
}

function detectionRiskColor(value: number): string {
  if (value > 0.5) return "#ef4444";
  if (value >= 0.25) return "#eab308";
  return "#22c55e";
}

function detectionRiskLabel(
  value: number,
  t: ReturnType<typeof useTranslations<"OPSEC">>,
): string {
  if (value > 0.5) return `${t("high")} - ${t("aboveThreshold")}`;
  if (value >= 0.25) return `${t("moderate")} - ${t("aboveThreshold")}`;
  return `${t("low")} - ${t("belowThreshold")}`;
}

function severityDotColor(severity: LogSeverity): string {
  switch (severity) {
    case "critical":
      return "#ef4444"; // red
    case "error":
      return "#ef4444"; // red
    case "warning":
      return "#eab308"; // yellow
    case "success":
      return "#22c55e"; // green
    default:
      return "#3b82f6"; // blue = info / success
  }
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");
    return `${hh}:${mm}:${ss}`;
  } catch {
    return iso;
  }
}

/** Filter log entries to only OPSEC-relevant ones. */
function isOpsecEvent(entry: LogEntry): boolean {
  const src = entry.source?.toLowerCase() ?? "";
  const msg = entry.message?.toLowerCase() ?? "";
  return (
    src.includes("opsec") ||
    msg.includes("opsec") ||
    msg.includes("noise") ||
    msg.includes("detection") ||
    msg.includes("exposure") ||
    entry.severity === "critical" ||
    entry.severity === "error"
  );
}

/* ── Skeleton ── */

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-4 animate-pulse">
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-24 rounded border border-athena-border bg-athena-surface"
          />
        ))}
      </div>
      <div className="h-[140px] rounded border border-athena-border bg-athena-surface" />
      <div className="h-48 rounded border border-athena-border bg-athena-surface" />
    </div>
  );
}

/* ── Metric Cards ── */

function NoiseScoreCard({
  value,
  t,
}: {
  value: number;
  t: ReturnType<typeof useTranslations<"OPSEC">>;
}) {
  const color = noiseScoreColor(value);
  const label = noiseScoreLabel(value, t);
  return (
    <div className="rounded-md bg-[#111827] border border-[#1f2937] p-4 flex flex-col gap-2">
      <p className="font-mono text-xs uppercase tracking-wider text-athena-text-secondary">
        {t("noiseScore")}
      </p>
      <p className="font-mono text-3xl font-bold" style={{ color }}>
        {value}
      </p>
      <p className="font-mono text-xs uppercase tracking-wider" style={{ color }}>
        {label}
      </p>
      {/* Indicator bar */}
      <div className="h-1 rounded-full bg-[#1f2937] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(value, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function DetectionRiskCard({
  value,
  t,
}: {
  value: number;
  t: ReturnType<typeof useTranslations<"OPSEC">>;
}) {
  const color = detectionRiskColor(value);
  const label = detectionRiskLabel(value, t);
  const pct = Math.min(value * 100, 100);
  return (
    <div className="rounded-md bg-[#111827] border border-[#1f2937] p-4 flex flex-col gap-2">
      <p className="font-mono text-xs uppercase tracking-wider text-athena-text-secondary">
        {t("detectionRisk")}
      </p>
      <p className="font-mono text-3xl font-bold" style={{ color }}>
        {value.toFixed(2)}
      </p>
      <p className="font-mono text-xs" style={{ color }}>
        {label}
      </p>
      <div className="h-1 rounded-full bg-[#1f2937] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function ExposureCountCard({
  value,
  t,
}: {
  value: number;
  t: ReturnType<typeof useTranslations<"OPSEC">>;
}) {
  const color = value > 5 ? "#ef4444" : value > 2 ? "#eab308" : "#22c55e";
  return (
    <div className="rounded-md bg-[#111827] border border-[#1f2937] p-4 flex flex-col gap-2">
      <p className="font-mono text-xs uppercase tracking-wider text-athena-text-secondary">
        {t("exposureCount")}
      </p>
      <p className="font-mono text-3xl font-bold" style={{ color }}>
        {value}
      </p>
      <p className="font-mono text-xs uppercase tracking-wider text-athena-text-secondary">
        {t("activeExposures")}
      </p>
    </div>
  );
}

function NoiseBudgetCard({
  remaining,
  total,
  t,
}: {
  remaining: number;
  total: number;
  t: ReturnType<typeof useTranslations<"OPSEC">>;
}) {
  const pct = total > 0 ? Math.round((remaining / total) * 100) : 0;
  const color = pct > 50 ? "#22c55e" : pct > 20 ? "#eab308" : "#ef4444";
  return (
    <div className="rounded-md bg-[#111827] border border-[#1f2937] p-4 flex flex-col gap-2">
      <p className="font-mono text-xs uppercase tracking-wider text-athena-text-secondary">
        {t("noiseBudget")}
      </p>
      <p className="font-mono text-3xl font-bold" style={{ color }}>
        {pct}%
      </p>
      <p className="font-mono text-xs uppercase tracking-wider text-athena-text-secondary">
        {t("remainingBudget")}
      </p>
      {/* Progress bar */}
      <div className="h-1 rounded-full bg-[#1f2937] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

/* ── OPSEC Events List ── */

function OpsecEventRow({
  entry,
  t,
}: {
  entry: LogEntry;
  t: ReturnType<typeof useTranslations<"OPSEC">>;
}) {
  const dotColor = severityDotColor(entry.severity);
  return (
    <div className="flex items-center gap-3 py-2 border-b border-[#1f2937] last:border-0">
      {/* Severity dot */}
      <span
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{ backgroundColor: dotColor }}
      />
      {/* Timestamp */}
      <span className="font-mono text-xs text-athena-text-secondary w-16 flex-shrink-0">
        {formatTimestamp(entry.timestamp)}
      </span>
      {/* Message */}
      <span className="font-mono text-xs text-athena-text flex-1 truncate">
        {entry.message}
      </span>
      {/* View button */}
      <button
        className="font-mono text-xs text-athena-text-secondary hover:text-athena-text transition-colors flex-shrink-0 uppercase tracking-wider"
        onClick={() => {/* no-op for now */}}
        type="button"
      >
        {t("view")}
      </button>
    </div>
  );
}

function OpsecEventsList({
  operationId,
  t,
}: {
  operationId: string | null;
  t: ReturnType<typeof useTranslations<"OPSEC">>;
}) {
  const [events, setEvents] = useState<LogEntry[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);

  const fetchEvents = useCallback(async () => {
    if (!operationId) return;
    setLoadingEvents(true);
    try {
      const data = await api.get<PaginatedLogs>(
        `/operations/${operationId}/logs?page_size=20`,
      );
      if (data?.items) {
        const filtered = data.items.filter(isOpsecEvent);
        setEvents(filtered);
      }
    } catch {
      // silently fail — events are supplementary
    } finally {
      setLoadingEvents(false);
    }
  }, [operationId]);

  useEffect(() => {
    fetchEvents();
    const timer = setInterval(fetchEvents, 30_000);
    return () => clearInterval(timer);
  }, [fetchEvents]);

  return (
    <div className="rounded border border-athena-border bg-athena-surface p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <p className="font-mono text-xs text-athena-text-secondary uppercase tracking-wider">
          {t("events")}
        </p>
        {events.length > 0 && (
          <span className="font-mono text-xs bg-[#1f2937] text-athena-text-secondary px-2 py-0.5 rounded uppercase tracking-wider">
            {t("eventCount", { count: events.length })}
          </span>
        )}
      </div>

      {loadingEvents && events.length === 0 ? (
        <div className="space-y-2 animate-pulse">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-7 rounded bg-athena-border/20" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="flex items-center justify-center py-8">
          <span className="text-xs font-mono text-athena-text-secondary">
            {t("noEvents")}
          </span>
        </div>
      ) : (
        <div>
          {events.map((entry) => (
            <OpsecEventRow key={entry.id} entry={entry} t={t} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Page ── */

export default function OpsecPage() {
  const t = useTranslations("OPSEC");
  const operationId = useOperationId();
  const { opsec, loading, error } = useOPSEC(operationId);
  const [timeSeriesData, setTimeSeriesData] = useState<OpsecTimeSeriesPoint[]>([]);

  const fetchTimeSeries = useCallback(async () => {
    if (!operationId) return;
    try {
      const data = await api.get<OpsecTimeSeriesPoint[]>(
        `/operations/${operationId}/metrics/time-series?metric=opsec&granularity=1min`,
      );
      if (Array.isArray(data)) setTimeSeriesData(data);
    } catch {
      // fall back to single-point display
    }
  }, [operationId]);

  useEffect(() => {
    fetchTimeSeries();
    const timer = setInterval(fetchTimeSeries, 30_000);
    return () => clearInterval(timer);
  }, [fetchTimeSeries]);

  const noiseTrendLines: TimeSeriesLine[] = useMemo(() => {
    if (timeSeriesData.length > 0) {
      return [
        {
          id: "noise",
          label: t("noiseTrend"),
          data: timeSeriesData.map((p) => ({
            timestamp: p.ts,
            value: p.totalNoise,
          })),
          color: "var(--color-accent)",
        },
      ];
    }
    if (!opsec) return [];
    const now = new Date().toISOString();
    return [
      {
        id: "noise",
        label: t("noiseTrend"),
        data: [{ timestamp: now, value: opsec.noiseScore }],
        color: "var(--color-accent)",
      },
    ];
  }, [timeSeriesData, opsec, t]);

  /* ── Error state ── */
  if (error && !opsec) {
    return (
      <div className="flex flex-col h-full athena-grid-bg">
        <PageHeader title={t("title")} />
        <div className="flex-1 flex items-center justify-center">
          <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-widest">
            {t("noData")}
          </span>
        </div>
      </div>
    );
  }

  /* ── Loading state ── */
  if (loading && !opsec) {
    return (
      <div className="flex flex-col h-full athena-grid-bg">
        <PageHeader title={t("title")} />
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full athena-grid-bg">
      <PageHeader title={t("title")} />

      <div className="flex-1 overflow-y-auto">
        {/* Top: 4-card Metric Row */}
        <div className="mx-4 my-3 grid grid-cols-4 gap-3">
          {opsec ? (
            <>
              <NoiseScoreCard value={opsec.noiseScore} t={t} />
              <DetectionRiskCard value={opsec.detectionRisk} t={t} />
              <ExposureCountCard value={opsec.exposureCount} t={t} />
              <NoiseBudgetCard
                remaining={opsec.noiseBudgetRemaining}
                total={opsec.noiseBudgetTotal}
                t={t}
              />
            </>
          ) : (
            Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-24 rounded-md bg-[#111827] border border-[#1f2937] animate-pulse"
              />
            ))
          )}
        </div>

        {/* Middle: Noise Score Trend */}
        <div className="mx-4 mt-3">
          <div className="rounded border border-athena-border bg-athena-surface p-3">
            <p className="font-mono text-xs text-athena-text-secondary mb-2 uppercase tracking-wider">
              {t("noiseTrend")}
            </p>
            <TimeSeriesChart
              lines={noiseTrendLines}
              height={120}
              yMin={0}
              yMax={100}
            />
          </div>
        </div>

        {/* Bottom: OPSEC Events */}
        <div className="mx-4 mt-3 mb-4">
          <OpsecEventsList operationId={operationId} t={t} />
        </div>
      </div>
    </div>
  );
}
