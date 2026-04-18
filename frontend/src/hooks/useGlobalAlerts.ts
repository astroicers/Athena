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

import { useCallback, useEffect, useState } from "react";
import type { UseWebSocketReturn } from "@/hooks/useWebSocket";

export interface ConstraintAlert {
  active: boolean;
  messages: string[];
  domains: string[];
}

export interface GlobalAlerts {
  constraints: ConstraintAlert;
  opsecAlerts: OpsecAlert[];
}

export interface OpsecAlert {
  id: string;
  message: string;
  severity: "warning" | "error";
  timestamp: string;
}

const MAX_OPSEC_ALERTS = 50;
const EMPTY_CONSTRAINTS: ConstraintAlert = { active: false, messages: [], domains: [] };
let alertCounter = 0;

export function useGlobalAlerts(ws: UseWebSocketReturn | null): GlobalAlerts {
  const [constraints, setConstraints] = useState<ConstraintAlert>(EMPTY_CONSTRAINTS);
  const [opsecAlerts, setOpsecAlerts] = useState<OpsecAlert[]>([]);

  const handleConstraintActive = useCallback((data: unknown) => {
    const d = data as { constraints?: string[]; message?: string; domains?: string[] };
    const messages = d.constraints ?? (d.message ? [d.message] : []);
    const domains = d.domains ?? [];
    setConstraints({ active: true, messages, domains });
  }, []);

  const handleConstraintExpired = useCallback(() => {
    setConstraints(EMPTY_CONSTRAINTS);
  }, []);

  const handleOpsecAlert = useCallback((data: unknown) => {
    const d = data as { message?: string; severity?: string };
    const alert: OpsecAlert = {
      id: `opsec-${++alertCounter}`,
      message: d.message ?? "OPSEC threshold exceeded",
      severity: d.severity === "error" ? "error" : "warning",
      timestamp: new Date().toISOString(),
    };
    setOpsecAlerts((prev) => [...prev.slice(-(MAX_OPSEC_ALERTS - 1)), alert]);
  }, []);

  // Reset stale alerts when WS reference changes (i.e. operation switch)
  useEffect(() => {
    setConstraints(EMPTY_CONSTRAINTS);
    setOpsecAlerts([]);
  }, [ws]);

  useEffect(() => {
    if (!ws) return;

    const unsubs = [
      ws.subscribe("constraint.active", handleConstraintActive),
      ws.subscribe("constraint.override_expired", handleConstraintExpired),
      ws.subscribe("opsec.alert", handleOpsecAlert),
    ];

    return () => {
      unsubs.forEach((unsub) => unsub());
    };
  }, [ws, handleConstraintActive, handleConstraintExpired, handleOpsecAlert]);

  return { constraints, opsecAlerts };
}
