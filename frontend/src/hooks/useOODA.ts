"use client";

import { useEffect, useState } from "react";
import type { OODAPhase } from "@/types/enums";
import type { UseWebSocketReturn } from "./useWebSocket";

export function useOODA(ws: UseWebSocketReturn): OODAPhase | null {
  const [phase, setPhase] = useState<OODAPhase | null>(null);

  useEffect(() => {
    const unsub = ws.subscribe("ooda.phase", (data) => {
      const payload = data as { phase?: OODAPhase };
      if (payload.phase) {
        setPhase(payload.phase);
      }
    });
    return unsub;
  }, [ws]);

  return phase;
}
