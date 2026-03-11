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
import { Toggle } from "@/components/atoms/Toggle";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";

import { ToolExecuteModal } from "@/components/tools/ToolExecuteModal";
import type { ToolRegistryEntry } from "@/types/tool";

const RISK_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  low: "success",
  medium: "warning",
  high: "error",
  critical: "error",
};

interface ToolRegistryTableProps {
  tools: ToolRegistryEntry[];
  onToggleEnabled: (toolId: string, enabled: boolean) => Promise<void>;
  onDelete: (toolId: string) => Promise<void>;
  containerStatuses: Record<string, boolean>;
}

function getContainerStatus(
  tool: ToolRegistryEntry,
  containerStatuses: Record<string, boolean>,
): "online" | "offline" | "none" {
  const server = (tool.configJson?.mcpServer ?? tool.configJson?.mcp_server) as string | undefined;
  if (!server) return "none";
  return containerStatuses[server] ? "online" : "offline";
}

export function ToolRegistryTable({
  tools,
  onToggleEnabled,
  onDelete,
  containerStatuses,
}: ToolRegistryTableProps) {
  const t = useTranslations("Tools");
  const tRisk = useTranslations("Risk");
  const tCategory = useTranslations("ToolCategory");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<ToolRegistryEntry | null>(null);

  async function handleDelete(toolId: string) {
    setDeletingId(toolId);
    try {
      await onDelete(toolId);
    } finally {
      setDeletingId(null);
    }
  }

  if (tools.length === 0) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-6 text-center">
        <span className="text-xs font-mono text-athena-text-secondary">
          {t("noTools")}
        </span>
      </div>
    );
  }

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md overflow-hidden">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-athena-border">
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              {t("colName")}
            </th>
            <th className="px-3 py-2 text-center text-athena-text-secondary font-medium uppercase tracking-wider w-28">
              {t("colCategory")}
            </th>
            <th className="px-3 py-2 text-center text-athena-text-secondary font-medium uppercase tracking-wider w-20">
              {t("colStatus")}
            </th>
            <th className="px-3 py-2 text-center text-athena-text-secondary font-medium uppercase tracking-wider w-20">
              {t("colRisk")}
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider w-40">
              {t("colMitre")}
            </th>
            <th className="px-3 py-2 text-center text-athena-text-secondary font-medium uppercase tracking-wider w-24">
              {t("colContainer")}
            </th>
            <th className="px-3 py-2 text-center text-athena-text-secondary font-medium uppercase tracking-wider w-24">
              {t("colActions")}
            </th>
          </tr>
        </thead>
        <tbody>
          {tools.map((tool) => {
            const status = getContainerStatus(tool, containerStatuses);
            return (
              <tr
                key={tool.id}
                className="border-b border-athena-border/50 hover:bg-athena-elevated/30"
              >
                {/* Name + delete for user tools */}
                <td className="px-3 py-2 text-athena-text">
                  <div className="flex items-center gap-2">
                    <div className="min-w-0 flex-1">
                      <span className="text-athena-accent font-bold">
                        {tool.name}
                      </span>
                      {tool.description && (
                        <p className="text-sm text-athena-text-secondary mt-0.5 truncate max-w-[200px]">
                          {tool.description}
                        </p>
                      )}
                    </div>
                    {tool.source === "user" && (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(tool.toolId)}
                        disabled={deletingId === tool.toolId}
                      >
                        {deletingId === tool.toolId ? "..." : t("del")}
                      </Button>
                    )}
                  </div>
                </td>

                {/* Category */}
                <td className="px-3 py-2 text-center w-28">
                  <Badge variant="info">{tCategory(tool.category as any)}</Badge>
                </td>

                {/* Status toggle */}
                <td className="px-3 py-2 text-center w-20">
                  <Toggle
                    checked={tool.enabled}
                    onChange={(checked) =>
                      onToggleEnabled(tool.toolId, checked)
                    }
                    label={tool.enabled ? t("on") : t("off")}
                  />
                </td>

                {/* Risk */}
                <td className="px-3 py-2 text-center w-20">
                  <Badge
                    variant={RISK_VARIANT[tool.riskLevel] || "info"}
                  >
                    {tRisk(tool.riskLevel as any)}
                  </Badge>
                </td>

                {/* MITRE technique IDs */}
                <td className="px-3 py-2 w-40">
                  {tool.mitreTechniques.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {tool.mitreTechniques.map((tid) => (
                        <span
                          key={tid}
                          className="text-sm font-mono text-athena-accent bg-athena-accent/10 px-1.5 py-0.5 rounded"
                        >
                          {tid}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-athena-text-secondary">&mdash;</span>
                  )}
                </td>

                {/* Container status */}
                <td className="px-3 py-2 text-center w-24">
                  {status === "online" && (
                    <Badge variant="success">
                      <span className="relative inline-flex h-2.5 w-2.5 mr-1.5">
                        <span className="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping bg-[#00ff88]" />
                        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#00ff88]" />
                      </span>
                      {t("containerOnline")}
                    </Badge>
                  )}
                  {status === "offline" && (
                    <Badge variant="error">
                      <span className="relative inline-flex h-2.5 w-2.5 mr-1.5">
                        <span className="absolute inline-flex h-full w-full rounded-full opacity-50 animate-pulse bg-[#ff4444]" />
                        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#ff4444]" />
                      </span>
                      {t("containerOffline")}
                    </Badge>
                  )}
                  {status === "none" && (
                    <span className="text-sm text-athena-text-secondary">{t("containerNA")}</span>
                  )}
                </td>

                {/* Actions */}
                <td className="px-3 py-2 text-center w-24">
                  {tool.enabled && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setSelectedTool(tool)}
                    >
                      {t("execute")}
                    </Button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <ToolExecuteModal
        tool={selectedTool}
        onClose={() => setSelectedTool(null)}
      />
    </div>
  );
}
