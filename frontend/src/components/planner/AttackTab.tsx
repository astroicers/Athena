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

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { MITRECell } from "@/components/mitre/MITRECell";
import { KillChainIndicator } from "@/components/mitre/KillChainIndicator";
import { AttackPathTimeline } from "@/components/mitre/AttackPathTimeline";
import { TechniqueCard } from "@/components/cards/TechniqueCard";
import {
  TACTIC_ID_TO_SLUG,
  TACTIC_ORDER,
  normalizeTactic,
  tacticLabel,
  getToolsForTechnique,
} from "@/lib/mitre-mapping";
import { useStageCounts } from "@/hooks/useStageCounts";
import type { TechniqueWithStatus } from "@/types/technique";
import type { ToolRegistryEntry } from "@/types/tool";
import type { AttackPathResponse } from "@/types/attackPath";
import type { TechniqueStatus } from "@/types/enums";

export interface AttackTabProps {
  techniques: TechniqueWithStatus[];
  selectedTech: TechniqueWithStatus | null;
  attackPath: AttackPathResponse | null;
  allTools: ToolRegistryEntry[];
  compact: boolean;
  onSetSelectedTech: (tech: TechniqueWithStatus | null) => void;
  onSetCompact: (compact: boolean) => void;
}

export function AttackTab({
  techniques,
  selectedTech,
  attackPath,
  allTools,
  compact,
  onSetSelectedTech,
  onSetCompact,
}: AttackTabProps) {
  const t = useTranslations("Planner");
  const tHints = useTranslations("Hints");
  const tEmpty = useTranslations("EmptyStates");

  const grouped = useMemo(() => {
    const map = new Map<string, TechniqueWithStatus[]>();
    for (const tech of techniques) {
      const key = TACTIC_ID_TO_SLUG[tech.tacticId] || normalizeTactic(tech.tactic);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(tech);
    }
    return map;
  }, [techniques]);

  const orderedTactics = useMemo(() => {
    return TACTIC_ORDER.filter((tac) => grouped.has(tac));
  }, [grouped]);

  const stageCounts = useStageCounts(techniques);

  return (
    <div className="flex-1 space-y-4 min-h-0 overflow-y-auto py-4 px-6">
      {/* Attack Path Timeline */}
      <AttackPathTimeline data={attackPath} loading={false} />
      <p className="text-sm font-mono text-[#9ca3af] -mt-3 ml-1">{tHints("attackPath")}</p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* ATT&CK Matrix */}
        <div className="lg:col-span-3">
          <SectionHeader
            className="mb-2"
            trailing={
              <button
                onClick={() => onSetCompact(!compact)}
                className="text-[10px] font-mono text-[#9ca3af] hover:text-[#3b82f6] transition-colors rounded bg-[#111827] border border-[#374151]"
                style={{ padding: "5px 10px" }}
              >
                {compact ? t("expandView") : t("compactView")}
              </button>
            }
          >
            {t("mitreMatrix")}
          </SectionHeader>
          <p className="text-sm font-mono text-[#9ca3af] -mt-1 mb-2 ml-1">{tHints("mitreMatrix")}</p>
          <div className="bg-[#111827] border border-[#1f2937] rounded-lg p-3 overflow-x-auto">
            <div className="flex gap-2 min-w-max">
              {orderedTactics.map((tactic) => (
                <div key={tactic} className={`${compact ? "w-20" : "w-28"} shrink-0`}>
                  <div className="text-sm font-mono text-[#3b82f6] font-bold uppercase mb-2 truncate">
                    {tacticLabel(tactic)}
                  </div>
                  <div className="space-y-1">
                    {(grouped.get(tactic) || []).map((tech) => (
                      <MITRECell
                        key={tech.id}
                        mitreId={tech.mitreId}
                        name={tech.name}
                        status={tech.latestStatus as TechniqueStatus | null}
                        isSelected={selectedTech?.id === tech.id}
                        onClick={() => onSetSelectedTech(tech)}
                        compact={compact}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right sidebar -- Kill Chain + Technique Card */}
        <div className="space-y-4">
          <KillChainIndicator stageCounts={stageCounts} />
          {selectedTech ? (
            <TechniqueCard
              technique={selectedTech}
              relatedTools={getToolsForTechnique(allTools, selectedTech.mitreId)}
            />
          ) : (
            <div className="border border-[#1f293740] rounded-lg p-4">
              <span className="text-xs font-mono text-[#9ca3af]">
                {tEmpty("navigatorNoSelection")}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
