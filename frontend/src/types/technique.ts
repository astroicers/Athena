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
  calderaAbilityId: string | null;
  platforms: string[];
}

export interface TechniqueWithStatus extends Technique {
  latestStatus: TechniqueStatus | null;
  latestExecutionId: string | null;
}
