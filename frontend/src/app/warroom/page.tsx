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

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { api } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useC5ISRData } from "@/hooks/useC5ISRData";
import { ConstraintBanner } from "@/components/layout/ConstraintBanner";
import { OODAFlowDiagram } from "@/components/c5isr/OODAFlowDiagram";
import { C5ISRHealthGrid } from "@/components/c5isr/C5ISRHealthGrid";
import { ConstraintStatusPanel } from "@/components/c5isr/ConstraintStatusPanel";
import { C5ISRDomainDetail } from "@/components/c5isr/C5ISRDomainDetail";
import { OpsecPanel } from "@/components/warroom/OpsecPanel";
import { DecisionPanel } from "@/components/warroom/DecisionPanel";
import type { LogEntry } from "@/types/log";
import type { C5ISRDomain } from "@/types/enums";
import type { DomainReport } from "@/types/c5isr";

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
      return "#3b82f6";
    case "orient":
      return "#A855F7";
    case "decide":
      return "#FBBF24";
    case "act":
      return "#22C55E";
    default:
      return "#6b728060";
  }
}

function phaseBg(phase: string): string {
  switch (phase?.toLowerCase()) {
    case "observe":
      return "#3b82f610";
    case "orient":
      return "#A855F710";
    case "decide":
      return "#FBBF2410";
    case "act":
      return "#22C55E10";
    default:
      return "#ffffff05";
  }
}

/* ── Severity colors for log entries ── */

