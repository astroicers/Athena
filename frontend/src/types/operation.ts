// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

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
  missionProfile: string;
  operatorId: string | null;
  createdAt: string;
  updatedAt: string;
}
