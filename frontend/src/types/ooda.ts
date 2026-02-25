import { OODAPhase } from "./enums";

export interface OODAIteration {
  id: string;
  operationId: string;
  iterationNumber: number;
  phase: OODAPhase;
  observeSummary: string | null;
  orientSummary: string | null;
  decideSummary: string | null;
  actSummary: string | null;
  recommendationId: string | null;
  techniqueExecutionId: string | null;
  startedAt: string;
  completedAt: string | null;
}

export interface OODATimelineEntry {
  iterationNumber: number;
  phase: string;
  summary: string;
  timestamp: string;
}
