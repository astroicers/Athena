"use client";

const STATUS_COLORS: Record<string, string> = {
  alive: "bg-athena-success",
  operational: "bg-athena-success",
  active: "bg-athena-accent",
  nominal: "bg-athena-success",
  engaged: "bg-athena-warning",
  scanning: "bg-athena-accent",
  pending: "bg-athena-warning",
  degraded: "bg-athena-warning",
  untrusted: "bg-athena-error",
  offline: "bg-gray-500",
  dead: "bg-athena-error",
  critical: "bg-athena-critical",
};

interface StatusDotProps {
  status: string;
  pulse?: boolean;
}

export function StatusDot({ status, pulse = false }: StatusDotProps) {
  const color = STATUS_COLORS[status] || "bg-gray-500";
  return (
    <span className="relative inline-flex h-2.5 w-2.5">
      {pulse && (
        <span
          className={`absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping ${color}`}
        />
      )}
      <span
        className={`relative inline-flex h-2.5 w-2.5 rounded-full ${color}`}
      />
    </span>
  );
}
