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
import type { TopologyData, NodeSummary } from "@/types/api";
import { KillChainStage } from "@/types/enums";
import { api } from "@/lib/api";
import { KILL_CHAIN_COLORS } from "./topologyColors";

interface FactRow {
  id: string;
  trait: string;
  value: string;
  category: string;
  sourceTargetId: string | null;
}

type CardTab = "facts" | "ai" | "basic";

const CARD_W = 420;
const OFFSET_X = 20;
const OFFSET_Y = -40;

const CATEGORY_ORDER = ["credential", "host", "service", "network"];
// Category colors mapped to design tokens (see globals.css --color-*)
const CATEGORY_COLORS: Record<string, string> = {
  credential: "var(--color-error)",     // #ff4444
  host: "var(--color-info)",            // #00d4ff
  service: "var(--color-success)",      // #00ff88
  network: "var(--color-warning)",      // #ffaa00
};
const CATEGORY_KEYS: Record<string, string> = {
  credential: "catCredential",
  host: "catHost",
  service: "catService",
  network: "catNetwork",
};
const FACTS_PER_CATEGORY = 5;

const AI_SECTION_ICONS: Record<string, string> = {
  attackSurface: "◇",
  credentialChain: "◆",
  lateralMovement: "→",
  persistenceOpp: "⚑",
  riskAssessment: "⚠",
  recommendedNext: "▶",
};

const AI_SECTION_KEYS = [
  "attackSurface",
  "credentialChain",
  "lateralMovement",
  "persistenceOpp",
  "riskAssessment",
  "recommendedNext",
] as const;

// Maps i18n key → API response field
const AI_FIELD_MAP: Record<string, string> = {
  attackSurface: "attackSurface",
  credentialChain: "credentialChain",
  lateralMovement: "lateralMovement",
  persistenceOpp: "persistence",
  riskAssessment: "riskAssessment",
  recommendedNext: "recommendedNext",
};

interface FloatingNodeCardProps {
  nodeId: string;
  topologyData: TopologyData;
  nodeKillChainMap: Record<string, KillChainStage>;
  operationId: string;
  screenX: number;
  screenY: number;
  containerWidth: number;
  containerHeight: number;
  onClose: () => void;
  onReconScan?: (targetId: string) => void;
  onInitialAccess?: (targetId: string) => void;
}

