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
