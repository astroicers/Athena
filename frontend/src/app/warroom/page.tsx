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

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { api } from "@/lib/api";
import type { LogEntry } from "@/types/log";

/* ── Constants ── */

const POLL_MS = 15_000;
const LOG_PAGE_SIZE = 30;

/* ── Types ── */

interface OodaIteration {
  id: string;
  iterationNumber: number;
  phase: string;
  observeSummary?: string;
  orientSummary?: string;
  decideSummary?: string;
  actSummary?: string;
  startedAt: string;
  completedAt?: string;
}

interface OodaDashboard {
  currentPhase: string;
  iterationCount: number;
  latestIteration?: OodaIteration;
  recentIterations?: OodaIteration[];
}

/* ── OODA phase colors ── */

function phaseColor(phase: string): string {
  switch (phase?.toLowerCase()) {
    case "observe":
      return "#3B82F6";
    case "orient":
      return "#A855F7";
    case "decide":
      return "#FFA500";
    case "act":
      return "#22C55E";
    default:
      return "#6B7280";
  }
}

function phaseBg(phase: string): string {
  switch (phase?.toLowerCase()) {
    case "observe":
      return "#3B82F610";
    case "orient":
      return "#A855F710";
    case "decide":
      return "#FFA50010";
    case "act":
      return "#22C55E10";
    default:
      return "#FFFFFF05";
  }
}

/* ── Severity colors for log entries ── */

function logSeverityColor(severity: string): string {
  switch (severity) {
    case "critical":
    case "error":
      return "#EF4444";
    case "warning":
      return "#FFA500";
    case "success":
      return "#22C55E";
    default:
      return "#6B7280";
  }
}

/* ── OODA Phase Card ── */

function PhaseCard({
  phase,
  summary,
  active,
}: {
  phase: string;
  summary?: string;
  active: boolean;
}) {
  const color = phaseColor(phase);
  const bg = phaseBg(phase);

  return (
    <div
      className="rounded-md flex flex-col gap-2"
      style={{
        backgroundColor: bg,
        border: active ? `1px solid ${color}40` : "1px solid #FFFFFF08",
        padding: "12px 14px",
      }}
    >
      <div className="flex items-center gap-2">
        {active && (
          <span
            className="w-2 h-2 rounded-full shrink-0 animate-pulse"
            style={{ backgroundColor: color }}
          />
        )}
        <span
          className="font-mono text-[10px] font-bold uppercase tracking-wider"
          style={{ color: active ? color : "#FFFFFF40" }}
        >
          {phase}
        </span>
      </div>
      {summary && (
        <p
          className="font-mono text-[9px] leading-relaxed"
          style={{ color: "#FFFFFFA0" }}
        >
          {summary}
        </p>
      )}
      {!summary && !active && (
        <p
          className="font-mono text-[9px]"
          style={{ color: "#FFFFFF20" }}
        >
          Awaiting data...
        </p>
      )}
    </div>
  );
}

/* ── Main Content ── */

function WarRoomContent() {
  const t = useTranslations("WarRoom");
  const operationId = useOperationId();

  const [dashboard, setDashboard] = useState<OodaDashboard | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    if (!operationId) return;
    try {
      const [dashData, logData] = await Promise.allSettled([
        api.get<OodaDashboard>(
          `/operations/${operationId}/ooda/dashboard`,
        ),
        api.get<LogEntry[]>(
          `/operations/${operationId}/logs?page_size=${LOG_PAGE_SIZE}`,
        ),
      ]);

      if (dashData.status === "fulfilled" && dashData.value) {
        setDashboard(dashData.value);
      }
      if (logData.status === "fulfilled" && Array.isArray(logData.value)) {
        setLogs(logData.value);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [operationId]);

  useEffect(() => {
    fetchData();
    timerRef.current = setInterval(fetchData, POLL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchData]);

  const currentPhase = dashboard?.currentPhase ?? "idle";
  const iteration = dashboard?.latestIteration;
  const phases = ["observe", "orient", "decide", "act"];

  if (loading && !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
          {t("title")}...
        </p>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{ backgroundColor: "#0A0E17" }}
    >
      {/* Two-column layout */}
      <div className="flex flex-1 gap-4 p-4 min-h-0">
        {/* Left panel: OODA Loop */}
        <div
          className="flex-1 rounded-lg flex flex-col gap-3 overflow-y-auto"
          style={{
            backgroundColor: "#111827",
            padding: 16,
          }}
        >
          <span
            className="font-mono text-xs font-bold"
            style={{ color: "#FFFFFF60" }}
          >
            OODA LOOP
          </span>

          {phases.map((phase) => (
            <PhaseCard
              key={phase}
              phase={phase}
              active={currentPhase.toLowerCase() === phase}
              summary={
                iteration
                  ? (iteration[
                      `${phase}Summary` as keyof OodaIteration
                    ] as string | undefined)
                  : undefined
              }
            />
          ))}

          {/* Iteration counter */}
          {dashboard && (
            <div
              className="rounded-md mt-2"
              style={{
                backgroundColor: "#FFFFFF05",
                border: "1px solid #FFFFFF08",
                padding: "10px 14px",
              }}
            >
              <div className="flex items-center justify-between">
                <span
                  className="font-mono text-[9px] uppercase tracking-wider"
                  style={{ color: "#FFFFFF40" }}
                >
                  {t("sidePanel.iteration")}
                </span>
                <span
                  className="font-mono text-sm font-bold athena-tabular-nums"
                  style={{ color: "#FFFFFF" }}
                >
                  #{dashboard.iterationCount}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Right panel: Action Log */}
        <div
          className="flex flex-col gap-3 overflow-y-auto"
          style={{
            width: 360,
            backgroundColor: "#111827",
            borderRadius: 8,
            padding: 16,
          }}
        >
          <span
            className="font-mono text-xs font-bold"
            style={{ color: "#FFFFFF60" }}
          >
            ACTION LOG
          </span>

          {logs.length === 0 ? (
            <div className="flex items-center justify-center flex-1">
              <p
                className="font-mono text-[10px]"
                style={{ color: "#FFFFFF30" }}
              >
                {t("sidePanel.waitingForLogs")}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {logs.map((entry) => (
                <div
                  key={entry.id}
                  className="rounded flex flex-col gap-1"
                  style={{
                    backgroundColor: "#FFFFFF05",
                    padding: "10px 12px",
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-1.5 h-1.5 rounded-full shrink-0"
                        style={{
                          backgroundColor: logSeverityColor(entry.severity),
                        }}
                      />
                      <span
                        className="font-mono text-[8px] font-bold uppercase tracking-wider"
                        style={{
                          color: logSeverityColor(entry.severity),
                        }}
                      >
                        {entry.severity}
                      </span>
                    </div>
                    <span
                      className="font-mono text-[8px] athena-tabular-nums"
                      style={{ color: "#FFFFFF30" }}
                    >
                      {new Date(entry.timestamp).toLocaleTimeString("en-US", {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                        hour12: false,
                      })}
                    </span>
                  </div>
                  <p
                    className="font-mono text-[9px] leading-relaxed"
                    style={{ color: "#FFFFFFA0" }}
                  >
                    {entry.message}
                  </p>
                  {entry.source && (
                    <span
                      className="font-mono text-[8px]"
                      style={{ color: "#FFFFFF25" }}
                    >
                      Source: {entry.source}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Page wrapper ── */

export default function WarRoomPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
            Loading War Room...
          </p>
        </div>
      }
    >
      <WarRoomContent />
    </Suspense>
  );
}
