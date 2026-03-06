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
import { api } from "@/lib/api";
import { useOperation } from "@/hooks/useOperation";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useLiveLog } from "@/hooks/useLiveLog";
import { useOODA } from "@/hooks/useOODA";
import { useExecutionUpdate } from "@/hooks/useExecutionUpdate";
import { useToast } from "@/contexts/ToastContext";
import { MonitorPageSkeleton } from "@/components/ui/Skeleton";
import { NetworkTopology } from "@/components/topology/NetworkTopology";
import { TacticalDashboard } from "@/components/warroom/TacticalDashboard";
import { WarRoomSidePanel } from "@/components/warroom/WarRoomSidePanel";
import type { TopologyData } from "@/types/api";
import type { OrientRecommendation } from "@/types/recommendation";
import type { Agent } from "@/types/agent";
import type { LogEntry } from "@/types/log";
import type { TechniqueWithStatus } from "@/types/technique";
import type { OODATimelineEntry } from "@/types/ooda";
import type { C5ISRStatus } from "@/types/c5isr";
import { KillChainStage } from "@/types/enums";

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

export default function WarRoomPage() {
  const t = useTranslations("WarRoom");
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
  const [c5isrDomains, setC5isrDomains] = useState<C5ISRStatus[]>([]);
  const [oodaTimeline, setOodaTimeline] = useState<OODATimelineEntry[]>([]);

  // War Room specific
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [openNodeIds, setOpenNodeIds] = useState<string[]>([]);

  // ── Node click handler (toggle, max 6 open) ──
  const handleNodeClick = useCallback((nodeId: string) => {
    setOpenNodeIds((prev) =>
      prev.includes(nodeId)
        ? prev.filter((id) => id !== nodeId)
        : prev.length >= 6
          ? [...prev.slice(1), nodeId]
          : [...prev, nodeId]
    );
  }, []);

  // ── Initial data fetch ──
  useEffect(() => {
    Promise.all([
      api.get<TopologyData>(`/operations/${DEFAULT_OP_ID}/topology`).then(setTopology),
      api.get<Agent[]>(`/operations/${DEFAULT_OP_ID}/agents`).then(setAgents),
      api.get<{ items: LogEntry[] }>(`/operations/${DEFAULT_OP_ID}/logs?page_size=50`).then((r) => setInitialLogs(r.items || [])),
      api.get<OrientRecommendation>(`/operations/${DEFAULT_OP_ID}/recommendations/latest`).then(setRecommendation),
      api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`).then(setTechniques),
      api.get<C5ISRStatus[]>(`/operations/${DEFAULT_OP_ID}/c5isr`).then(setC5isrDomains).catch(() => {}),
      api.get<OODATimelineEntry[]>(`/operations/${DEFAULT_OP_ID}/ooda/timeline`).then(setOodaTimeline).catch(() => {}),
    ]).catch(() => addToast(tErrors("failedLoadWarRoom"), "error"))
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Refresh recommendation on OODA phase change ──
  useEffect(() => {
    if (oodaPhase) {
      api.get<OrientRecommendation>(`/operations/${DEFAULT_OP_ID}/recommendations/latest`)
        .then(setRecommendation)
        .catch(() => {});
    }
  }, [oodaPhase]);

  // ── WebSocket subscriptions ──

  // execution.update → refresh techniques
  useEffect(() => {
    const unsub = ws.subscribe("execution.update", () => {
      api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`)
        .then(setTechniques)
        .catch(() => {});
    });
    return unsub;
  }, [ws]);

  // fact.new → refresh topology
  useEffect(() => {
    const unsub = ws.subscribe("fact.new", (raw: unknown) => {
      const data = raw as Record<string, unknown>;
      const trait = (data.trait as string) ?? "";
      const category = (data.category as string) ?? "";
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

  // recommendation → update immediately
  useEffect(() => {
    const unsub = ws.subscribe("recommendation", (raw: unknown) => {
      const data = raw as Record<string, unknown>;
      setRecommendation(data as unknown as OrientRecommendation);
      setLlmThinking(false);
    });
    return unsub;
  }, [ws]);

  // orient.thinking → LLM status
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

  // c5isr.update
  useEffect(() => {
    const unsub = ws.subscribe("c5isr.update", (raw: unknown) => {
      const data = raw as Record<string, unknown>;
      const domains = data.domains as C5ISRStatus[] | undefined;
      if (domains) setC5isrDomains(domains);
    });
    return unsub;
  }, [ws]);

  // recon/initial_access completion → refresh topology
  useEffect(() => {
    const refreshTopo = () => {
      api.get<TopologyData>(`/operations/${DEFAULT_OP_ID}/topology`)
        .then(setTopology)
        .catch(() => {});
    };
    const unsub1 = ws.subscribe("recon.completed", refreshTopo);
    const unsub2 = ws.subscribe("initial_access.completed", refreshTopo);
    return () => { unsub1(); unsub2(); };
  }, [ws]);

  // ooda.phase → refresh timeline
  useEffect(() => {
    const unsub = ws.subscribe("ooda.phase", () => {
      api.get<OODATimelineEntry[]>(`/operations/${DEFAULT_OP_ID}/ooda/timeline`)
        .then(setOodaTimeline)
        .catch(() => {});
    });
    return unsub;
  }, [ws]);

  // ── Computed ──
  const allLogs = [...initialLogs, ...liveLogs];

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

  // ── Directive handler ──
  async function handleDirectiveSubmit(directive: string) {
    await api.post(`/operations/${DEFAULT_OP_ID}/ooda/directive`, {
      directive,
      scope: "next_cycle",
    });
    addToast(t("directiveSent"), "success");
  }

  async function handleOodaTrigger() {
    await api.post(`/operations/${DEFAULT_OP_ID}/ooda/trigger`);
    addToast(t("oodaStarted"), "info");
  }

  async function handleReconScan(targetId: string) {
    try {
      await api.post(`/operations/${DEFAULT_OP_ID}/recon/scan`, {
        target_id: targetId,
        enable_initial_access: false,
      });
      addToast(t("reconStarted"), "info");
    } catch {
      addToast(tErrors("failedRecon"), "error");
    }
  }

  async function handleInitialAccess(targetId: string) {
    try {
      await api.post(`/operations/${DEFAULT_OP_ID}/recon/initial-access`, {
        target_id: targetId,
      });
      addToast(t("initialAccessStarted"), "info");
    } catch {
      addToast(tErrors("failedInitialAccess"), "error");
    }
  }

  if (isLoading) return <MonitorPageSkeleton />;

  return (
    <div className="-m-4 h-[calc(100vh-48px)] flex flex-col overflow-hidden">
      {/* Tactical Dashboard */}
      <TacticalDashboard c5isrDomains={c5isrDomains} />

      {/* Main area: Topology + Side Panel */}
      <div className="flex-1 flex min-h-0">
        {/* Topology — fills remaining space */}
        <div className="flex-1 min-w-0 relative">
          <NetworkTopology
            data={topology}
            nodeKillChainMap={nodeKillChainMap}
            nodeSizeMultiplier={1.5}
            height="auto"
            onNodeClick={handleNodeClick}
            openNodeIds={openNodeIds}
            operationId={DEFAULT_OP_ID}
            onCloseNode={(id) => setOpenNodeIds((prev) => prev.filter((n) => n !== id))}
            onReconScan={handleReconScan}
            onInitialAccess={handleInitialAccess}
          />
          {/* Side Panel Toggle */}
          <button
            onClick={() => setSidePanelOpen((v) => !v)}
            className="absolute top-2 right-[72px] z-10 px-2 py-1 rounded border border-athena-border bg-athena-surface hover:bg-athena-elevated text-[10px] font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
            title={t("sidePanel")}
          >
            {sidePanelOpen ? "▶" : "◀"} {t("sidePanel")}
          </button>
        </div>

        {/* Side Panel */}
        {sidePanelOpen && (
          <div className="w-96 shrink-0 border-l border-athena-border">
            <WarRoomSidePanel
              activeTechniqueId={executionUpdate?.techniqueId ?? null}
              activeEngine={executionUpdate?.engine ?? null}
              activeStatus={executionUpdate?.status ?? null}
              activeTechniqueName={activeTechnique?.name ?? null}
              activeKillChainStage={activeTechnique?.killChainStage ?? null}
              activeConfidence={activeConfidence}
              llmThinking={llmThinking}
              llmBackend={llmBackend}
              llmLatencyMs={llmLatencyMs}
              recommendation={recommendation}
              oodaTimeline={oodaTimeline}
              currentOodaPhase={oodaPhase}
              agents={agents}
              allLogs={allLogs}
              operationId={DEFAULT_OP_ID}
              onDirectiveSubmit={handleDirectiveSubmit}
              onOodaTrigger={handleOodaTrigger}
            />
          </div>
        )}
      </div>
    </div>
  );
}
