// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

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
  offline: "bg-athena-border",
  dead: "bg-athena-error",
  critical: "bg-athena-critical",
};

interface StatusDotProps {
  status: string;
  pulse?: boolean;
}

export function StatusDot({ status, pulse = false }: StatusDotProps) {
  const color = STATUS_COLORS[status] || "bg-athena-border";
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
