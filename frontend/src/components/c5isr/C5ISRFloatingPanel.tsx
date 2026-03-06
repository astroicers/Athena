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
import { ThreatLevelGauge } from "@/components/topology/ThreatLevelGauge";
import { C5ISRStatusBoard } from "./C5ISRStatusBoard";
import type { C5ISRStatus } from "@/types/c5isr";

interface C5ISRFloatingPanelProps {
  c5isrDomains: C5ISRStatus[];
  threatLevel: number;
}

const DOMAIN_ABBR: Record<string, string> = {
  command: "CMD",
  control: "CTRL",
  communications: "COMMS",
  computers: "COMP",
  cyber: "CYBER",
  isr: "ISR",
};

export function C5ISRFloatingPanel({ c5isrDomains, threatLevel }: C5ISRFloatingPanelProps) {
  const t = useTranslations("C5ISR");
  const [modalOpen, setModalOpen] = useState(false);

  if (c5isrDomains.length === 0) return null;

  return (
    <>
      {/* Compact floating panel — bottom-left */}
      <button
        onClick={() => setModalOpen(true)}
        className="absolute bottom-12 left-2 z-10 flex items-center gap-2 px-3 py-1.5 bg-athena-surface/90 backdrop-blur-sm border border-athena-border rounded-athena-sm hover:bg-athena-surface transition-colors cursor-pointer"
      >
        <span className="text-[10px] font-mono text-athena-warning font-bold">
          ⚠ {threatLevel.toFixed(1)}
        </span>
        <div className="flex items-center gap-1">
          {c5isrDomains.map((d) => {
            const abbr = DOMAIN_ABBR[d.domain.toLowerCase()] || d.domain.slice(0, 4).toUpperCase();
            const color =
              d.healthPct >= 80 ? "text-athena-success" :
              d.healthPct >= 50 ? "text-athena-warning" :
              "text-athena-error";
            return (
              <span key={d.domain} className={`text-[9px] font-mono ${color}`} title={`${d.domain}: ${d.healthPct}%`}>
                {abbr}
              </span>
            );
          })}
        </div>
      </button>

      {/* Full modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-athena-surface border border-athena-border rounded-athena-md shadow-2xl w-[600px] max-h-[80vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-athena-border">
              <span className="text-sm font-mono font-bold text-athena-text">
                {t("title")} — {t("domainStatus")}
              </span>
              <button
                onClick={() => setModalOpen(false)}
                className="text-athena-text-secondary hover:text-athena-text transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              <ThreatLevelGauge level={threatLevel} />
              <C5ISRStatusBoard domains={c5isrDomains} />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
