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
import { OPSECMiniBar } from "@/components/opsec/OPSECMiniBar";
import {
  TimeSeriesChart,
  type TimeSeriesLine,
} from "@/components/ui/TimeSeriesChart";
import { PageHeader } from "@/components/layout/PageHeader";

interface OpsecTimeSeriesPoint {
  ts: string;
  totalNoise: number;
  eventCount: number;
}

/* ── Skeleton ── */

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-4 animate-pulse">
      {/* Metrics row */}
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-24 rounded border border-athena-border bg-athena-surface"
          />
        ))}
      </div>
      {/* Chart placeholder */}
      <div className="h-[140px] rounded border border-athena-border bg-athena-surface" />
      {/* Events placeholder */}
      <div className="h-48 rounded border border-athena-border bg-athena-surface" />
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
    // Use historical time-series data when available, otherwise fall back to current value
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
        {/* Top: OPSEC Metrics */}
        <OPSECMiniBar operationId={operationId} />

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
          <div className="rounded border border-athena-border bg-athena-surface p-3">
            <p className="font-mono text-xs text-athena-text-secondary mb-2 uppercase tracking-wider">
              {t("events")}
            </p>
            <div className="flex items-center justify-center py-8">
              <span className="text-xs font-mono text-athena-text-secondary">
                {t("noEvents")}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
