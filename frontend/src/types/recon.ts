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
