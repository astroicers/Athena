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
