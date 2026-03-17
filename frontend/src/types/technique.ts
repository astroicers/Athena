// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { KillChainStage, RiskLevel, TechniqueStatus } from "./enums";

export interface Technique {
  id: string;
  mitreId: string;
  name: string;
  tactic: string;
  tacticId: string;
  description: string | null;
  killChainStage: KillChainStage;
  riskLevel: RiskLevel;
  c2AbilityId: string | null;
  platforms: string[];
}

export interface TechniqueWithStatus extends Technique {
  latestStatus: TechniqueStatus | null;
  latestExecutionId: string | null;
}
