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
  C5ISRIcon,
  NavigatorIcon,
  PlannerIcon,
  MonitorIcon,
  ToolsIcon,
} from "@/components/atoms/NavIcons";

export const NAV_ITEMS = [
  { href: "/c5isr", icon: C5ISRIcon, labelKey: "c5isr" },
  { href: "/navigator", icon: NavigatorIcon, labelKey: "navigator" },
  { href: "/planner", icon: PlannerIcon, labelKey: "planner" },
  { href: "/monitor", icon: MonitorIcon, labelKey: "monitor" },
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
  low: "#00ff88",
  medium: "#ffaa00",
  high: "#ff4444",
  critical: "#ff0040",
} as const;
