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

import { useState, useRef, useEffect } from "react";
import type { TopologyData } from "@/types/api";
import { KillChainStage } from "@/types/enums";
import { NetworkTopology } from "./NetworkTopology";
import { NodeDetailPanel } from "./NodeDetailPanel";
import { KillChainIndicator } from "@/components/mitre/KillChainIndicator";
import type { KillChainStageCounts } from "@/components/mitre/KillChainIndicator";

interface TopologyViewProps {
  topologyData: TopologyData | null;
  nodeKillChainMap: Record<string, KillChainStage>;
  stageCounts: Record<string, KillChainStageCounts>;
  operationId: string;
}

export function TopologyView({
  topologyData,
  nodeKillChainMap,
  stageCounts,
  operationId,
}: TopologyViewProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const kcRef = useRef<HTMLDivElement>(null);
  const [kcHeight, setKcHeight] = useState(0);

  // Measure Kill Chain bar height so we can subtract it from the graph height
  useEffect(() => {
    if (!kcRef.current) return;
    const ro = new ResizeObserver(() => {
      setKcHeight(kcRef.current?.getBoundingClientRect().height ?? 0);
    });
    ro.observe(kcRef.current);
    setKcHeight(kcRef.current.getBoundingClientRect().height);
    return () => ro.disconnect();
  }, []);

  // Total available height = viewport - page chrome (header 48px + KPI 80px + tabs 40px + spacing 48px)
  const PAGE_CHROME = 216;
  const GAP = 16; // gap-4 between rows
  const graphHeightPx = Math.max(
    300,
    (typeof window !== "undefined" ? window.innerHeight : 800) -
      PAGE_CHROME -
      (kcHeight > 0 ? kcHeight + GAP : 0),
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Main row: graph + detail panel — equal height */}
      <div className="grid grid-cols-4 gap-4" style={{ height: graphHeightPx }}>
        {/* Topology graph — 3/4 width, fills row height */}
        <div className="col-span-3 h-full">
          <NetworkTopology
            data={topologyData}
            nodeKillChainMap={nodeKillChainMap}
            nodeSizeMultiplier={2}
            height={graphHeightPx}
            onNodeClick={setSelectedNodeId}
          />
        </div>

        {/* Node detail panel — 1/4 width, same height as graph */}
        <div className="col-span-1 h-full">
          <NodeDetailPanel
            nodeId={selectedNodeId}
            topologyData={topologyData}
            nodeKillChainMap={nodeKillChainMap}
            operationId={operationId}
          />
        </div>
      </div>

      {/* Kill Chain progress bar — full width, measured height */}
      <div ref={kcRef}>
        <KillChainIndicator stageCounts={stageCounts} />
      </div>
    </div>
  );
}
