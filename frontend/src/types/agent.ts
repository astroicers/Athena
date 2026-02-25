import { AgentStatus } from "./enums";

export interface Agent {
  id: string;
  paw: string;
  hostId: string;
  status: AgentStatus;
  privilege: string;
  lastBeacon: string | null;
  beaconIntervalSec: number;
  platform: string;
  operationId: string;
}
