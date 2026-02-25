"use client";

import { AgentStatus } from "@/types/enums";

const STATUS_STYLES: Record<string, { dot: string; text: string }> = {
  [AgentStatus.ALIVE]: { dot: "bg-athena-success animate-pulse", text: "text-athena-success" },
  [AgentStatus.DEAD]: { dot: "bg-athena-error", text: "text-athena-error" },
  [AgentStatus.PENDING]: { dot: "bg-athena-warning", text: "text-athena-warning" },
  [AgentStatus.UNTRUSTED]: { dot: "bg-athena-text-secondary", text: "text-athena-text-secondary" },
};

interface AgentBeaconProps {
  paw: string;
  status: AgentStatus;
  privilege: string;
  platform: string;
  lastBeacon: string | null;
}

export function AgentBeacon({ paw, status, privilege, platform, lastBeacon }: AgentBeaconProps) {
  const style = STATUS_STYLES[status] || STATUS_STYLES[AgentStatus.PENDING];
  const beaconTime = lastBeacon?.split("T")[1]?.slice(0, 8) || "—";

  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-athena-surface border border-athena-border rounded-athena-sm">
      <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${style.dot}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-mono font-bold ${style.text}`}>{paw}</span>
          <span className="text-[10px] font-mono text-athena-text-secondary uppercase">{status}</span>
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono text-athena-text-secondary">
          <span>{platform}</span>
          <span>{privilege}</span>
          <span>{beaconTime}</span>
        </div>
      </div>
    </div>
  );
}
