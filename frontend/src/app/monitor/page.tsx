// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { api } from "@/lib/api";
import { useOperation } from "@/hooks/useOperation";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useLiveLog } from "@/hooks/useLiveLog";
import { useToast } from "@/contexts/ToastContext";
import { PageLoading } from "@/components/ui/PageLoading";
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
  const tTips = useTranslations("Tooltips");
  const tEmpty = useTranslations("EmptyStates");
  const tErrors = useTranslations("Errors");

  const { operation } = useOperation(DEFAULT_OP_ID);
  const { addToast } = useToast();
  const ws = useWebSocket(DEFAULT_OP_ID);
  const oodaPhase = useOODA(ws);
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
  const [recHistoryExpanded, setRecHistoryExpanded] = useState(false);
  const [recHistoryOpenIds, setRecHistoryOpenIds] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [c5isrDomains, setC5isrDomains] = useState<Array<{domain: string; healthPct: number}>>([]);
  const logEndRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allLogs.length]);

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

  if (isLoading) return <PageLoading />;

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
    { id: "situation", label: "SITUATION" },
  ];

  return (
    <div className="space-y-4 h-full">
      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          title={t("dataExfiltrated")}
          value={operation ? formatBytes(operation.dataExfiltratedBytes) : "—"}
          accentColor="var(--color-warning)"
        />
        <MetricCard
          title={t("activeConnections")}
          value={operation?.activeAgents ?? "—"}
          accentColor="var(--color-accent)"
        />
        <MetricCard
          title={t("successRate")}
          value={operation ? `${operation.successRate}%` : "—"}
          accentColor={operation && operation.successRate < 50 ? "var(--color-warning)" : "var(--color-success)"}
        />
        <MetricCard
          title={t("websocket")}
          value={ws.isConnected ? tCommon("connected") : tCommon("offline")}
          accentColor={ws.isConnected ? "var(--color-success)" : "var(--color-error)"}
        />
      </div>

      {/* Tab bar */}
      <TabBar tabs={MONITOR_TABS} activeTab={activeTab} onChange={setActiveTab} />

      {/* OVERVIEW tab */}
      {activeTab === "overview" && (
        <>
          {/* Main content: Topology + Sidebar */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* 3D Topology — 3 cols */}
            <div className="lg:col-span-3 space-y-3">
              <div>
                <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-2">
                  {t("networkTopology")}
                </h2>
                <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-1 mb-2 ml-1">{tHints("topology")}</p>
                <NetworkTopology data={topology} nodeKillChainMap={nodeKillChainMap} />
              </div>
              <KillChainIndicator stageCounts={stageCounts} />
            </div>

            {/* Right sidebar */}
            <div className="space-y-4">
              <OODAIndicator currentPhase={oodaPhase} />
              <ThreatLevelGauge level={operation?.threatLevel ?? 0} />

              {/* Agent Beacons */}
              <div>
                <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-2">
                  {t("agentBeacons")}
                </h3>
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

          {/* AI Recommendation */}
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
          <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-3 ml-1">{tHints("recommendation")}</p>

          {/* Recommendation History */}
          {recHistory.length > 0 && (
        <div className="bg-athena-surface border border-athena-border rounded-athena-md overflow-hidden">
          <button
            onClick={() => setRecHistoryExpanded((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-2 hover:bg-athena-border/20 transition-colors"
          >
            <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
              {t("recHistory", { count: recHistory.length })}
            </span>
            <span className="text-[10px] font-mono text-athena-text-secondary">
              {recHistoryExpanded ? "▲" : "▼"}
            </span>
          </button>
          {recHistoryExpanded && (
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
                        {isOpen ? "▲" : "▼"}
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
          )}
          </div>
          )}

          {/* Live Log Stream */}
          <div>
            <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-2">
              {t("liveLogStream")}
            </h2>
            <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-1 mb-2 ml-1">{tHints("logStream")}</p>
            <div className="bg-athena-surface border border-athena-border rounded-athena-md max-h-48 overflow-y-auto">
              {allLogs.length === 0 ? (
                <div className="p-4 text-center">
                  <span className="text-xs font-mono text-athena-text-secondary">{t("waitingForLogs")}</span>
                </div>
              ) : (
                allLogs.map((entry) => (
                  <LogEntryRow key={entry.id} entry={entry} />
                ))
              )}
              <div ref={logEndRef} />
            </div>
          </div>
        </>
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
    </div>
  );
}
