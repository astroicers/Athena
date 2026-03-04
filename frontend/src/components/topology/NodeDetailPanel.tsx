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

import { useEffect, useState } from "react";
import type { TopologyData } from "@/types/api";
import { KillChainStage } from "@/types/enums";
import { api } from "@/lib/api";
import { KILL_CHAIN_COLORS } from "./NetworkTopology";

interface FactRow {
  id: string;
  trait: string;
  value: string;
  category: string;
  source_target_id: string | null;
}

const KC_STAGES: KillChainStage[] = [
  KillChainStage.RECON,
  KillChainStage.WEAPONIZE,
  KillChainStage.DELIVER,
  KillChainStage.EXPLOIT,
  KillChainStage.INSTALL,
  KillChainStage.C2,
  KillChainStage.ACTION,
];

const KC_LABELS: Record<KillChainStage, string> = {
  [KillChainStage.RECON]: "RECON",
  [KillChainStage.WEAPONIZE]: "WEAPON",
  [KillChainStage.DELIVER]: "DELIVER",
  [KillChainStage.EXPLOIT]: "EXPLOIT",
  [KillChainStage.INSTALL]: "INSTALL",
  [KillChainStage.C2]: "C2",
  [KillChainStage.ACTION]: "ACTION",
};

interface NodeDetailPanelProps {
  nodeId: string | null;
  topologyData: TopologyData | null;
  nodeKillChainMap: Record<string, KillChainStage>;
  operationId: string;
}

export function NodeDetailPanel({
  nodeId,
  topologyData,
  nodeKillChainMap,
  operationId,
}: NodeDetailPanelProps) {
  const [facts, setFacts] = useState<FactRow[]>([]);
  const [loadingFacts, setLoadingFacts] = useState(false);

  const node = topologyData?.nodes.find((n) => n.id === nodeId) ?? null;

  useEffect(() => {
    if (!nodeId || !operationId) return;
    setLoadingFacts(true);
    api
      .get<FactRow[]>(`/operations/${operationId}/facts`)
      .then((all) => {
        setFacts(all.filter((f) => f.source_target_id === nodeId));
      })
      .catch(() => setFacts([]))
      .finally(() => setLoadingFacts(false));
  }, [nodeId, operationId]);

  if (!nodeId || !node) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 h-full flex items-center justify-center">
        <span className="text-xs font-mono text-athena-text-secondary text-center">
          Select a node<br />to view details
        </span>
      </div>
    );
  }

  const isCompromised = !!node.data?.isCompromised;
  const role = (node.data?.role as string) || "host";
  const ip = (node.data?.ip_address as string) || "—";
  const os = (node.data?.os as string) || "—";
  const priv = (node.data?.privilege_level as string) || null;
  const kcStage = nodeKillChainMap[nodeId] ?? null;
  const kcIndex = kcStage ? KC_STAGES.indexOf(kcStage) : -1;

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 space-y-4 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-mono font-bold text-athena-text-primary truncate">
          {node.label}
        </span>
        <span
          className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
            isCompromised
              ? "text-red-400 border-red-500/40 bg-red-500/10"
              : "text-green-400 border-green-500/40 bg-green-500/10"
          }`}
        >
          {isCompromised ? "COMPROMISED" : "SECURE"}
        </span>
      </div>

      {/* Basic info */}
      <div className="space-y-1.5">
        {[
          ["IP", ip],
          ["OS", os],
          ["ROLE", role],
          ...(priv ? [["PRIV", priv]] : []),
        ].map(([label, value]) => (
          <div key={label} className="flex gap-2 text-[11px] font-mono">
            <span className="text-athena-text-secondary w-10 shrink-0">{label}</span>
            <span className="text-athena-text-primary break-all">{value}</span>
          </div>
        ))}
      </div>

      {/* Kill Chain progress */}
      <div>
        <div className="text-[10px] font-mono text-athena-text-secondary mb-2 tracking-wider">
          KILL CHAIN
        </div>
        <div className="flex gap-0.5">
          {KC_STAGES.map((stage, i) => {
            const reached = i <= kcIndex;
            const isCurrent = i === kcIndex;
            return (
              <div
                key={stage}
                className="flex-1 flex flex-col items-center gap-1"
                title={KC_LABELS[stage]}
              >
                <div
                  className="w-full h-2 rounded-sm"
                  style={{
                    background: reached
                      ? KILL_CHAIN_COLORS[stage]
                      : "rgba(255,255,255,0.08)",
                    boxShadow: isCurrent
                      ? `0 0 6px ${KILL_CHAIN_COLORS[stage]}`
                      : undefined,
                  }}
                />
                {isCurrent && (
                  <span
                    className="text-[10px] font-mono leading-none"
                    style={{ color: KILL_CHAIN_COLORS[stage] }}
                  >
                    {KC_LABELS[stage]}
                  </span>
                )}
              </div>
            );
          })}
        </div>
        {kcStage === null && (
          <p className="text-[10px] font-mono text-athena-text-secondary mt-1">
            No attack stage recorded
          </p>
        )}
      </div>

      {/* Collected Facts */}
      <div>
        <div className="text-[10px] font-mono text-athena-text-secondary mb-2 tracking-wider">
          COLLECTED FACTS {loadingFacts && <span className="animate-pulse">…</span>}
          {!loadingFacts && <span className="ml-1 text-athena-accent">({facts.length})</span>}
        </div>
        {facts.length === 0 && !loadingFacts && (
          <p className="text-[10px] font-mono text-athena-text-secondary">No facts collected</p>
        )}
        <div className="space-y-1">
          {facts.map((f) => (
            <div key={f.id} className="text-[10px] font-mono space-y-0.5">
              <span className="text-athena-accent/80">{f.trait}</span>
              <div className="text-athena-text-primary break-all pl-2 opacity-80">
                {f.value.length > 60 ? f.value.slice(0, 60) + "…" : f.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
