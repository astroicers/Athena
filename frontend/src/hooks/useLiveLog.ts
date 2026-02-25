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
