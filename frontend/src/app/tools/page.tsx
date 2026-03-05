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
import { AddToolModal } from "@/components/tools/AddToolModal";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { PageLoading } from "@/components/ui/PageLoading";
import type { ToolRegistryCreate } from "@/types/tool";

export default function ToolsPage() {
  const t = useTranslations("Tools");
  const [showAddModal, setShowAddModal] = useState(false);

  const {
    tools,
    loading,
    fetchTools,
    toggleEnabled,
    deleteTool,
    createTool,
  } = useTools();

  const { servers } = useMCPServers();

  const containerStatuses = useMemo(() => {
    const map: Record<string, boolean> = {};
    for (const srv of servers) map[srv.name] = srv.connected;
    return map;
  }, [servers]);

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

      {/* All tools in a single table with container status */}
      <ToolRegistryTable
        tools={tools}
        onToggleEnabled={toggleEnabled}
        onDelete={deleteTool}
        containerStatuses={containerStatuses}
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
