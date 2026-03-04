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
  mcpStatuses: Record<string, boolean>;
}

export function ToolRegistryTable({
  tools,
  onToggleEnabled,
  onDelete,
  mcpStatuses,
}: ToolRegistryTableProps) {
  const t = useTranslations("Tools");
  const tRisk = useTranslations("Risk");
  const tCategory = useTranslations("ToolCategory");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(toolId: string) {
    setDeletingId(toolId);
    try {
      await onDelete(toolId);
    } finally {
      setDeletingId(null);
    }
  }

  function getMcpStatus(
    tool: ToolRegistryEntry,
  ): "online" | "offline" | "n/a" {
    const mcpServer = tool.configJson?.mcp_server as string | undefined;
    if (!mcpServer) return "n/a";
    return mcpStatuses[mcpServer] ? "online" : "offline";
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
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              {t("colCategory")}
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              {t("colStatus")}
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              {t("colRisk")}
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              {t("colMitre")}
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              {t("colMcpStatus")}
            </th>
          </tr>
        </thead>
        <tbody>
          {tools.map((tool) => {
            const status = getMcpStatus(tool);
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
                        <p className="text-[10px] text-athena-text-secondary mt-0.5 truncate max-w-[200px]">
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
                <td className="px-3 py-2">
                  <Badge variant="info">{tCategory(tool.category as any)}</Badge>
                </td>

                {/* Status toggle */}
                <td className="px-3 py-2">
                  <Toggle
                    checked={tool.enabled}
                    onChange={(checked) =>
                      onToggleEnabled(tool.toolId, checked)
                    }
                    label={tool.enabled ? t("on") : t("off")}
                  />
                </td>

                {/* Risk */}
                <td className="px-3 py-2">
                  <Badge
                    variant={RISK_VARIANT[tool.riskLevel] || "info"}
                  >
                    {tRisk(tool.riskLevel as any)}
                  </Badge>
                </td>

                {/* MITRE technique IDs */}
                <td className="px-3 py-2">
                  {tool.mitreTechniques.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {tool.mitreTechniques.map((tid) => (
                        <span
                          key={tid}
                          className="text-[10px] font-mono text-athena-accent bg-athena-accent/10 px-1.5 py-0.5 rounded"
                        >
                          {tid}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-athena-text-secondary">&mdash;</span>
                  )}
                </td>

                {/* MCP Status */}
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`inline-block h-2 w-2 rounded-full ${
                        status === "online"
                          ? "bg-emerald-400"
                          : status === "offline"
                            ? "bg-amber-400"
                            : "bg-neutral-500"
                      }`}
                    />
                    <span
                      className={`text-[10px] ${
                        status === "online"
                          ? "text-emerald-400"
                          : status === "offline"
                            ? "text-amber-400"
                            : "text-athena-text-secondary"
                      }`}
                    >
                      {status === "online"
                        ? t("mcpOnline")
                        : status === "offline"
                          ? t("mcpOffline")
                          : t("mcpNA")}
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
