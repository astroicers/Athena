import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useLiveLog } from "@/hooks/useLiveLog";
import type { UseWebSocketReturn } from "@/hooks/useWebSocket";

describe("useLiveLog", () => {
  it("returns empty array initially", () => {
    const ws: UseWebSocketReturn = {
      isConnected: true,
      events: [],
      send: vi.fn(),
      subscribe: vi.fn().mockReturnValue(() => {}),
    };
    const { result } = renderHook(() => useLiveLog(ws));
    expect(result.current).toEqual([]);
  });
});
