import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOODA } from "@/hooks/useOODA";
import { OODAPhase } from "@/types/enums";
import type { UseWebSocketReturn } from "@/hooks/useWebSocket";

function createMockWs(): UseWebSocketReturn & { _trigger: (event: string, data: unknown) => void } {
  const subscribers = new Map<string, Set<(data: unknown) => void>>();
  return {
    isConnected: true,
    events: [],
    send: vi.fn(),
    subscribe: (eventType: string, callback: (data: unknown) => void) => {
      if (!subscribers.has(eventType)) {
        subscribers.set(eventType, new Set());
      }
      subscribers.get(eventType)!.add(callback);
      return () => { subscribers.get(eventType)?.delete(callback); };
    },
    _trigger: (event: string, data: unknown) => {
      subscribers.get(event)?.forEach((cb) => cb(data));
    },
  };
}

describe("useOODA", () => {
  it("returns null initially", () => {
    const ws = createMockWs();
    const { result } = renderHook(() => useOODA(ws));
    expect(result.current).toBeNull();
  });

  it("updates phase on ooda.phase event", () => {
    const ws = createMockWs();
    const { result } = renderHook(() => useOODA(ws));

    act(() => {
      ws._trigger("ooda.phase", { phase: OODAPhase.ORIENT });
    });

    expect(result.current).toBe(OODAPhase.ORIENT);
  });
});
