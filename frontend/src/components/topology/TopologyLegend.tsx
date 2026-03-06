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

import { useState } from "react";
import { useTranslations } from "next-intl";
import { PHASE_COLORS } from "./topologyColors";

const NODE_ENTRIES: { key: string; color: string; isHex: boolean }[] = [
  { key: "session", color: PHASE_COLORS.session, isHex: false },
  { key: "attacking", color: PHASE_COLORS.attacking, isHex: false },
  { key: "scanning", color: PHASE_COLORS.scanning, isHex: false },
  { key: "idle", color: PHASE_COLORS.idle, isHex: false },
  { key: "c2Server", color: PHASE_COLORS.c2, isHex: true },
];

const EDGE_ENTRIES: { key: string; color: string; width: number; dash: string | null }[] = [
  { key: "session", color: "rgba(255,68,68,0.7)", width: 2.5, dash: null },
  { key: "attacking", color: "rgba(255,136,0,0.7)", width: 2, dash: "4 4" },
  { key: "scanning", color: "rgba(68,136,255,0.7)", width: 2, dash: "4 4" },
  { key: "lateral", color: "rgba(255,170,0,0.7)", width: 2, dash: "6 3" },
  { key: "idle", color: "rgba(0,255,136,0.3)", width: 0.8, dash: null },
];

export function TopologyLegend() {
  const t = useTranslations("Legend");
  const [collapsed, setCollapsed] = useState(true);

  if (collapsed) {
    return (
      <div className="absolute top-2 left-2 z-10">
        <button
          onClick={() => setCollapsed(false)}
          className="px-2 py-1 rounded border border-athena-border bg-athena-surface hover:bg-athena-elevated text-[10px] font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
        >
          &#x25B6; {t("title")}
        </button>
      </div>
    );
  }

  return (
    <div className="absolute top-2 left-2 z-10">
      <div className="bg-athena-surface border border-athena-border rounded-athena-sm shadow-lg max-h-[50vh] overflow-y-auto">
        <button
          onClick={() => setCollapsed(true)}
          className="w-full flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
        >
          &#x25BC; {t("title")}
        </button>

        <div className="px-3 pb-3 space-y-3">
          {/* Node Status */}
          <div>
            <div className="text-[9px] font-mono text-athena-text-secondary tracking-wider mb-1.5 uppercase">
              {t("nodeStatus")}
            </div>
            {NODE_ENTRIES.map(({ key, color, isHex }) => (
              <div key={key} className="flex items-center gap-2 mb-0.5">
                {isHex ? (
                  <svg width="10" height="10" viewBox="0 0 10 10" className="shrink-0">
                    <polygon points="5,0 10,2.5 10,7.5 5,10 0,7.5 0,2.5" fill={color} />
                  </svg>
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
                )}
                <span className="text-[10px] font-mono text-athena-text">{t(key)}</span>
              </div>
            ))}
          </div>

          <div className="border-t border-athena-border/30" />

          {/* Connections */}
          <div>
            <div className="text-[9px] font-mono text-athena-text-secondary tracking-wider mb-1.5 uppercase">
              {t("connections")}
            </div>
            {EDGE_ENTRIES.map(({ key, color, width, dash }) => (
              <div key={key} className="flex items-center gap-2 mb-0.5">
                <svg width="20" height="6" className="shrink-0">
                  <line
                    x1="0" y1="3" x2="20" y2="3"
                    stroke={color}
                    strokeWidth={width}
                    strokeDasharray={dash || undefined}
                  />
                </svg>
                <span className="text-[10px] font-mono text-athena-text">{t(key)}</span>
              </div>
            ))}
          </div>

          <div className="border-t border-athena-border/30" />

          {/* Status Badges */}
          <div>
            <div className="text-[9px] font-mono text-athena-text-secondary tracking-wider mb-1.5 uppercase">
              {t("statusBadges")}
            </div>
            {[
              { key: "recon", color: "#4488ff", slot: "↖" },
              { key: "compromised", color: "#ff4444", slot: "↗" },
              { key: "privilege", color: "#eab308", slot: "↙" },
              { key: "persistence", color: "#ffaa00", slot: "↘" },
            ].map(({ key, color, slot }) => (
              <div key={key} className="flex items-center gap-2 mb-0.5">
                <span
                  className="w-3 h-3 rounded-full shrink-0 flex items-center justify-center text-[7px] font-mono text-white border"
                  style={{ background: color + "40", borderColor: color }}
                >
                  {slot}
                </span>
                <span className="text-[10px] font-mono text-athena-text">{t(key)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
