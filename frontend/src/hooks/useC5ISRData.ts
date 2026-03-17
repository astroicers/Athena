// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { C5ISRStatus, DomainReport } from "@/types/c5isr";
import type { OperationalConstraints } from "@/types/constraint";
import type { UseWebSocketReturn } from "@/hooks/useWebSocket";

const POLL_MS = 15_000;

interface UseC5ISRDataReturn {
  domains: C5ISRStatus[];
  constraints: OperationalConstraints | null;
  override: (domain: string) => Promise<void>;
  fetchReport: (domain: string) => Promise<DomainReport | null>;
}

export function useC5ISRData(
  operationId: string | null,
  ws?: UseWebSocketReturn | null,
): UseC5ISRDataReturn {
  const [domains, setDomains] = useState<C5ISRStatus[]>([]);
  const [constraints, setConstraints] =
    useState<OperationalConstraints | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    if (!operationId) return;
    try {
      const [c5isrRes, constraintRes] = await Promise.allSettled([
        api.get<C5ISRStatus[]>(`/operations/${operationId}/c5isr`),
        api.get<OperationalConstraints>(
          `/operations/${operationId}/constraints`,
        ),
      ]);

      if (c5isrRes.status === "fulfilled" && c5isrRes.value) {
        setDomains(
          Array.isArray(c5isrRes.value) ? c5isrRes.value : [],
        );
      }
      if (constraintRes.status === "fulfilled" && constraintRes.value) {
        setConstraints(constraintRes.value);
      }
    } catch {
      // silent
    }
  }, [operationId]);

  // Initial fetch + polling
  useEffect(() => {
    fetchData();
    timerRef.current = setInterval(fetchData, POLL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchData]);

  // WebSocket: real-time C5ISR updates
  useEffect(() => {
    if (!ws) return;

    const unsub1 = ws.subscribe("c5isr.update", (data) => {
      const payload = data as { domains?: C5ISRStatus[] };
      if (payload?.domains && Array.isArray(payload.domains)) {
        setDomains(payload.domains);
      }
    });

    const unsub2 = ws.subscribe("constraint.active", (data) => {
      const payload = data as OperationalConstraints;
      if (payload) {
        setConstraints(payload);
      }
    });

    return () => {
      unsub1();
      unsub2();
    };
  }, [ws]);

  const fetchReport = useCallback(
    async (domain: string): Promise<DomainReport | null> => {
      if (!operationId) return null;
      try {
        return await api.get<DomainReport>(
          `/operations/${operationId}/c5isr/${domain}/report`,
        );
      } catch {
        return null;
      }
    },
    [operationId],
  );

  const override = useCallback(
    async (domain: string) => {
      if (!operationId) return;
      await api.post(`/operations/${operationId}/constraints/override`, {
        domain,
      });
      // Immediate refresh after override
      fetchData();
    },
    [operationId, fetchData],
  );

  return { domains, constraints, override, fetchReport };
}
