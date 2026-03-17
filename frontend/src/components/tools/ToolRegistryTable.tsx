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

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  recon: { bg: "rgba(59,130,246,0.125)", text: "#3b82f6" },
  execution: { bg: "rgba(167,139,250,0.125)", text: "#A78BFA" },
  vuln_scan: { bg: "rgba(34,197,94,0.125)", text: "#22C55E" },
  credential: { bg: "rgba(239,68,68,0.125)", text: "#EF4444" },
};

const RISK_COLORS: Record<string, { bg: string; text: string }> = {
  low: { bg: "rgba(34,197,94,0.125)", text: "#22C55E" },
  medium: { bg: "rgba(251,191,36,0.125)", text: "#FBBF24" },
  high: { bg: "rgba(251,146,60,0.125)", text: "#FB923C" },
  critical: { bg: "rgba(239,68,68,0.125)", text: "#EF4444" },
};

const DEFAULT_CATEGORY_COLOR = { bg: "rgba(107,114,128,0.125)", text: "#6b7280" };

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
        className="rounded-athena-md text-center"
        style={{
          border: "1px solid rgba(31,41,55,0.25)",
          padding: 24,
        }}
      >
        <span className="font-mono text-xs" style={{ color: "#4b5563" }}>
          {t("noTools")}
        </span>
      </div>
    );
  }

  return (
    <div>
      {/* Header row */}
      <div
        className="flex items-center font-mono uppercase tracking-wider"
        style={{
          height: 36,
          padding: "0 12px",
          color: "#6b7280",
          fontSize: 10,
          fontWeight: 600,
          borderBottom: "1px solid #1f2937",
        }}
      >
        <div style={{ width: 260, flexShrink: 0 }}>{t("colName")}</div>
        <div style={{ width: 120, flexShrink: 0 }}>{t("colCategory")}</div>
        <div style={{ width: 70, flexShrink: 0 }}>{t("colStatus")}</div>
        <div style={{ width: 80, flexShrink: 0 }}>{t("colRisk")}</div>
        <div style={{ width: 180, flexShrink: 0 }}>{t("colMitre")}</div>
        <div style={{ width: 100, flexShrink: 0 }}>{t("colContainer")}</div>
        <div style={{ width: 80, flexShrink: 0, textAlign: "center" }}>{t("colActions")}</div>
      </div>

      {/* Data rows */}
      {tools.map((tool) => {
        const status = getContainerStatus(tool, containerStatuses);
        const catColor = CATEGORY_COLORS[tool.category] ?? DEFAULT_CATEGORY_COLOR;
        const riskColor = RISK_COLORS[tool.riskLevel] ?? DEFAULT_CATEGORY_COLOR;

        return (
          <div
            key={tool.id}
            className="flex items-center transition-colors hover:bg-white/[0.02]"
            style={{
              height: 52,
              padding: "0 12px",
              borderBottom: "1px solid rgba(31,41,55,0.25)",
            }}
          >
            {/* NAME */}
            <div
              className="flex flex-col"
              style={{ width: 260, flexShrink: 0, gap: 2 }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="font-semibold truncate"
                  style={{ color: "#3b82f6", fontSize: 12 }}
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
                  className="truncate"
                  style={{ color: "#6b7280", fontSize: 9, maxWidth: 240 }}
                >
                  {tool.description}
                </span>
              )}
            </div>

            {/* CATEGORY */}
            <div style={{ width: 120, flexShrink: 0 }}>
              <span
                className="font-mono inline-block"
                style={{
                  background: catColor.bg,
                  color: catColor.text,
                  borderRadius: 4,
                  padding: "2px 6px",
                  fontSize: 10,
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
              className="flex items-center transition-opacity hover:opacity-75"
              style={{ width: 70, flexShrink: 0, gap: 6, background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              <span
                className="inline-block rounded-full"
                style={{
                  width: 8,
                  height: 8,
                  background: tool.enabled ? "#22C55E" : "#6b7280",
                  flexShrink: 0,
                }}
              />
              <span
                className="font-semibold"
                style={{
                  fontSize: 10,
                  color: tool.enabled ? "#22C55E" : "#6b7280",
                }}
              >
                {tool.enabled ? t("on") : t("off")}
              </span>
            </button>

            {/* RISK */}
            <div style={{ width: 80, flexShrink: 0 }}>
              <span
                className="font-mono inline-block"
                style={{
                  background: riskColor.bg,
                  color: riskColor.text,
                  borderRadius: 4,
                  padding: "2px 6px",
                  fontSize: 10,
                }}
              >
                {tRisk(tool.riskLevel as any)}
              </span>
            </div>

            {/* MITRE */}
            <div
              className="flex flex-wrap"
              style={{ width: 180, flexShrink: 0, gap: 4 }}
            >
              {tool.mitreTechniques.map((tid) => (
                <span
                  key={tid}
                  className="font-mono inline-block"
                  style={{
                    background: "#374151",
                    color: "#9ca3af",
                    borderRadius: 4,
                    padding: "2px 6px",
                    fontSize: 10,
                  }}
                >
                  {tid}
                </span>
              ))}
            </div>

            {/* CONTAINER */}
            <div
              className="flex items-center"
              style={{ width: 100, flexShrink: 0, gap: 6 }}
            >
              {status === "online" && (
                <>
                  <span
                    className="inline-block rounded-full"
                    style={{ width: 6, height: 6, background: "#22C55E", flexShrink: 0 }}
                  />
                  <span style={{ color: "#22C55E", fontSize: 10 }}>
                    {t("containerOnline")}
                  </span>
                </>
              )}
              {status === "offline" && (
                <>
                  <span
                    className="inline-block rounded-full"
                    style={{ width: 6, height: 6, background: "#EF4444", flexShrink: 0 }}
                  />
                  <span style={{ color: "#EF4444", fontSize: 10 }}>
                    {t("containerOffline")}
                  </span>
                </>
              )}
              {status === "none" && (
                <span className="font-mono" style={{ color: "#4b5563", fontSize: 10 }}>
                  --
                </span>
              )}
            </div>

            {/* ACTIONS */}
            <div
              className="flex items-center justify-center"
              style={{ width: 80, flexShrink: 0 }}
            >
              {tool.enabled ? (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setSelectedTool(tool)}
                  className="text-[10px]"
                >
                  {t("execute")}
                </Button>
              ) : (
                <span className="font-mono" style={{ color: "#4b5563", fontSize: 10 }}>
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
