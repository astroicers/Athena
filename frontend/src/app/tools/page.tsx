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

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useTools } from "@/hooks/useTools";
import { useMCPServers } from "@/hooks/useMCPServers";
import { Button } from "@/components/atoms/Button";
import { ToolRegistryTable } from "@/components/tools/ToolRegistryTable";
import { PlaybookBrowser } from "@/components/tools/PlaybookBrowser";
import { OnboardingGuide } from "@/components/tools/OnboardingGuide";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { PageLoading } from "@/components/ui/PageLoading";

type ToolsTab = "registry" | "playbooks";

export default function ToolsPage() {
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
    <div className="space-y-4">
      {/* Page Header */}
      <SectionHeader
        trailing={
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowGuide(true)}
          >
            {t("howToAdd")}
          </Button>
        }
      >
        {t("title")}
      </SectionHeader>

      {/* Tab Bar */}
      <div className="flex items-center gap-0 border-b border-athena-border">
        <button
          onClick={() => setActiveTab("registry")}
          className={`px-4 py-2 text-xs font-mono font-bold uppercase tracking-wider transition-colors
            ${activeTab === "registry"
              ? "text-athena-accent border-b-2 border-athena-accent"
              : "text-athena-text-secondary hover:text-athena-text"
            }`}
        >
          {t("registryTab")}
        </button>
        <button
          onClick={() => setActiveTab("playbooks")}
          className={`px-4 py-2 text-xs font-mono font-bold uppercase tracking-wider transition-colors
            ${activeTab === "playbooks"
              ? "text-athena-accent border-b-2 border-athena-accent"
              : "text-athena-text-secondary hover:text-athena-text"
            }`}
        >
          {t("playbooksTab")}
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
