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

import { createContext, useCallback, useContext, useState, ReactNode } from "react";

const STORAGE_KEY = "athena-op-id";
const DEFAULT_OP_ID = "op-0001";

function getPersistedOpId(): string {
  if (typeof window === "undefined") return DEFAULT_OP_ID;
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_OP_ID;
}

interface OperationContextType {
  operationId: string;
  setOperationId: (id: string) => void;
}

const OperationContext = createContext<OperationContextType | null>(null);

export function OperationProvider({ children }: { children: ReactNode }) {
  const [operationId, setOperationIdRaw] = useState(getPersistedOpId);

  const setOperationId = useCallback((id: string) => {
    setOperationIdRaw(id);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, id);
    }
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
