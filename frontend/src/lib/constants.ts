export const NAV_ITEMS = [
  { href: "/c5isr", icon: "command", label: "C5ISR Board" },
  { href: "/navigator", icon: "mitre", label: "MITRE Navigator" },
  { href: "/planner", icon: "mission", label: "Mission Planner" },
  { href: "/monitor", icon: "monitor", label: "Battle Monitor" },
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
  high: "#ff8800",
  critical: "#ff0040",
} as const;
