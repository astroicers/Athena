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
import type { ToolRegistryEntry } from "@/types/tool";

/* ── Badge color maps (hex with alpha suffixes) ── */

const CATEGORY_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  recon:      { bg: "#1E609120", border: "#1E609140", text: "#1E6091" },
  execution:  { bg: "#7C3AED20", border: "#7C3AED40", text: "#7C3AED" },
  vuln_scan:  { bg: "#05966920", border: "#05966940", text: "#059669" },
  credential: { bg: "#B91C1C20", border: "#B91C1C40", text: "#B91C1C" },
};

const RISK_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  low:      { bg: "#05966920", border: "#05966940", text: "#059669" },
  medium:   { bg: "#B4530920", border: "#B4530940", text: "#B45309" },
  high:     { bg: "#FB923C20", border: "#FB923C40", text: "#FB923C" },
  critical: { bg: "#B91C1C20", border: "#B91C1C40", text: "#B91C1C" },
};

const DEFAULT_COLOR = { bg: "#71717A20", border: "#71717A40", text: "#71717A" };

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
      <div className="rounded-[var(--radius)] text-center p-6 border border-[var(--color-border)]">
        <span className="font-mono text-xs text-[var(--color-text-secondary)]">
          {t("noTools")}
        </span>
      </div>
    );
  }

  return (
    <div>
      {/* Table Header — 36px, fill #18181B */}
      <div className="flex items-center h-9 px-3 bg-[var(--color-bg-surface)]">
        <div className="w-[260px] shrink-0 font-mono text-xs font-bold uppercase tracking-[1px] text-[var(--color-text-secondary)]">
          {t("colName")}
        </div>
        <div className="w-[120px] shrink-0 font-mono text-xs font-bold uppercase tracking-[1px] text-[var(--color-text-secondary)]">
          {t("colCategory")}
        </div>
        <div className="w-[70px] shrink-0 font-mono text-xs font-bold uppercase tracking-[1px] text-[var(--color-text-secondary)]">
          {t("colStatus")}
        </div>
        <div className="w-[80px] shrink-0 font-mono text-xs font-bold uppercase tracking-[1px] text-[var(--color-text-secondary)]">
          {t("colRisk")}
        </div>
        <div className="w-[180px] shrink-0 font-mono text-xs font-bold uppercase tracking-[1px] text-[var(--color-text-secondary)]">
          {t("colMitre")}
        </div>
        <div className="w-[100px] shrink-0 font-mono text-xs font-bold uppercase tracking-[1px] text-[var(--color-text-secondary)]">
          {t("colContainer")}
        </div>
        <div className="w-[80px] shrink-0 font-mono text-xs font-bold uppercase tracking-[1px] text-[var(--color-text-secondary)] text-center">
          {t("colActions")}
        </div>
      </div>

      {/* Data rows */}
      {tools.map((tool) => {
        const status = getContainerStatus(tool, containerStatuses);
        const catColor = CATEGORY_COLORS[tool.category] ?? DEFAULT_COLOR;
        const riskColor = RISK_COLORS[tool.riskLevel] ?? DEFAULT_COLOR;

        return (
          <div
            key={tool.id}
            className="flex items-center h-[52px] px-3 border-b border-[var(--color-border)] transition-colors hover:bg-[rgba(255,255,255,0.02)]"
          >
            {/* NAME — 12px semibold #D4D4D8 */}
            <div className="flex flex-col w-[260px] shrink-0 gap-0.5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[12px] font-semibold text-[var(--color-text-primary)] truncate">
                  {tool.name}
                </span>
                {tool.source === "user" && (
                  <button
                    onClick={() => handleDelete(tool.toolId)}
                    disabled={deletingId === tool.toolId}
                    className="font-mono text-xs font-semibold text-[var(--color-error)] bg-[#B91C1C14] border border-[#B91C1C40] rounded-[var(--radius)] px-1.5 py-0.5 shrink-0 cursor-pointer hover:bg-[#B91C1C20] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {deletingId === tool.toolId ? "..." : t("del")}
                  </button>
                )}
              </div>
              {tool.description && (
                <span className="font-mono text-xs font-normal text-[var(--color-text-secondary)] truncate max-w-[240px]">
                  {tool.description}
                </span>
              )}
            </div>

            {/* CATEGORY — badge with color coding */}
            <div className="w-[120px] shrink-0">
              <span
                className="font-mono text-xs inline-block rounded-[var(--radius)] px-1.5 py-0.5"
                style={{
                  backgroundColor: catColor.bg,
                  borderWidth: "1px",
                  borderStyle: "solid",
                  borderColor: catColor.border,
                  color: catColor.text,
                }}
              >
                {tCategory(tool.category as any)}
              </span>
            </div>

            {/* STATUS — dot 8px + ON/OFF 10px 600 */}
            <button
              role="switch"
              aria-checked={tool.enabled}
              onClick={() => onToggleEnabled(tool.toolId, !tool.enabled)}
              className="flex items-center w-[70px] shrink-0 gap-1.5 bg-transparent border-none cursor-pointer p-0 transition-opacity hover:opacity-75"
            >
              <span
                className={`inline-block rounded-full w-2 h-2 shrink-0 ${
                  tool.enabled ? "bg-[var(--color-success)]" : "bg-[var(--color-text-secondary)]"
                }`}
              />
              <span
                className={`font-mono text-xs font-semibold ${
                  tool.enabled ? "text-[var(--color-success)]" : "text-[var(--color-text-secondary)]"
                }`}
              >
                {tool.enabled ? t("on") : t("off")}
              </span>
            </button>

            {/* RISK — badge with color coding */}
            <div className="w-[80px] shrink-0">
              <span
                className="font-mono text-xs inline-block rounded-[var(--radius)] px-1.5 py-0.5"
                style={{
                  backgroundColor: riskColor.bg,
                  borderWidth: "1px",
                  borderStyle: "solid",
                  borderColor: riskColor.border,
                  color: riskColor.text,
                }}
              >
                {tRisk(tool.riskLevel as any)}
              </span>
            </div>

            {/* MITRE — bg #27272A, text #52525B */}
            <div className="flex flex-wrap w-[180px] shrink-0 gap-1">
              {tool.mitreTechniques.map((tid) => (
                <span
                  key={tid}
                  className="font-mono text-xs inline-block rounded-[var(--radius)] bg-[var(--color-bg-elevated)] text-[var(--color-text-tertiary)] px-1.5 py-0.5"
                >
                  {tid}
                </span>
              ))}
            </div>

            {/* CONTAINER — dot 6px + text 10px */}
            <div className="flex items-center w-[100px] shrink-0 gap-1.5">
              {status === "online" && (
                <>
                  <span className="inline-block rounded-full w-2.5 h-2.5 shrink-0 bg-[var(--color-success)]" />
                  <span className="font-mono text-xs text-[var(--color-success)]">
                    {t("containerOnline")}
                  </span>
                </>
              )}
              {status === "offline" && (
                <>
                  <span className="inline-block rounded-full w-2.5 h-2.5 shrink-0 bg-[var(--color-error)]" />
                  <span className="font-mono text-xs text-[var(--color-error)]">
                    {t("containerOffline")}
                  </span>
                </>
              )}
              {status === "none" && (
                <span className="font-mono text-xs text-[var(--color-text-secondary)]">
                  --
                </span>
              )}
            </div>

            {/* ACTIONS — execute button */}
            <div className="flex items-center justify-center w-[80px] shrink-0">
              {tool.enabled ? (
                <button
                  onClick={() => setSelectedTool(tool)}
                  className="font-mono text-xs font-semibold text-[var(--color-text-primary)] bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)] rounded-[var(--radius)] px-3 py-1 cursor-pointer hover:bg-[var(--color-bg-elevated)] transition-colors"
                >
                  {t("execute")}
                </button>
              ) : (
                <span className="font-mono text-xs text-[var(--color-text-secondary)]">
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
