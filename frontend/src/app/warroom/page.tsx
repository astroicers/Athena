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
import { ReconBlock } from "@/components/warroom/ReconBlock";
import { OODATimelineBlock } from "@/components/warroom/OODATimelineBlock";
import { DirectiveInput } from "@/components/warroom/DirectiveInput";
import { MissionObjective } from "@/components/warroom/MissionObjective";
import { StatusPanel } from "@/components/warroom/StatusPanel";
import type { OODATimelineEntry } from "@/types/ooda";

/* ── Constants ── */

const POLL_MS = 15_000;

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

/* ── Main Content ── */

function WarRoomContent() {
  const t = useTranslations("WarRoom");
  const operationId = useOperationId();

  const [dashboard, setDashboard] = useState<OodaDashboard | null>(null);
  const [timeline, setTimeline] = useState<OODATimelineEntry[]>([]);
  const [autoMode, setAutoMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // WebSocket + C5ISR data hook
  const ws = useWebSocket(operationId);
  const { domains, constraints, override } = useC5ISRData(operationId, ws);

  const fetchData = useCallback(async () => {
    if (!operationId) return;
    try {
      const [dashData, timelineData] = await Promise.allSettled([
        api.get<OodaDashboard>(
          `/operations/${operationId}/ooda/dashboard`,
        ),
        api.get<OODATimelineEntry[]>(
          `/operations/${operationId}/ooda/timeline`,
        ),
      ]);

      if (dashData.status === "fulfilled" && dashData.value) {
        setDashboard(dashData.value);
      }
      if (timelineData.status === "fulfilled" && timelineData.value) {
        setTimeline(
          Array.isArray(timelineData.value) ? timelineData.value : [],
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

  // Build iteration list from dashboard
  const iterations = dashboard?.recentIterations ?? (dashboard?.latestIteration ? [dashboard.latestIteration] : []);
  const reconEntries = timeline.filter((e) => e.iterationNumber === 0);

  // Constraint banner data
  const bannerData = {
    active: (constraints?.hardLimits?.length ?? 0) > 0,
    messages: constraints?.hardLimits?.map((l) => l.suggestedAction) ?? [],
    domains: constraints?.hardLimits?.map((l) => l.domain) ?? [],
  };

  // Noise/Risk from dashboard (fallback to safe values)
  const noiseLevel = 32; // TODO: wire from opsec metrics
  const riskLevel = "LOW"; // TODO: wire from recommendation
  const matrixAction = "GO"; // TODO: wire from recommendation
  const confidence = 0.78; // TODO: wire from recommendation

  // Directive handler
  const handleDirective = useCallback(
    async (directive: string) => {
      if (!operationId || !dashboard?.latestIteration) return;
      try {
        await api.post(
          `/operations/${operationId}/ooda/${dashboard.latestIteration.id}/directive`,
          { directive },
        );
        fetchData();
      } catch {
        // silent — API may not support this yet
      }
    },
    [operationId, dashboard, fetchData],
  );

  if (loading && !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-athena-text-tertiary">
          {t("title")}...
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-athena-bg">
      {/* Constraint Banner */}
      <ConstraintBanner constraints={bannerData} onOverride={override} />

      {/* Two-column layout: Timeline + Status */}
      <div className="flex flex-1 min-h-0">
        {/* Main: Vertical Campaign Timeline */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="font-mono text-xs font-bold text-athena-text-tertiary uppercase tracking-widest">
                CAMPAIGN TIMELINE
              </h2>
              {dashboard && (
                <span className="font-mono text-xs text-athena-accent font-bold">
                  OODA #{dashboard.iterationCount}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setAutoMode(!autoMode)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-[var(--radius)] text-xs font-mono font-semibold transition-colors ${
                  autoMode
                    ? "bg-athena-accent-bg text-athena-accent border border-[var(--color-accent)]/25"
                    : "bg-athena-surface text-athena-text-tertiary border border-[var(--color-border)]"
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${autoMode ? "bg-athena-accent" : "bg-athena-text-tertiary"}`} />
                {autoMode ? "AUTO" : "MANUAL"}
              </button>
            </div>
          </div>

          {/* Recon Block */}
          {reconEntries.length > 0 && (
            <ReconBlock entries={reconEntries} />
          )}

          {/* OODA Iteration Blocks */}
          {iterations.map((iter, idx) => {
            const isCurrent = idx === iterations.length - 1 && !iter.completedAt;
            return (
              <div key={iter.id}>
                {/* Connector line */}
                {idx > 0 || reconEntries.length > 0 ? (
                  <div className="flex justify-center py-1">
                    <div className="w-px h-4 bg-athena-border" />
                  </div>
                ) : null}

                {/* OODA Block */}
                <OODATimelineBlock
                  iteration={iter}
                  c5isrDomains={domains}
                  constraints={constraints ?? undefined}
                  isCurrent={isCurrent}
                />

                {/* Directive Input (after completed iterations) */}
                {iter.completedAt && (
                  <div className="mt-2">
                    <DirectiveInput
                      iterationId={iter.id}
                      autoMode={autoMode}
                      onToggleAutoMode={() => setAutoMode(!autoMode)}
                      onSubmit={handleDirective}
                    />
                  </div>
                )}
              </div>
            );
          })}

          {/* Connector to Mission */}
          {iterations.length > 0 && (
            <div className="flex justify-center py-1">
              <div className="w-px h-4 bg-athena-border" />
            </div>
          )}

          {/* Mission Objective */}
          <MissionObjective
            objective="Domain Admin on corp.local"
            targetsCompromised={iterations.filter((i) => i.completedAt).length}
            targetsTotal={5}
          />
        </div>

        {/* Right: Status Panel */}
        <StatusPanel
          c5isrDomains={domains}
          noiseLevel={noiseLevel}
          riskLevel={riskLevel}
          matrixAction={matrixAction}
          confidence={confidence}
        />
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
          <p className="text-sm font-mono text-athena-text-tertiary">
            Loading War Room...
          </p>
        </div>
      }
    >
      <WarRoomContent />
    </Suspense>
  );
}
