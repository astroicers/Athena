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
import type { Operation } from "@/types/operation";
import { api } from "@/lib/api";

interface UseOperationReturn {
  operation: Operation | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useOperation(operationId: string | null): UseOperationReturn {
  const [operation, setOperation] = useState<Operation | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOperation = useCallback(async () => {
    if (!operationId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<Operation>(`/operations/${operationId}`);
      setOperation(data);
    } catch (e) {
      const msg = (e as { detail?: string }).detail || "Failed to load operation";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [operationId]);

  useEffect(() => {
    fetchOperation();
  }, [fetchOperation]);

  return { operation, isLoading, error, refresh: fetchOperation };
}
