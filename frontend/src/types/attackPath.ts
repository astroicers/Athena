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
