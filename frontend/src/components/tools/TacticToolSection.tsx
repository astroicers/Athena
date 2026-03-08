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
      className="border border-athena-border rounded-athena-md overflow-hidden"
    >
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 bg-athena-surface hover:bg-athena-elevated/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span
            className={`text-sm font-mono transition-transform ${isOpen ? "rotate-90" : ""}`}
          >
            ▶
          </span>
          <span className="text-xs font-mono font-bold text-athena-text uppercase">
            {tacticLabel}
          </span>
          <span className="text-sm font-mono text-athena-accent px-1.5 py-0.5 bg-athena-accent/10 rounded-full">
            {tacticId}
          </span>
        </div>
        <span className="text-sm font-mono text-athena-text-secondary">
          {tools.length} {t("toolCount")}
        </span>
      </button>

      {/* Body */}
      {isOpen && (
        <div className="border-t border-athena-border">
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
