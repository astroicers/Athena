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

import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useExecutionUpdate } from "@/hooks/useExecutionUpdate";
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

describe("useExecutionUpdate", () => {
  it("returns null initially", () => {
    const ws = createMockWs();
    const { result } = renderHook(() => useExecutionUpdate(ws));
    expect(result.current).toBeNull();
  });

  it("updates state on execution.update event with techniqueId", () => {
    const ws = createMockWs();
    const { result } = renderHook(() => useExecutionUpdate(ws));

    act(() => {
      ws._trigger("execution.update", { techniqueId: "T1595.001", engine: "caldera", status: "running" });
    });

    expect(result.current).toEqual({ techniqueId: "T1595.001", engine: "caldera", status: "running" });
  });

  it("does not update state when techniqueId is missing", () => {
    const ws = createMockWs();
    const { result } = renderHook(() => useExecutionUpdate(ws));

    act(() => {
      ws._trigger("execution.update", { engine: "caldera", status: "running" });
    });

    expect(result.current).toBeNull();
  });

  it("unsubscribes on cleanup", () => {
    const ws = createMockWs();
    const unsubscribeFn = vi.fn();
    const originalSubscribe = ws.subscribe;
    ws.subscribe = (eventType: string, callback: (data: unknown) => void) => {
      originalSubscribe(eventType, callback);
      return unsubscribeFn;
    };

    const { unmount } = renderHook(() => useExecutionUpdate(ws));
    unmount();

    expect(unsubscribeFn).toHaveBeenCalledOnce();
  });
});
