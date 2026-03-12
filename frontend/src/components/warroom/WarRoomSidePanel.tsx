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
import Link from "next/link";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Badge } from "@/components/atoms/Badge";
import { AIDecisionPanel } from "@/components/topology/AIDecisionPanel";
import { RecommendationPanel } from "@/components/ooda/RecommendationPanel";
import { OODATimeline } from "@/components/ooda/OODATimeline";
import { AgentBeacon } from "@/components/data/AgentBeacon";
import { LogEntryRow } from "@/components/data/LogEntryRow";
import { AccordionSection } from "./AccordionSection";
import { LLMDirectiveInput } from "./LLMDirectiveInput";
import type { ConfidenceSource } from "@/components/topology/ConfidenceBreakdown";
import type { OODAPhase, AgentStatus, KillChainStage } from "@/types/enums";
import type { OrientRecommendation } from "@/types/recommendation";
import type { OODATimelineEntry } from "@/types/ooda";
import type { Agent } from "@/types/agent";
import type { LogEntry } from "@/types/log";

interface OODAIteration {
  id: string;
  operationId: string;
  iterationNumber: number;
  phase: string;
  observeSummary: string | null;
  orientSummary: string | null;
  decideSummary: string | null;
  actSummary: string | null;
  recommendationId: string | null;
  techniqueExecutionId: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

interface WarRoomSidePanelProps {
  // AI Decision
  activeTechniqueId: string | null;
  activeEngine: string | null;
  activeStatus: string | null;
  activeTechniqueName: string | null;
  activeKillChainStage: KillChainStage | null;
  activeConfidence: number | null;
  llmThinking: boolean;
  llmBackend: string | null;
  llmLatencyMs: number | null;
  confidenceSources?: ConfidenceSource[];
  noiseLevel?: "low" | "medium" | "high";
  riskLevel?: "low" | "medium" | "high" | "critical";
  // Recommendation
  recommendation: OrientRecommendation | null;
  // OODA
  oodaTimeline: OODATimelineEntry[];
  currentOodaPhase: OODAPhase | null;
  // Agents
  agents: Agent[];
  // Logs
  allLogs: LogEntry[];
  // Directive
  operationId: string;
  onDirectiveSubmit: (directive: string) => Promise<void>;
  onOodaTrigger: () => Promise<void>;
}

export function WarRoomSidePanel({
  activeTechniqueId,
  activeEngine,
  activeStatus,
  activeTechniqueName,
  activeKillChainStage,
  activeConfidence,
  llmThinking,
  llmBackend,
  llmLatencyMs,
  confidenceSources,
  noiseLevel,
  riskLevel,
  recommendation,
  oodaTimeline,
  currentOodaPhase,
  agents,
  allLogs,
  operationId,
  onDirectiveSubmit,
  onOodaTrigger,
}: WarRoomSidePanelProps) {
  const t = useTranslations("WarRoom");
  const [openSection, setOpenSection] = useState<string | null>("aiDecision");
  const [oodaCurrent, setOodaCurrent] = useState<OODAIteration | null>(null);
  const [oodaHistory, setOodaHistory] = useState<OODAIteration[]>([]);
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null);

  const fetchOodaCurrent = useCallback(async () => {
    try {
      const data = await api.get<OODAIteration | null>(
        `/operations/${operationId}/ooda/current`,
      );
      setOodaCurrent(data);
    } catch {
      // silently ignore - endpoint may not be available
    }
  }, [operationId]);

  const fetchOodaHistory = useCallback(async () => {
    try {
      const data = await api.get<OODAIteration[]>(
        `/operations/${operationId}/ooda/history`,
      );
      setOodaHistory(data);
    } catch {
      // silently ignore
    }
  }, [operationId]);

  useEffect(() => {
    fetchOodaCurrent();
    fetchOodaHistory();
  }, [fetchOodaCurrent, fetchOodaHistory]);

  function toggle(id: string) {
    setOpenSection((prev) => (prev === id ? null : id));
  }

  const activeAgentCount = agents.filter(
    (a) => a.status === "alive"
  ).length;

