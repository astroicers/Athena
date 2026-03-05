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

import { useMemo } from "react";
import type { TechniqueWithStatus } from "@/types/technique";

export function useStageCounts(techniques: TechniqueWithStatus[]) {
  return useMemo(() => {
    const counts: Record<string, { total: number; tested: number; success: number; failed: number }> = {};
    techniques.forEach((tech) => {
      const stage = tech.killChainStage;
      if (!counts[stage]) counts[stage] = { total: 0, tested: 0, success: 0, failed: 0 };
      counts[stage].total += 1;
      if (tech.latestStatus && tech.latestStatus !== "untested") {
        counts[stage].tested += 1;
        if (tech.latestStatus === "success" || tech.latestStatus === "partial") {
          counts[stage].success += 1;
        } else if (tech.latestStatus === "failed") {
          counts[stage].failed += 1;
        }
      }
    });
    return counts;
  }, [techniques]);
}
