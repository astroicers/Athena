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
import { ToolRegistryTable } from "@/components/tools/ToolRegistryTable";
import type { ToolRegistryEntry } from "@/types/tool";

interface TacticToolSectionProps {
  tacticSlug: string;
  tacticLabel: string;
  tacticId: string;
  tools: ToolRegistryEntry[];
  onToggleEnabled: (toolId: string, enabled: boolean) => Promise<void>;
  onDelete: (toolId: string) => Promise<void>;
  containerStatuses: Record<string, boolean>;
  defaultOpen?: boolean;
  highlightToolId?: string;
}

export function TacticToolSection({
  tacticSlug,
  tacticLabel,
  tacticId,
  tools,
  onToggleEnabled,
  onDelete,
  containerStatuses,
  defaultOpen = false,
  highlightToolId,
}: TacticToolSectionProps) {
  const t = useTranslations("Tools");
  const [isOpen, setIsOpen] = useState(
    defaultOpen || (highlightToolId ? tools.some((tl) => tl.toolId === highlightToolId) : false),
  );

  return (
    <div
      id={`tactic-${tacticSlug}`}
      className="border border-[#1f2937] rounded-athena-md overflow-hidden"
    >
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 bg-[#111827] hover:bg-[#1f2937]/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span
            className={`text-sm font-mono transition-transform ${isOpen ? "rotate-90" : ""}`}
          >
            ▶
          </span>
          <span className="text-xs font-mono font-bold text-[#e5e7eb] uppercase">
            {tacticLabel}
          </span>
          <span className="text-sm font-mono text-[#3b82f6] px-1.5 py-0.5 bg-[#3b82f610] rounded-full">
            {tacticId}
          </span>
        </div>
        <span className="text-sm font-mono text-[#9ca3af]">
          {tools.length} {t("toolCount")}
        </span>
      </button>

      {/* Body */}
      {isOpen && (
        <div className="border-t border-[#1f2937]">
          <ToolRegistryTable
            tools={tools}
            onToggleEnabled={onToggleEnabled}
            onDelete={onDelete}
            containerStatuses={containerStatuses}
          />
        </div>
      )}
    </div>
  );
}
