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

export function C5ISRMiniBar({ health }: C5ISRMiniBarProps) {
  const domains = DOMAIN_ORDER.filter((d) => d in health || DOMAIN_LABELS[d]);

  return (
    <div className="flex items-center justify-center gap-3 py-2 px-4">
      <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mr-1">
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
            className="flex flex-col items-center gap-0.5 px-2 py-1 rounded bg-athena-surface border border-athena-border"
          >
            <span className="text-[10px] font-mono text-athena-text-secondary font-bold">
              {label}
            </span>
            <div className="w-10 h-1.5 rounded-full bg-athena-border overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }}
              />
            </div>
            <span className={`text-[10px] font-mono font-bold ${textClass}`}>
              {pct}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
