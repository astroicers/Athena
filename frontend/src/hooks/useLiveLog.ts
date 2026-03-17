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

import { useEffect, useState } from "react";
import type { LogEntry } from "@/types/log";
import type { UseWebSocketReturn } from "./useWebSocket";

const MAX_LOGS = 200;

export function useLiveLog(ws: UseWebSocketReturn): LogEntry[] {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    const unsub = ws.subscribe("log.new", (data) => {
      const entry = data as LogEntry;
      setLogs((prev) => [...prev.slice(-(MAX_LOGS - 1)), entry]);
    });
    return unsub;
  }, [ws]);

  return logs;
}
