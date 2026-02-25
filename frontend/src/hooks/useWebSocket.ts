"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WebSocketEvent } from "@/types/api";

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
const MAX_RECONNECT_DELAY = 30_000;

type EventCallback = (data: unknown) => void;

export interface UseWebSocketReturn {
  isConnected: boolean;
  events: WebSocketEvent[];
  send: (data: unknown) => void;
  subscribe: (eventType: string, callback: EventCallback) => () => void;
}

export function useWebSocket(operationId: string | null): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const subscribersRef = useRef<Map<string, Set<EventCallback>>>(new Map());
  const reconnectDelayRef = useRef(1000);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (typeof window === "undefined" || !operationId) return;

    const ws = new WebSocket(`${WS_BASE}/${operationId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectDelayRef.current = 1000;
    };

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as WebSocketEvent;
        setEvents((prev) => [...prev.slice(-499), event]);

        const subs = subscribersRef.current.get(event.event);
        if (subs) {
          subs.forEach((cb) => cb(event.data));
        }
      } catch {
        console.warn("[WS] Failed to parse message:", e.data);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;

      const delay = reconnectDelayRef.current;
      reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY);
      reconnectTimerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [operationId]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const subscribe = useCallback(
    (eventType: string, callback: EventCallback): (() => void) => {
      if (!subscribersRef.current.has(eventType)) {
        subscribersRef.current.set(eventType, new Set());
      }
      subscribersRef.current.get(eventType)!.add(callback);

      return () => {
        subscribersRef.current.get(eventType)?.delete(callback);
      };
    },
    [],
  );

  return { isConnected, events, send, subscribe };
}
