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
import { Toggle } from "@/components/atoms/Toggle";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import type { ToolRegistryEntry, ToolHealthCheck } from "@/types/tool";

const RISK_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  low: "success",
  medium: "warning",
  high: "error",
  critical: "error",
};

interface ToolRegistryTableProps {
  tools: ToolRegistryEntry[];
  onToggleEnabled: (toolId: string, enabled: boolean) => Promise<void>;
  onCheckHealth: (toolId: string) => Promise<ToolHealthCheck>;
  onDelete: (toolId: string) => Promise<void>;
}

export function ToolRegistryTable({
  tools,
  onToggleEnabled,
  onCheckHealth,
  onDelete,
}: ToolRegistryTableProps) {
  const [healthResults, setHealthResults] = useState<
    Record<string, ToolHealthCheck>
  >({});
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleHealthCheck(toolId: string) {
    setCheckingId(toolId);
    try {
      const result = await onCheckHealth(toolId);
      setHealthResults((prev) => ({ ...prev, [toolId]: result }));
    } catch {
      setHealthResults((prev) => ({
        ...prev,
        [toolId]: { toolId, available: false, detail: "Check failed" },
      }));
    } finally {
      setCheckingId(null);
    }
  }

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
          No tools registered
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
              Name
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              Category
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              Status
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              Risk
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              MITRE
            </th>
            <th className="px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {tools.map((tool) => {
            const health = healthResults[tool.toolId];
            return (
              <tr
                key={tool.id}
                className="border-b border-athena-border/50 hover:bg-athena-elevated/30"
              >
                {/* Name */}
                <td className="px-3 py-2 text-athena-text">
                  <div>
                    <span className="text-athena-accent font-bold">
                      {tool.name}
                    </span>
                    {tool.description && (
                      <p className="text-[10px] text-athena-text-secondary mt-0.5 truncate max-w-[200px]">
                        {tool.description}
                      </p>
                    )}
                  </div>
                </td>

                {/* Category */}
                <td className="px-3 py-2">
                  <Badge variant="info">{tool.category.toUpperCase()}</Badge>
                </td>

                {/* Status toggle */}
                <td className="px-3 py-2">
                  <Toggle
                    checked={tool.enabled}
                    onChange={(checked) =>
                      onToggleEnabled(tool.toolId, checked)
                    }
                    label={tool.enabled ? "ON" : "OFF"}
                  />
                </td>

                {/* Risk */}
                <td className="px-3 py-2">
                  <Badge
                    variant={RISK_VARIANT[tool.riskLevel] || "info"}
                  >
                    {tool.riskLevel.toUpperCase()}
                  </Badge>
                </td>

                {/* MITRE technique count */}
                <td className="px-3 py-2 text-athena-text">
                  {tool.mitreTechniques.length}
                </td>

                {/* Actions */}
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleHealthCheck(tool.toolId)}
                      disabled={checkingId === tool.toolId}
                    >
                      {checkingId === tool.toolId ? "..." : "CHECK"}
                    </Button>

                    {tool.source === "user" && (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(tool.toolId)}
                        disabled={deletingId === tool.toolId}
                      >
                        {deletingId === tool.toolId ? "..." : "DEL"}
                      </Button>
                    )}

                    {health && (
                      <span
                        className={`text-[10px] ${
                          health.available
                            ? "text-athena-success"
                            : "text-athena-error"
                        }`}
                      >
                        {health.available ? "OK" : "FAIL"}
                      </span>
                    )}
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
