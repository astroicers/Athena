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

/* ── Backend → Frontend Adapters ── */

interface BackendGraphNode {
  nodeId: string;
  targetId: string;
  techniqueId: string;
  tacticId: string;
  status: string;
  source: string;
}

interface BackendGraphEdge {
  edgeId: string;
  source: string;
  target: string;
  relationship: string;
}

interface BackendGraphResponse {
  nodes: BackendGraphNode[];
  edges: BackendGraphEdge[];
  stats: { totalNodes: number; exploredNodes: number; coverageScore?: number };
  coverageScore: number;
}

function adaptGraphResponse(resp: BackendGraphResponse): AttackGraphData {
  return {
    nodes: (resp.nodes ?? []).map((n) => ({
      id: n.nodeId,
      label: n.targetId || n.techniqueId || n.nodeId,
      type: (n.techniqueId && n.techniqueId !== n.nodeId
        ? "technique"
        : "host") as AttackNode["type"],
      status: (["explored", "pending", "failed"].includes(n.status)
        ? n.status
        : "unreachable") as AttackNode["status"],
      ip: n.targetId || undefined,
      techniqueId: n.techniqueId || undefined,
    })),
    edges: (resp.edges ?? []).map((e) => ({
      id: e.edgeId,
      source: e.source,
      target: e.target,
      type: (e.relationship === "lateral_move"
        ? "lateral"
        : e.relationship === "enables"
          ? "enables"
          : "alternative") as AttackEdge["type"],
    })),
    stats: {
      totalNodes: resp.stats?.totalNodes ?? 0,
      exploredNodes: resp.stats?.exploredNodes ?? 0,
      coverageScore: resp.coverageScore ?? resp.stats?.coverageScore ?? 0,
    },
  };
}

interface BackendCredNode {
  id: string;
  label: string;
  type: string;
  metadata?: { secretType?: string };
}

interface BackendCredEdge {
  source: string;
  target: string;
  relation: string;
}

interface BackendCredResponse {
  nodes: BackendCredNode[];
  edges: BackendCredEdge[];
}

function adaptCredentialResponse(
  resp: BackendCredResponse,
): CredentialGraphData {
  const edgeList = resp.edges ?? [];

  // Build reusedOn map from valid/tested edges
  const reusedOnMap = new Map<string, string[]>();
  for (const e of edgeList) {
    if (e.relation === "valid_on" || e.relation === "tested_on") {
      const arr = reusedOnMap.get(e.source) ?? [];
      arr.push(e.target);
      reusedOnMap.set(e.source, arr);
    }
  }

  const credNodes = (resp.nodes ?? []).filter((n) => n.type === "credential");

  return {
    nodes: credNodes.map((n) => ({
      id: n.id,
      username: (n.label ?? "unknown").split("@")[0] || "unknown",
      credentialType: n.metadata?.secretType ?? "unknown",
      source: "credential",
      reusedOn: reusedOnMap.get(n.id) ?? [],
    })),
    edges: edgeList.map((e, i) => ({
      id: `cred-edge-${i}`,
      source: e.source,
      target: e.target,
    })),
  };
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
      const [rawGraph, rawCred] = await Promise.all([
        api.get<BackendGraphResponse>(
          `/operations/${operationId}/attack-graph`,
        ),
        api.get<BackendCredResponse>(
          `/operations/${operationId}/credential-graph`,
        ),
      ]);
      setGraph(adaptGraphResponse(rawGraph));
      setCredentialGraph(adaptCredentialResponse(rawCred));
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
    // /attack-graph/path endpoint doesn't exist; reuse fetchGraph
    await fetchGraph();
  }, [fetchGraph]);

  return { graph, credentialGraph, loading, error, rebuild, fetchPath };
}
