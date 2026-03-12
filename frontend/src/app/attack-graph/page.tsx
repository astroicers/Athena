"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import {
  useAttackGraph,
  type AttackNode,
  type AttackEdge,
  type CredentialNode,
  type CredentialEdge,
} from "@/hooks/useAttackGraph";

/* ── Design Tokens ── */

const BG_BASE = "#0A0E17";
const BG_SURFACE = "#111827";
const BG_ELEVATED = "#1F2937";
const BORDER = "#1f2937";
const ACCENT = "#3B82F6";
const TEXT_MUTED = "#6B7280";
const GRID_COLOR = "#1f2937";

/* ── Status Color Map ── */

const STATUS_COLORS: Record<
  string,
  { fill: string; glow: string; text: string }
> = {
  explored: { fill: "#22C55E", glow: "#22C55E12", text: "#22C55E70" },
  pending: { fill: "#F59E0B", glow: "#F59E0B10", text: "#F59E0B80" },
  failed: { fill: "#EF4444", glow: "#EF444412", text: "#EF444480" },
  unreachable: { fill: "#6A6A6A", glow: "#6A6A6A0C", text: "#6A6A6A60" },
};

const DEFAULT_STATUS_COLOR = {
  fill: "#6A6A6A",
  glow: "#6A6A6A0C",
  text: "#6A6A6A60",
};

/* ── Edge Color Map ── */

const EDGE_COLORS: Record<string, string> = {
  enables: "#22C55E30",
  lateral: "#A855F730",
  alternative: "#FF880030",
};

/* ── Credential Node Colors ── */

const CRED_COLORS = ["#22C55E", "#3B82F6", "#F97316", "#A855F7", "#EAB308"];

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
        const color = EDGE_COLORS[edge.type] ?? "#FFFFFF15";
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
              fill="#FFFFFFCC"
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
                fill="#FFFFFF55"
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
              fill="#FFFFFF06"
              stroke={color}
              strokeWidth={1.5}
            />
            {/* Username */}
            <text
              x={pos.x}
              y={pos.y - 10}
              textAnchor="middle"
              fill="#FFFFFFDD"
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
              fill="#FFFFFF55"
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
            fill="#FFFFFF08"
            stroke="#FFFFFF15"
            strokeWidth={1}
          />
          <text
            x={pos.x}
            y={pos.y + 4}
            textAnchor="middle"
            fill="#FFFFFFBB"
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
    <div
      style={{
        background: BG_SURFACE,
        border: `1px solid ${BORDER}`,
        borderRadius: 6,
        padding: "12px 14px",
        minWidth: 160,
      }}
    >
      <div
        style={{
          fontFamily: "monospace",
          fontSize: 10,
          color: TEXT_MUTED,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: 10,
        }}
      >
        {t("statsTitle")}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <StatRow label={t("totalNodes")} value={String(totalNodes)} color="#FFFFFFCC" />
        <StatRow label={t("exploredNodes")} value={String(exploredNodes)} color="#22C55E" />
        <StatRow
          label={t("coverage")}
          value={`${Math.round(coverageScore * 100)}%`}
          color={ACCENT}
        />
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
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
      }}
    >
      <span
        style={{
          fontFamily: "monospace",
          fontSize: 10,
          color: TEXT_MUTED,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: "monospace",
          fontSize: 12,
          color,
          fontWeight: 600,
        }}
      >
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
    <div
      style={{
        background: BG_SURFACE,
        border: `1px solid ${BORDER}`,
        borderRadius: 6,
        padding: "12px 14px",
        minWidth: 160,
      }}
    >
      <div
        style={{
          fontFamily: "monospace",
          fontSize: 10,
          color: TEXT_MUTED,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: 10,
        }}
      >
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {items.map((item) => (
          <div
            key={item.label}
            style={{ display: "flex", alignItems: "center", gap: 8 }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: item.color,
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontFamily: "monospace",
                fontSize: 10,
                color: "#FFFFFFAA",
              }}
            >
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
    <div
      style={{
        background: BG_SURFACE,
        border: `1px solid ${BORDER}`,
        borderRadius: 6,
        padding: "12px 14px",
        minWidth: 160,
      }}
    >
      <div
        style={{
          fontFamily: "monospace",
          fontSize: 10,
          color: TEXT_MUTED,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: 10,
        }}
      >
        {t("statsTitle")}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <StatRow
          label={t("credCount")}
          value={String(credNodes.length)}
          color="#FFFFFFCC"
        />
        <StatRow label={t("credTypes")} value={String(types)} color={ACCENT} />
        <StatRow
          label={t("credSources")}
          value={String(sources)}
          color="#A855F7"
        />
      </div>
    </div>
  );
}

