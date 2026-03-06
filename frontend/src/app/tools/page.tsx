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
import { OnboardingGuide } from "@/components/tools/OnboardingGuide";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { PageLoading } from "@/components/ui/PageLoading";

export default function ToolsPage() {
  const t = useTranslations("Tools");
  const [showGuide, setShowGuide] = useState(false);

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

      {/* All tools in a single table with container status */}
      <ToolRegistryTable
        tools={tools}
        onToggleEnabled={toggleEnabled}
        onDelete={deleteTool}
        containerStatuses={containerStatuses}
      />

      {/* Onboarding Guide */}
      <OnboardingGuide
        isOpen={showGuide}
        onClose={() => setShowGuide(false)}
      />
    </div>
  );
}
