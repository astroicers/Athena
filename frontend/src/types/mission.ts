import { ExecutionEngine, MissionStepStatus } from "./enums";

export interface MissionStep {
  id: string;
  operationId: string;
  stepNumber: number;
  techniqueId: string;
  techniqueName: string;
  targetId: string;
  targetLabel: string;
  engine: ExecutionEngine;
  status: MissionStepStatus;
}
