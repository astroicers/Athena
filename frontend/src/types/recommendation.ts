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
