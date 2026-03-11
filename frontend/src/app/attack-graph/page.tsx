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
import { PageHeader } from "@/components/layout/PageHeader";
import { useOperationId } from "@/contexts/OperationContext";
import { useAttackGraph } from "@/hooks/useAttackGraph";
import { AttackGraphCanvas } from "@/components/attack-graph/AttackGraphCanvas";
import { CredentialGraphCanvas } from "@/components/attack-graph/CredentialGraphCanvas";

type Tab = "graph" | "credentials";

export default function AttackGraphPage() {
  const t = useTranslations("AttackGraph");
  const operationId = useOperationId();
  const { graph, credentialGraph, loading, error, rebuild } =
    useAttackGraph(operationId);

  const [activeTab, setActiveTab] = useState<Tab>("graph");
  const [rebuilding, setRebuilding] = useState(false);

  const handleRebuild = async () => {
    setRebuilding(true);
    try {
      await rebuild();
    } finally {
      setRebuilding(false);
    }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "graph", label: t("tabGraph") },
    { key: "credentials", label: t("tabCredentials") },
  ];

  /* ── Loading skeleton ── */
  if (loading) {
    return (
      <div className="flex flex-col h-full athena-grid-bg">
        <PageHeader title={t("title")} />
        <div className="flex-1 flex items-center justify-center">
          <div className="space-y-3 w-64">
            <div className="h-3 bg-athena-bg-secondary rounded animate-pulse" />
            <div className="h-3 bg-athena-bg-secondary rounded animate-pulse w-3/4" />
            <div className="h-3 bg-athena-bg-secondary rounded animate-pulse w-1/2" />
          </div>
        </div>
      </div>
    );
  }

  /* ── Error state ── */
  if (error) {
    return (
      <div className="flex flex-col h-full athena-grid-bg">
        <PageHeader title={t("title")} />
        <div className="flex-1 flex items-center justify-center">
          <span className="text-xs font-mono text-red-400 uppercase tracking-widest">
            {error}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full athena-grid-bg">
      <PageHeader title={t("title")} />

      {/* Tab bar */}
      <div className="flex border-b border-athena-border px-4">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-xs font-mono uppercase tracking-wider transition-colors
              ${
                activeTab === tab.key
                  ? "text-athena-accent border-b-2 border-athena-accent"
                  : "text-athena-text-secondary hover:text-athena-text"
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col min-h-0">
        {activeTab === "graph" && graph && (
          <AttackGraphCanvas
            nodes={graph.nodes}
            edges={graph.edges}
            stats={graph.stats}
            onRebuild={handleRebuild}
            rebuilding={rebuilding}
          />
        )}

        {activeTab === "graph" && !graph && (
          <div className="flex-1 flex items-center justify-center">
            <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-widest">
              {t("noData")}
            </span>
          </div>
        )}

        {activeTab === "credentials" && credentialGraph && (
          <CredentialGraphCanvas
            nodes={credentialGraph.nodes}
            edges={credentialGraph.edges}
          />
        )}

        {activeTab === "credentials" && !credentialGraph && (
          <div className="flex-1 flex items-center justify-center">
            <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-widest">
              {t("noCredentials")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
