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

import { useTranslations } from "next-intl";
import { AgentStatus } from "@/types/enums";

const STATUS_STYLES: Record<string, { dot: string; text: string }> = {
  [AgentStatus.ALIVE]: { dot: "bg-athena-success-bg animate-pulse", text: "text-athena-success" },
  [AgentStatus.DEAD]: { dot: "bg-athena-error-bg", text: "text-athena-error" },
  [AgentStatus.PENDING]: { dot: "bg-athena-warning-bg", text: "text-athena-warning" },
  [AgentStatus.UNTRUSTED]: { dot: "bg-athena-text-tertiary", text: "text-athena-text-tertiary" },
};

interface AgentBeaconProps {
  paw: string;
  status: AgentStatus;
  privilege: string;
  platform: string;
  lastBeacon: string | null;
}

export function AgentBeacon({ paw, status, privilege, platform, lastBeacon }: AgentBeaconProps) {
  const tStatus = useTranslations("Status");
  const style = STATUS_STYLES[status] || STATUS_STYLES[AgentStatus.PENDING];
  const beaconTime = lastBeacon?.split("T")[1]?.slice(0, 8) || "—";

  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-athena-surface border border-athena-border rounded-athena">
      <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${style.dot}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-mono font-bold ${style.text}`}>{paw}</span>
          <span className="text-sm font-mono text-athena-text-tertiary">{tStatus(status as any)}</span>
        </div>
        <div className="flex items-center gap-3 text-sm font-mono text-athena-text-tertiary">
          <span>{platform}</span>
          <span>{privilege}</span>
          <span>{beaconTime}</span>
        </div>
      </div>
    </div>
  );
}
