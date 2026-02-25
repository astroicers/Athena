import { LogSeverity } from "./enums";

export interface LogEntry {
  id: string;
  timestamp: string;
  severity: LogSeverity;
  source: string;
  message: string;
  operationId: string | null;
  techniqueId: string | null;
}
