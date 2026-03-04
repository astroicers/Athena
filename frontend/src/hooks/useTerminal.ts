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

import { useCallback, useEffect, useRef, useState } from "react";

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:58000/ws";

export interface TerminalEntry {
  type: "input" | "output" | "error" | "system";
  text: string;
  timestamp: string;
}

interface TerminalMessage {
  output?: string;
  error?: string;
  exit_code?: number;
  prompt?: string;
}

export interface UseTerminalReturn {
  entries: TerminalEntry[];
  prompt: string;
  isConnected: boolean;
  sendCommand: (cmd: string) => void;
  clear: () => void;
}

export function useTerminal(
  operationId: string,
  targetId: string,
  enabled: boolean,
): UseTerminalReturn {
  const [entries, setEntries] = useState<TerminalEntry[]>([]);
  const [prompt, setPrompt] = useState("$ ");
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const addEntry = useCallback((type: TerminalEntry["type"], text: string) => {
    setEntries((prev) => [
      ...prev,
      { type, text, timestamp: new Date().toISOString() },
    ]);
  }, []);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;

    const url = `${WS_BASE}/${operationId}/targets/${targetId}/terminal`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as TerminalMessage;
        if (msg.error) {
          addEntry("error", msg.error);
        } else if (msg.output !== undefined) {
          addEntry("output", msg.output);
          if (msg.prompt) setPrompt(msg.prompt);
        }
      } catch {
        addEntry("error", "Failed to parse server message");
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      addEntry("system", "Connection closed.");
    };

    ws.onerror = () => {
      addEntry("error", "WebSocket error — connection failed.");
      ws.close();
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, operationId, targetId]);

  const sendCommand = useCallback((cmd: string) => {
    if (!cmd.trim()) return;
    addEntry("input", cmd);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ cmd }));
    } else {
      addEntry("error", "Not connected");
    }
  }, [addEntry]);

  const clear = useCallback(() => setEntries([]), []);

  return { entries, prompt, isConnected, sendCommand, clear };
}
