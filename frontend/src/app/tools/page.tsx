// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use client";

import { Suspense, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useTools } from "@/hooks/useTools";
import { useMCPServers } from "@/hooks/useMCPServers";
import { ToolRegistryTable } from "@/components/tools/ToolRegistryTable";
import { PlaybookBrowser } from "@/components/tools/PlaybookBrowser";
import { OnboardingGuide } from "@/components/tools/OnboardingGuide";
import { PageLoading } from "@/components/ui/PageLoading";

type ToolsTab = "registry" | "playbooks";

export default function ToolsPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <ToolsContent />
    </Suspense>
  );
}

function ToolsContent() {
  const t = useTranslations("Tools");
  const [showGuide, setShowGuide] = useState(false);
  const [activeTab, setActiveTab] = useState<ToolsTab>("registry");

  const {
    tools,
    loading,
    toggleEnabled,
    deleteTool,
  } = useTools();

  const { servers } = useMCPServers();

  const containerStatuses = useMemo(() => {
    const map: Record<string, boolean> = {};
    for (const srv of servers) map[srv.name] = srv.connected;
    return map;
  }, [servers]);

  if (loading) return <PageLoading />;

  return (
    <div className="flex flex-col h-full">
      {/* Tab Bar + Actions — 40px, fill #09090B */}
      <div className="flex items-center justify-between h-10 px-4 bg-[var(--color-bg-primary)]">
        <div className="flex items-center h-full">
        <button
          onClick={() => setActiveTab("registry")}
          className={`relative h-full px-4 font-mono text-[12px] flex items-center cursor-pointer bg-transparent border-none transition-colors ${
            activeTab === "registry"
              ? "text-[var(--color-accent)] font-semibold"
              : "text-[var(--color-text-tertiary)] font-normal hover:text-[var(--color-text-secondary)]"
          }`}
        >
          {t("registryTab")}
          {activeTab === "registry" && (
            <span className="absolute bottom-0 left-4 right-4 h-[2px] bg-[var(--color-accent)]" />
          )}
        </button>
        <button
          onClick={() => setActiveTab("playbooks")}
          className={`relative h-full px-4 font-mono text-[12px] flex items-center cursor-pointer bg-transparent border-none transition-colors ${
            activeTab === "playbooks"
              ? "text-[var(--color-accent)] font-semibold"
              : "text-[var(--color-text-tertiary)] font-normal hover:text-[var(--color-text-secondary)]"
          }`}
        >
          {t("playbooksTab")}
          {activeTab === "playbooks" && (
            <span className="absolute bottom-0 left-4 right-4 h-[2px] bg-[var(--color-accent)]" />
          )}
        </button>
        </div>
        <button
          onClick={() => setShowGuide(true)}
          className="font-mono text-xs font-semibold text-[var(--color-text-primary)] bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)] rounded-[var(--radius)] px-3 py-1 cursor-pointer hover:bg-[var(--color-bg-elevated)] transition-colors"
        >
          {t("howToAdd")}
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "registry" ? (
        <ToolRegistryTable
          tools={tools}
          onToggleEnabled={toggleEnabled}
          onDelete={deleteTool}
          containerStatuses={containerStatuses}
        />
      ) : (
        <PlaybookBrowser />
      )}

      {/* Onboarding Guide */}
      <OnboardingGuide
        isOpen={showGuide}
        onClose={() => setShowGuide(false)}
      />
    </div>
  );
}
