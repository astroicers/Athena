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

import { DomainCard } from "./DomainCard";
import type { C5ISRStatus } from "@/types/c5isr";

interface C5ISRStatusBoardProps {
  domains: C5ISRStatus[];
}

export function C5ISRStatusBoard({ domains }: C5ISRStatusBoardProps) {
  if (domains.length === 0) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-6 text-center">
        <span className="text-xs font-mono text-athena-text-secondary">
          No C5ISR domain data available
        </span>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-3">
        C5ISR Domain Status
      </h2>
      <div className="grid grid-cols-3 gap-3">
        {domains.map((d) => (
          <DomainCard key={d.id} domain={d} />
        ))}
      </div>
    </div>
  );
}