function logSeverityColor(severity: string): string {
  switch (severity) {
    case "critical":
    case "error":
      return "#EF4444";
    case "warning":
      return "#FBBF24";
    case "success":
      return "#22C55E";
    default:
      return "#6b7280";
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
      className="rounded-athena-md flex flex-col gap-2 px-3.5 py-3"
      style={{
        backgroundColor: bg,
        border: active ? `1px solid ${color}40` : "1px solid #1f2937",
      }}
    >
      <div className="flex items-center gap-2">
        {active && (
          <span
            className="w-1.5 h-1.5 rounded-full shrink-0 animate-pulse"
            style={{ backgroundColor: color }}
          />
        )}
        <span
          className="font-mono text-[10px] font-bold uppercase tracking-wider"
          style={{ color: active ? color : "#ffffff40" }}
        >
          {phase}
        </span>
      </div>
      {summary && (
        <p className="font-mono text-[9px] leading-relaxed text-[#ffffff50]">
          {summary}
        </p>
      )}
      {!summary && !active && (
        <p className="font-mono text-[9px]" style={{ color: "#ffffff20" }}>
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
  const [selectedDomain, setSelectedDomain] = useState<C5ISRDomain | null>(
    null,
  );
  const [selectedReport, setSelectedReport] = useState<DomainReport | null>(
    null,
  );
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // WebSocket + C5ISR data hook
  const ws = useWebSocket(operationId);
  const { domains, constraints, override, fetchReport } = useC5ISRData(operationId, ws);

  const fetchData = useCallback(async () => {
    if (!operationId) return;
    try {
      const [dashData, logData] = await Promise.allSettled([
        api.get<OodaDashboard>(
          `/operations/${operationId}/ooda/dashboard`,
        ),
        api.get<{ items: LogEntry[] }>(
          `/operations/${operationId}/logs?page_size=${LOG_PAGE_SIZE}`,
        ),
      ]);

      if (dashData.status === "fulfilled" && dashData.value) {
        setDashboard(dashData.value);
      }
      if (logData.status === "fulfilled" && logData.value?.items) {
        setLogs(
          Array.isArray(logData.value.items) ? logData.value.items : [],
        );
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

  // Fetch domain report on selection
  useEffect(() => {
    if (selectedDomain) {
      fetchReport(selectedDomain).then(setSelectedReport);
    } else {
      setSelectedReport(null);
    }
  }, [selectedDomain, fetchReport]);

  const currentPhase = dashboard?.currentPhase ?? "idle";
  const iteration = dashboard?.latestIteration;
  const phases = ["observe", "orient", "decide", "act"];

  // Constraint banner data
  const bannerData = {
    active: (constraints?.hardLimits?.length ?? 0) > 0,
    messages: constraints?.hardLimits?.map((l) => l.suggestedAction) ?? [],
    domains: constraints?.hardLimits?.map((l) => l.domain) ?? [],
  };

  // Find selected domain object
  const selectedDomainObj = selectedDomain
    ? domains.find((d) => d.domain === selectedDomain) ?? null
    : null;

  if (loading && !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-[#9ca3af]">
          {t("title")}...
        </p>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full overflow-hidden bg-[#0A0E17]"
    >
      {/* Constraint Banner */}
      <ConstraintBanner constraints={bannerData} onOverride={override} />

      {/* Three-column layout */}
      <div className="flex flex-1 gap-4 py-4 px-6 min-h-0">
        {/* Left panel: OODA Loop */}
        <div
          className="rounded-athena-md flex flex-col gap-3 overflow-y-auto shrink-0 bg-[#111827] p-4"
          style={{
            width: 200,
          }}
        >
          <span
            className="font-mono font-bold"
            style={{ color: "#ffffff60", fontSize: 10 }}
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
              className="rounded-athena-md mt-2 px-3 py-2.5"
              style={{
                backgroundColor: "#ffffff05",
                border: "1px solid #ffffff08",
              }}
            >
              <div className="flex items-center justify-between">
                <span
                  className="font-mono uppercase tracking-wider"
                  style={{ color: "#ffffff40", fontSize: 8 }}
                >
                  {t("sidePanel.iteration")}
                </span>
                <span
                  className="font-mono font-bold athena-tabular-nums"
                  style={{ color: "#ffffff", fontSize: 14 }}
                >
                  #{dashboard.iterationCount}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Center panel: C5ISR + Mermaid Flow + Constraints */}
        <div className="flex-1 flex flex-col gap-4 overflow-y-auto min-w-0">
          {/* Mermaid Decision Flow Diagram */}
          <OODAFlowDiagram
            dashboard={dashboard}
            constraints={constraints}
            c5isrDomains={domains}
          />

          {/* C5ISR Domain Health Grid */}
          <C5ISRHealthGrid
            domains={domains}
            onDomainClick={(d) =>
              setSelectedDomain(selectedDomain === d ? null : d)
            }
          />

          {/* Domain Detail (expandable) */}
          {selectedDomainObj && (
            <C5ISRDomainDetail
              domain={selectedDomainObj}
              report={selectedReport}
              onClose={() => setSelectedDomain(null)}
            />
          )}

          {/* Constraint Status Panel */}
          <ConstraintStatusPanel
            constraints={constraints}
            onOverride={override}
          />

          {/* OPSEC Status Panel */}
          <OpsecPanel operationId={operationId} />

          {/* AI Decision Engine Panel */}
          <DecisionPanel operationId={operationId} />
        </div>

        {/* Right panel: Action Log */}
        <div
          className="flex flex-col gap-3 overflow-y-auto shrink-0 bg-[#111827] rounded-athena-md p-4"
          style={{
            width: 300,
          }}
        >
          <span className="font-mono font-bold" style={{ color: "#ffffff60", fontSize: 10 }}>
            ACTION LOG
          </span>

          {logs.length === 0 ? (
            <div className="flex items-center justify-center flex-1">
              <p className="font-mono text-[10px] text-[#ffffff25]">
                {t("sidePanel.waitingForLogs")}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {logs.map((entry) => (
                <div
                  key={entry.id}
                  className="flex flex-col gap-1 px-3 py-2.5"
                  style={{
                    backgroundColor: "#0a0e17",
                    border: "1px solid #1f2937",
                    borderRadius: 6,
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
                      style={{ color: "#ffffff25" }}
                    >
                      {new Date(entry.timestamp).toLocaleTimeString("en-US", {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                        hour12: false,
                      })}
                    </span>
                  </div>
                  <p className="font-mono text-[9px] leading-relaxed text-[#ffffff50]">
                    {entry.message}
                  </p>
                  {entry.source && (
                    <span className="font-mono text-[8px]" style={{ color: "#ffffff25" }}>
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
          <p className="text-sm font-mono text-[#9ca3af]">
            Loading War Room...
          </p>
        </div>
      }
    >
      <WarRoomContent />
    </Suspense>
  );
}
