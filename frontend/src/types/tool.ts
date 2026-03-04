// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

export interface ToolRegistryEntry {
  id: string;
  toolId: string;
  name: string;
  description: string | null;
  kind: "tool" | "engine";
  category: string;
  version: string | null;
  enabled: boolean;
  source: "seed" | "user";
  configJson: Record<string, unknown>;
  mitreTechniques: string[];
  riskLevel: string;
  outputTraits: string[];
  createdAt: string;
  updatedAt: string;
}

export interface ToolRegistryCreate {
  toolId: string;
  name: string;
  description?: string;
  kind?: "tool" | "engine";
  category?: string;
  version?: string;
  enabled?: boolean;
  configJson?: Record<string, unknown>;
  mitreTechniques?: string[];
  riskLevel?: string;
  outputTraits?: string[];
}

export interface ToolHealthCheck {
  toolId: string;
  available: boolean;
  detail: string;
}