  return (
    <div className="flex flex-col h-full bg-athena-surface">
      {/* Accordion sections — scrollable */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <AccordionSection
          id="aiDecision"
          title={t("sidePanel.aiDecision")}
          summary={`${activeTechniqueName || "—"} • ${activeConfidence ? Math.round(activeConfidence * 100) + "%" : "—"}`}
          isOpen={openSection === "aiDecision"}
          onToggle={() => toggle("aiDecision")}
        >
          <AIDecisionPanel
            activeTechniqueId={activeTechniqueId}
            activeEngine={activeEngine}
            activeStatus={activeStatus}
            activeTechniqueName={activeTechniqueName}
            activeKillChainStage={activeKillChainStage}
            activeConfidence={activeConfidence}
            llmThinking={llmThinking}
            llmBackend={llmBackend}
            llmLatencyMs={llmLatencyMs}
            confidenceSources={confidenceSources}
            noiseLevel={noiseLevel}
            riskLevel={riskLevel}
          />
        </AccordionSection>

        <AccordionSection
          id="recommendation"
          title={t("sidePanel.recommendation")}
          summary={recommendation?.options?.[0]?.techniqueName || "—"}
          isOpen={openSection === "recommendation"}
          onToggle={() => toggle("recommendation")}
        >
          <RecommendationPanel recommendation={recommendation} />
        </AccordionSection>

        <AccordionSection
          id="ooda"
          title={t("sidePanel.oodaTimeline")}
          summary={`Phase: ${currentOodaPhase || "idle"}`}
          isOpen={openSection === "ooda"}
          onToggle={() => toggle("ooda")}
        >
          <OODATimeline entries={oodaTimeline} defaultExpandLatest={1} />
        </AccordionSection>

        <AccordionSection
          id="agents"
          title={t("sidePanel.agents")}
          summary={`${activeAgentCount} ${t("sidePanel.active")}`}
          isOpen={openSection === "agents"}
          onToggle={() => toggle("agents")}
        >
          <div className="space-y-2">
            {agents.length === 0 ? (
              <span className="text-sm font-mono text-athena-text-secondary">
                {t("sidePanel.noAgents")}
              </span>
            ) : (
              agents.map((a) => (
                <AgentBeacon
                  key={a.id}
                  paw={a.paw}
                  status={a.status as AgentStatus}
                  privilege={a.privilege}
                  platform={a.platform}
                  lastBeacon={a.lastBeacon}
                />
              ))
            )}
          </div>
        </AccordionSection>

        <AccordionSection
          id="logs"
          title={t("sidePanel.logs")}
          summary={allLogs[allLogs.length - 1]?.message?.slice(0, 40) || "—"}
          isOpen={openSection === "logs"}
          onToggle={() => toggle("logs")}
        >
          {allLogs.length === 0 ? (
            <span className="text-sm font-mono text-athena-text-secondary">
              {t("sidePanel.waitingForLogs")}
            </span>
          ) : (
            <div className="space-y-0">
              <div className="bg-athena-bg border border-athena-border rounded-athena-sm overflow-hidden">
                {allLogs.slice(-5).map((entry) => (
                  <LogEntryRow key={entry.id} entry={entry} />
                ))}
              </div>
              <Link
                href="/planner"
                className="block text-center text-xs font-mono text-athena-accent hover:underline mt-1.5 py-0.5"
              >
                {t("viewFullLogs")} →
              </Link>
            </div>
          )}
        </AccordionSection>

        {/* OODA Current Iteration */}
        <AccordionSection
          id="oodaCurrent"
          title={t("sidePanel.oodaCurrent")}
          summary={
            oodaCurrent
              ? `#${oodaCurrent.iterationNumber} - ${oodaCurrent.phase}`
              : "---"
          }
          isOpen={openSection === "oodaCurrent"}
          onToggle={() => toggle("oodaCurrent")}
        >
          {oodaCurrent ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-athena-accent">
                  {t("sidePanel.iteration")} #{oodaCurrent.iterationNumber}
                </span>
                <Badge variant="info">{oodaCurrent.phase}</Badge>
              </div>
              {oodaCurrent.observeSummary && (
                <div>
                  <span className="text-xs font-mono font-bold text-athena-text-secondary">
                    {t("sidePanel.observeSummary")}
                  </span>
                  <p className="text-xs font-mono text-athena-text mt-0.5">
                    {oodaCurrent.observeSummary}
                  </p>
                </div>
              )}
              {oodaCurrent.orientSummary && (
                <div>
                  <span className="text-xs font-mono font-bold text-athena-text-secondary">
                    {t("sidePanel.orientSummary")}
                  </span>
                  <p className="text-xs font-mono text-athena-text mt-0.5">
                    {oodaCurrent.orientSummary}
                  </p>
                </div>
              )}
              {oodaCurrent.decideSummary && (
                <div>
                  <span className="text-xs font-mono font-bold text-athena-text-secondary">
                    {t("sidePanel.decideSummary")}
                  </span>
                  <p className="text-xs font-mono text-athena-text mt-0.5">
                    {oodaCurrent.decideSummary}
                  </p>
                </div>
              )}
              {oodaCurrent.actSummary && (
                <div>
                  <span className="text-xs font-mono font-bold text-athena-text-secondary">
                    {t("sidePanel.actSummary")}
                  </span>
                  <p className="text-xs font-mono text-athena-text mt-0.5">
                    {oodaCurrent.actSummary}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <span className="text-sm font-mono text-athena-text-secondary">
              {t("sidePanel.noCurrentIteration")}
            </span>
          )}
        </AccordionSection>

        {/* OODA History */}
        <AccordionSection
          id="oodaHistory"
          title={t("sidePanel.oodaHistory")}
          summary={`${oodaHistory.length} ${t("sidePanel.iteration")}s`}
          isOpen={openSection === "oodaHistory"}
          onToggle={() => toggle("oodaHistory")}
        >
          {oodaHistory.length === 0 ? (
            <span className="text-sm font-mono text-athena-text-secondary">
              {t("sidePanel.noHistory")}
            </span>
          ) : (
            <div className="space-y-1">
              {oodaHistory.map((iter) => (
                <div
                  key={iter.id}
                  className="bg-athena-bg border border-athena-border/50 rounded-athena-sm"
                >
                  <button
                    onClick={() =>
                      setExpandedHistoryId(
                        expandedHistoryId === iter.id ? null : iter.id,
                      )
                    }
                    className="w-full flex items-center justify-between px-2 py-1.5 text-xs font-mono hover:bg-athena-border/20 transition-colors"
                  >
                    <span className="text-athena-accent font-bold">
                      #{iter.iterationNumber}
                    </span>
                    <span className="text-athena-text-secondary">
                      {iter.phase}
                    </span>
                    <span className="text-athena-text-secondary">
                      {expandedHistoryId === iter.id ? "▼" : "►"}
                    </span>
                  </button>
                  {expandedHistoryId === iter.id && (
                    <div className="px-2 pb-2 space-y-1 border-t border-athena-border/30">
                      {iter.observeSummary && (
                        <div className="mt-1">
                          <span className="text-xs font-mono font-bold text-athena-text-secondary">
                            {t("sidePanel.observeSummary")}
                          </span>
                          <p className="text-xs font-mono text-athena-text">
                            {iter.observeSummary}
                          </p>
                        </div>
                      )}
                      {iter.orientSummary && (
                        <div>
                          <span className="text-xs font-mono font-bold text-athena-text-secondary">
                            {t("sidePanel.orientSummary")}
                          </span>
                          <p className="text-xs font-mono text-athena-text">
                            {iter.orientSummary}
                          </p>
                        </div>
                      )}
                      {iter.decideSummary && (
                        <div>
                          <span className="text-xs font-mono font-bold text-athena-text-secondary">
                            {t("sidePanel.decideSummary")}
                          </span>
                          <p className="text-xs font-mono text-athena-text">
                            {iter.decideSummary}
                          </p>
                        </div>
                      )}
                      {iter.actSummary && (
                        <div>
                          <span className="text-xs font-mono font-bold text-athena-text-secondary">
                            {t("sidePanel.actSummary")}
                          </span>
                          <p className="text-xs font-mono text-athena-text">
                            {iter.actSummary}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </AccordionSection>
      </div>

      {/* LLM Directive — fixed at bottom */}
      <div className="shrink-0 border-t border-athena-border">
        <LLMDirectiveInput
          operationId={operationId}
          currentOodaPhase={currentOodaPhase}
          onSubmit={onDirectiveSubmit}
          onOodaTrigger={onOodaTrigger}
        />
      </div>
    </div>
  );
}
