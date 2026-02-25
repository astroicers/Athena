"use client";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  accentColor?: string;
}

export function MetricCard({ title, value, subtitle, accentColor }: MetricCardProps) {
  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 flex flex-col gap-1">
      <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
        {title}
      </span>
      <span
        className="text-2xl font-mono font-bold"
        style={accentColor ? { color: accentColor } : undefined}
      >
        {value}
      </span>
      {subtitle && (
        <span className="text-[10px] font-mono text-athena-text-secondary">
          {subtitle}
        </span>
      )}
    </div>
  );
}
