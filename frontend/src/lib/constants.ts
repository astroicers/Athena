// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import {
  OperationsIcon,
  PlannerIcon,
  MonitorIcon,
  PocIcon,
  VulnsIcon,
  OPSECIcon,
  AttackGraphIcon,
  ToolsIcon,
  AIDecisionsIcon,
} from "@/components/atoms/NavIcons";

export const NAV_ITEMS = [
  { href: "/operations", icon: OperationsIcon, labelKey: "operations" },
  { href: "/planner", icon: PlannerIcon, labelKey: "planner" },
  { href: "/warroom", icon: MonitorIcon, labelKey: "warRoom" },
  { href: "/decisions", icon: AIDecisionsIcon, labelKey: "decisions" },
  { href: "/poc", icon: PocIcon, labelKey: "poc" },
  { href: "/vulns", icon: VulnsIcon, labelKey: "vulns" },
  { href: "/opsec", icon: OPSECIcon, labelKey: "opsec" },
  { href: "/attack-graph", icon: AttackGraphIcon, labelKey: "attackGraph" },
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
