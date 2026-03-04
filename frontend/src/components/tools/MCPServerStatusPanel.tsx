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

import { useTranslations } from "next-intl";
import { useMCPServers } from "@/hooks/useMCPServers";

export function MCPServerStatusPanel() {
  const t = useTranslations("Tools");
  const { servers, loading } = useMCPServers();

  if (loading || servers.length === 0) return null;

  return (
    <div className="rounded-lg border border-neutral-700 bg-neutral-800/50 p-4">
      <h3 className="mb-3 text-sm font-semibold text-neutral-300">
        {t("mcpServers")}
      </h3>
      <div className="flex flex-wrap gap-3">
        {servers.map((srv) => (
          <div
            key={srv.name}
            className="flex items-center gap-2 rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-xs"
          >
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                srv.connected
                  ? "bg-emerald-400"
                  : srv.enabled
                    ? "bg-amber-400"
                    : "bg-neutral-500"
              }`}
            />
            <span className="font-medium text-neutral-200">{srv.name}</span>
            {srv.connected && (
              <span className="text-neutral-500">
                {srv.tool_count} {t("mcpTools")}
              </span>
            )}
            {!srv.connected && srv.enabled && (
              <span className="text-amber-400">{t("mcpDisconnected")}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
