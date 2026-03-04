// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

"use client";

import { useCallback, useEffect, useState } from "react";
import type { OODAPhase } from "@/types/enums";
import type { UseWebSocketReturn } from "./useWebSocket";

// Module-level cache so the phase survives page navigation (component unmount/remount).
let _cachedPhase: OODAPhase | null = null;

export interface UseOODAReturn {
  phase: OODAPhase | null;
  clearPhase: () => void;
}

export function useOODA(ws: UseWebSocketReturn): UseOODAReturn {
  const [phase, setPhase] = useState<OODAPhase | null>(_cachedPhase);

  const clearPhase = useCallback(() => {
    _cachedPhase = null;
    setPhase(null);
  }, []);

  useEffect(() => {
    const unsubs = [
      ws.subscribe("ooda.phase", (data) => {
        const payload = data as { phase?: OODAPhase };
        if (payload.phase) {
          _cachedPhase = payload.phase;
          setPhase(payload.phase);
        }
      }),
      ws.subscribe("ooda.failed", () => {
        _cachedPhase = null;
        setPhase(null);
      }),
      ws.subscribe("operation.reset", () => {
        _cachedPhase = null;
        setPhase(null);
      }),
    ];
    return () => unsubs.forEach((fn) => fn());
  }, [ws]);

  return { phase, clearPhase };
}
