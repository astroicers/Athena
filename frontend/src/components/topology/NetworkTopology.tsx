// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import dynamic from "next/dynamic";
import { useCallback, useMemo, useRef } from "react";
import type { TopologyData } from "@/types/api";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), { ssr: false });

const NODE_COLORS: Record<string, string> = {
  compromised: "#ff4444",
  secure: "#00d4ff",
  target: "#ffaa00",
};

interface NetworkTopologyProps {
  data: TopologyData | null;
}

export function NetworkTopology({ data }: NetworkTopologyProps) {
  const fgRef = useRef<unknown>(null);

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
        color: NODE_COLORS[(n.data?.status as string) || "secure"] || NODE_COLORS.secure,
        val: n.type === "Domain Controller" ? 3 : 1,
      })),
      links: data.edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
      })),
    };
  }, [data]);

  const handleNodeLabel = useCallback(
    (node: Record<string, unknown>) =>
      `<div style="background:#1a1a2e;border:1px solid #2a2a4a;padding:4px 8px;border-radius:4px;font-family:monospace;font-size:10px;color:#fff">
        <strong>${node.label || node.id}</strong><br/>
        <span style="color:#a0a0b0">${node.type || ""}</span>
      </div>`,
    [],
  );

  if (!data || data.nodes.length === 0) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-6 flex items-center justify-center h-full min-h-[300px]">
        <span className="text-xs font-mono text-athena-text-secondary">
          No topology data available
        </span>
      </div>
    );
  }

  return (
    <div className="bg-athena-bg rounded-athena-md overflow-hidden border border-athena-border h-full min-h-[300px]">
      <ForceGraph3D
        ref={fgRef as never}
        graphData={graphData}
        nodeLabel={handleNodeLabel as never}
        nodeColor={"color" as never}
        nodeVal={"val" as never}
        nodeOpacity={0.9}
        linkColor={() => "#2a2a4a"}
        linkOpacity={0.6}
        linkDirectionalParticles={2}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleColor={() => "#00d4ff"}
        backgroundColor="#0a0a1a"
        showNavInfo={false}
        width={undefined}
        height={400}
      />
    </div>
  );
}