/* ── Main Content ── */

function AttackGraphContent() {
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
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          background: BG_BASE,
        }}
      >
        <span
          style={{ fontFamily: "monospace", fontSize: 12, color: TEXT_MUTED }}
        >
          Loading...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          background: BG_BASE,
        }}
      >
        <span
          style={{ fontFamily: "monospace", fontSize: 12, color: "#EF4444" }}
        >
          {error}
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: BG_BASE,
        overflow: "hidden",
      }}
    >
      {/* ── Tab Bar ── */}
      <div
        style={{
          height: 40,
          display: "flex",
          alignItems: "stretch",
          gap: 24,
          padding: "0 24px",
          background: BG_SURFACE,
          flexShrink: 0,
        }}
      >
        <TabButton
          label={t("tabGraph").toUpperCase()}
          active={activeTab === "graph"}
          onClick={() => setActiveTab("graph")}
        />
        <TabButton
          label={t("tabCredentials").toUpperCase()}
          active={activeTab === "credentials"}
          onClick={() => setActiveTab("credentials")}
        />
      </div>

      {/* ── Canvas Area ── */}
      <div
        style={{
          flex: 1,
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* ── Attack Graph Tab ── */}
        {activeTab === "graph" && (
          <>
            {graph && graph.nodes.length > 0 ? (
              <AttackGraphCanvas nodes={graph.nodes} edges={graph.edges} />
            ) : (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  background: BG_BASE,
                }}
              >
                <span
                  style={{
                    fontFamily: "monospace",
                    fontSize: 12,
                    color: TEXT_MUTED,
                  }}
                >
                  {t("noData")}
                </span>
              </div>
            )}

            {/* Rebuild button */}
            <div
              style={{
                position: "absolute",
                top: 12,
                left: 16,
              }}
            >
              <button
                onClick={handleRebuild}
                disabled={rebuilding}
                style={{
                  fontFamily: "monospace",
                  fontSize: 10,
                  color: ACCENT,
                  background: "transparent",
                  border: `1px solid ${ACCENT}50`,
                  borderRadius: 4,
                  padding: "6px 14px",
                  cursor: rebuilding ? "not-allowed" : "pointer",
                  opacity: rebuilding ? 0.6 : 1,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                {rebuilding ? t("rebuilding") : t("rebuild")}
              </button>
            </div>

            {/* Right-side panels */}
            {graph && (
              <div
                style={{
                  position: "absolute",
                  top: 12,
                  right: 12,
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  zIndex: 10,
                }}
              >
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

        {/* ── Credentials Tab ── */}
        {activeTab === "credentials" && (
          <>
            {credentialGraph && credentialGraph.nodes.length > 0 ? (
              <CredentialGraphCanvas
                credNodes={credentialGraph.nodes}
                credEdges={credentialGraph.edges}
              />
            ) : (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  background: BG_BASE,
                }}
              >
                <span
                  style={{
                    fontFamily: "monospace",
                    fontSize: 12,
                    color: TEXT_MUTED,
                  }}
                >
                  {t("noCredentials")}
                </span>
              </div>
            )}

            {/* Right-side panels */}
            {credentialGraph && credentialGraph.nodes.length > 0 && (
              <div
                style={{
                  position: "absolute",
                  top: 12,
                  right: 12,
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  zIndex: 10,
                }}
              >
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

/* ── Tab Button ── */

function TabButton({
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
      style={{
        fontFamily: "monospace",
        fontSize: 10,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        color: active ? ACCENT : TEXT_MUTED,
        background: "transparent",
        border: "none",
        borderBottom: active ? `2px solid ${ACCENT}` : "2px solid transparent",
        padding: "0 4px",
        cursor: "pointer",
        transition: "color 150ms, border-color 150ms",
      }}
    >
      {label}
    </button>
  );
}

/* ── Page Wrapper with Suspense ── */

export default function AttackGraphPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
          }}
        >
          <p style={{ fontFamily: "monospace", fontSize: 13, color: TEXT_MUTED }}>
            Loading Attack Graph...
          </p>
        </div>
      }
    >
      <AttackGraphContent />
    </Suspense>
  );
}
