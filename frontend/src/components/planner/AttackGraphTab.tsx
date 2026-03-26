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

import { useCallback, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { Button } from "@/components/atoms/Button";
import {
  useAttackGraph,
  type AttackNode,
  type AttackEdge,
  type CredentialNode,
  type CredentialEdge,
} from "@/hooks/useAttackGraph";
import { COLORS } from "@/lib/designTokens";

/* ── Design Tokens ── */

const BG_BASE = COLORS.bgPrimary;
const BG_SURFACE = COLORS.bgSurface;
const BORDER = `${COLORS.textPrimary}10`;
const ACCENT = COLORS.accent;
const TEXT_MUTED = `${COLORS.textPrimary}50`;
const GRID_COLOR = COLORS.bgPrimary;

/* ── Status Color Map ── */

const STATUS_COLORS: Record<
  string,
  { fill: string; glow: string; text: string }
> = {
  explored: { fill: COLORS.success, glow: `${COLORS.success}12`, text: `${COLORS.success}70` },
  pending: { fill: COLORS.warning, glow: `${COLORS.warning}10`, text: `${COLORS.warning}80` },
  failed: { fill: COLORS.error, glow: `${COLORS.error}12`, text: `${COLORS.error}80` },
  unreachable: { fill: COLORS.textTertiary, glow: `${COLORS.textTertiary}0C`, text: `${COLORS.textTertiary}60` },
};

const DEFAULT_STATUS_COLOR = {
  fill: COLORS.textTertiary,
  glow: `${COLORS.textTertiary}0C`,
  text: `${COLORS.textTertiary}60`,
};

/* ── Edge Color Map ── */

const EDGE_COLORS: Record<string, string> = {
  enables: "color-mix(in srgb, var(--color-success) 19%, transparent)",
  lateral: `${COLORS.phaseOrient}30`,
  alternative: `${COLORS.warning}30`,
};

/* ── Credential Node Colors ── */

const CRED_COLORS = [COLORS.success, COLORS.accent, COLORS.warning, COLORS.phaseOrient, COLORS.warning];

/* ── Canvas Dimensions ── */

const CANVAS_W = 1200;
const CANVAS_H = 700;
const NODE_RADIUS_DEFAULT = 25;
const ENTRY_RADIUS = 30;

/* ── Layout: deterministic position from node index ── */

function layoutNodes(
  nodes: AttackNode[],
): Map<string, { x: number; y: number; r: number }> {
  const map = new Map<string, { x: number; y: number; r: number }>();
  if (nodes.length === 0) return map;

  // Place nodes in concentric rings around center
  const cx = CANVAS_W / 2 - 100; // shift left to leave room for side panels
  const cy = CANVAS_H / 2;

  // First node (entry) goes in center
  const entryIdx = nodes.findIndex(
    (n) => n.type === "host" && n.label.toLowerCase().includes("entry"),
  );
  const entryNode = entryIdx >= 0 ? nodes[entryIdx] : null;

  if (entryNode) {
    map.set(entryNode.id, { x: cx, y: cy, r: ENTRY_RADIUS });
  }

  // Remaining nodes in concentric rings
  const remaining = nodes.filter((n) => n.id !== entryNode?.id);
  const ringCapacities = [6, 12, 18, 24]; // nodes per ring
  let placed = 0;
  let ring = 0;

  while (placed < remaining.length) {
    const capacity = ringCapacities[Math.min(ring, ringCapacities.length - 1)];
    const radius = 100 + ring * 90;
    const nodesInRing = Math.min(capacity, remaining.length - placed);

    for (let i = 0; i < nodesInRing; i++) {
      const angle = (2 * Math.PI * i) / nodesInRing - Math.PI / 2;
      const node = remaining[placed + i];
      const nr =
        NODE_RADIUS_DEFAULT - 5 + ((hashCode(node.id) % 15) + 5);
      map.set(node.id, {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
        r: Math.max(20, Math.min(35, nr)),
      });
    }

    placed += nodesInRing;
    ring++;
  }

  return map;
}

/* ── Layout for credential graph ── */

function layoutCredentialGraph(
  credNodes: CredentialNode[],
  credEdges: CredentialEdge[],
): {
  credPositions: Map<string, { x: number; y: number }>;
  hostPositions: Map<string, { x: number; y: number; label: string }>;
} {
  const credPositions = new Map<string, { x: number; y: number }>();
  const hostPositions = new Map<
    string,
    { x: number; y: number; label: string }
  >();

  // Credential nodes on the left, hosts on the right
  const leftX = 200;
  const rightX = CANVAS_W - 350;
  const startY = 80;
  const spacingY = 100;

  // Place credential nodes
  credNodes.forEach((cn, i) => {
    credPositions.set(cn.id, {
      x: leftX,
      y: startY + i * spacingY,
    });
  });

  // Collect unique host IDs from edges
  const hostIds = new Set<string>();
  credEdges.forEach((e) => {
    if (!credPositions.has(e.target)) {
      hostIds.add(e.target);
    }
  });

  // Also add reusedOn hosts
  credNodes.forEach((cn) => {
    cn.reusedOn.forEach((h) => hostIds.add(h));
  });

  const hostArray = Array.from(hostIds);
  const hostSpacing = Math.max(
    70,
    Math.min(spacingY, (CANVAS_H - 100) / Math.max(hostArray.length, 1)),
  );
  hostArray.forEach((hid, i) => {
    hostPositions.set(hid, {
      x: rightX,
      y: startY + i * hostSpacing,
      label: hid,
    });
  });

  return { credPositions, hostPositions };
}

/* ── Simple string hash ── */

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

/* ── Tab type ── */

type Tab = "graph" | "credentials";

/* ── Attack Graph SVG Canvas ── */

function AttackGraphCanvas({
  nodes,
  edges,
}: {
  nodes: AttackNode[];
  edges: AttackEdge[];
}) {
  const positions = useMemo(() => layoutNodes(nodes), [nodes]);

  // Grid lines
  const gridLines = useMemo(() => {
    const lines: { x1: number; y1: number; x2: number; y2: number }[] = [];
    for (let x = 0; x <= CANVAS_W; x += 60) {
      lines.push({ x1: x, y1: 0, x2: x, y2: CANVAS_H });
    }
    for (let y = 0; y <= CANVAS_H; y += 60) {
      lines.push({ x1: 0, y1: y, x2: CANVAS_W, y2: y });
    }
    return lines;
  }, []);

  return (
    <svg
      width="100%"
      height="100%"
      viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ background: BG_BASE }}
    >
      <defs>
        {/* Glow filters for each status */}
        {Object.entries(STATUS_COLORS).map(([key, c]) => (
          <filter key={key} id={`glow-${key}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="8" />
            <feColorMatrix
              type="matrix"
              values={`0 0 0 0 ${parseInt(c.fill.slice(1, 3), 16) / 255} 0 0 0 0 ${parseInt(c.fill.slice(3, 5), 16) / 255} 0 0 0 0 ${parseInt(c.fill.slice(5, 7), 16) / 255} 0 0 0 0.12 0`}
            />
          </filter>
        ))}
      </defs>

      {/* Grid */}
      {gridLines.map((l, i) => (
        <line
          key={i}
          x1={l.x1}
          y1={l.y1}
          x2={l.x2}
          y2={l.y2}
          stroke={GRID_COLOR}
          strokeWidth={0.5}
          opacity={0.4}
        />
      ))}

      {/* Edges */}
      {edges.map((edge) => {
        const src = positions.get(edge.source);
        const tgt = positions.get(edge.target);
        if (!src || !tgt) return null;
        const color = EDGE_COLORS[edge.type] ?? "var(--color-white-8)";
        return (
          <line
            key={edge.id}
            x1={src.x}
            y1={src.y}
            x2={tgt.x}
            y2={tgt.y}
            stroke={color}
            strokeWidth={1.5}
          />
        );
      })}

      {/* Nodes */}
      {nodes.map((node) => {
        const pos = positions.get(node.id);
        if (!pos) return null;
        const colors = STATUS_COLORS[node.status] ?? DEFAULT_STATUS_COLOR;
        const isEntry =
          node.type === "host" &&
          node.label.toLowerCase().includes("entry");

        return (
          <g key={node.id}>
            {/* Glow */}
            <ellipse
              cx={pos.x}
              cy={pos.y}
              rx={pos.r + 12}
              ry={pos.r + 12}
              fill={colors.glow}
              filter={`url(#glow-${node.status})`}
            />
            {/* Node circle */}
            <ellipse
              cx={pos.x}
              cy={pos.y}
              rx={pos.r}
              ry={pos.r}
              fill={colors.fill}
              opacity={0.9}
            />
            {/* Entry marker */}
            {isEntry && (
              <circle
                cx={pos.x}
                cy={pos.y}
                r={5}
                fill={BG_BASE}
              />
            )}
            {/* Label */}
            <text
              x={pos.x}
              y={pos.y + pos.r + 14}
              textAnchor="middle"
              fill="var(--color-text-soft)"
              fontSize={9}
              fontFamily="monospace"
            >
              {node.label}
            </text>
            {/* IP sub-label */}
            {node.ip && (
              <text
                x={pos.x}
                y={pos.y + pos.r + 25}
                textAnchor="middle"
                fill="var(--color-text-muted)"
                fontSize={7}
                fontFamily="monospace"
              >
                {node.ip}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

/* ── Credential Graph SVG Canvas ── */

function CredentialGraphCanvas({
  credNodes,
  credEdges,
}: {
  credNodes: CredentialNode[];
  credEdges: CredentialEdge[];
}) {
  const { credPositions, hostPositions } = useMemo(
    () => layoutCredentialGraph(credNodes, credEdges),
    [credNodes, credEdges],
  );

  // Grid lines
  const gridLines = useMemo(() => {
    const lines: { x1: number; y1: number; x2: number; y2: number }[] = [];
    for (let x = 0; x <= CANVAS_W; x += 60) {
      lines.push({ x1: x, y1: 0, x2: x, y2: CANVAS_H });
    }
    for (let y = 0; y <= CANVAS_H; y += 60) {
      lines.push({ x1: 0, y1: y, x2: CANVAS_W, y2: y });
    }
    return lines;
  }, []);

  return (
    <svg
      width="100%"
      height="100%"
      viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ background: BG_BASE }}
    >
      {/* Grid */}
      {gridLines.map((l, i) => (
        <line
          key={i}
          x1={l.x1}
          y1={l.y1}
          x2={l.x2}
          y2={l.y2}
          stroke={GRID_COLOR}
          strokeWidth={0.5}
          opacity={0.4}
        />
      ))}

      {/* Connecting lines from credentials to hosts */}
      {credEdges.map((edge, idx) => {
        const src = credPositions.get(edge.source);
        const tgt = hostPositions.get(edge.target);
        if (!src || !tgt) return null;
        // Find credential index for color
        const credIdx = credNodes.findIndex((c) => c.id === edge.source);
        const color =
          CRED_COLORS[credIdx >= 0 ? credIdx % CRED_COLORS.length : 0] + "40";
        return (
          <line
            key={`cedge-${idx}`}
            x1={src.x + 70}
            y1={src.y}
            x2={tgt.x - 60}
            y2={tgt.y}
            stroke={color}
            strokeWidth={1.5}
          />
        );
      })}

      {/* Credential nodes */}
      {credNodes.map((cn, i) => {
        const pos = credPositions.get(cn.id);
        if (!pos) return null;
        const color = CRED_COLORS[i % CRED_COLORS.length];

        return (
          <g key={cn.id}>
            {/* Card background */}
            <rect
              x={pos.x - 70}
              y={pos.y - 30}
              width={140}
              height={60}
              rx={6}
              fill="var(--color-white-8)"
              stroke={color}
              strokeWidth={1.5}
            />
            {/* Username */}
            <text
              x={pos.x}
              y={pos.y - 10}
              textAnchor="middle"
              fill="var(--color-text-dim)"
              fontSize={11}
              fontFamily="monospace"
              fontWeight="bold"
            >
              {cn.username}
            </text>
            {/* Credential type */}
            <text
              x={pos.x}
              y={pos.y + 5}
              textAnchor="middle"
              fill={color}
              fontSize={9}
              fontFamily="monospace"
            >
              {cn.credentialType}
            </text>
            {/* Source */}
            <text
              x={pos.x}
              y={pos.y + 18}
              textAnchor="middle"
              fill="var(--color-text-muted)"
              fontSize={8}
              fontFamily="monospace"
            >
              {cn.source}
            </text>
          </g>
        );
      })}

      {/* Host nodes */}
      {Array.from(hostPositions.entries()).map(([hid, pos]) => (
        <g key={hid}>
          <rect
            x={pos.x - 60}
            y={pos.y - 20}
            width={120}
            height={40}
            rx={4}
            fill="var(--color-white-10)"
            stroke="var(--color-white-8)"
            strokeWidth={1}
          />
          <text
            x={pos.x}
            y={pos.y + 4}
            textAnchor="middle"
            fill="var(--color-text-subtle)"
            fontSize={10}
            fontFamily="monospace"
          >
            {pos.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

/* ── Right-Side Stats Panel (Attack Graph) ── */

function GraphStatsPanel({
  totalNodes,
  exploredNodes,
  coverageScore,
  t,
}: {
  totalNodes: number;
  exploredNodes: number;
  coverageScore: number;
  t: (key: string) => string;
}) {
  return (
    <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] px-3.5 py-3 min-w-[160px]">
      <div className="font-mono text-athena-floor uppercase tracking-wider mb-2.5" style={{ color: TEXT_MUTED }}>
        {t("statsTitle")}
      </div>
      <div className="flex flex-col gap-2">
        <StatRow label={t("totalNodes")} value={String(totalNodes)} color="var(--color-text-soft)" />
        <StatRow label={t("exploredNodes")} value={String(exploredNodes)} color="var(--color-success)" />
        <StatRow
          label={t("coverage")}
          value={`${Math.round(coverageScore * 100)}%`}
          color={ACCENT}
        />
        {/* Threat Gauge Bar -- 5 segments */}
        <div className="flex gap-0.5 mt-1.5">
          {[0.2, 0.4, 0.6, 0.8, 1.0].map((threshold, i) => (
            <div
              key={i}
              className="w-6 h-3 rounded-sm transition-colors duration-300"
              style={{
                backgroundColor:
                  coverageScore >= threshold
                    ? i < 2 ? "var(--color-error)" : i < 4 ? "var(--color-warning-alt)" : "var(--color-success)"
                    : "var(--color-white-8)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function StatRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="flex justify-between items-center gap-3">
      <span className="font-mono text-athena-floor" style={{ color: TEXT_MUTED }}>
        {label}
      </span>
      <span className="font-mono text-athena-floor font-semibold" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

/* ── Legend Panel ── */

function LegendPanel({
  items,
  title,
}: {
  items: { color: string; label: string }[];
  title: string;
}) {
  return (
    <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] px-3.5 py-3 min-w-[160px]">
      <div className="font-mono text-athena-floor uppercase tracking-wider mb-2.5" style={{ color: TEXT_MUTED }}>
        {title}
      </div>
      <div className="flex flex-col gap-1.5">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex items-center gap-2"
          >
            <div
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: item.color }}
            />
            <span className="font-mono text-athena-floor text-athena-text-secondary">
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Credential Stats Panel ── */

function CredStatsPanel({
  credNodes,
  t,
}: {
  credNodes: CredentialNode[];
  t: (key: string) => string;
}) {
  const types = useMemo(
    () => new Set(credNodes.map((c) => c.credentialType)).size,
    [credNodes],
  );
  const sources = useMemo(
    () => new Set(credNodes.map((c) => c.source)).size,
    [credNodes],
  );

  return (
    <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] px-3.5 py-3 min-w-[160px]">
      <div className="font-mono text-athena-floor uppercase tracking-wider mb-2.5" style={{ color: TEXT_MUTED }}>
        {t("statsTitle")}
      </div>
      <div className="flex flex-col gap-2">
        <StatRow
          label={t("credCount")}
          value={String(credNodes.length)}
          color="var(--color-text-soft)"
        />
        <StatRow label={t("credTypes")} value={String(types)} color={ACCENT} />
        <StatRow
          label={t("credSources")}
          value={String(sources)}
          color="var(--color-text-dim)"
        />
      </div>
    </div>
  );
}

/* ── Tab Button ── */

function SubTabButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`font-mono text-athena-floor uppercase tracking-wider bg-transparent border-none border-b-2 px-1 cursor-pointer transition-colors duration-150 ${active ? "text-athena-accent border-b-[var(--color-accent)]" : "text-athena-text-tertiary border-b-transparent"}`}
    >
      {label}
    </button>
  );
}

/* ── Main AttackGraphTab Component ── */

export function AttackGraphTab() {
  const t = useTranslations("AttackGraph");
  const operationId = useOperationId();
  const { graph, credentialGraph, loading, error, rebuild } =
    useAttackGraph(operationId);

  const [activeTab, setActiveTab] = useState<Tab>("graph");
  const [rebuilding, setRebuilding] = useState(false);

  const handleRebuild = useCallback(async () => {
    setRebuilding(true);
    try {
      await rebuild();
    } finally {
      setRebuilding(false);
    }
  }, [rebuild]);

  /* ── Legend items ── */

  const graphLegend = useMemo(
    () => [
      { color: STATUS_COLORS.explored.fill, label: t("statusExplored") },
      { color: STATUS_COLORS.pending.fill, label: t("statusPending") },
      { color: STATUS_COLORS.failed.fill, label: t("statusFailed") },
      { color: STATUS_COLORS.unreachable.fill, label: t("statusUnreachable") },
    ],
    [t],
  );

  const credLegend = useMemo(() => {
    if (!credentialGraph) return [];
    return credentialGraph.nodes.map((cn, i) => ({
      color: CRED_COLORS[i % CRED_COLORS.length],
      label: cn.username,
    }));
  }, [credentialGraph]);

  /* ── Loading / Error ── */

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-athena-bg">
        <span className="font-mono text-athena-floor text-athena-text-tertiary">
          Loading...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-athena-bg">
        <span className="font-mono text-athena-floor text-athena-error">
          {error}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-athena-bg overflow-hidden">
      {/* ── Sub-Tab Bar ── */}
      <div className="h-10 flex items-stretch gap-6 px-6 bg-athena-surface shrink-0">
        <SubTabButton
          label={t("tabGraph").toUpperCase()}
          active={activeTab === "graph"}
          onClick={() => setActiveTab("graph")}
        />
        <SubTabButton
          label={t("tabCredentials").toUpperCase()}
          active={activeTab === "credentials"}
          onClick={() => setActiveTab("credentials")}
        />
      </div>

      {/* ── Canvas Area ── */}
      <div className="flex-1 relative overflow-hidden">
        {/* ── Attack Graph Sub-Tab ── */}
        {activeTab === "graph" && (
          <>
            {graph && graph.nodes.length > 0 ? (
              <AttackGraphCanvas nodes={graph.nodes} edges={graph.edges} />
            ) : (
              <div className="flex items-center justify-center h-full bg-athena-bg">
                <span className="font-mono text-athena-floor text-athena-text-tertiary">
                  {t("noData")}
                </span>
              </div>
            )}

            {/* Action buttons */}
            <div className="absolute top-3 left-4 flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleRebuild}
                disabled={rebuilding}
                className="text-athena-floor uppercase tracking-wider text-athena-accent bg-transparent border-[color-mix(in_srgb,var(--color-accent)_31%,transparent)]"
              >
                {rebuilding ? t("rebuilding") : t("rebuild")}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                className="text-athena-floor uppercase tracking-wider text-athena-accent bg-transparent border-[color-mix(in_srgb,var(--color-accent)_31%,transparent)]"
              >
                DEPTH SCAN
              </Button>
            </div>

            {/* Right-side panels */}
            {graph && (
              <div className="absolute top-3 right-3 flex flex-col gap-2.5 z-10">
                <GraphStatsPanel
                  totalNodes={graph.stats.totalNodes}
                  exploredNodes={graph.stats.exploredNodes}
                  coverageScore={graph.stats.coverageScore}
                  t={t}
                />
                <LegendPanel items={graphLegend} title={t("legendTitle")} />
              </div>
            )}
          </>
        )}

        {/* ── Credentials Sub-Tab ── */}
        {activeTab === "credentials" && (
          <>
            {credentialGraph && credentialGraph.nodes.length > 0 ? (
              <CredentialGraphCanvas
                credNodes={credentialGraph.nodes}
                credEdges={credentialGraph.edges}
              />
            ) : (
              <div className="flex items-center justify-center h-full bg-athena-bg">
                <span className="font-mono text-athena-floor text-athena-text-tertiary">
                  {t("noCredentials")}
                </span>
              </div>
            )}

            {/* Right-side panels */}
            {credentialGraph && credentialGraph.nodes.length > 0 && (
              <div className="absolute top-3 right-3 flex flex-col gap-2.5 z-10">
                <CredStatsPanel credNodes={credentialGraph.nodes} t={t} />
                <LegendPanel items={credLegend} title={t("legendTitle")} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