export function FloatingNodeCard({
  nodeId,
  topologyData,
  nodeKillChainMap,
  operationId,
  screenX,
  screenY,
  containerWidth,
  containerHeight,
  onClose,
  onReconScan,
  onInitialAccess,
}: FloatingNodeCardProps) {
  const t = useTranslations("Topology");
  const tKC = useTranslations("KillChain");
  const [facts, setFacts] = useState<FactRow[]>([]);
  const [loadingFacts, setLoadingFacts] = useState(false);
  const [activeTab, setActiveTab] = useState<CardTab>("facts");
  const [summary, setSummary] = useState<NodeSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [killChainStages, setKillChainStages] = useState<Record<string, boolean> | null>(null);
  const [killChainLoading, setKillChainLoading] = useState(false);

  const node = topologyData.nodes.find((n) => n.id === nodeId) ?? null;
  const isC2 = node?.type === "c2";

  useEffect(() => {
    if (!nodeId || !operationId) return;
    setLoadingFacts(true);
    api
      .get<FactRow[]>(`/operations/${operationId}/facts?target_id=${nodeId}`)
      .then(setFacts)
      .catch(() => setFacts([]))
      .finally(() => setLoadingFacts(false));

    // Fetch kill chain progress for this target
    setKillChainLoading(true);
    api
      .get<{ stages: Record<string, boolean> }>(
        `/operations/${operationId}/targets/${nodeId}/kill-chain`,
      )
      .then((data) => setKillChainStages(data.stages ?? null))
      .catch(() => setKillChainStages(null))
      .finally(() => setKillChainLoading(false));
  }, [nodeId, operationId]);

  // Lazy-load AI summary only when tab is activated
  const loadSummary = (force = false) => {
    setSummaryLoading(true);
    setSummaryError(false);
    api
      .get<NodeSummary>(
        `/operations/${operationId}/targets/${nodeId}/summary${force ? "?force_refresh=true" : ""}`
      )
      .then((data) => {
        setSummary(data);
        setSummaryError(false);
      })
      .catch(() => setSummaryError(true))
      .finally(() => setSummaryLoading(false));
  };

  useEffect(() => {
    if (activeTab !== "ai" || summary || summaryLoading) return;
    loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  // Group facts by category
  const groupedFacts = useMemo(() => {
    const groups: Record<string, FactRow[]> = {};
    for (const f of facts) {
      const cat = f.category || "other";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(f);
    }
    const sortedKeys = [
      ...CATEGORY_ORDER.filter((k) => groups[k]),
      ...Object.keys(groups)
        .filter((k) => !CATEGORY_ORDER.includes(k))
        .sort(),
    ];
    return sortedKeys.map((k) => ({ category: k, facts: groups[k] }));
  }, [facts]);

  if (!node) return null;

  const isCompromised = !!node.data?.isCompromised;
  const role = (node.data?.role as string) || "host";
  const ip = (node.data?.ipAddress as string) || "—";
  const osFact = facts.find((f) => f.trait === "host.os");
  const os = (node.data?.os as string) || osFact?.value || "—";
  const priv = (node.data?.privilegeLevel as string) || null;
  const kcStage = nodeKillChainMap[nodeId] ?? null;

  // Position calculation with boundary detection
  let left = screenX + OFFSET_X;
  if (left + CARD_W > containerWidth) {
    left = screenX - CARD_W - 10;
  }
  let top = screenY + OFFSET_Y;
  if (top < 0) top = 10;
  if (left < 0) left = 10;

  const toggleCategory = (cat: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const tabs: { key: CardTab; label: string }[] = [
    { key: "facts", label: t("tabFacts") },
    ...(isC2 ? [] : [{ key: "ai" as CardTab, label: t("tabAI") }]),
    { key: "basic", label: t("tabBasic") },
  ];

  return (
    <div
      className="absolute z-20 pointer-events-auto overflow-hidden"
      style={{ left, top, width: CARD_W }}
    >
      <div className="bg-athena-surface border border-athena-border rounded-athena-sm shadow-lg flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-1.5 border-b border-athena-border shrink-0">
          <span className="text-[13px] font-mono font-bold text-athena-text-primary truncate mr-2">
            {node.label}
          </span>
          <div className="flex items-center gap-1.5 shrink-0">
            <span
              className={`text-xs font-mono px-1 py-0.5 rounded border ${
                isCompromised
                  ? "text-red-400 border-red-500/40 bg-red-500/10"
                  : "text-green-400 border-green-500/40 bg-green-500/10"
              }`}
            >
              {isCompromised ? t("compromised") : t("secure")}
            </span>
            <button
              onClick={onClose}
              className="text-athena-text-secondary hover:text-athena-text transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* Tab Bar */}
        <div className="flex border-b border-athena-border/30 shrink-0">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-1 text-[12px] font-mono transition-colors ${
                activeTab === tab.key
                  ? "text-athena-accent border-b border-athena-accent"
                  : "text-athena-text-secondary hover:text-athena-text-primary"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="px-3 py-1.5">
          {/* Facts Tab */}
          {activeTab === "facts" && (
            <div>
              {loadingFacts && (
                <div className="text-[12px] font-mono text-athena-text-secondary animate-pulse py-2">
                  …
                </div>
              )}
              {!loadingFacts && facts.length === 0 && (
                <p className="text-[12px] font-mono text-athena-text-secondary">
                  {t("noFacts")}
                </p>
              )}
              {!loadingFacts &&
                groupedFacts.map(({ category, facts: catFacts }) => {
                  const color = CATEGORY_COLORS[category] || "var(--color-text-secondary)";
                  const catKey = CATEGORY_KEYS[category] || "catOther";
                  const isExpanded = expandedCategories.has(category);
                  const displayFacts = isExpanded
                    ? catFacts
                    : catFacts.slice(0, FACTS_PER_CATEGORY);
                  const hasMore = catFacts.length > FACTS_PER_CATEGORY;
                  const isCredential = category === "credential";

                  return (
                    <div
                      key={category}
                      className={`mb-1.5 ${isCredential ? "border-l-2 border-red-500/50 pl-1.5" : ""}`}
                    >
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span
                          className="w-1.5 h-1.5 rounded-full shrink-0"
                          style={{ background: color }}
                        />
                        <span className="text-[12px] font-mono text-athena-accent">
                          {t(catKey)}
                        </span>
                        <span className="text-xs font-mono text-athena-text-secondary">
                          ({catFacts.length})
                        </span>
                      </div>
                      {displayFacts.map((f) => (
                        <div
                          key={f.id}
                          className="text-[12px] font-mono mb-1 pl-3"
                        >
                          <div className="text-athena-text-secondary text-xs">
                            {f.trait}
                          </div>
                          <div className="text-athena-text-primary break-all">
                            {f.value}
                          </div>
                        </div>
                      ))}
                      {hasMore && (
                        <button
                          onClick={() => toggleCategory(category)}
                          className="text-xs font-mono text-athena-accent hover:underline pl-3"
                        >
                          {isExpanded
                            ? "▲"
                            : t("moreItems", {
                                count: catFacts.length - FACTS_PER_CATEGORY,
                              })}
                        </button>
                      )}
                    </div>
                  );
                })}
            </div>
          )}

          {/* AI Summary Tab */}
          {activeTab === "ai" && (
            <div>
              {summaryLoading && (
                <div className="py-4 text-center">
                  <div className="text-[12px] font-mono text-athena-text-secondary animate-pulse">
                    {t("aiAnalyzing")}
                  </div>
                  <div className="mt-2 h-1 w-32 mx-auto bg-athena-border/50 rounded overflow-hidden">
                    <div className="h-full w-1/3 bg-athena-accent/60 rounded animate-[shimmer_1.5s_ease-in-out_infinite]" />
                  </div>
                </div>
              )}
              {summaryError && !summaryLoading && (
                <div className="py-3 text-center">
                  <p className="text-[12px] font-mono text-red-400 mb-2">
                    {t("aiError")}
                  </p>
                  <button
                    onClick={() => loadSummary(true)}
                    className="text-xs font-mono text-athena-accent hover:underline"
                  >
                    {t("aiRetry")}
                  </button>
                </div>
              )}
              {summary && !summaryLoading && !summaryError && (
                <div>
                  {AI_SECTION_KEYS.map((key) => {
                    const fieldKey = AI_FIELD_MAP[key];
                    const value =
                      summary.summary[
                        fieldKey as keyof typeof summary.summary
                      ] || "—";
                    return (
                      <div key={key} className="mb-1.5">
                        <div className="flex items-center gap-1 text-[12px] font-mono">
                          <span className="text-athena-accent">
                            {AI_SECTION_ICONS[key]}
                          </span>
                          <span className="text-athena-accent font-bold">
                            {t(key)}
                          </span>
                        </div>
                        <p className="text-[12px] font-mono text-athena-text-primary pl-4 leading-relaxed">
                          {value}
                        </p>
                      </div>
                    );
                  })}
                  <div className="flex items-center justify-between border-t border-athena-border/30 pt-1 mt-1">
                    <button
                      onClick={() => loadSummary(true)}
                      className="text-xs font-mono text-athena-accent hover:underline"
                    >
                      ↻ {t("aiRetry")}
                    </button>
                    <div className="flex items-center gap-2 text-xs font-mono text-athena-text-secondary">
                      <span>{summary.model}</span>
                      {summary.cached && (
                        <span className="text-green-400">{t("aiCached")}</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Basic Tab */}
          {activeTab === "basic" && (
            <div>
              <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[12px] font-mono mb-1.5">
                {[
                  [t("ip"), ip],
                  [t("os"), os],
                  [t("role"), role],
                  ...(priv ? [[t("privilege"), priv]] : []),
                ].map(([label, value]) => (
                  <div key={label} className="flex gap-1">
                    <span className="text-athena-text-secondary">{label}</span>
                    <span className="text-athena-text-primary truncate">
                      {value}
                    </span>
                  </div>
                ))}
              </div>

              {kcStage && (
                <div className="flex items-center gap-2 border-t border-athena-border/30 pt-1">
                  <span className="text-[12px] font-mono text-athena-text-secondary">
                    {t("killChain")}
                  </span>
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ background: KILL_CHAIN_COLORS[kcStage] }}
                  />
                  <span
                    className="text-[12px] font-mono"
                    style={{ color: KILL_CHAIN_COLORS[kcStage] }}
                  >
                    {tKC(kcStage as any)}
                  </span>
                </div>
              )}

              {/* Kill Chain Progress Bar */}
              {!killChainLoading && killChainStages && (
                <div className="border-t border-athena-border/30 pt-1 mt-1">
                  <span className="text-[12px] font-mono text-athena-text-secondary mb-1 block">
                    {tKC("progress")}
                  </span>
                  <div className="flex gap-0.5">
                    {(["recon", "weaponize", "deliver", "exploit", "install", "c2", "action"] as const).map((stage) => {
                      const reached = !!killChainStages[stage];
                      const color = reached
                        ? KILL_CHAIN_COLORS[stage as KillChainStage]
                        : undefined;
                      return (
                        <div key={stage} className="flex-1 flex flex-col items-center gap-0.5">
                          <div
                            className="w-full h-2 rounded-sm"
                            style={{
                              background: reached ? color : "var(--color-border)",
                              opacity: reached ? 1 : 0.3,
                            }}
                          />
                          <span
                            className="text-[8px] font-mono leading-none"
                            style={{ color: reached ? color : "var(--color-text-secondary)" }}
                          >
                            {tKC(stage as "recon" | "weaponize" | "deliver" | "exploit" | "install" | "c2" | "action")}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {killChainLoading && (
                <div className="border-t border-athena-border/30 pt-1 mt-1">
                  <div className="text-[12px] font-mono text-athena-text-secondary animate-pulse">
                    {tKC("progress")}...
                  </div>
                </div>
              )}

              <div className="border-t border-athena-border/30 pt-1 mt-1">
                <span className="text-[12px] font-mono text-athena-text-secondary">
                  {t("collectedFacts")}{" "}
                  {loadingFacts ? (
                    <span className="animate-pulse">…</span>
                  ) : (
                    <span className="text-athena-accent">({facts.length})</span>
                  )}
                </span>
              </div>

              {/* Recon / Initial Access actions */}
              {!isC2 && (onReconScan || onInitialAccess) && (
                <div className="flex gap-2 border-t border-athena-border pt-1.5 mt-1.5">
                  {onReconScan && (
                    <button
                      onClick={() => onReconScan(nodeId)}
                      className="flex-1 px-2 py-1 text-xs font-mono font-bold text-athena-accent bg-athena-accent/10 border border-athena-accent rounded-athena-sm hover:bg-athena-accent/20 transition-colors"
                    >
                      {t("reconScan")}
                    </button>
                  )}
                  {onInitialAccess && (
                    <button
                      onClick={() => onInitialAccess(nodeId)}
                      className="flex-1 px-2 py-1 text-xs font-mono font-bold text-amber-400 bg-amber-500/10 border border-amber-500 rounded-athena-sm hover:bg-amber-500/20 transition-colors"
                    >
                      {t("initialAccess")}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
