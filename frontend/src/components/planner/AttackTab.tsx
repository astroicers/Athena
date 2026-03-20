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
import { Button } from "@/components/atoms/Button";
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
    <div className="flex-1 space-y-3 min-h-0 overflow-y-auto py-3 px-4">
      {/* Attack Path Timeline */}
      <AttackPathTimeline data={attackPath} loading={false} />
      <p className="text-[10px] font-mono text-athena-text-tertiary -mt-2 ml-0.5">{tHints("attackPath")}</p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
        {/* ATT&CK Matrix */}
        <div className="lg:col-span-3">
          <SectionHeader
            className="mb-2"
            trailing={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onSetCompact(!compact)}
                className="text-[10px] text-athena-text-tertiary hover:text-athena-accent"
              >
                {compact ? t("expandView") : t("compactView")}
              </Button>
            }
          >
            {t("mitreMatrix")}
          </SectionHeader>
          <p className="text-[10px] font-mono text-athena-text-tertiary -mt-1 mb-1.5 ml-0.5">{tHints("mitreMatrix")}</p>
          <div className="bg-athena-surface border border-athena-border rounded-athena p-2.5 overflow-x-auto">
            <div className="flex gap-1.5 min-w-max">
              {orderedTactics.map((tactic) => (
                <div key={tactic} className={`${compact ? "w-20" : "w-28"} shrink-0`}>
                  <div className="text-[10px] font-mono text-athena-accent font-bold uppercase mb-1.5 truncate tracking-wider">
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
        <div className="space-y-3">
          <KillChainIndicator stageCounts={stageCounts} />
          {selectedTech ? (
            <TechniqueCard
              technique={selectedTech}
              relatedTools={getToolsForTechnique(allTools, selectedTech.mitreId)}
            />
          ) : (
            <div className="bg-athena-surface border border-athena-border rounded-athena p-3">
              <span className="text-[10px] font-mono text-athena-text-tertiary">
                {tEmpty("navigatorNoSelection")}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
