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
import type { OODATimelineEntry } from "@/types/ooda";

const PHASE_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  observe: "info",
  orient: "warning",
  decide: "success",
  act: "error",
};

interface OODATimelineProps {
  entries: OODATimelineEntry[];
}

export function OODATimeline({ entries }: OODATimelineProps) {
  if (entries.length === 0) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-6 text-center">
        <span className="text-xs font-mono text-athena-text-secondary">No OODA iterations yet</span>
      </div>
    );
  }

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4">
      <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-3">
        OODA Timeline
      </h3>
      <div className="space-y-3">
        {entries.map((entry, i) => {
          const time = entry.timestamp.split("T")[1]?.slice(0, 8) || entry.timestamp;
          return (
            <div key={i} className="flex items-start gap-3">
              <div className="flex flex-col items-center">
                <div className="w-2 h-2 rounded-full bg-athena-accent shrink-0 mt-1" />
                {i < entries.length - 1 && (
                  <div className="w-px flex-1 bg-athena-border mt-1" />
                )}
              </div>
              <div className="flex-1 min-w-0 pb-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono text-athena-text-secondary">{time}</span>
                  <Badge variant={PHASE_VARIANT[entry.phase] || "info"}>
                    {entry.phase.toUpperCase()}
                  </Badge>
                  <span className="text-[10px] font-mono text-athena-text-secondary">
                    Iteration #{entry.iterationNumber}
                  </span>
                </div>
                <p className="text-xs font-mono text-athena-text">{entry.summary}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
