// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

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
    expect(result.current.phase).toBeNull();
  });

  it("updates phase on ooda.phase event", () => {
    const ws = createMockWs();
    const { result } = renderHook(() => useOODA(ws));

    act(() => {
      ws._trigger("ooda.phase", { phase: OODAPhase.ORIENT });
    });

    expect(result.current.phase).toBe(OODAPhase.ORIENT);
  });

  it("clears phase on ooda.failed event", () => {
    const ws = createMockWs();
    const { result } = renderHook(() => useOODA(ws));

    act(() => {
      ws._trigger("ooda.phase", { phase: OODAPhase.OBSERVE });
    });
    expect(result.current.phase).toBe(OODAPhase.OBSERVE);

    act(() => {
      ws._trigger("ooda.failed", {});
    });
    expect(result.current.phase).toBeNull();
  });

  it("clears phase on operation.reset event", () => {
    const ws = createMockWs();
    const { result } = renderHook(() => useOODA(ws));

    act(() => {
      ws._trigger("ooda.phase", { phase: OODAPhase.ACT });
    });
    expect(result.current.phase).toBe(OODAPhase.ACT);

    act(() => {
      ws._trigger("operation.reset", {});
    });
    expect(result.current.phase).toBeNull();
  });

  it("clears phase via clearPhase()", () => {
    const ws = createMockWs();
    const { result } = renderHook(() => useOODA(ws));

    act(() => {
      ws._trigger("ooda.phase", { phase: OODAPhase.DECIDE });
    });
    expect(result.current.phase).toBe(OODAPhase.DECIDE);

    act(() => {
      result.current.clearPhase();
    });
    expect(result.current.phase).toBeNull();
  });
});
