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
