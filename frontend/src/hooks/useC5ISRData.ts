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

// Backend returns snake_case; frontend type is camelCase. Normalize on ingest.
function normalizeConstraints(raw: unknown): OperationalConstraints | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const warningsRaw = Array.isArray(r.warnings) ? r.warnings : [];
  const hardLimitsRaw = Array.isArray(r.hard_limits)
    ? r.hard_limits
    : Array.isArray(r.hardLimits)
      ? r.hardLimits
      : [];
  return {
    warnings: warningsRaw.map((w) => {
      const o = w as Record<string, unknown>;
      return {
        domain: String(o.domain ?? ""),
        healthPct: Number(o.health_pct ?? o.healthPct ?? 0),
        message: String(o.message ?? ""),
      };
    }),
    hardLimits: hardLimitsRaw.map((h) => {
      const o = h as Record<string, unknown>;
      return {
        domain: String(o.domain ?? ""),
        healthPct: Number(o.health_pct ?? o.healthPct ?? 0),
        rule: String(o.rule ?? ""),
        effect: (o.effect as Record<string, unknown>) ?? {},
        suggestedAction: String(o.suggested_action ?? o.suggestedAction ?? ""),
      };
    }),
    orientMaxOptions: Number(r.orient_max_options ?? r.orientMaxOptions ?? 0),
    minConfidenceOverride:
      (r.min_confidence_override as number | null) ??
      (r.minConfidenceOverride as number | null) ??
      null,
    maxParallelOverride:
      (r.max_parallel_override as number | null) ??
      (r.maxParallelOverride as number | null) ??
      null,
    blockedTargets: Array.isArray(r.blocked_targets)
      ? (r.blocked_targets as string[])
      : Array.isArray(r.blockedTargets)
        ? (r.blockedTargets as string[])
        : [],
    forcedMode:
      (r.forced_mode as string | null) ?? (r.forcedMode as string | null) ?? null,
    noiseBudgetRemaining: Number(
      r.noise_budget_remaining ?? r.noiseBudgetRemaining ?? 0,
    ),
    activeOverrides: Array.isArray(r.active_overrides)
      ? (r.active_overrides as string[])
      : Array.isArray(r.activeOverrides)
        ? (r.activeOverrides as string[])
        : [],
  };
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
        setConstraints(normalizeConstraints(constraintRes.value));
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
      const normalized = normalizeConstraints(data);
      if (normalized) {
        setConstraints(normalized);
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
