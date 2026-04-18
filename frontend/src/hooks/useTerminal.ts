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

import { useCallback, useEffect, useRef, useState } from "react";

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:58000/ws";

const MAX_RECONNECT_DELAY = 16000;

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
  pending: boolean;
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
  const [pending, setPending] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(1000);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const intentionalCloseRef = useRef(false);

  const addEntry = useCallback((type: TerminalEntry["type"], text: string) => {
    setEntries((prev) => [
      ...prev,
      { type, text, timestamp: new Date().toISOString() },
    ]);
  }, []);

  const connect = useCallback(() => {
    if (!enabled || typeof window === "undefined") return;

    const url = `${WS_BASE}/${operationId}/targets/${targetId}/terminal`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectDelayRef.current = 1000;
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as TerminalMessage;
        if (msg.error) {
          addEntry("error", msg.error);
          setPending(false);
        } else if (msg.output !== undefined) {
          addEntry("output", msg.output);
          if (msg.prompt) setPrompt(msg.prompt);
          setPending(false);
        }
      } catch (parseErr) {
        console.warn("[Terminal] Failed to parse server message:", parseErr);
        addEntry("error", "Failed to parse server message");
        setPending(false);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;

      if (!intentionalCloseRef.current) {
        addEntry("system", "Connection lost. Reconnecting...");
        const delay = reconnectDelayRef.current;
        reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY);
        reconnectTimerRef.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [enabled, operationId, targetId, addEntry]);

  useEffect(() => {
    intentionalCloseRef.current = false;
    connect();
    return () => {
      intentionalCloseRef.current = true;
      clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const sendCommand = useCallback((cmd: string) => {
    if (!cmd.trim()) return;
    addEntry("input", cmd);
    setPending(true);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ cmd }));
    } else {
      addEntry("error", "Not connected");
      setPending(false);
    }
  }, [addEntry]);

  const clear = useCallback(() => setEntries([]), []);

  return { entries, prompt, isConnected, pending, sendCommand, clear };
}
