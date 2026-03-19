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

import { useTranslations } from "next-intl";
import { LogSeverity } from "@/types/enums";
import type { LogEntry } from "@/types/log";

const SEVERITY_STYLES: Record<string, string> = {
  [LogSeverity.INFO]: "border-l-athena-accent text-athena-accent",
  [LogSeverity.SUCCESS]: "border-l-[#22C55E] text-athena-success",
  [LogSeverity.WARNING]: "border-l-athena-warning text-athena-warning",
  [LogSeverity.ERROR]: "border-l-[#EF4444] text-athena-error",
  [LogSeverity.CRITICAL]: "border-l-[#DC2626] text-[#DC2626] animate-pulse",
};

interface LogEntryRowProps {
  entry: LogEntry;
}

export function LogEntryRow({ entry }: LogEntryRowProps) {
  const tSev = useTranslations("LogSeverity");
  const style = SEVERITY_STYLES[entry.severity] || SEVERITY_STYLES[LogSeverity.INFO];
  const time = entry.timestamp.split("T")[1]?.slice(0, 8) || entry.timestamp;

  return (
    <div className={`flex items-center gap-1.5 px-2 py-0.5 border-l-2 text-xs font-mono ${style}`}>
      <span className="text-athena-text-tertiary shrink-0 w-[4.5rem]">{time}</span>
      <span className="shrink-0 text-sm">
        [{tSev(entry.severity as any)}]
      </span>
      <span className="text-athena-text-light flex-1 truncate">{entry.message}</span>
    </div>
  );
}
