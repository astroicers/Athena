import { AutomationMode, OODAPhase, OperationStatus, RiskLevel } from "./enums";

export interface Operation {
  id: string;
  code: string;
  name: string;
  codename: string;
  strategicIntent: string;
  status: OperationStatus;
  currentOodaPhase: OODAPhase;
  oodaIterationCount: number;
  threatLevel: number;
  successRate: number;
  techniquesExecuted: number;
  techniquesTotal: number;
  activeAgents: number;
  dataExfiltratedBytes: number;
  automationMode: AutomationMode;
  riskThreshold: RiskLevel;
  operatorId: string | null;
  createdAt: string;
  updatedAt: string;
}
