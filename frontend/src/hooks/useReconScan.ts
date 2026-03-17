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

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { UseWebSocketReturn } from "./useWebSocket";

// ---------------------------------------------------------------------------
// ScanState: tracks an in-flight recon scan.
// ---------------------------------------------------------------------------
export interface ScanState {
  targetId: string;
  phase: string | null;
  step: number;
  totalSteps: number;
}

// ---------------------------------------------------------------------------
// Module-level cache so scan state survives component unmount/remount
// (same pattern as useOODA.ts `_cachedPhase`).
// ---------------------------------------------------------------------------
let _cachedScanState: ScanState | null = null;

// ---------------------------------------------------------------------------
// Callbacks the consumer can provide. Stored via useRef internally to avoid
// stale closures (same pattern as useWebSocket.ts).
// ---------------------------------------------------------------------------
export interface ReconCompletedData {
  factsWritten: number;
  servicesFound: number;
  scanId: string;
  targetId: string;
  credentialFound: string | null;
}

export interface UseReconScanCallbacks {
  onCompleted?: (data: ReconCompletedData) => void;
  onFailed?: (error: string) => void;
}

export interface UseReconScanReturn {
  scanState: ScanState | null;
  setScanState: React.Dispatch<React.SetStateAction<ScanState | null>>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useReconScan(
  operationId: string,
  ws: UseWebSocketReturn,
  callbacks?: UseReconScanCallbacks,
): UseReconScanReturn {
  const [scanState, setScanState] = useState<ScanState | null>(_cachedScanState);

  // Keep callback refs fresh to avoid stale closures.
  const onCompletedRef = useRef(callbacks?.onCompleted);
  const onFailedRef = useRef(callbacks?.onFailed);
  useEffect(() => {
    onCompletedRef.current = callbacks?.onCompleted;
    onFailedRef.current = callbacks?.onFailed;
  }, [callbacks?.onCompleted, callbacks?.onFailed]);

  // Helper: update both React state and module-level cache.
  function setCachedScanState(next: ScanState | null) {
    _cachedScanState = next;
    setScanState(next);
  }

  // ---- Hydrate from REST on mount ----------------------------------------
  // If the user navigated away and back while a scan is running, we recover
  // the scan state from the backend so the progress bar reappears.
  useEffect(() => {
    // Only hydrate when we have no cached state (fresh session or after clear).
    if (_cachedScanState) return;

    api
      .get<Record<string, unknown>>(
        `/operations/${operationId}/recon/status`,
      )
      .then((res) => {
        if (res.status === "running" || res.status === "queued") {
          const hydrated: ScanState = {
            targetId: (res.target_id as string) ?? (res.targetId as string) ?? "",
            phase: null,
            step: 0,
            totalSteps: 0,
          };
          setCachedScanState(hydrated);
        }
      })
      .catch(() => {
        // Endpoint may 404 if no scan has been run — that's fine.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [operationId]);

  // ---- WebSocket subscriptions -------------------------------------------
  useEffect(() => {
    const unsubs = [
      // recon.started — a scan was just kicked off (possibly from another tab).
      ws.subscribe("recon.started", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        const next: ScanState = {
          targetId: (data.target_id as string) ?? "",
          phase: null,
          step: 0,
          totalSteps: 0,
        };
        setCachedScanState(next);
      }),

      // recon.progress — update progress; NO prev-guard so it works even if
      // the component was remounted and state was null.
      ws.subscribe("recon.progress", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        setScanState((prev) => {
          const next: ScanState = {
            targetId: (data.target_id as string) ?? prev?.targetId ?? "",
            phase: (data.phase as string) ?? prev?.phase ?? null,
            step: (data.step as number) ?? prev?.step ?? 0,
            totalSteps: (data.total_steps as number) ?? prev?.totalSteps ?? 6,
          };
          _cachedScanState = next;
          return next;
        });
      }),

      // recon.completed — scan finished successfully.
      // WS payload is snake_case (directly from Python ws_manager.broadcast).
      ws.subscribe("recon.completed", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        setCachedScanState(null);
        onCompletedRef.current?.({
          factsWritten: (data.facts_written as number) ?? 0,
          servicesFound: (data.services_found as number) ?? 0,
          scanId: (data.scan_id as string) ?? "",
          targetId: (data.target_id as string) ?? "",
          credentialFound: (data.credential_found as string | null) ?? null,
        });
      }),

      // recon.failed — scan errored out.
      ws.subscribe("recon.failed", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        setCachedScanState(null);
        onFailedRef.current?.((data.error as string) ?? "Unknown error");
      }),

      // operation.reset — clear everything.
      ws.subscribe("operation.reset", () => {
        setCachedScanState(null);
      }),
    ];

    return () => unsubs.forEach((fn) => fn());
  }, [ws]);

  return { scanState, setScanState };
}
