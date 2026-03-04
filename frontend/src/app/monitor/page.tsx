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

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { api } from "@/lib/api";
import { useOperation } from "@/hooks/useOperation";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useLiveLog } from "@/hooks/useLiveLog";
import { useToast } from "@/contexts/ToastContext";
import { MonitorPageSkeleton } from "@/components/ui/Skeleton";
import { SlidePanel } from "@/components/ui/SlidePanel";
import { VirtualList } from "@/components/ui/VirtualList";
import { MetricCard } from "@/components/cards/MetricCard";
import { NetworkTopology } from "@/components/topology/NetworkTopology";
import { ThreatLevelGauge } from "@/components/topology/ThreatLevelGauge";
import { TopologyView } from "@/components/topology/TopologyView";
import { OODAIndicator } from "@/components/ooda/OODAIndicator";
import { RecommendationPanel } from "@/components/ooda/RecommendationPanel";
import { AgentBeacon } from "@/components/data/AgentBeacon";
import { LogEntryRow } from "@/components/data/LogEntryRow";
import { useOODA } from "@/hooks/useOODA";
import { useExecutionUpdate } from "@/hooks/useExecutionUpdate";
import { KillChainIndicator } from "@/components/mitre/KillChainIndicator";
import { TabBar } from "@/components/nav/TabBar";
import type { TopologyData } from "@/types/api";
import type { OrientRecommendation } from "@/types/recommendation";
import type { Agent } from "@/types/agent";
import type { LogEntry } from "@/types/log";
import type { TechniqueWithStatus } from "@/types/technique";
import { AgentStatus, KillChainStage } from "@/types/enums";
import { AIDecisionPanel } from "@/components/topology/AIDecisionPanel";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { AttackSituationDiagram } from "@/components/situation/AttackSituationDiagram";

const DEFAULT_OP_ID = "op-0001";

