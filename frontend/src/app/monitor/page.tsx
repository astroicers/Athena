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

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useOperation } from "@/hooks/useOperation";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useLiveLog } from "@/hooks/useLiveLog";
import { useToast } from "@/contexts/ToastContext";
import { PageLoading } from "@/components/ui/PageLoading";
import { MetricCard } from "@/components/cards/MetricCard";
import { NetworkTopology } from "@/components/topology/NetworkTopology";
import { ThreatLevelGauge } from "@/components/topology/ThreatLevelGauge";
import { OODAIndicator } from "@/components/ooda/OODAIndicator";
import { RecommendationPanel } from "@/components/ooda/RecommendationPanel";
import { AgentBeacon } from "@/components/data/AgentBeacon";
import { LogEntryRow } from "@/components/data/LogEntryRow";
import { useOODA } from "@/hooks/useOODA";
import type { TopologyData } from "@/types/api";
import type { PentestGPTRecommendation } from "@/types/recommendation";
import type { Agent } from "@/types/agent";
import type { LogEntry } from "@/types/log";
import { AgentStatus } from "@/types/enums";

const DEFAULT_OP_ID = "op-0001";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function MonitorPage() {
  const { operation } = useOperation(DEFAULT_OP_ID);
  const { addToast } = useToast();
  const ws = useWebSocket(DEFAULT_OP_ID);
  const oodaPhase = useOODA(ws);
  const liveLogs = useLiveLog(ws);
  const [isLoading, setIsLoading] = useState(true);
  const [topology, setTopology] = useState<TopologyData | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [initialLogs, setInitialLogs] = useState<LogEntry[]>([]);
  const [recommendation, setRecommendation] = useState<PentestGPTRecommendation | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const fetchRecommendation = () => {
    api.get<PentestGPTRecommendation>(`/operations/${DEFAULT_OP_ID}/recommendations/latest`)
      .then(setRecommendation)
      .catch(() => addToast("Failed to load recommendation", "error"));
  };

  useEffect(() => {
    Promise.all([
      api.get<TopologyData>(`/operations/${DEFAULT_OP_ID}/topology`).then(setTopology),
      api.get<Agent[]>(`/operations/${DEFAULT_OP_ID}/agents`).then(setAgents),
      api.get<{ items: LogEntry[] }>(`/operations/${DEFAULT_OP_ID}/logs?page_size=50`).then((r) => setInitialLogs(r.items || [])),
      api.get<PentestGPTRecommendation>(`/operations/${DEFAULT_OP_ID}/recommendations/latest`).then(setRecommendation),
    ]).catch(() => addToast("Failed to load monitor data", "error"))
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refresh recommendation when OODA phase changes (new recommendation may be available)
  useEffect(() => {
    if (oodaPhase) fetchRecommendation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oodaPhase]);

  const allLogs = [...initialLogs, ...liveLogs];

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allLogs.length]);

  if (isLoading) return <PageLoading />;

  return (
    <div className="space-y-4 h-full">
      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard
          title="Data Exfiltrated"
          value={operation ? formatBytes(operation.dataExfiltratedBytes) : "—"}
          accentColor="var(--color-warning)"
        />
        <MetricCard
          title="Active Connections"
          value={operation?.activeAgents ?? "—"}
          accentColor="var(--color-accent)"
        />
        <MetricCard
          title="Success Rate"
          value={operation ? `${operation.successRate}%` : "—"}
          accentColor="var(--color-success)"
        />
        <MetricCard
          title="WebSocket"
          value={ws.isConnected ? "CONNECTED" : "OFFLINE"}
          accentColor={ws.isConnected ? "var(--color-success)" : "var(--color-error)"}
        />
      </div>

      {/* Main content: Topology + Sidebar */}
      <div className="grid grid-cols-4 gap-4">
        {/* 3D Topology — 3 cols */}
        <div className="col-span-3">
          <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-2">
            Network Topology
          </h2>
          <NetworkTopology data={topology} />
        </div>

        {/* Right sidebar */}
        <div className="space-y-4">
          <OODAIndicator currentPhase={oodaPhase} />
          <ThreatLevelGauge level={operation?.threatLevel ?? 0} />

          {/* Agent Beacons */}
          <div>
            <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-2">
              Agent Beacons
            </h3>
            <div className="space-y-2">
              {agents.length === 0 ? (
                <div className="bg-athena-surface border border-athena-border rounded-athena-sm p-3 text-center">
                  <span className="text-xs font-mono text-athena-text-secondary">No agents</span>
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
        </div>
      </div>

      {/* PentestGPT Recommendation */}
      <RecommendationPanel
        recommendation={recommendation}
        operationId={DEFAULT_OP_ID}
        onAccepted={fetchRecommendation}
      />

      {/* Live Log Stream */}
      <div>
        <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-2">
          Live Log Stream
        </h2>
        <div className="bg-athena-surface border border-athena-border rounded-athena-md max-h-48 overflow-y-auto">
          {allLogs.length === 0 ? (
            <div className="p-4 text-center">
              <span className="text-xs font-mono text-athena-text-secondary">Waiting for log events...</span>
            </div>
          ) : (
            allLogs.map((entry) => (
              <LogEntryRow key={entry.id} entry={entry} />
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
