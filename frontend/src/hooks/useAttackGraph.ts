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

/* ── Attack Graph Types ── */

export interface AttackNode {
  id: string;
  label: string;
  type: "host" | "technique" | "credential";
  status: "explored" | "pending" | "failed" | "unreachable";
  ip?: string;
  techniqueId?: string;
}

export interface AttackEdge {
  id: string;
  source: string;
  target: string;
  type: "enables" | "alternative" | "lateral";
}

export interface AttackGraphData {
  nodes: AttackNode[];
  edges: AttackEdge[];
  stats: {
    totalNodes: number;
    exploredNodes: number;
    coverageScore: number;
  };
}

/* ── Credential Graph Types ── */

export interface CredentialNode {
  id: string;
  username: string;
  credentialType: string;
  source: string;
  reusedOn: string[];
}

export interface CredentialEdge {
  id: string;
  source: string;
  target: string;
}

export interface CredentialGraphData {
  nodes: CredentialNode[];
  edges: CredentialEdge[];
}

/* ── Hook Return ── */

interface UseAttackGraphReturn {
  graph: AttackGraphData | null;
  credentialGraph: CredentialGraphData | null;
  loading: boolean;
  error: string | null;
  rebuild: () => Promise<void>;
  fetchPath: () => Promise<void>;
}

export function useAttackGraph(operationId: string): UseAttackGraphReturn {
  const [graph, setGraph] = useState<AttackGraphData | null>(null);
  const [credentialGraph, setCredentialGraph] =
    useState<CredentialGraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [graphData, credData] = await Promise.all([
        api.get<AttackGraphData>(
          `/operations/${operationId}/attack-graph`,
        ),
        api.get<CredentialGraphData>(
          `/operations/${operationId}/credential-graph`,
        ),
      ]);
      setGraph(graphData);
      setCredentialGraph(credData);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to load attack graph";
      setError(msg);
      setGraph(null);
      setCredentialGraph(null);
    } finally {
      setLoading(false);
    }
  }, [operationId]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const rebuild = useCallback(async () => {
    setError(null);
    try {
      await api.post(
        `/operations/${operationId}/attack-graph/rebuild`,
      );
      await fetchGraph();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to rebuild graph";
      setError(msg);
    }
  }, [operationId, fetchGraph]);

  const fetchPath = useCallback(async () => {
    setError(null);
    try {
      const data = await api.get<AttackGraphData>(
        `/operations/${operationId}/attack-graph/path`,
      );
      setGraph(data);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to fetch path";
      setError(msg);
    }
  }, [operationId]);

  return { graph, credentialGraph, loading, error, rebuild, fetchPath };
}
