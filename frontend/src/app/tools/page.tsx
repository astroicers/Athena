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
    fetchTools,
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
      {/* Page Header — 48px, fill #18181B */}
      <header className="flex items-center justify-between h-12 px-4 bg-[var(--color-bg-surface)]">
        <div className="flex items-center gap-3">
          <h2 className="font-mono text-[13px] font-bold text-[var(--color-text-primary)]">
            {t("title")}
          </h2>
          <span className="font-mono text-[10px] font-semibold text-[var(--color-accent)] bg-[#1E609120] border border-[#1E609140] rounded-[var(--radius)] px-2.5 py-1">
            PHANTOM-EYE
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowGuide(true)}
            className="font-mono text-[11px] font-semibold text-[var(--color-text-primary)] bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)] rounded-[var(--radius)] px-3 py-1 cursor-pointer hover:bg-[var(--color-bg-elevated)] transition-colors"
          >
            {t("howToAdd")}
          </button>
          {/* Bell icon */}
          <div className="relative">
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              className="text-[var(--color-text-secondary)]"
            >
              <path
                d="M8 1.5a4.5 4.5 0 00-4.5 4.5v2.7L2.4 10.6a.75.75 0 00.6 1.15h10a.75.75 0 00.6-1.15L12.5 8.7V6A4.5 4.5 0 008 1.5zM6.5 12.5a1.5 1.5 0 003 0"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {/* Red badge */}
            <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-[var(--color-error)] rounded-full border-2 border-[var(--color-bg-surface)]" />
          </div>
        </div>
      </header>

      {/* Tab Bar — 40px, fill #09090B */}
      <div className="flex items-center h-10 px-4 bg-[var(--color-bg-primary)]">
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
