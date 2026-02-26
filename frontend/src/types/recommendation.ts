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

export interface PentestGPTRecommendation {
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
