// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import { KillChainStage } from "@/types/enums";

// ── Phase-aware colour palette ──
export const PHASE_COLORS: Record<string, string> = {
  session:   "#ff4444",   // red — active session
  attacking: "#ff8800",   // orange — technique executing
  scanning:  "#4488ff",   // blue — recon running
  attempted: "#00ff8866", // faded green — tried but no session
  idle:      "#00ff88",   // green — untouched target
  c2:        "#4488ff",   // blue — Athena C2 node
  lateral:   "#ffaa00",   // gold — lateral movement path
};

export const KILL_CHAIN_COLORS: Record<KillChainStage, string> = {
  [KillChainStage.RECON]:     "#4488ff",
  [KillChainStage.WEAPONIZE]: "#8855ff",
  [KillChainStage.DELIVER]:   "#aa44ff",
  [KillChainStage.EXPLOIT]:   "#ff8800",
  [KillChainStage.INSTALL]:   "#ffaa00",
  [KillChainStage.C2]:        "#ff4444",
  [KillChainStage.ACTION]:    "#ff0040",
};
