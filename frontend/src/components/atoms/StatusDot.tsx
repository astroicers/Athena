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
  alive: "bg-[#22C55E20]",
  operational: "bg-[#22C55E20]",
  active: "bg-[#3b82f6]",
  nominal: "bg-[#22C55E20]",
  engaged: "bg-[#FBBF2420]",
  scanning: "bg-[#3b82f6]",
  pending: "bg-[#FBBF2420]",
  degraded: "bg-[#FBBF2420]",
  untrusted: "bg-[#EF444420]",
  offline: "bg-[#1f2937]",
  dead: "bg-[#EF444420]",
  critical: "bg-[#DC262620]",
};

interface StatusDotProps {
  status: string;
  pulse?: boolean;
}

export function StatusDot({ status, pulse = false }: StatusDotProps) {
  const color = STATUS_COLORS[status] || "bg-[#1f2937]";
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
