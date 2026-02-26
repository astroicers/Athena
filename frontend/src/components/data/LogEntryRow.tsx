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

import { LogSeverity } from "@/types/enums";
import type { LogEntry } from "@/types/log";

const SEVERITY_STYLES: Record<string, string> = {
  [LogSeverity.INFO]: "border-l-athena-accent text-athena-accent",
  [LogSeverity.SUCCESS]: "border-l-athena-success text-athena-success",
  [LogSeverity.WARNING]: "border-l-athena-warning text-athena-warning",
  [LogSeverity.ERROR]: "border-l-athena-error text-athena-error",
  [LogSeverity.CRITICAL]: "border-l-athena-critical text-athena-critical animate-pulse",
};

interface LogEntryRowProps {
  entry: LogEntry;
}

export function LogEntryRow({ entry }: LogEntryRowProps) {
  const style = SEVERITY_STYLES[entry.severity] || SEVERITY_STYLES[LogSeverity.INFO];
  const time = entry.timestamp.split("T")[1]?.slice(0, 8) || entry.timestamp;

  return (
    <div className={`flex items-start gap-2 px-3 py-1.5 border-l-2 text-xs font-mono ${style}`}>
      <span className="text-athena-text-secondary shrink-0 w-16">{time}</span>
      <span className="shrink-0 w-20 uppercase text-[10px]">
        [{entry.severity}]
      </span>
      <span className="text-athena-text-secondary shrink-0 w-16 truncate">
        {entry.source}
      </span>
      <span className="text-athena-text flex-1">{entry.message}</span>
    </div>
  );
}
