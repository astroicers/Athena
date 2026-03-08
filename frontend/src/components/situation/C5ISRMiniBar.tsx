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

interface C5ISRMiniBarProps {
  health: Record<string, number>;
}

const DOMAIN_LABELS: Record<string, string> = {
  command: "CMD",
  control: "CTRL",
  comms: "COMMS",
  computers: "COMP",
  cyber: "CYBER",
  isr: "ISR",
};

const DOMAIN_ORDER = ["command", "control", "comms", "computers", "cyber", "isr"];

function getHealthColor(pct: number): string {
  if (pct > 80) return "#22c55e"; // green
  if (pct >= 50) return "#eab308"; // yellow
  return "#ef4444"; // red
}

function getHealthTextClass(pct: number): string {
  if (pct > 80) return "text-green-400";
  if (pct >= 50) return "text-yellow-400";
  return "text-red-400";
}

/** Small hex gauge matching DomainCard HexGauge style */
function MiniHexGauge({ value, color }: { value: number; color: string }) {
  // Flat-top hexagon vertices for 28x32 viewBox
  const points = "14,1 25.5,8 25.5,24 14,31 2.5,24 2.5,8";
  const perimeter = 86; // approximate
  const filled = (Math.min(100, Math.max(0, value)) / 100) * perimeter;

  return (
    <svg width="28" height="32" viewBox="0 0 28 32" className="shrink-0">
      {/* Background hex */}
      <polygon
        points={points}
        fill="none"
        stroke="#2a2a4a"
        strokeWidth="1.2"
      />
      {/* Foreground hex — filled proportional to health % */}
      <polygon
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.2"
        strokeDasharray={`${filled} ${perimeter - filled}`}
        strokeLinecap="round"
      />
      {/* Percentage label */}
      <text
        x="14"
        y="17.5"
        textAnchor="middle"
        dominantBaseline="central"
        fill={color}
        fontFamily="var(--font-mono)"
        fontSize="12"
        fontWeight="700"
      >
        {value}
      </text>
    </svg>
  );
}

export function C5ISRMiniBar({ health }: C5ISRMiniBarProps) {
  const domains = DOMAIN_ORDER.filter((d) => d in health || DOMAIN_LABELS[d]);

  return (
    <div className="flex items-center justify-center gap-3 py-2.5 px-4">
      <span className="text-sm font-mono text-athena-text-secondary uppercase tracking-wider mr-1">
        C5ISR
      </span>
      {domains.map((domain) => {
        const pct = health[domain] ?? 0;
        const label = DOMAIN_LABELS[domain] ?? domain.toUpperCase();
        const color = getHealthColor(pct);
        const textClass = getHealthTextClass(pct);

        return (
          <div
            key={domain}
            className="flex flex-col items-center gap-0.5"
          >
            <span className="text-xs font-mono text-athena-text-secondary font-bold tracking-wider">
              {label}
            </span>
            <MiniHexGauge value={pct} color={color} />
            <span className={`text-xs font-mono font-bold ${textClass}`}>
              {pct}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
