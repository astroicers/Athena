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
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { KillChainStage } from "@/types/enums";

const STAGES: { key: KillChainStage }[] = [
  { key: KillChainStage.RECON },
  { key: KillChainStage.WEAPONIZE },
  { key: KillChainStage.DELIVER },
  { key: KillChainStage.EXPLOIT },
  { key: KillChainStage.INSTALL },
  { key: KillChainStage.C2 },
  { key: KillChainStage.ACTION },
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
    <div className="bg-[#111827] border border-[#1f2937] rounded-athena-md p-4">
      <SectionHeader level="card" className="mb-1">
        {t("progress")}
      </SectionHeader>
      <p className="text-sm font-mono text-[#9ca3af] mb-3">{tHints("killChain")}</p>
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
              <span className="text-sm font-mono text-[#3b82f6] font-bold">
                {data.total > 0 ? `${data.tested}/${data.total}` : ""}
              </span>
              <div
                className="w-full bg-[#1f293733] rounded-athena-sm overflow-hidden flex flex-col justify-end"
                style={{ height: `${BAR_H}px` }}
              >
                {successH > 0 && (
                  <div
                    className="w-full bg-[#3b82f6]/70 transition-all"
                    style={{ height: `${(successH / 100) * BAR_H}px` }}
                  />
                )}
                {failedH > 0 && (
                  <div
                    className="w-full bg-[#EF444420]/50 transition-all"
                    style={{ height: `${(failedH / 100) * BAR_H}px` }}
                  />
                )}
                {untestedH > 0 && (
                  <div
                    className="w-full bg-[#1f2937]/40 transition-all"
                    style={{ height: `${(untestedH / 100) * BAR_H}px` }}
                  />
                )}
              </div>
              <span className="text-sm font-mono text-[#9ca3af]">
                {t(stage.key as any)}
              </span>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-3 mt-2">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-athena-sm bg-[#3b82f6]/70" />
          <span className="text-sm font-mono text-[#9ca3af]">
            {t("tested")}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-athena-sm bg-[#EF444420]/50" />
          <span className="text-sm font-mono text-[#9ca3af]">
            {t("failed")}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-athena-sm bg-[#1f2937]/40" />
          <span className="text-sm font-mono text-[#9ca3af]">
            {t("untested")}
          </span>
        </div>
      </div>
    </div>
  );
}
