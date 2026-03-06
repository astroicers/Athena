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

import type { TopologyData } from "@/types/api";
import { KillChainStage } from "@/types/enums";
import { FloatingNodeCard } from "./FloatingNodeCard";

interface FloatingCardLayerProps {
  openNodeIds: string[];
  fgRef: React.MutableRefObject<any>;
  graphData: { nodes: Array<Record<string, unknown>>; links: unknown[] };
  topologyData: TopologyData | null;
  nodeKillChainMap: Record<string, KillChainStage>;
  operationId: string;
  containerWidth: number;
  containerHeight: number;
  onCloseNode: (nodeId: string) => void;
  /** Changing this value triggers re-render so cards follow zoom/pan */
  viewTick?: number;
  onReconScan?: (targetId: string) => void;
  onInitialAccess?: (targetId: string) => void;
}

export function FloatingCardLayer({
  openNodeIds,
  fgRef,
  graphData,
  topologyData,
  nodeKillChainMap,
  operationId,
  containerWidth,
  containerHeight,
  onCloseNode,
  viewTick,
  onReconScan,
  onInitialAccess,
}: FloatingCardLayerProps) {
  void viewTick; // Triggers re-render on zoom/pan so graph2ScreenCoords returns fresh values
  if (!topologyData || openNodeIds.length === 0) return null;

  const fg = fgRef.current;
  if (!fg) return null;

  // Compute screen positions from graph coordinates
  // graphData.nodes are the same objects the force-engine mutates in-place with x/y
  const positions: Record<string, { x: number; y: number }> = {};
  for (const id of openNodeIds) {
    const node = graphData.nodes.find((n) => n.id === id);
    if (!node || node.x == null || node.y == null) continue;
    const screen = fg.graph2ScreenCoords(node.x as number, node.y as number);
    positions[id] = { x: screen.x, y: screen.y };
  }

  return (
    <div className="absolute inset-0 z-20 pointer-events-none overflow-hidden">
      {openNodeIds.map((id) => {
        const pos = positions[id];
        if (!pos) return null;
        return (
          <FloatingNodeCard
            key={id}
            nodeId={id}
            screenX={pos.x}
            screenY={pos.y}
            containerWidth={containerWidth}
            containerHeight={containerHeight}
            topologyData={topologyData}
            nodeKillChainMap={nodeKillChainMap}
            operationId={operationId}
            onClose={() => onCloseNode(id)}
            onReconScan={onReconScan}
            onInitialAccess={onInitialAccess}
          />
        );
      })}
    </div>
  );
}
