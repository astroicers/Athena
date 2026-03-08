// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

export interface PocRecord {
  id: string;
  technique_id: string;
  technique_name: string;
  target_ip: string;
  commands_executed: string[];
  input_params: Record<string, string>;
  output_snippet: string;
  environment: Record<string, string>;
  reproducible: "reproducible" | "partial" | "not_reproducible";
  timestamp: string;
  engine: string;
}

export interface PocSummary {
  total: number;
  reproducible: number;
  targets: number;
  techniques: number;
}
