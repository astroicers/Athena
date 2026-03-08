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

import { useMemo } from "react";
import { useTranslations } from "next-intl";
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

const KILL_CHAIN_ORDER: KillChainStage[] = [
  KillChainStage.RECON,
  KillChainStage.WEAPONIZE,
  KillChainStage.DELIVER,
  KillChainStage.EXPLOIT,
  KillChainStage.INSTALL,
  KillChainStage.C2,
  KillChainStage.ACTION,
];

const NODE_SPACING = 160;
const START_X = 90;
const CENTER_Y = 170;
const HEX_HW = 60; // half-width of hex node for edge offset

export function AttackSituationDiagram({
  techniques,
  oodaPhase,
  executionUpdate,
  c5isrDomains,
}: AttackSituationDiagramProps) {
  const t = useTranslations("Situation");
  const tKC = useTranslations("KillChain");
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
        <span className="text-sm font-mono text-athena-text-secondary uppercase tracking-wider">
          {t("title")}
        </span>
        <span className="text-sm font-mono text-athena-accent">
          {t("progress", { value: Math.round(situation.overallProgress) })}
        </span>
      </div>

      {/* SVG Diagram */}
      <svg
        viewBox="0 0 1200 340"
        preserveAspectRatio="xMidYMid meet"
        className="w-full"
        style={{ minHeight: 220 }}
      >
        <defs>
          {/* Background grid pattern */}
          <pattern id="sit-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="#2a2a4a"
              strokeWidth="0.5"
              opacity="0.25"
            />
          </pattern>

          {/* Scan-line gradient */}
          <linearGradient id="sit-scanline" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00d4ff" stopOpacity="0" />
            <stop offset="50%" stopColor="#00d4ff" stopOpacity="0.04" />
            <stop offset="100%" stopColor="#00d4ff" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* CSS animations inside SVG */}
        <style>{`
          .situation-node-pulse {
            animation: situation-pulse 2s ease-in-out infinite;
          }
          @keyframes situation-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
          }
          .situation-edge-flow {
            animation: situation-flow 1.5s linear infinite;
          }
          @keyframes situation-flow {
            0% { stroke-dashoffset: 0; }
            100% { stroke-dashoffset: -24; }
          }
          .situation-scanline {
            animation: sit-scan 6s linear infinite;
          }
          @keyframes sit-scan {
            0%   { transform: translateY(-340px); }
            100% { transform: translateY(340px); }
          }
        `}</style>

        {/* Background grid */}
        <rect width="1200" height="340" fill="url(#sit-grid)" />

        {/* Animated scan line */}
        <rect
          width="1200"
          height="60"
          fill="url(#sit-scanline)"
          className="situation-scanline"
        />

        {/* Centre guide line (very subtle) */}
        <line
          x1="0" y1={CENTER_Y} x2="1200" y2={CENTER_Y}
          stroke="#2a2a4a" strokeWidth="0.5" opacity="0.2"
          strokeDasharray="6 8"
        />

        {/* Edges */}
        {KILL_CHAIN_ORDER.slice(0, -1).map((stage, i) => {
          const from = nodePositions[i];
          const to = nodePositions[i + 1];
          const nextStage = KILL_CHAIN_ORDER[i + 1];
          return (
            <SituationEdge
              key={`edge-${i}`}
              fromX={from.x + HEX_HW}
              fromY={from.y}
              toX={to.x - HEX_HW}
              toY={to.y}
              status={edgeStatuses[i]}
              fromColor={KILL_CHAIN_COLORS[stage] ?? "#666"}
              toColor={KILL_CHAIN_COLORS[nextStage] ?? "#666"}
              index={i}
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
            label={tKC(stage as any)}
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
