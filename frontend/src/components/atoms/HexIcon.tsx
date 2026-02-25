"use client";

const VARIANT_COLORS = {
  default: "text-athena-accent",
  success: "text-athena-success",
  warning: "text-athena-warning",
  error: "text-athena-error",
  muted: "text-athena-text-secondary",
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
  return (
    <div
      className={`inline-flex items-center justify-center font-mono font-bold
        ${SIZE_MAP[size]} ${VARIANT_COLORS[variant]}
        bg-current/10 rounded-lg`}
    >
      <span className="opacity-100">{icon}</span>
    </div>
  );
}
