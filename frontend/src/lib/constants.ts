// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import {
  OperationsIcon,
  MonitorIcon,
  AttackGraphIcon,
  VulnsIcon,
  ToolsIcon,
} from "@/components/atoms/NavIcons";

export const NAV_ITEMS = [
  { href: "/operations", icon: OperationsIcon, labelKey: "operations" },
  { href: "/warroom", icon: MonitorIcon, labelKey: "warRoom" },
  { href: "/attack-surface", icon: AttackGraphIcon, labelKey: "attackSurface" },
  { href: "/vulns", icon: VulnsIcon, labelKey: "vulns" },
  { href: "/tools", icon: ToolsIcon, labelKey: "tools" },
] as const;

export const C5ISR_DOMAINS = [
  "command",
  "control",
  "comms",
  "computers",
  "cyber",
  "isr",
] as const;

export const RISK_COLORS = {
  low: "#22C55E",
  medium: "#F59E0B",
  high: "#EF4444",
  critical: "#DC2626",
} as const;
