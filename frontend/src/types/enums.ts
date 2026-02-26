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

export enum OODAPhase {
  OBSERVE = "observe",
  ORIENT = "orient",
  DECIDE = "decide",
  ACT = "act",
}

export enum OperationStatus {
  PLANNING = "planning",
  ACTIVE = "active",
  PAUSED = "paused",
  COMPLETED = "completed",
  ABORTED = "aborted",
}

export enum TechniqueStatus {
  UNTESTED = "untested",
  QUEUED = "queued",
  RUNNING = "running",
  SUCCESS = "success",
  PARTIAL = "partial",
  FAILED = "failed",
}

export enum MissionStepStatus {
  QUEUED = "queued",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  SKIPPED = "skipped",
}

export enum AgentStatus {
  ALIVE = "alive",
  DEAD = "dead",
  PENDING = "pending",
  UNTRUSTED = "untrusted",
}

export enum ExecutionEngine {
  CALDERA = "caldera",
  SHANNON = "shannon",
}

export enum C5ISRDomain {
  COMMAND = "command",
  CONTROL = "control",
  COMMS = "comms",
  COMPUTERS = "computers",
  CYBER = "cyber",
  ISR = "isr",
}

export enum C5ISRDomainStatus {
  OPERATIONAL = "operational",
  ACTIVE = "active",
  NOMINAL = "nominal",
  ENGAGED = "engaged",
  SCANNING = "scanning",
  DEGRADED = "degraded",
  OFFLINE = "offline",
  CRITICAL = "critical",
}

export enum FactCategory {
  CREDENTIAL = "credential",
  HOST = "host",
  NETWORK = "network",
  SERVICE = "service",
  VULNERABILITY = "vulnerability",
  FILE = "file",
}

export enum LogSeverity {
  INFO = "info",
  SUCCESS = "success",
  WARNING = "warning",
  ERROR = "error",
  CRITICAL = "critical",
}

export enum KillChainStage {
  RECON = "recon",
  WEAPONIZE = "weaponize",
  DELIVER = "deliver",
  EXPLOIT = "exploit",
  INSTALL = "install",
  C2 = "c2",
  ACTION = "action",
}

export enum RiskLevel {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  CRITICAL = "critical",
}

export enum AutomationMode {
  MANUAL = "manual",
  SEMI_AUTO = "semi_auto",
}
