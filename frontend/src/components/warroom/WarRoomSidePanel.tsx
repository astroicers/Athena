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

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AIDecisionPanel } from "@/components/topology/AIDecisionPanel";
import { RecommendationPanel } from "@/components/ooda/RecommendationPanel";
import { OODATimeline } from "@/components/ooda/OODATimeline";
import { AgentBeacon } from "@/components/data/AgentBeacon";
import { C5ISRStatusBoard } from "@/components/c5isr/C5ISRStatusBoard";
import { ThreatLevelGauge } from "@/components/topology/ThreatLevelGauge";
import { AttackSituationDiagram } from "@/components/situation/AttackSituationDiagram";
import { LogEntryRow } from "@/components/data/LogEntryRow";
import { VirtualList } from "@/components/ui/VirtualList";
import { AccordionSection } from "./AccordionSection";
import { LLMDirectiveInput } from "./LLMDirectiveInput";
import type { OODAPhase, AgentStatus, KillChainStage } from "@/types/enums";
import type { OrientRecommendation } from "@/types/recommendation";
import type { OODATimelineEntry } from "@/types/ooda";
import type { Agent } from "@/types/agent";
import type { LogEntry } from "@/types/log";
import type { TechniqueWithStatus } from "@/types/technique";
import type { C5ISRStatus } from "@/types/c5isr";
import type { ExecutionUpdate } from "@/hooks/useExecutionUpdate";

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
  // Recommendation
  recommendation: OrientRecommendation | null;
  // OODA
  oodaTimeline: OODATimelineEntry[];
  currentOodaPhase: OODAPhase | null;
  // Agents
  agents: Agent[];
  // C5ISR
  c5isrDomains: C5ISRStatus[];
  threatLevel: number;
  // Situation
  techniques: TechniqueWithStatus[];
  executionUpdate: ExecutionUpdate | null;
  // Logs
  allLogs: LogEntry[];
  // Directive
  operationId: string;
  onDirectiveSubmit: (directive: string) => Promise<void>;
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
  recommendation,
  oodaTimeline,
  currentOodaPhase,
  agents,
  c5isrDomains,
  threatLevel,
  techniques,
  executionUpdate,
  allLogs,
  operationId,
  onDirectiveSubmit,
}: WarRoomSidePanelProps) {
  const t = useTranslations("WarRoom");
  const [openSection, setOpenSection] = useState<string | null>("aiDecision");

  function toggle(id: string) {
    setOpenSection((prev) => (prev === id ? null : id));
  }

  const activeAgentCount = agents.filter(
    (a) => a.status === "alive"
  ).length;

  const successCount = techniques.filter(
    (tech) => tech.latestStatus === "success" || tech.latestStatus === "partial"
  ).length;

  return (
    <div className="flex flex-col h-full bg-athena-surface">
      {/* Accordion sections — scrollable */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <AccordionSection
          id="aiDecision"
          title="AI Decision"
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
          />
        </AccordionSection>

        <AccordionSection
          id="recommendation"
          title="Recommendation"
          summary={recommendation?.options?.[0]?.techniqueName || "—"}
          isOpen={openSection === "recommendation"}
          onToggle={() => toggle("recommendation")}
        >
          <RecommendationPanel recommendation={recommendation} />
        </AccordionSection>

        <AccordionSection
          id="ooda"
          title="OODA Timeline"
          summary={`Phase: ${currentOodaPhase || "idle"}`}
          isOpen={openSection === "ooda"}
          onToggle={() => toggle("ooda")}
        >
          <OODATimeline entries={oodaTimeline} defaultExpandLatest={1} />
        </AccordionSection>

        <AccordionSection
          id="agents"
          title="Agents"
          summary={`${activeAgentCount} active`}
          isOpen={openSection === "agents"}
          onToggle={() => toggle("agents")}
        >
          <div className="space-y-2">
            {agents.length === 0 ? (
              <span className="text-[10px] font-mono text-athena-text-secondary">
                No agents
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
          id="c5isr"
          title="C5ISR"
          summary={c5isrDomains.map((d) => `${d.domain[0].toUpperCase()}:${d.healthPct}%`).join(" ")}
          isOpen={openSection === "c5isr"}
          onToggle={() => toggle("c5isr")}
        >
          <ThreatLevelGauge level={threatLevel} />
          <C5ISRStatusBoard domains={c5isrDomains} />
        </AccordionSection>

        <AccordionSection
          id="situation"
          title="Situation"
          summary={`${successCount} success`}
          isOpen={openSection === "situation"}
          onToggle={() => toggle("situation")}
        >
          <AttackSituationDiagram
            techniques={techniques}
            oodaPhase={currentOodaPhase}
            executionUpdate={executionUpdate}
            c5isrDomains={c5isrDomains as Array<{ domain: string; healthPct: number }>}
          />
        </AccordionSection>

        <AccordionSection
          id="logs"
          title="Logs"
          summary={allLogs[allLogs.length - 1]?.message?.slice(0, 40) || "—"}
          isOpen={openSection === "logs"}
          onToggle={() => toggle("logs")}
        >
          {allLogs.length === 0 ? (
            <span className="text-[10px] font-mono text-athena-text-secondary">
              Waiting for logs...
            </span>
          ) : (
            <VirtualList
              items={allLogs}
              rowHeight={28}
              height={200}
              className="bg-athena-bg border border-athena-border rounded-athena-sm"
              renderRow={(entry) => <LogEntryRow key={entry.id} entry={entry} />}
            />
          )}
        </AccordionSection>
      </div>

      {/* LLM Directive — fixed at bottom */}
      <div className="shrink-0 border-t border-athena-border">
        <LLMDirectiveInput
          operationId={operationId}
          currentOodaPhase={currentOodaPhase}
          onSubmit={onDirectiveSubmit}
        />
      </div>
    </div>
  );
}
