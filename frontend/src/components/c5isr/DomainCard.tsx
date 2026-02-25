"use client";

import { Badge } from "@/components/atoms/Badge";
import { ProgressBar } from "@/components/atoms/ProgressBar";
import { C5ISRDomainStatus } from "@/types/enums";
import type { C5ISRStatus } from "@/types/c5isr";

const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [C5ISRDomainStatus.OPERATIONAL]: "success",
  [C5ISRDomainStatus.ACTIVE]: "success",
  [C5ISRDomainStatus.NOMINAL]: "success",
  [C5ISRDomainStatus.ENGAGED]: "info",
  [C5ISRDomainStatus.SCANNING]: "info",
  [C5ISRDomainStatus.DEGRADED]: "warning",
  [C5ISRDomainStatus.OFFLINE]: "error",
  [C5ISRDomainStatus.CRITICAL]: "error",
};

const DOMAIN_LABELS: Record<string, string> = {
  command: "COMMAND",
  control: "CONTROL",
  comms: "COMMS",
  computers: "COMPUTERS",
  cyber: "CYBER",
  isr: "ISR",
};

function healthVariant(pct: number): "success" | "warning" | "error" | "default" {
  if (pct >= 80) return "success";
  if (pct >= 60) return "warning";
  return "error";
}

interface DomainCardProps {
  domain: C5ISRStatus;
}

export function DomainCard({ domain }: DomainCardProps) {
  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono font-bold text-athena-text">
          {DOMAIN_LABELS[domain.domain] || domain.domain.toUpperCase()}
        </span>
        <Badge variant={STATUS_VARIANT[domain.status] || "info"}>
          {domain.status.toUpperCase()}
        </Badge>
      </div>
      <ProgressBar value={domain.healthPct} max={100} variant={healthVariant(domain.healthPct)} />
      <div className="flex items-center justify-between mt-2">
        <span className="text-[10px] font-mono text-athena-text-secondary">
          {domain.detail}
        </span>
        <span className="text-[10px] font-mono text-athena-text-secondary">
          {domain.healthPct}%
        </span>
      </div>
    </div>
  );
}
