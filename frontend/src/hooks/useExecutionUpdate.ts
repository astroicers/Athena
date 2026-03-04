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

import { useEffect, useState } from "react";
import type { UseWebSocketReturn } from "./useWebSocket";

export interface ExecutionUpdate {
  techniqueId: string;
  engine: string | null;
  status: string | null;
}

export function useExecutionUpdate(ws: UseWebSocketReturn): ExecutionUpdate | null {
  const [update, setUpdate] = useState<ExecutionUpdate | null>(null);

  useEffect(() => {
    const unsub = ws.subscribe("execution.update", (data) => {
      const payload = data as { techniqueId?: string; engine?: string | null; status?: string | null };
      if (payload.techniqueId) {
        setUpdate({
          techniqueId: payload.techniqueId,
          engine: payload.engine ?? null,
          status: payload.status ?? null,
        });
      }
    });
    return unsub;
  }, [ws]);

  return update;
}
