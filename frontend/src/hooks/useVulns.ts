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

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Vulnerability, VulnStatus } from "@/types/vulnerability";

interface UseVulnsReturn {
  vulns: Vulnerability[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
  updateStatus: (vulnId: string, newStatus: VulnStatus) => Promise<void>;
}

export function useVulns(operationId: string): UseVulnsReturn {
  const [vulns, setVulns] = useState<Vulnerability[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVulns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<Vulnerability[]>(
        `/operations/${operationId}/vulnerabilities`,
      );
      setVulns(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load vulnerabilities";
      setError(msg);
      setVulns([]);
    } finally {
      setLoading(false);
    }
  }, [operationId]);

  useEffect(() => {
    fetchVulns();
  }, [fetchVulns]);

  const updateStatus = useCallback(
    async (vulnId: string, newStatus: VulnStatus) => {
      await api.put(
        `/operations/${operationId}/vulnerabilities/${vulnId}/status`,
        { status: newStatus },
      );
      setVulns((prev) =>
        prev.map((v) => (v.id === vulnId ? { ...v, status: newStatus } : v)),
      );
    },
    [operationId],
  );

  return { vulns, loading, error, refresh: fetchVulns, updateStatus };
}
