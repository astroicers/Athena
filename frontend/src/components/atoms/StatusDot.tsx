// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use client";

const STATUS_COLORS: Record<string, string> = {
  alive: "bg-athena-success-bg",
  operational: "bg-athena-success-bg",
  active: "bg-[#3b82f6]",
  nominal: "bg-athena-success-bg",
  engaged: "bg-athena-warning-bg",
  scanning: "bg-[#3b82f6]",
  pending: "bg-athena-warning-bg",
  degraded: "bg-athena-warning-bg",
  untrusted: "bg-athena-error-bg",
  offline: "bg-athena-elevated",
  dead: "bg-athena-error-bg",
  critical: "bg-[#DC262620]",
};

interface StatusDotProps {
  status: string;
  pulse?: boolean;
}

export function StatusDot({ status, pulse = false }: StatusDotProps) {
  const color = STATUS_COLORS[status] || "bg-athena-elevated";
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
