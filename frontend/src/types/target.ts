// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

export interface Target {
  id: string;
  hostname: string;
  ipAddress: string;
  os: string | null;
  role: string;
  networkSegment: string;
  isCompromised: boolean;
  isActive: boolean;
  privilegeLevel: string | null;
  operationId: string;
}
