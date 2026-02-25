"use client";

const VARIANT_COLORS = {
  default: { text: "text-athena-accent", bg: "bg-athena-accent/10" },
  success: { text: "text-athena-success", bg: "bg-athena-success/10" },
  warning: { text: "text-athena-warning", bg: "bg-athena-warning/10" },
  error: { text: "text-athena-error", bg: "bg-athena-error/10" },
  muted: { text: "text-athena-text-secondary", bg: "bg-athena-text-secondary/10" },
} as const;

const SIZE_MAP = {
  sm: "w-6 h-6 text-xs",
  md: "w-8 h-8 text-sm",
  lg: "w-10 h-10 text-base",
} as const;

interface HexIconProps {
  icon: string;
  size?: keyof typeof SIZE_MAP;
  variant?: keyof typeof VARIANT_COLORS;
}

export function HexIcon({
  icon,
  size = "md",
  variant = "default",
}: HexIconProps) {
  const { text, bg } = VARIANT_COLORS[variant];
  return (
    <div
      className={`inline-flex items-center justify-center font-mono font-bold rounded-lg
        ${SIZE_MAP[size]} ${text} ${bg}`}
    >
      <span>{icon}</span>
    </div>
  );
}
