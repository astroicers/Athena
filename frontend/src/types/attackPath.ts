// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { TechniqueStatus } from "./enums";

export interface AttackPathEntry {
  executionId: string;
  mitreId: string;
  techniqueName: string;
  tactic: string;
  tacticId: string;
  killChainStage: string;
  riskLevel: string;
  status: TechniqueStatus;
  engine: string;
  startedAt: string | null;
  completedAt: string | null;
  durationSec: number | null;
  resultSummary: string | null;
  errorMessage: string | null;
  factsCollectedCount: number;
  targetHostname: string | null;
  targetIp: string | null;
}

export interface AttackPathResponse {
  operationId: string;
  entries: AttackPathEntry[];
  highestTacticIdx: number;
  tacticCoverage: Record<string, number>;
}
