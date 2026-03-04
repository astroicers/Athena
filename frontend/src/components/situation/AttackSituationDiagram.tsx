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

import { useMemo } from "react";
import { KillChainStage } from "@/types/enums";
import type { OODAPhase } from "@/types/enums";
import type { TechniqueWithStatus } from "@/types/technique";
import { useSituationData } from "@/hooks/useSituationData";
import { SituationNode } from "./SituationNode";
import { SituationEdge } from "./SituationEdge";
import { OODARing } from "./OODARing";
import { C5ISRMiniBar } from "./C5ISRMiniBar";

interface AttackSituationDiagramProps {
  techniques: TechniqueWithStatus[];
  oodaPhase: OODAPhase | null;
  executionUpdate: { techniqueId?: string } | null;
  c5isrDomains: Array<{ domain: string; healthPct: number }>;
}

const KILL_CHAIN_COLORS: Record<string, string> = {
  recon: "#4488ff",
  weaponize: "#8855ff",
  deliver: "#aa44ff",
  exploit: "#ff8800",
  install: "#ffaa00",
  c2: "#ff4444",
  action: "#ff0040",
};

const STAGE_LABELS: Record<string, string> = {
  recon: "RECON",
  weaponize: "WEAPON",
  deliver: "DELIVER",
  exploit: "EXPLOIT",
  install: "INSTALL",
  c2: "C2",
  action: "ACTION",
};

const KILL_CHAIN_ORDER: KillChainStage[] = [
  KillChainStage.RECON,
  KillChainStage.WEAPONIZE,
  KillChainStage.DELIVER,
  KillChainStage.EXPLOIT,
  KillChainStage.INSTALL,
  KillChainStage.C2,
  KillChainStage.ACTION,
];

const NODE_SPACING = 155;
const START_X = 80;
const CENTER_Y = 150;
const NODE_WIDTH = 140;

export function AttackSituationDiagram({
  techniques,
  oodaPhase,
  executionUpdate,
  c5isrDomains,
}: AttackSituationDiagramProps) {
  const situation = useSituationData(
    techniques,
    oodaPhase,
    executionUpdate,
    c5isrDomains,
  );

  // Compute node positions
  const nodePositions = useMemo(
    () =>
      KILL_CHAIN_ORDER.map((_, i) => ({
        x: START_X + i * NODE_SPACING,
        y: CENTER_Y,
      })),
    [],
  );

  // Determine edge statuses
  const edgeStatuses = useMemo(() => {
    return KILL_CHAIN_ORDER.slice(0, -1).map((_, i) => {
      const fromStage = situation.stages[i];
      const toStage = situation.stages[i + 1];
      if (
        fromStage.status === "completed" &&
        (toStage.status === "completed" || toStage.status === "partial")
      ) {
        return "completed" as const;
      }
      if (
        (fromStage.status === "completed" || fromStage.status === "partial") &&
        (toStage.status === "active" || toStage.runningCount > 0)
      ) {
        return "active" as const;
      }
      if (fromStage.successCount > 0 && toStage.status !== "inactive") {
        return "active" as const;
      }
      return "pending" as const;
    });
  }, [situation.stages]);

  // Current stage position for OODA ring
  const currentPos =
    situation.currentStageIndex >= 0
      ? nodePositions[situation.currentStageIndex]
      : null;

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-athena-border">
        <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
          Attack Situation Diagram
        </span>
        <span className="text-[10px] font-mono text-athena-accent">
          Progress: {Math.round(situation.overallProgress)}%
        </span>
      </div>

      {/* SVG Diagram */}
      <svg
        viewBox="0 0 1200 300"
        preserveAspectRatio="xMidYMid meet"
        className="w-full"
        style={{ minHeight: 200 }}
      >
        <defs>
          {/* Arrow marker */}
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#00d4ff" opacity="0.7" />
          </marker>

          {/* Glow filter for active stage */}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* CSS animations inside SVG */}
        <style>{`
          .situation-node-pulse {
            animation: situation-pulse 2s ease-in-out infinite;
          }
          @keyframes situation-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
          }
          .situation-edge-flow {
            animation: situation-flow 1.5s linear infinite;
          }
          @keyframes situation-flow {
            0% { stroke-dashoffset: 0; }
            100% { stroke-dashoffset: -24; }
          }
        `}</style>

        {/* Edges */}
        {KILL_CHAIN_ORDER.slice(0, -1).map((_, i) => {
          const from = nodePositions[i];
          const to = nodePositions[i + 1];
          return (
            <SituationEdge
              key={`edge-${i}`}
              fromX={from.x + NODE_WIDTH / 2}
              fromY={from.y}
              toX={to.x - NODE_WIDTH / 2}
              toY={to.y}
              status={edgeStatuses[i]}
            />
          );
        })}

        {/* Nodes */}
        {KILL_CHAIN_ORDER.map((stage, i) => (
          <SituationNode
            key={stage}
            stage={situation.stages[i]}
            x={nodePositions[i].x}
            y={nodePositions[i].y}
            isCurrentStage={i === situation.currentStageIndex}
            color={KILL_CHAIN_COLORS[stage] ?? "#666"}
            label={STAGE_LABELS[stage] ?? stage.toUpperCase()}
          />
        ))}

        {/* OODA Ring at current stage */}
        {currentPos && (
          <OODARing
            cx={currentPos.x}
            cy={currentPos.y}
            phase={situation.oodaPhase}
          />
        )}
      </svg>

      {/* C5ISR Health Bar */}
      <div className="border-t border-athena-border">
        <C5ISRMiniBar health={situation.c5isrHealth} />
      </div>
    </div>
  );
}
