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

import { useTranslations } from "next-intl";
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

export interface KillChainStageCounts {
  total: number;
  tested: number;
  success: number;
  failed: number;
}

interface KillChainIndicatorProps {
  stageCounts: Record<string, KillChainStageCounts>;
}

const BAR_H = 48;

export function KillChainIndicator({ stageCounts }: KillChainIndicatorProps) {
  const t = useTranslations("KillChain");
  const tHints = useTranslations("Hints");

  const maxTotal = Math.max(
    1,
    ...Object.values(stageCounts).map((s) => s.total),
  );

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
      <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
        {t("progress")}
      </h3>
      <p className="text-[10px] font-mono text-athena-text-secondary/60 mb-3">{tHints("killChain")}</p>
      <div className="flex items-end gap-1.5 h-20">
        {STAGES.map((stage) => {
          const data = stageCounts[stage.key] || {
            total: 0,
            tested: 0,
            success: 0,
            failed: 0,
          };
          const totalPct = (data.total / maxTotal) * 100;
          const successH =
            data.total > 0 ? (data.success / data.total) * totalPct : 0;
          const failedH =
            data.total > 0 ? (data.failed / data.total) * totalPct : 0;
          const untestedH = totalPct - successH - failedH;

          return (
            <div
              key={stage.key}
              className="flex-1 flex flex-col items-center gap-1"
            >
              <span className="text-[10px] font-mono text-athena-accent font-bold">
                {data.total > 0 ? `${data.tested}/${data.total}` : ""}
              </span>
              <div
                className="w-full bg-athena-border/20 rounded-sm overflow-hidden flex flex-col justify-end"
                style={{ height: `${BAR_H}px` }}
              >
                {successH > 0 && (
                  <div
                    className="w-full bg-athena-accent/70 transition-all"
                    style={{ height: `${(successH / 100) * BAR_H}px` }}
                  />
                )}
                {failedH > 0 && (
                  <div
                    className="w-full bg-athena-error/50 transition-all"
                    style={{ height: `${(failedH / 100) * BAR_H}px` }}
                  />
                )}
                {untestedH > 0 && (
                  <div
                    className="w-full bg-athena-border/40 transition-all"
                    style={{ height: `${(untestedH / 100) * BAR_H}px` }}
                  />
                )}
              </div>
              <span className="text-[10px] font-mono text-athena-text-secondary">
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-3 mt-2">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-sm bg-athena-accent/70" />
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {t("tested")}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-sm bg-athena-error/50" />
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {t("failed")}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-sm bg-athena-border/40" />
          <span className="text-[10px] font-mono text-athena-text-secondary">
            {t("untested")}
          </span>
        </div>
      </div>
    </div>
  );
}
