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

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { useTools } from "@/hooks/useTools";
import { TabBar } from "@/components/nav/TabBar";
import { Button } from "@/components/atoms/Button";
import { ToolRegistryTable } from "@/components/tools/ToolRegistryTable";
import { AddToolModal } from "@/components/tools/AddToolModal";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { MCPServerStatusPanel } from "@/components/tools/MCPServerStatusPanel";
import { PageLoading } from "@/components/ui/PageLoading";
import type { ToolRegistryCreate } from "@/types/tool";

export default function ToolsPage() {
  const t = useTranslations("Tools");
  const [activeTab, setActiveTab] = useState<string>("tool");
  const [showAddModal, setShowAddModal] = useState(false);

  const tabs = useMemo(
    () => [
      { id: "tool", label: t("reconTools") },
      { id: "engine", label: t("executionEngines") },
    ],
    [t],
  );

  const {
    tools,
    loading,
    fetchTools,
    toggleEnabled,
    checkHealth,
    deleteTool,
    createTool,
  } = useTools(activeTab as "tool" | "engine");

  async function handleCreateTool(data: ToolRegistryCreate) {
    await createTool(data);
    setShowAddModal(false);
    fetchTools();
  }

  if (loading) return <PageLoading />;

  return (
    <div className="space-y-4">
      {/* Page Header */}
      <SectionHeader
        trailing={
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowAddModal(true)}
          >
            {t("addTool")}
          </Button>
        }
      >
        {t("title")}
      </SectionHeader>

      {/* MCP Server Status */}
      <MCPServerStatusPanel />

      {/* Tab Bar */}
      <TabBar tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Tool Table */}
      <ToolRegistryTable
        tools={tools}
        onToggleEnabled={toggleEnabled}
        onCheckHealth={checkHealth}
        onDelete={deleteTool}
      />

      {/* Add Tool Modal */}
      <AddToolModal
        isOpen={showAddModal}
        onSubmit={handleCreateTool}
        onCancel={() => setShowAddModal(false)}
      />
    </div>
  );
}
