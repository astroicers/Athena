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
import { PHASE_COLORS, KILL_CHAIN_COLORS } from "./topologyColors";
import { KillChainStage } from "@/types/enums";

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
  { key: "attackPath", color: "#ff2222", width: 3, dash: null },
];

export function TopologyLegend() {
  const t = useTranslations("Legend");
  const tc = useTranslations("KillChain");
  const [collapsed, setCollapsed] = useState(true);

  if (collapsed) {
    return (
      <div className="absolute top-2 left-2 z-10">
        <button
          onClick={() => setCollapsed(false)}
          className="px-2 py-1 rounded border border-athena-border bg-athena-surface hover:bg-athena-elevated text-sm font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
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
          className="w-full flex items-center gap-1 px-3 py-1.5 text-sm font-mono text-athena-text-secondary hover:text-athena-text transition-colors"
        >
          &#x25BC; {t("title")}
        </button>

        <div className="px-3 pb-3 space-y-3">
          {/* Node Status */}
          <div>
            <div className="text-xs font-mono text-athena-text-secondary tracking-wider mb-1.5 uppercase">
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
                <span className="text-sm font-mono text-athena-text">{t(key)}</span>
              </div>
            ))}
          </div>

          <div className="border-t border-athena-border/30" />

          {/* Connections */}
          <div>
            <div className="text-xs font-mono text-athena-text-secondary tracking-wider mb-1.5 uppercase">
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
                <span className="text-sm font-mono text-athena-text">{t(key)}</span>
              </div>
            ))}
          </div>

          <div className="border-t border-athena-border/30" />

          {/* Status Badges */}
          <div>
            <div className="text-xs font-mono text-athena-text-secondary tracking-wider mb-1.5 uppercase">
              {t("statusBadges")}
            </div>
            {/* Recon — magnifying glass */}
            <div className="flex items-center gap-2 mb-0.5">
              <svg width="14" height="14" viewBox="0 0 14 14" className="shrink-0">
                <circle cx="7" cy="7" r="6" fill="#4488ff40" stroke="#4488ff" strokeWidth="0.8" />
                <circle cx="6" cy="6" r="2.5" fill="none" stroke="#fff" strokeWidth="0.7" />
                <line x1="8" y1="8" x2="10.5" y2="10.5" stroke="#fff" strokeWidth="0.7" strokeLinecap="round" />
              </svg>
              <span className="text-sm font-mono text-athena-text">{t("recon")}</span>
            </div>
            {/* Compromised — skull */}
            <div className="flex items-center gap-2 mb-0.5">
              <svg width="14" height="14" viewBox="0 0 14 14" className="shrink-0">
                <circle cx="7" cy="7" r="6" fill="#ff444440" stroke="#ff4444" strokeWidth="0.8" />
                <path d="M4.5 7 A2.5 2.5 0 0 1 9.5 7" fill="none" stroke="#fff" strokeWidth="0.7" />
                <rect x="5.2" y="6.5" width="1" height="1" fill="#fff" />
                <rect x="7.8" y="6.5" width="1" height="1" fill="#fff" />
                <line x1="5" y1="9" x2="9" y2="9" stroke="#fff" strokeWidth="0.7" />
              </svg>
              <span className="text-sm font-mono text-athena-text">{t("compromised")}</span>
            </div>
            {/* Privilege — shield */}
            <div className="flex items-center gap-2 mb-0.5">
              <svg width="14" height="14" viewBox="0 0 14 14" className="shrink-0">
                <circle cx="7" cy="7" r="6" fill="#eab30840" stroke="#eab308" strokeWidth="0.8" />
                <path d="M7 4 L4.5 5.5 L4.5 7.5 Q7 10.5 7 10.5 Q7 10.5 9.5 7.5 L9.5 5.5 Z" fill="none" stroke="#fff" strokeWidth="0.7" />
              </svg>
              <span className="text-sm font-mono text-athena-text">{t("privilege")}</span>
            </div>
            {/* Persistence — chain link */}
            <div className="flex items-center gap-2 mb-0.5">
              <svg width="14" height="14" viewBox="0 0 14 14" className="shrink-0">
                <circle cx="7" cy="7" r="6" fill="#ffaa0040" stroke="#ffaa00" strokeWidth="0.8" />
                <ellipse cx="6" cy="7" rx="2.2" ry="1.5" fill="none" stroke="#fff" strokeWidth="0.7" />
                <ellipse cx="8" cy="7" rx="2.2" ry="1.5" fill="none" stroke="#fff" strokeWidth="0.7" />
              </svg>
              <span className="text-sm font-mono text-athena-text">{t("persistence")}</span>
            </div>
          </div>

          <div className="border-t border-athena-border/30" />

          {/* Kill Chain Ring */}
          <div>
            <div className="text-xs font-mono text-athena-text-secondary tracking-wider mb-1.5 uppercase">
              {tc("progress")}
            </div>
            {([
              { stage: KillChainStage.RECON, key: "recon" },
              { stage: KillChainStage.WEAPONIZE, key: "weaponize" },
              { stage: KillChainStage.DELIVER, key: "deliver" },
              { stage: KillChainStage.EXPLOIT, key: "exploit" },
              { stage: KillChainStage.INSTALL, key: "install" },
              { stage: KillChainStage.C2, key: "c2" },
              { stage: KillChainStage.ACTION, key: "action" },
            ] as const).map(({ stage, key }) => (
              <div key={key} className="flex items-center gap-2 mb-0.5">
                <svg width="12" height="12" viewBox="0 0 12 12" className="shrink-0">
                  <circle cx="6" cy="6" r="4.5" fill="none" stroke={KILL_CHAIN_COLORS[stage]} strokeWidth="2.5" />
                </svg>
                <span className="text-sm font-mono text-athena-text">{tc(key)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
