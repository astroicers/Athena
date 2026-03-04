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

import { useMemo } from "react";
import { KillChainStage, TechniqueStatus } from "@/types/enums";
import type { OODAPhase } from "@/types/enums";
import type { TechniqueWithStatus } from "@/types/technique";

const KILL_CHAIN_ORDER: KillChainStage[] = [
  KillChainStage.RECON,
  KillChainStage.WEAPONIZE,
  KillChainStage.DELIVER,
  KillChainStage.EXPLOIT,
  KillChainStage.INSTALL,
  KillChainStage.C2,
  KillChainStage.ACTION,
];

export interface SituationStage {
  stage: KillChainStage;
  status: "inactive" | "active" | "completed" | "partial";
  totalCount: number;
  successCount: number;
  failedCount: number;
  runningCount: number;
}

export interface SituationData {
  stages: SituationStage[];
  currentStageIndex: number;
  oodaPhase: OODAPhase | null;
  c5isrHealth: Record<string, number>;
  activeTechniqueId: string | null;
  overallProgress: number;
}

export function useSituationData(
  techniques: TechniqueWithStatus[],
  oodaPhase: OODAPhase | null,
  executionUpdate: { techniqueId?: string } | null,
  c5isrDomains: Array<{ domain: string; healthPct: number }>,
): SituationData {
  return useMemo(() => {
    // Group techniques by kill chain stage
    const grouped: Record<string, TechniqueWithStatus[]> = {};
    for (const t of techniques) {
      const key = t.killChainStage;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(t);
    }

    // Build stage data
    const stages: SituationStage[] = KILL_CHAIN_ORDER.map((stage) => {
      const techs = grouped[stage] ?? [];
      const totalCount = techs.length;
      const successCount = techs.filter(
        (t) =>
          t.latestStatus === TechniqueStatus.SUCCESS ||
          t.latestStatus === TechniqueStatus.PARTIAL,
      ).length;
      const failedCount = techs.filter(
        (t) => t.latestStatus === TechniqueStatus.FAILED,
      ).length;
      const runningCount = techs.filter(
        (t) =>
          t.latestStatus === TechniqueStatus.RUNNING ||
          t.latestStatus === TechniqueStatus.QUEUED,
      ).length;

      let status: SituationStage["status"];
      if (totalCount === 0) {
        status = "inactive";
      } else if (runningCount > 0) {
        status = "active";
      } else if (successCount === totalCount && totalCount > 0) {
        status = "completed";
      } else if (successCount > 0 || failedCount > 0) {
        status = "partial";
      } else {
        status = "inactive";
      }

      return { stage, status, totalCount, successCount, failedCount, runningCount };
    });

    // Determine current stage index: highest stage with running, or most recent success
    let currentStageIndex = -1;
    for (let i = stages.length - 1; i >= 0; i--) {
      if (stages[i].runningCount > 0) {
        currentStageIndex = i;
        break;
      }
    }
    if (currentStageIndex === -1) {
      for (let i = stages.length - 1; i >= 0; i--) {
        if (stages[i].successCount > 0) {
          currentStageIndex = i;
          break;
        }
      }
    }

    // Convert c5isrDomains array to Record
    const c5isrHealth: Record<string, number> = {};
    for (const d of c5isrDomains) {
      c5isrHealth[d.domain] = d.healthPct;
    }

    // Active technique from execution update
    const activeTechniqueId = executionUpdate?.techniqueId ?? null;

    // Overall progress: stages with any success / 7 * 100
    const stagesWithSuccess = stages.filter((s) => s.successCount > 0).length;
    const overallProgress = (stagesWithSuccess / 7) * 100;

    return {
      stages,
      currentStageIndex,
      oodaPhase,
      c5isrHealth,
      activeTechniqueId,
      overallProgress,
    };
  }, [techniques, oodaPhase, executionUpdate, c5isrDomains]);
}
