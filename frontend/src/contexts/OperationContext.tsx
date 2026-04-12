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

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";

const STORAGE_KEY = "athena-op-id";
// Empty string = no operation selected yet. Consumers guard against
// empty operationId before making API calls.
const DEFAULT_OP_ID = "";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:58000/api";

interface OperationContextType {
  operationId: string;
  setOperationId: (id: string) => void;
}

const OperationContext = createContext<OperationContextType | null>(null);

export function OperationProvider({ children }: { children: ReactNode }) {
  const [operationId, setOperationIdRaw] = useState(DEFAULT_OP_ID);

  // Hydrate from localStorage after mount (avoids SSR mismatch).
  // If localStorage is empty or stale, auto-select the first active
  // operation from the backend so the War Room always has a valid
  // operation context (C5 regression fix).
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && stored.length > 0) {
      setOperationIdRaw(stored);
      return;
    }
    // No stored operation — fetch the first one from the API
    fetch(`${API_BASE}/operations`)
      .then((r) => (r.ok ? r.json() : []))
      .then((ops: Array<{ id: string; status?: string }>) => {
        const active = ops.find((o) => o.status === "active") ?? ops[0];
        if (active?.id) {
          setOperationIdRaw(active.id);
          localStorage.setItem(STORAGE_KEY, active.id);
        }
      })
      .catch(() => {
        // API not available — stay with empty operationId
      });
  }, []);

  const setOperationId = useCallback((id: string) => {
    setOperationIdRaw(id);
    localStorage.setItem(STORAGE_KEY, id);
  }, []);

  return (
    <OperationContext.Provider value={{ operationId, setOperationId }}>
      {children}
    </OperationContext.Provider>
  );
}

export function useOperationId(): string {
  const ctx = useContext(OperationContext);
  if (!ctx) throw new Error("useOperationId must be used inside OperationProvider");
  return ctx.operationId;
}

export function useOperationContext(): OperationContextType {
  const ctx = useContext(OperationContext);
  if (!ctx) throw new Error("useOperationContext must be used inside OperationProvider");
  return ctx;
}
