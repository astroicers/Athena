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
import type { OODAPhase } from "@/types/enums";
import type { C5ISRStatus } from "@/types/c5isr";

// ── Arc math (from OODARing.tsx) ──

const OODA_PHASES: { phase: string; startAngle: number }[] = [
  { phase: "observe", startAngle: -90 },
  { phase: "orient", startAngle: 0 },
  { phase: "decide", startAngle: 90 },
  { phase: "act", startAngle: 180 },
];

const RING_RADIUS = 30;
const ARC_WIDTH = 4;
const GAP_DEG = 8;
const ARC_DEG = 90 - GAP_DEG;

function polarToCartesian(cx: number, cy: number, radius: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
}

function describeArc(cx: number, cy: number, radius: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

// ── Sub-components ──

function OODAStatusRing({ phase, iterationCount }: {
  phase: OODAPhase | null;
  iterationCount: number;
}) {
  const tOoda = useTranslations("OODA");
  const CX = 50, CY = 45;

  return (
    <div className="flex flex-col items-center gap-0.5">
      <svg width={100} height={90} viewBox="0 0 100 90">
        {OODA_PHASES.map(({ phase: p, startAngle }) => {
          const isActive = p === phase;
          const endAngle = startAngle + ARC_DEG;
          const arcPath = describeArc(CX, CY, RING_RADIUS, startAngle + GAP_DEG / 2, endAngle + GAP_DEG / 2);
          return (
            <g key={p} className={isActive ? "animate-pulse" : ""}>
              <path
                d={arcPath}
                fill="none"
                stroke={isActive ? "#00d4ff" : "#2a2a4a"}
                strokeWidth={ARC_WIDTH}
                strokeLinecap="round"
                opacity={isActive ? 1 : 0.5}
              />
            </g>
          );
        })}
        <text
          x={CX} y={CY}
          textAnchor="middle" dominantBaseline="central"
          fill={phase ? "#00d4ff" : "#4a4a6a"}
          fontFamily="var(--font-mono)" fontSize={14} fontWeight="bold"
        >
          {phase ? `#${iterationCount}` : "IDLE"}
        </text>
      </svg>
      <span className={`text-[10px] font-mono font-bold uppercase tracking-wider ${
        phase ? "text-athena-accent" : "text-athena-text-secondary"
      }`}>
        {phase ? tOoda(phase as "observe" | "orient" | "decide" | "act") : "—"}
      </span>
    </div>
  );
}

// ── Health color ──

function getHealthColor(pct: number): string {
  if (pct > 80) return "var(--color-success)";
  if (pct >= 50) return "var(--color-warning)";
  return "var(--color-error)";
}

// ── MiniHexGauge (from C5ISRMiniBar.tsx) ──

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

// ── Inline directive (from CollapsibleKPIRow.tsx) ──

function InlineDirective({ currentOodaPhase, onSubmit, onOodaTrigger }: {
  currentOodaPhase: OODAPhase | null;
  onSubmit: (directive: string) => Promise<void>;
  onOodaTrigger: () => Promise<void>;
}) {
  const t = useTranslations("WarRoom");
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const isCycleIdle = currentOodaPhase === null;

  async function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || sending) return;
    setSending(true);
    try {
      await onSubmit(trimmed);
      setValue("");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className={`flex items-center gap-1.5 border rounded px-1.5 py-0.5 transition-colors ${
        isCycleIdle ? "border-athena-accent/60 animate-pulse" : "border-athena-border"
      }`}>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={t("directivePlaceholder")}
          className="bg-transparent text-[10px] font-mono text-athena-text flex-1 outline-none placeholder:text-athena-text-secondary/40"
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); handleSubmit(); }
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!value.trim() || sending}
          className="text-[9px] font-mono uppercase tracking-wider text-athena-accent hover:text-athena-accent-hover disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {t("directiveSend")}
        </button>
      </div>
      <button
        onClick={onOodaTrigger}
        className="text-[9px] font-mono uppercase tracking-wider text-athena-accent hover:text-athena-accent-hover border border-athena-border rounded px-2 py-0.5 hover:bg-athena-accent/10 transition-colors"
      >
        ▶ {t("battleRhythm")}
      </button>
    </div>
  );
}

// ── Main component ──

interface TacticalDashboardProps {
  c5isrDomains: C5ISRStatus[];
  currentOodaPhase: OODAPhase | null;
  oodaIterationCount: number;
  onDirectiveSubmit: (directive: string) => Promise<void>;
  onOodaTrigger: () => Promise<void>;
}

const DOMAIN_ORDER = ["command", "control", "comms", "computers", "cyber", "isr"];

export function TacticalDashboard({
  c5isrDomains, currentOodaPhase, oodaIterationCount, onDirectiveSubmit, onOodaTrigger,
}: TacticalDashboardProps) {
  const sortedDomains = DOMAIN_ORDER
    .map((d) => c5isrDomains.find((cd) => cd.domain === d))
    .filter(Boolean) as C5ISRStatus[];

  return (
    <div className="shrink-0 flex items-stretch border-b border-athena-border bg-athena-surface h-[96px]">
      {/* Zone A: OODA Ring */}
      <div className="w-[120px] flex flex-col items-center justify-center border-r border-athena-border px-2">
        <OODAStatusRing phase={currentOodaPhase} iterationCount={oodaIterationCount} />
      </div>

      {/* Zone B: C5ISR Domain Strip */}
      <div className="flex-1 grid grid-cols-6 gap-1 items-stretch py-1 px-2">
        {sortedDomains.map((d) => (
          <DomainCell key={d.domain} domain={d} />
        ))}
      </div>

      {/* Zone C: Directive Input */}
      <div className="w-[240px] flex flex-col justify-center border-l border-athena-border px-3">
        <InlineDirective
          currentOodaPhase={currentOodaPhase}
          onSubmit={onDirectiveSubmit}
          onOodaTrigger={onOodaTrigger}
        />
      </div>
    </div>
  );
}
