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

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useToast } from "@/contexts/ToastContext";
import { PageLoading } from "@/components/ui/PageLoading";
import { MITRECell } from "@/components/mitre/MITRECell";
import { KillChainIndicator } from "@/components/mitre/KillChainIndicator";
import { AttackPathTimeline } from "@/components/mitre/AttackPathTimeline";
import { TechniqueCard } from "@/components/cards/TechniqueCard";
import { RecommendCard } from "@/components/cards/RecommendCard";
import type { TechniqueWithStatus } from "@/types/technique";
import type { OrientRecommendation } from "@/types/recommendation";
import type { AttackPathResponse } from "@/types/attackPath";
import type { TechniqueStatus } from "@/types/enums";

const DEFAULT_OP_ID = "op-0001";

function normalizeTactic(tactic: string): string {
  return tactic.toLowerCase().replace(/\s+/g, "-");
}

const TACTIC_ID_TO_SLUG: Record<string, string> = {
  "TA0043": "reconnaissance",
  "TA0042": "resource-development",
  "TA0001": "initial-access",
  "TA0002": "execution",
  "TA0003": "persistence",
  "TA0004": "privilege-escalation",
  "TA0005": "defense-evasion",
  "TA0006": "credential-access",
  "TA0007": "discovery",
  "TA0008": "lateral-movement",
  "TA0009": "collection",
  "TA0011": "command-and-control",
  "TA0010": "exfiltration",
  "TA0040": "impact",
};

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
  const t = useTranslations("Navigator");
  const tHints = useTranslations("Hints");
  const tEmpty = useTranslations("EmptyStates");
  const tErrors = useTranslations("Errors");

  const { addToast } = useToast();
  const ws = useWebSocket(DEFAULT_OP_ID);
  const [isLoading, setIsLoading] = useState(true);
  const [techniques, setTechniques] = useState<TechniqueWithStatus[]>([]);
  const [selected, setSelected] = useState<TechniqueWithStatus | null>(null);
  const [recommendation, setRecommendation] = useState<OrientRecommendation | null>(null);
  const [attackPath, setAttackPath] = useState<AttackPathResponse | null>(null);
  const [loadingPath, setLoadingPath] = useState(true);
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`).then(setTechniques),
      api.get<OrientRecommendation>(`/operations/${DEFAULT_OP_ID}/recommendations/latest`).then(setRecommendation),
      api.getAttackPath(DEFAULT_OP_ID)
        .then(setAttackPath)
        .catch(() => {
          // Attack path may not yet exist; non-fatal
          setAttackPath(null);
        })
        .finally(() => setLoadingPath(false)),
    ]).catch(() => addToast(tErrors("failedLoadC5isr"), "error"))
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // WebSocket: refresh techniques and attack path on execution updates
  useEffect(() => {
    return ws.subscribe("execution.update", () => {
      api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`)
        .then(setTechniques)
        .catch(() => addToast(tErrors("failedRefreshTechniques"), "error"));

      api.getAttackPath(DEFAULT_OP_ID)
        .then(setAttackPath)
        .catch(() => {
          // Non-fatal; keep existing data if refetch fails
        });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws]);

  // WebSocket: update recommendation card immediately when AI analysis completes
  useEffect(() => {
    const unsub = ws.subscribe("recommendation", (raw: unknown) => {
      setRecommendation(raw as unknown as OrientRecommendation);
    });
    return unsub;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws]);

  const grouped = useMemo(() => {
    const map = new Map<string, TechniqueWithStatus[]>();
    for (const t of techniques) {
      const key = TACTIC_ID_TO_SLUG[t.tacticId] || normalizeTactic(t.tactic);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(t);
    }
    return map;
  }, [techniques]);

  const orderedTactics = useMemo(() => {
    return TACTIC_ORDER.filter((t) => grouped.has(t));
  }, [grouped]);

  const stageCounts = useMemo(() => {
    const counts: Record<string, { total: number; tested: number; success: number; failed: number }> = {};
    for (const t of techniques) {
      const stage = t.killChainStage || "exploit";
      if (!counts[stage]) counts[stage] = { total: 0, tested: 0, success: 0, failed: 0 };
      counts[stage].total += 1;
      if (t.latestStatus && t.latestStatus !== "untested") {
        counts[stage].tested += 1;
        if (t.latestStatus === "success" || t.latestStatus === "partial") {
          counts[stage].success += 1;
        } else if (t.latestStatus === "failed") {
          counts[stage].failed += 1;
        }
      }
    }
    return counts;
  }, [techniques]);

  if (isLoading) return <PageLoading />;

  return (
    <div className="space-y-4">
      {/* Attack Path Timeline — above the ATT&CK matrix */}
      <AttackPathTimeline data={attackPath} loading={loadingPath} />
      <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-3 ml-1">{tHints("attackPath")}</p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* ATT&CK Matrix — 3 cols */}
        <div className="lg:col-span-3">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider">
              {t("mitreMatrix")}
            </h2>
            <button
              onClick={() => setCompact(!compact)}
              className="text-[10px] font-mono text-athena-text-secondary hover:text-athena-accent transition-colors px-2 py-0.5 border border-athena-border rounded-athena-sm"
            >
              {compact ? t("expandView") : t("compactView")}
            </button>
          </div>
          <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-1 mb-2 ml-1">{tHints("mitreMatrix")}</p>
          <div className="bg-athena-surface border border-athena-border rounded-athena-md p-3 overflow-x-auto">
            <div className="flex gap-2 min-w-max">
              {orderedTactics.map((tactic) => (
                <div key={tactic} className={`${compact ? "w-20" : "w-28"} shrink-0`}>
                  <div className="text-[10px] font-mono text-athena-accent font-bold uppercase mb-2 truncate">
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
                        compact={compact}
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
            <div className="border-2 border-dashed border-athena-border/50 rounded-athena-md p-4">
              <span className="text-xs font-mono text-athena-text-secondary">
                {tEmpty("navigatorNoSelection")}
              </span>
            </div>
          )}
          <RecommendCard recommendation={recommendation} />
        </div>
      </div>
    </div>
  );
}
