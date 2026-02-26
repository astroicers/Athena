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

import { Badge } from "@/components/atoms/Badge";

interface HostNodeCardProps {
  hostname: string;
  ipAddress: string;
  role: string;
  isCompromised: boolean;
  privilegeLevel: string | null;
}

export function HostNodeCard({
  hostname,
  ipAddress,
  role,
  isCompromised,
  privilegeLevel,
}: HostNodeCardProps) {
  return (
    <div
      className={`bg-athena-surface border rounded-athena-md p-3 ${
        isCompromised ? "border-athena-error/60" : "border-athena-border"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-mono font-bold text-athena-text">
          {hostname}
        </span>
        <Badge variant={isCompromised ? "error" : "info"}>
          {isCompromised ? "COMPROMISED" : "SECURE"}
        </Badge>
      </div>
      <div className="space-y-1 text-xs font-mono text-athena-text-secondary">
        <div className="flex justify-between">
          <span>IP</span>
          <span className="text-athena-text">{ipAddress}</span>
        </div>
        <div className="flex justify-between">
          <span>Role</span>
          <span className="text-athena-text">{role}</span>
        </div>
        {privilegeLevel && (
          <div className="flex justify-between">
            <span>Privilege</span>
            <span className="text-athena-accent">{privilegeLevel}</span>
          </div>
        )}
      </div>
    </div>
  );
}
