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

import { KillChainStage } from "@/types/enums";

const STAGES: { key: KillChainStage; label: string }[] = [
  { key: KillChainStage.RECON, label: "RECON" },
  { key: KillChainStage.WEAPONIZE, label: "WEAPON" },
  { key: KillChainStage.DELIVER, label: "DELIVER" },
  { key: KillChainStage.EXPLOIT, label: "EXPLOIT" },
  { key: KillChainStage.INSTALL, label: "INSTALL" },
  { key: KillChainStage.C2, label: "C2" },
  { key: KillChainStage.ACTION, label: "ACTION" },
];

interface KillChainIndicatorProps {
  stageCounts: Record<string, number>;
}

export function KillChainIndicator({ stageCounts }: KillChainIndicatorProps) {
  const maxCount = Math.max(1, ...Object.values(stageCounts));

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
      <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-3">
        Kill Chain Progress
      </h3>
      <div className="flex items-end gap-1.5 h-20">
        {STAGES.map((stage) => {
          const count = stageCounts[stage.key] || 0;
          const pct = (count / maxCount) * 100;
          return (
            <div key={stage.key} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-[9px] font-mono text-athena-accent font-bold">
                {count > 0 ? count : ""}
              </span>
              <div className="w-full bg-athena-border/30 rounded-sm overflow-hidden" style={{ height: "48px" }}>
                <div
                  className="w-full bg-athena-accent/70 rounded-sm transition-all"
                  style={{ height: `${pct}%`, marginTop: `${100 - pct}%` }}
                />
              </div>
              <span className="text-[8px] font-mono text-athena-text-secondary">{stage.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
