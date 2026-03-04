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

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { useMCPServers } from "@/hooks/useMCPServers";
import { StatusDot } from "@/components/atoms/StatusDot";
import { SectionHeader } from "@/components/atoms/SectionHeader";

interface MCPServerInfo {
  name: string;
  transport: string;
  enabled: boolean;
  connected: boolean;
  tool_count: number;
  description: string;
  circuit_state: string;
  failure_count: number;
}

function MCPServerCard({ server }: { server: MCPServerInfo }) {
  const t = useTranslations("Tools");
  const circuitState = server.circuit_state ?? "closed";

  const { dotStatus, pulse, statusLabel, statusColor } = useMemo(() => {
    if (!server.enabled) {
      return {
        dotStatus: "offline",
        pulse: false,
        statusLabel: t("mcpStatusDisabled"),
        statusColor: "text-athena-text-secondary",
      };
    }
    if (circuitState === "open") {
      return {
        dotStatus: "critical",
        pulse: false,
        statusLabel: t("mcpStatusCircuitOpen"),
        statusColor: "text-athena-error",
      };
    }
    if (circuitState === "half_open") {
      return {
        dotStatus: "engaged",
        pulse: true,
        statusLabel: t("mcpStatusHalfOpen"),
        statusColor: "text-athena-warning",
      };
    }
    if (server.connected) {
      return {
        dotStatus: "operational",
        pulse: true,
        statusLabel: t("mcpStatusOnline"),
        statusColor: "text-athena-success",
      };
    }
    return {
      dotStatus: "degraded",
      pulse: false,
      statusLabel: t("mcpDisconnected"),
      statusColor: "text-athena-warning",
    };
  }, [server.enabled, server.connected, circuitState, t]);

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 hover:border-athena-accent/40 transition-colors duration-200 flex flex-col gap-3">
      {/* Header: status dot + name */}
      <div className="flex items-center gap-2 min-w-0">
        <StatusDot status={dotStatus} pulse={pulse} />
        <span className="text-sm font-mono font-bold text-athena-text truncate">
          {server.name}
        </span>
      </div>

      {/* Description */}
      {server.description && (
        <p className="text-[11px] font-mono text-athena-text-secondary leading-relaxed line-clamp-2">
          {server.description}
        </p>
      )}

      {/* Footer: status label + failure count + tool count */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-athena-border">
        <span
          className={`text-[10px] font-mono uppercase tracking-wider ${statusColor}`}
        >
          {statusLabel}
        </span>
        <div className="flex items-center gap-3">
          {(server.failure_count ?? 0) > 0 && (
            <span className="text-[10px] font-mono text-athena-error">
              {server.failure_count} {t("mcpFailures")}
            </span>
          )}
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {server.tool_count} {t("mcpTools")}
          </span>
        </div>
      </div>
    </div>
  );
}

export function MCPServerStatusPanel() {
  const t = useTranslations("Tools");
  const { servers, loading } = useMCPServers();

  if (loading || servers.length === 0) return null;

  return (
    <div className="space-y-3">
      <SectionHeader level="page">{t("mcpServers")}</SectionHeader>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {servers.map((srv) => (
          <MCPServerCard key={srv.name} server={srv} />
        ))}
      </div>
    </div>
  );
}
