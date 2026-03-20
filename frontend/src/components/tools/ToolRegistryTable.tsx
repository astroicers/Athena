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

import { useState } from "react";
import { useTranslations } from "next-intl";

import { ToolExecuteModal } from "@/components/tools/ToolExecuteModal";
import { Button } from "@/components/atoms/Button";
import type { ToolRegistryEntry } from "@/types/tool";
import { COLORS } from "@/lib/designTokens";

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  recon: { bg: `${COLORS.accent}20`, text: COLORS.accent },
  execution: { bg: "#7C3AED20", text: "#A78BFA" },
  vuln_scan: { bg: `${COLORS.success}20`, text: COLORS.success },
  credential: { bg: `${COLORS.error}20`, text: COLORS.error },
};

const RISK_COLORS: Record<string, { bg: string; text: string }> = {
  low: { bg: `${COLORS.success}20`, text: COLORS.success },
  medium: { bg: `${COLORS.warning}20`, text: COLORS.warning },
  high: { bg: "#FB923C20", text: "#FB923C" },
  critical: { bg: `${COLORS.error}20`, text: COLORS.error },
};

const DEFAULT_CATEGORY_COLOR = { bg: `${COLORS.textSecondary}20`, text: COLORS.textSecondary };

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
      <div
        className="rounded-athena text-center p-6 border border-athena-border/25"
      >
        <span className="font-mono text-xs text-athena-text-secondary">
          {t("noTools")}
        </span>
      </div>
    );
  }

  return (
    <div>
      {/* Header row */}
      <div
        className="flex items-center font-mono uppercase tracking-wider h-9 px-3 text-athena-text-secondary text-[10px] font-semibold border-b border-athena-border"
      >
        <div className="w-[260px] shrink-0">{t("colName")}</div>
        <div className="w-[120px] shrink-0">{t("colCategory")}</div>
        <div className="w-[70px] shrink-0">{t("colStatus")}</div>
        <div className="w-[80px] shrink-0">{t("colRisk")}</div>
        <div className="w-[180px] shrink-0">{t("colMitre")}</div>
        <div className="w-[100px] shrink-0">{t("colContainer")}</div>
        <div className="w-[80px] shrink-0 text-center">{t("colActions")}</div>
      </div>

      {/* Data rows */}
      {tools.map((tool) => {
        const status = getContainerStatus(tool, containerStatuses);
        const catColor = CATEGORY_COLORS[tool.category] ?? DEFAULT_CATEGORY_COLOR;
        const riskColor = RISK_COLORS[tool.riskLevel] ?? DEFAULT_CATEGORY_COLOR;

        return (
          <div
            key={tool.id}
            className="flex items-center transition-colors hover:bg-white/5 h-12 px-3 border-b border-athena-border/25"
          >
            {/* NAME */}
            <div
              className="flex flex-col w-[260px] shrink-0 gap-0.5"
            >
              <div className="flex items-center gap-2">
                <span
                  className="font-semibold truncate text-athena-text text-xs"
                >
                  {tool.name}
                </span>
                {tool.source === "user" && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleDelete(tool.toolId)}
                    disabled={deletingId === tool.toolId}
                    className="text-[10px] px-1.5 py-0.5 shrink-0"
                  >
                    {deletingId === tool.toolId ? "..." : t("del")}
                  </Button>
                )}
              </div>
              {tool.description && (
                <span
                  className="truncate text-athena-text-secondary text-[9px] max-w-[240px]"
                >
                  {tool.description}
                </span>
              )}
            </div>

            {/* CATEGORY */}
            <div className="w-[120px] shrink-0">
              <span
                className="font-mono inline-block rounded-athena px-1.5 py-0.5 text-[10px]"
                style={{
                  backgroundColor: catColor.bg,
                  color: catColor.text,
                }}
              >
                {tCategory(tool.category as any)}
              </span>
            </div>

            {/* STATUS */}
            <button
              role="switch"
              aria-checked={tool.enabled}
              onClick={() => onToggleEnabled(tool.toolId, !tool.enabled)}
              className="flex items-center transition-opacity hover:opacity-75 w-[70px] shrink-0 gap-1.5 bg-transparent border-none cursor-pointer p-0"
            >
              <span
                className={`inline-block rounded-full w-2 h-2 shrink-0 ${tool.enabled ? "bg-athena-success" : "bg-athena-text-secondary"}`}
              />
              <span
                className={`font-semibold text-[10px] ${tool.enabled ? "text-athena-success" : "text-athena-text-secondary"}`}
              >
                {tool.enabled ? t("on") : t("off")}
              </span>
            </button>

            {/* RISK */}
            <div className="w-[80px] shrink-0">
              <span
                className="font-mono inline-block rounded-athena px-1.5 py-0.5 text-[10px]"
                style={{
                  backgroundColor: riskColor.bg,
                  color: riskColor.text,
                }}
              >
                {tRisk(tool.riskLevel as any)}
              </span>
            </div>

            {/* MITRE */}
            <div
              className="flex flex-wrap w-[180px] shrink-0 gap-1"
            >
              {tool.mitreTechniques.map((tid) => (
                <span
                  key={tid}
                  className="font-mono inline-block rounded-athena bg-athena-elevated text-athena-text-tertiary px-1.5 py-0.5 text-[10px]"
                >
                  {tid}
                </span>
              ))}
            </div>

            {/* CONTAINER */}
            <div
              className="flex items-center w-[100px] shrink-0 gap-1.5"
            >
              {status === "online" && (
                <>
                  <span
                    className="inline-block rounded-full w-1.5 h-1.5 shrink-0 bg-athena-success"
                  />
                  <span className="text-athena-success text-[10px]">
                    {t("containerOnline")}
                  </span>
                </>
              )}
              {status === "offline" && (
                <>
                  <span
                    className="inline-block rounded-full w-1.5 h-1.5 shrink-0 bg-athena-error"
                  />
                  <span className="text-athena-error text-[10px]">
                    {t("containerOffline")}
                  </span>
                </>
              )}
              {status === "none" && (
                <span className="font-mono text-athena-text-secondary text-[10px]">
                  --
                </span>
              )}
            </div>

            {/* ACTIONS */}
            <div
              className="flex items-center justify-center w-[80px] shrink-0"
            >
              {tool.enabled ? (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setSelectedTool(tool)}
                  className="text-[10px]"
                >
                  {t("execute")}
                </Button>
              ) : (
                <span className="font-mono text-athena-text-secondary text-[10px]">
                  --
                </span>
              )}
            </div>
          </div>
        );
      })}

      <ToolExecuteModal
        tool={selectedTool}
        onClose={() => setSelectedTool(null)}
      />
    </div>
  );
}
