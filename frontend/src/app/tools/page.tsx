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

import { Suspense, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useTools } from "@/hooks/useTools";
import { useMCPServers } from "@/hooks/useMCPServers";
import { Button } from "@/components/atoms/Button";
import { ToolRegistryTable } from "@/components/tools/ToolRegistryTable";
import { PlaybookBrowser } from "@/components/tools/PlaybookBrowser";
import { OnboardingGuide } from "@/components/tools/OnboardingGuide";
import { PageHeader } from "@/components/layout/PageHeader";
import { PageLoading } from "@/components/ui/PageLoading";
import { TabBar } from "@/components/nav/TabBar";

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
    <div className="athena-grid-bg flex flex-col h-full space-y-4">
      {/* Page Header */}
      <PageHeader
        title={t("title")}
        trailing={
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowGuide(true)}
          >
            {t("howToAdd")}
          </Button>
        }
      />

      {/* Tab Bar */}
      <TabBar
        tabs={[
          { id: "registry", label: t("registryTab") },
          { id: "playbooks", label: t("playbooksTab") },
        ]}
        activeTab={activeTab}
        onChange={(tabId) => setActiveTab(tabId as ToolsTab)}
      />

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
