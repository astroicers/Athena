// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { useState } from "react";
import { useTools } from "@/hooks/useTools";
import { TabBar } from "@/components/nav/TabBar";
import { Button } from "@/components/atoms/Button";
import { ToolRegistryTable } from "@/components/tools/ToolRegistryTable";
import { AddToolModal } from "@/components/tools/AddToolModal";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { PageLoading } from "@/components/ui/PageLoading";
import type { ToolRegistryCreate } from "@/types/tool";

const TABS = [
  { id: "tool", label: "Recon Tools" },
  { id: "engine", label: "Execution Engines" },
];

export default function ToolsPage() {
  const [activeTab, setActiveTab] = useState<string>("tool");
  const [showAddModal, setShowAddModal] = useState(false);

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
            + ADD TOOL
          </Button>
        }
      >
        Tool Registry
      </SectionHeader>

      {/* Tab Bar */}
      <TabBar tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

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