const KILL_CHAIN_ORDER: KillChainStage[] = [
  KillChainStage.RECON,
  KillChainStage.WEAPONIZE,
  KillChainStage.DELIVER,
  KillChainStage.EXPLOIT,
  KillChainStage.INSTALL,
  KillChainStage.C2,
  KillChainStage.ACTION,
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function MonitorPage() {
  const t = useTranslations("Monitor");
  const tCommon = useTranslations("Common");
  const tHints = useTranslations("Hints");
  const tEmpty = useTranslations("EmptyStates");
  const tErrors = useTranslations("Errors");

  const { operation } = useOperation(DEFAULT_OP_ID);
  const { addToast } = useToast();
  const ws = useWebSocket(DEFAULT_OP_ID);
  const { phase: oodaPhase } = useOODA(ws);
  const executionUpdate = useExecutionUpdate(ws);
  const liveLogs = useLiveLog(ws);
  const [isLoading, setIsLoading] = useState(true);
  const [topology, setTopology] = useState<TopologyData | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [initialLogs, setInitialLogs] = useState<LogEntry[]>([]);
  const [recommendation, setRecommendation] = useState<OrientRecommendation | null>(null);
  const [techniques, setTechniques] = useState<TechniqueWithStatus[]>([]);
  const [llmThinking, setLlmThinking] = useState(false);
  const [llmBackend, setLlmBackend] = useState<string | null>(null);
  const [llmLatencyMs, setLlmLatencyMs] = useState<number | null>(null);
  const [recHistory, setRecHistory] = useState<OrientRecommendation[]>([]);
  const [recHistoryOpen, setRecHistoryOpen] = useState(false);
  const [recHistoryOpenIds, setRecHistoryOpenIds] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [c5isrDomains, setC5isrDomains] = useState<Array<{domain: string; healthPct: number}>>([]);

  const fetchRecommendation = () => {
    api.get<OrientRecommendation>(`/operations/${DEFAULT_OP_ID}/recommendations/latest`)
      .then(setRecommendation)
      .catch(() => addToast(tErrors("failedLoadRecommendation"), "error"));
  };

  const fetchRecHistory = () => {
    api.get<OrientRecommendation[]>(`/operations/${DEFAULT_OP_ID}/recommendations?limit=20`)
      .then(setRecHistory)
      .catch(() => {});
  };

  useEffect(() => {
    Promise.all([
      api.get<TopologyData>(`/operations/${DEFAULT_OP_ID}/topology`).then(setTopology),
      api.get<Agent[]>(`/operations/${DEFAULT_OP_ID}/agents`).then(setAgents),
      api.get<{ items: LogEntry[] }>(`/operations/${DEFAULT_OP_ID}/logs?page_size=50`).then((r) => setInitialLogs(r.items || [])),
      api.get<OrientRecommendation>(`/operations/${DEFAULT_OP_ID}/recommendations/latest`).then(setRecommendation),
      api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`).then(setTechniques),
      api.get<OrientRecommendation[]>(`/operations/${DEFAULT_OP_ID}/recommendations?limit=20`).then(setRecHistory).catch(() => {}),
      api.get<Array<{domain: string; healthPct: number; status: string; detail: string}>>(`/operations/${DEFAULT_OP_ID}/c5isr`).then(setC5isrDomains).catch(() => {}),
    ]).catch(() => addToast(tErrors("failedLoadMonitor"), "error"))
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refresh recommendation when OODA phase changes (new recommendation may be available)
  useEffect(() => {
    if (oodaPhase) fetchRecommendation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oodaPhase]);

  // Subscribe to execution.update to refresh techniques
  useEffect(() => {
    const unsub = ws.subscribe("execution.update", () => {
      api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`)
        .then(setTechniques)
        .catch(() => {});
    });
    return unsub;
  }, [ws]);

  // Subscribe to fact.new — refresh topology so new host facts are reflected
  useEffect(() => {
    const unsub = ws.subscribe("fact.new", (raw: unknown) => {
      const data = raw as Record<string, unknown>;
      const trait = (data.trait as string) ?? "";
      const category = (data.category as string) ?? "";
      // Refresh topology when network/host/service facts arrive
      if (
        category === "network" ||
        category === "host" ||
        category === "service" ||
        trait.startsWith("host.") ||
        trait.startsWith("service.") ||
        trait.startsWith("network.")
      ) {
        api.get<TopologyData>(`/operations/${DEFAULT_OP_ID}/topology`)
          .then(setTopology)
          .catch(() => {});
      }
    });
    return unsub;
  }, [ws]);

  // Subscribe to recommendation — update recommendation panel immediately on new AI analysis
  useEffect(() => {
    const unsub = ws.subscribe("recommendation", (raw: unknown) => {
      const data = raw as Record<string, unknown>;
      // Cast the broadcast payload directly to OrientRecommendation — the shape is identical
      setRecommendation(data as unknown as OrientRecommendation);
      setLlmThinking(false);
      fetchRecHistory();
      const techniqueId = (data.recommendedTechniqueId as string) ?? "";
      const confidence = (data.confidence as number) ?? 0;
      addToast(
        t("newRecommendation", { techniqueId: techniqueId || "analysis complete", confidence: Math.round(confidence * 100) }),
        "info",
      );
    });
    return unsub;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws, addToast]);

  // Subscribe to orient.thinking — show LLM analyzing indicator in AI Decision Panel
  useEffect(() => {
    const unsub = ws.subscribe("orient.thinking", (raw: unknown) => {
      const data = raw as Record<string, unknown>;
      const status = data.status as string;
      const backend = (data.backend as string) ?? null;
      if (status === "started") {
        setLlmThinking(true);
        setLlmBackend(backend);
        setLlmLatencyMs(null);
      } else if (status === "completed") {
        setLlmThinking(false);
        setLlmLatencyMs((data.latency_ms as number) ?? null);
      }
    });
    return unsub;
  }, [ws]);

  // Subscribe to c5isr.update — refresh C5ISR domain health for situation diagram
  useEffect(() => {
    const unsub = ws.subscribe("c5isr.update", (raw: unknown) => {
      const data = raw as Record<string, unknown>;
      const domains = data.domains as Array<{domain: string; healthPct: number}> | undefined;
      if (domains) setC5isrDomains(domains);
    });
    return unsub;
  }, [ws]);

  const allLogs = [...initialLogs, ...liveLogs];

  const stageCounts = useMemo(() => {
    const counts: Record<string, { total: number; tested: number; success: number; failed: number }> = {};
    techniques.forEach((tech) => {
      const stage = tech.killChainStage;
      if (!counts[stage]) counts[stage] = { total: 0, tested: 0, success: 0, failed: 0 };
      counts[stage].total += 1;
      if (tech.latestStatus && tech.latestStatus !== "untested") {
        counts[stage].tested += 1;
        if (tech.latestStatus === "success" || tech.latestStatus === "partial") {
          counts[stage].success += 1;
        } else if (tech.latestStatus === "failed") {
          counts[stage].failed += 1;
        }
      }
    });
    return counts;
  }, [techniques]);

  const nodeKillChainMap = useMemo(() => {
    if (!topology || techniques.length === 0) return {};
    const executed = techniques.filter(
      (tech) => tech.latestStatus && tech.latestStatus !== "untested"
    );
    const highestStage = executed.reduce<KillChainStage | null>((acc, tech) => {
      if (!acc) return tech.killChainStage;
      return KILL_CHAIN_ORDER.indexOf(tech.killChainStage) > KILL_CHAIN_ORDER.indexOf(acc)
        ? tech.killChainStage
        : acc;
    }, null);
    if (!highestStage) return {};
    const map: Record<string, KillChainStage> = {};
    topology.nodes.forEach((n) => {
      if (n.data?.isCompromised) map[n.id] = highestStage;
    });
    return map;
  }, [topology, techniques]);

  if (isLoading) return <MonitorPageSkeleton />;

  const activeTechnique = executionUpdate
    ? techniques.find(
        (tech) => tech.mitreId === executionUpdate.techniqueId || tech.id === executionUpdate.techniqueId
      ) ?? null
    : null;

  const activeConfidence =
    executionUpdate && recommendation
      ? (recommendation.options?.find(
          (o) => o.techniqueId === executionUpdate.techniqueId
        )?.confidence ?? null)
      : null;

  const MONITOR_TABS = [
    { id: "overview", label: t("overview") },
    { id: "topology", label: t("topology") },
    { id: "situation", label: t("situation") },
  ];

  return (
    <div className="flex flex-col h-full gap-3 overflow-hidden">
      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 shrink-0">
        <MetricCard
          title={t("dataExfiltrated")}
          value={operation ? formatBytes(operation.dataExfiltratedBytes) : "\u2014"}
          accentColor="var(--color-warning)"
        />
        <MetricCard
          title={t("activeConnections")}
          value={operation?.activeAgents ?? "\u2014"}
          accentColor="var(--color-accent)"
        />
        <MetricCard
          title={t("successRate")}
          value={operation ? `${operation.successRate}%` : "\u2014"}
          accentColor={operation && operation.successRate < 50 ? "var(--color-warning)" : "var(--color-success)"}
        />
        <MetricCard
          title={t("websocket")}
          value={ws.isConnected ? tCommon("connected") : tCommon("offline")}
          accentColor={ws.isConnected ? "var(--color-success)" : "var(--color-error)"}
        />
      </div>

      {/* Tab bar */}
      <div className="shrink-0">
        <TabBar tabs={MONITOR_TABS} activeTab={activeTab} onChange={setActiveTab} />
      </div>

      {/* OVERVIEW tab */}
      {activeTab === "overview" && (
        <div className="flex-1 grid grid-rows-[1fr_auto] gap-3 overflow-hidden min-h-0">
          {/* Top row: Topology + Right sidebar */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 overflow-hidden min-h-0">
            {/* Left column — 3 cols: Topology + KillChain */}
            <div className="lg:col-span-3 flex flex-col gap-3 overflow-hidden min-h-0">
              <div className="flex-1 flex flex-col min-h-0">
                <SectionHeader className="mb-2 shrink-0">
                  {t("networkTopology")}
                </SectionHeader>
                <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-1 mb-2 ml-1 shrink-0">{tHints("topology")}</p>
                <div className="flex-1 min-h-0">
                  <NetworkTopology data={topology} nodeKillChainMap={nodeKillChainMap} />
                </div>
              </div>
              <div className="shrink-0">
                <KillChainIndicator stageCounts={stageCounts} />
              </div>
            </div>

            {/* Right sidebar — 1 col, scrollable within */}
            <div className="overflow-y-auto space-y-4 min-h-0">
              <OODAIndicator currentPhase={oodaPhase} />
              <ThreatLevelGauge level={operation?.threatLevel ?? 0} />

              {/* Agent Beacons */}
              <div>
                <SectionHeader level="card" className="mb-2">
                  {t("agentBeacons")}
                </SectionHeader>
                <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-1 mb-2 ml-1">{tHints("agentBeacons")}</p>
                <div className="space-y-2">
                  {agents.length === 0 ? (
                    <div className="border-2 border-dashed border-athena-border/50 rounded-athena-md p-4 text-center">
                      <span className="text-xs font-mono text-athena-text-secondary">{t("noAgents")}</span>
                    </div>
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
              </div>

              <AIDecisionPanel
                activeTechniqueId={executionUpdate?.techniqueId ?? null}
                activeEngine={executionUpdate?.engine ?? null}
                activeStatus={executionUpdate?.status ?? null}
                activeTechniqueName={activeTechnique?.name ?? null}
                activeKillChainStage={activeTechnique?.killChainStage ?? null}
                activeConfidence={activeConfidence}
                llmThinking={llmThinking}
                llmBackend={llmBackend}
                llmLatencyMs={llmLatencyMs}
              />
            </div>
          </div>

          {/* Bottom row: Recommendation + Live Logs */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 shrink-0 max-h-64">
            {/* Left: AI Recommendation (compact) */}
            <div className="overflow-hidden flex flex-col min-h-0">
              {recHistory.length > 0 && (
                <div className="flex justify-end mb-1 shrink-0">
                  <button
                    onClick={() => setRecHistoryOpen(true)}
                    className="text-[10px] font-mono text-athena-accent hover:text-athena-text transition-colors uppercase tracking-wider"
                  >
                    {t("recHistory", { count: recHistory.length })}
                  </button>
                </div>
              )}
              <div className="flex-1 overflow-y-auto min-h-0">
                <RecommendationPanel
                  recommendation={recommendation}
                />
                {!recommendation && (
                  <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 text-center">
                    <p className="text-xs font-mono text-athena-text-secondary mb-2">{tEmpty("monitorNoRec")}</p>
                    <Link href="/planner" className="text-xs font-mono text-athena-accent hover:underline">
                      {tEmpty("monitorGoToPlanner")}
                    </Link>
                  </div>
                )}
              </div>
              <p className="text-[10px] font-mono text-athena-text-secondary/60 mt-1 ml-1 shrink-0">{tHints("recommendation")}</p>
            </div>

            {/* Right: Live Log Stream (virtualized) */}
            <div className="overflow-hidden flex flex-col min-h-0">
              <SectionHeader className="mb-2 shrink-0">
                {t("liveLogStream")}
              </SectionHeader>
              <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-1 mb-2 ml-1 shrink-0">{tHints("logStream")}</p>
              {allLogs.length === 0 ? (
                <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 text-center">
                  <span className="text-xs font-mono text-athena-text-secondary">{t("waitingForLogs")}</span>
                </div>
              ) : (
                <VirtualList
                  items={allLogs}
                  rowHeight={28}
                  height={200}
                  className="bg-athena-surface border border-athena-border rounded-athena-md"
                  renderRow={(entry) => <LogEntryRow key={entry.id} entry={entry} />}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* TOPOLOGY tab */}
      {activeTab === "topology" && (
        <TopologyView
          topologyData={topology}
          nodeKillChainMap={nodeKillChainMap}
          stageCounts={stageCounts}
          operationId={DEFAULT_OP_ID}
        />
      )}

      {/* SITUATION tab */}
      {activeTab === "situation" && (
        <AttackSituationDiagram
          techniques={techniques}
          oodaPhase={oodaPhase}
          executionUpdate={executionUpdate}
          c5isrDomains={c5isrDomains}
        />
      )}

      {/* Recommendation History SlidePanel */}
      <SlidePanel
        open={recHistoryOpen}
        onClose={() => setRecHistoryOpen(false)}
        title={t("recHistory", { count: recHistory.length })}
        width="md"
      >
        <div className="divide-y divide-athena-border/50">
          {recHistory.map((rec) => {
            const isOpen = recHistoryOpenIds.has(rec.id);
            const time = rec.createdAt?.split("T")[1]?.slice(0, 8) ?? "";
            const topOption = rec.options?.[0];
            return (
              <div key={rec.id} className="px-4 py-2">
                <button
                  onClick={() =>
                    setRecHistoryOpenIds((prev) => {
                      const next = new Set(prev);
                      if (next.has(rec.id)) next.delete(rec.id);
                      else next.add(rec.id);
                      return next;
                    })
                  }
                  className="w-full flex items-center gap-3 text-left"
                >
                  <span className="text-[10px] font-mono text-athena-text-secondary/60 shrink-0 w-16">
                    {time}
                  </span>
                  <span className="text-xs font-mono text-athena-accent font-bold shrink-0">
                    {rec.recommendedTechniqueId}
                  </span>
                  <span className="text-[10px] font-mono text-athena-success shrink-0">
                    {Math.round(rec.confidence * 100)}%
                  </span>
                  {topOption && (
                    <span className="text-[10px] font-mono text-athena-text-secondary/60 shrink-0 uppercase">
                      {topOption.riskLevel}
                    </span>
                  )}
                  <span className="text-[10px] font-mono text-athena-text-secondary truncate flex-1">
                    {rec.situationAssessment?.slice(0, 80)}
                    {(rec.situationAssessment?.length ?? 0) > 80 ? "..." : ""}
                  </span>
                  <span className="text-[10px] font-mono text-athena-text-secondary/40 shrink-0">
                    {isOpen ? "\u25B2" : "\u25BC"}
                  </span>
                </button>
                {isOpen && (
                  <div className="mt-2 pl-2 border-l-2 border-athena-border/50">
                    <p className="text-xs font-mono text-athena-text leading-relaxed">
                      {rec.situationAssessment}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </SlidePanel>
    </div>
  );
}
