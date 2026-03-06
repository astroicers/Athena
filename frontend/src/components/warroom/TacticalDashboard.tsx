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
import type { C5ISRStatus } from "@/types/c5isr";

// ── Health color ──

function getHealthColor(pct: number): string {
  if (pct > 80) return "var(--color-success)";
  if (pct >= 50) return "var(--color-warning)";
  return "var(--color-error)";
}

// ── MiniHexGauge ──

function MiniHexGauge({ value, color }: { value: number; color: string }) {
  const points = "14,1 25.5,8 25.5,24 14,31 2.5,24 2.5,8";
  const perimeter = 86;
  const filled = (Math.min(100, Math.max(0, value)) / 100) * perimeter;
  return (
    <svg width="28" height="32" viewBox="0 0 28 32" className="shrink-0">
      <polygon points={points} fill="none" stroke="#2a2a4a" strokeWidth="1.2" />
      <polygon points={points} fill="none" stroke={color} strokeWidth="1.2"
        strokeDasharray={`${filled} ${perimeter - filled}`} strokeLinecap="round" />
      <text x="14" y="17.5" textAnchor="middle" dominantBaseline="central"
        fill={color} fontFamily="var(--font-mono)" fontSize="8" fontWeight="700">
        {Math.round(value)}
      </text>
    </svg>
  );
}

// ── Format primary metric ──

function formatPrimaryMetric(d: C5ISRStatus, t: (key: string) => string): string {
  switch (d.domain) {
    case "command":
      return `${d.numerator ?? 0} ${t("iterLabel")}`;
    case "comms":
      return d.healthPct > 0 ? t("channelUp") : t("channelDown");
    case "isr":
      return `${Math.round(d.healthPct)}%`;
    default: // control, computers, cyber → fraction format
      if (d.numerator != null && d.denominator != null) {
        return `${d.numerator}/${d.denominator}`;
      }
      return `${Math.round(d.healthPct)}%`;
  }
}

// ── Domain cell maps ──

const CODE_MAP: Record<string, string> = {
  command: "CMD", control: "CTRL", comms: "COMMS",
  computers: "COMP", cyber: "CYBER", isr: "ISR",
};

const TACTICAL_KEY_MAP: Record<string, string> = {
  command: "tacticalCommand",
  control: "tacticalControl",
  comms: "tacticalComms",
  computers: "tacticalComputers",
  cyber: "tacticalCyber",
  isr: "tacticalIsr",
};

function DomainCell({ domain }: { domain: C5ISRStatus }) {
  const t = useTranslations("C5ISR");
  const tStatus = useTranslations("Status");
  const color = getHealthColor(domain.healthPct);
  const primary = formatPrimaryMetric(domain, t as (key: string) => string);

  return (
    <div className="flex flex-col items-center justify-center gap-0.5 px-1 h-full">
      {/* 1. Domain code */}
      <span className="text-[10px] font-mono font-bold text-athena-text-secondary uppercase tracking-wider">
        {CODE_MAP[domain.domain] ?? domain.domain}
      </span>
      {/* 2. HexGauge + tactical label */}
      <div className="flex items-center justify-center gap-1.5">
        <MiniHexGauge value={domain.healthPct} color={color} />
        <span className="text-[10px] font-mono text-athena-text-secondary leading-tight">
          {t(TACTICAL_KEY_MAP[domain.domain] as Parameters<typeof t>[0])}
        </span>
      </div>
      {/* 3. Primary metric */}
      <span className="text-sm font-mono font-bold leading-none" style={{ color }}>
        {primary}
      </span>
      {/* 4. Status badge */}
      <span className="text-[9px] font-mono uppercase text-athena-text-secondary">
        {tStatus(domain.status as Parameters<typeof tStatus>[0])}
      </span>
    </div>
  );
}

// ── Main component ──

interface TacticalDashboardProps {
  c5isrDomains: C5ISRStatus[];
}

const DOMAIN_ORDER = ["command", "control", "comms", "computers", "cyber", "isr"];

export function TacticalDashboard({ c5isrDomains }: TacticalDashboardProps) {
  const sortedDomains = DOMAIN_ORDER
    .map((d) => c5isrDomains.find((cd) => cd.domain === d))
    .filter(Boolean) as C5ISRStatus[];

  return (
    <div className="shrink-0 flex items-stretch border-b border-athena-border bg-athena-surface h-[96px]">
      <div className="flex-1 grid grid-cols-6 gap-1 items-stretch py-1 px-2">
        {sortedDomains.map((d) => (
          <DomainCell key={d.domain} domain={d} />
        ))}
      </div>
    </div>
  );
}
