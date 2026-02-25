"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { MITRECell } from "@/components/mitre/MITRECell";
import { KillChainIndicator } from "@/components/mitre/KillChainIndicator";
import { TechniqueCard } from "@/components/cards/TechniqueCard";
import { RecommendCard } from "@/components/cards/RecommendCard";
import type { TechniqueWithStatus } from "@/types/technique";
import type { PentestGPTRecommendation } from "@/types/recommendation";
import type { TechniqueStatus } from "@/types/enums";

const DEFAULT_OP_ID = "op-phantom-eye-001";

const TACTIC_ORDER = [
  "reconnaissance",
  "resource-development",
  "initial-access",
  "execution",
  "persistence",
  "privilege-escalation",
  "defense-evasion",
  "credential-access",
  "discovery",
  "lateral-movement",
  "collection",
  "command-and-control",
  "exfiltration",
  "impact",
];

function tacticLabel(tactic: string): string {
  return tactic
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function NavigatorPage() {
  const [techniques, setTechniques] = useState<TechniqueWithStatus[]>([]);
  const [selected, setSelected] = useState<TechniqueWithStatus | null>(null);
  const [recommendation, setRecommendation] = useState<PentestGPTRecommendation | null>(null);

  useEffect(() => {
    api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`).then(setTechniques).catch(() => {});
    api.get<PentestGPTRecommendation>(`/operations/${DEFAULT_OP_ID}/recommendations/latest`).then(setRecommendation).catch(() => {});
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, TechniqueWithStatus[]>();
    for (const t of techniques) {
      const key = t.tacticId || t.tactic;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(t);
    }
    return map;
  }, [techniques]);

  const orderedTactics = useMemo(() => {
    return TACTIC_ORDER.filter((t) => grouped.has(t));
  }, [grouped]);

  const stageCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const t of techniques) {
      if (t.latestStatus && t.latestStatus !== "untested") {
        const stage = t.killChainStage || "exploit";
        counts[stage] = (counts[stage] || 0) + 1;
      }
    }
    return counts;
  }, [techniques]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        {/* ATT&CK Matrix — 3 cols */}
        <div className="col-span-3">
          <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-2">
            MITRE ATT&CK Matrix
          </h2>
          <div className="bg-athena-surface border border-athena-border rounded-athena-md p-3 overflow-x-auto">
            <div className="flex gap-2 min-w-max">
              {orderedTactics.map((tactic) => (
                <div key={tactic} className="w-28 shrink-0">
                  <div className="text-[9px] font-mono text-athena-accent font-bold uppercase mb-2 truncate">
                    {tacticLabel(tactic)}
                  </div>
                  <div className="space-y-1">
                    {(grouped.get(tactic) || []).map((t) => (
                      <MITRECell
                        key={t.id}
                        mitreId={t.mitreId}
                        name={t.name}
                        status={t.latestStatus as TechniqueStatus | null}
                        isSelected={selected?.id === t.id}
                        onClick={() => setSelected(t)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right sidebar */}
        <div className="space-y-4">
          <KillChainIndicator stageCounts={stageCounts} />
          {selected ? (
            <TechniqueCard technique={selected} />
          ) : (
            <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
              <span className="text-xs font-mono text-athena-text-secondary">
                Select a technique to view details
              </span>
            </div>
          )}
          <RecommendCard recommendation={recommendation} />
        </div>
      </div>
    </div>
  );
}
