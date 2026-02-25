"use client";

import { Badge } from "@/components/atoms/Badge";

interface HostNodeCardProps {
  hostname: string;
  ipAddress: string;
  role: string;
  isCompromised: boolean;
  privilegeLevel: string | null;
}

export function HostNodeCard({
  hostname,
  ipAddress,
  role,
  isCompromised,
  privilegeLevel,
}: HostNodeCardProps) {
  return (
    <div
      className={`bg-athena-surface border rounded-athena-md p-3 ${
        isCompromised ? "border-athena-error/60" : "border-athena-border"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-mono font-bold text-athena-text">
          {hostname}
        </span>
        <Badge variant={isCompromised ? "error" : "info"}>
          {isCompromised ? "COMPROMISED" : "SECURE"}
        </Badge>
      </div>
      <div className="space-y-1 text-xs font-mono text-athena-text-secondary">
        <div className="flex justify-between">
          <span>IP</span>
          <span className="text-athena-text">{ipAddress}</span>
        </div>
        <div className="flex justify-between">
          <span>Role</span>
          <span className="text-athena-text">{role}</span>
        </div>
        {privilegeLevel && (
          <div className="flex justify-between">
            <span>Privilege</span>
            <span className="text-athena-accent">{privilegeLevel}</span>
          </div>
        )}
      </div>
    </div>
  );
}
