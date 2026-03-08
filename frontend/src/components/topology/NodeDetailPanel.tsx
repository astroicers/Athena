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

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import type { TopologyData } from "@/types/api";
import { KillChainStage } from "@/types/enums";
import { api } from "@/lib/api";
import { KILL_CHAIN_COLORS } from "./NetworkTopology";

interface FactRow {
  id: string;
  trait: string;
  value: string;
  category: string;
  sourceTargetId: string | null;
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
  const t = useTranslations("Topology");
  const tKC = useTranslations("KillChain");
  const [facts, setFacts] = useState<FactRow[]>([]);
  const [loadingFacts, setLoadingFacts] = useState(false);

  const node = topologyData?.nodes.find((n) => n.id === nodeId) ?? null;

  useEffect(() => {
    if (!nodeId || !operationId) return;
    setLoadingFacts(true);
    api
      .get<FactRow[]>(`/operations/${operationId}/facts`)
      .then((all) => {
        setFacts(all.filter((f) => f.sourceTargetId === nodeId));
      })
      .catch(() => setFacts([]))
      .finally(() => setLoadingFacts(false));
  }, [nodeId, operationId]);

  if (!nodeId || !node) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 h-full flex items-center justify-center">
        <span className="text-xs font-mono text-athena-text-secondary text-center">
          {t("selectNode")}<br />{t("toViewDetails")}
        </span>
      </div>
    );
  }

  const isCompromised = !!node.data?.isCompromised;
  const role = (node.data?.role as string) || "host";
  const ip = (node.data?.ipAddress as string) || "—";
  const osFact = facts.find((f) => f.trait === "host.os");
  const os = (node.data?.os as string) || osFact?.value || "—";
  const priv = (node.data?.privilegeLevel as string) || null;
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
          className={`text-sm font-mono px-2 py-0.5 rounded border ${
            isCompromised
              ? "text-red-400 border-red-500/40 bg-red-500/10"
              : "text-green-400 border-green-500/40 bg-green-500/10"
          }`}
        >
          {isCompromised ? t("compromised") : t("secure")}
        </span>
      </div>

      {/* Basic info */}
      <div className="space-y-1.5">
        {[
          [t("ip"), ip],
          [t("os"), os],
          [t("role"), role],
          ...(priv ? [[t("privilege"), priv]] : []),
        ].map(([label, value]) => (
          <div key={label} className="flex gap-2 text-xs font-mono">
            <span className="text-athena-text-secondary w-10 shrink-0">{label}</span>
            <span className="text-athena-text-primary break-all">{value}</span>
          </div>
        ))}
      </div>

      {/* Kill Chain progress */}
      <div>
        <div className="text-sm font-mono text-athena-text-secondary mb-2 tracking-wider">
          {t("killChain")}
        </div>
        <div className="flex gap-0.5">
          {KC_STAGES.map((stage, i) => {
            const reached = i <= kcIndex;
            const isCurrent = i === kcIndex;
            return (
              <div
                key={stage}
                className="flex-1 flex flex-col items-center gap-1"
                title={tKC(stage as any)}
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
                    className="text-sm font-mono leading-none"
                    style={{ color: KILL_CHAIN_COLORS[stage] }}
                  >
                    {tKC(stage as any)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
        {kcStage === null && (
          <p className="text-sm font-mono text-athena-text-secondary mt-1">
            {t("noAttackStage")}
          </p>
        )}
      </div>

      {/* Collected Facts */}
      <div>
        <div className="text-sm font-mono text-athena-text-secondary mb-2 tracking-wider">
          {t("collectedFacts")} {loadingFacts && <span className="animate-pulse">…</span>}
          {!loadingFacts && <span className="ml-1 text-athena-accent">({facts.length})</span>}
        </div>
        {facts.length === 0 && !loadingFacts && (
          <p className="text-sm font-mono text-athena-text-secondary">{t("noFacts")}</p>
        )}
        <div className="space-y-1">
          {facts.map((f) => (
            <div key={f.id} className="text-sm font-mono space-y-0.5">
              <span className="text-athena-accent">{f.trait}</span>
              <div className="text-athena-text-primary break-all pl-2">
                {f.value.length > 60 ? f.value.slice(0, 60) + "…" : f.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
