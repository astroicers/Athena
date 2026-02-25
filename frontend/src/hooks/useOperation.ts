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
