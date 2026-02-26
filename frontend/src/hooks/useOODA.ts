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
