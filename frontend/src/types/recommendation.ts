// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { ExecutionEngine, RiskLevel } from "./enums";

export interface TacticalOption {
  techniqueId: string;
  techniqueName: string;
  reasoning: string;
  riskLevel: RiskLevel;
  recommendedEngine: ExecutionEngine;
  confidence: number;
  prerequisites: string[];
}

export interface OrientRecommendation {
  id: string;
  operationId: string;
  oodaIterationId: string;
  situationAssessment: string;
  recommendedTechniqueId: string;
  confidence: number;
  options: TacticalOption[];
  reasoningText: string;
  accepted: boolean | null;
  createdAt: string;
}
