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

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

export interface OPSECStatus {
  noiseScore: number;
  detectionRisk: number;
  exposureCount: number;
  noiseBudgetRemaining: number;
  noiseBudgetTotal: number;
}

interface UseOPSECReturn {
  opsec: OPSECStatus | null;
  loading: boolean;
  error: string | null;
}

const POLL_INTERVAL_MS = 30_000;

export function useOPSEC(operationId: string | null): UseOPSECReturn {
  const [opsec, setOpsec] = useState<OPSECStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!operationId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<OPSECStatus>(
        `/operations/${operationId}/opsec-status`,
      );
      setOpsec(data);
    } catch (e) {
      const msg =
        (e as { detail?: string }).detail || "Failed to load OPSEC status";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [operationId]);

  useEffect(() => {
    fetchStatus();

    timerRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchStatus]);

  return { opsec, loading, error };
}
