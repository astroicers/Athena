// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

export interface ServiceInfo {
  port: number;
  protocol: string;
  service: string;
  version: string;
  state: string;
}

export interface InitialAccessResult {
  success: boolean;
  method: string;
  credential: string | null;
  agentDeployed: boolean;
  error: string | null;
}

export interface ReconScanResult {
  scanId: string;
  status: string;
  targetId: string;
  operationId: string;
  ipAddress: string;
  osGuess: string | null;
  servicesFound: number;
  services: ServiceInfo[];
  factsWritten: number;
  initialAccess: InitialAccessResult;
  scanDurationSec: number;
}

export interface ReconScanQueued {
  scanId: string;
  status: "queued";
  targetId: string;
  operationId: string;
}
