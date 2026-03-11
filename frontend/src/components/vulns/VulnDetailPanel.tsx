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

import { useTranslations } from "next-intl";
import type { Vulnerability, VulnSeverity, VulnStatus } from "@/types/vulnerability";

const SEVERITY_COLORS: Record<VulnSeverity, string> = {
  critical: "#ff0040",
  high: "#ff4444",
  medium: "#ffaa00",
  low: "#00d4ff",
  info: "#8a8a9a",
};

function cvssColor(score: number): string {
  if (score >= 9.0) return "#ff0040";
  if (score >= 7.0) return "#ffaa00";
  if (score >= 4.0) return "#ffff00";
  return "#00d4ff";
}

interface TimelineEntry {
  label: string;
  time: string | undefined;
}

interface VulnDetailPanelProps {
  vuln: Vulnerability | null;
  onClose: () => void;
  onStatusChange?: (vulnId: string, newStatus: VulnStatus) => void;
}

export function VulnDetailPanel({ vuln, onClose, onStatusChange }: VulnDetailPanelProps) {
  const t = useTranslations("Vulns");

  if (!vuln) return null;

  const timeline: TimelineEntry[] = [
    { label: t("status.discovered"), time: vuln.discovered_at },
    { label: t("status.confirmed"), time: vuln.confirmed_at },
    { label: t("status.exploited"), time: vuln.exploited_at },
    { label: t("status.reported"), time: vuln.reported_at },
  ];

  const sevColor = SEVERITY_COLORS[vuln.severity];

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-athena-surface border-l border-athena-border z-50 flex flex-col animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-athena-border">
        <h3 className="text-sm font-mono font-bold text-athena-text">
          {t("detail.title")}
        </h3>
        <button
          onClick={onClose}
          className="text-xs font-mono text-athena-text-secondary hover:text-athena-accent px-2 py-1 border border-athena-border rounded-athena-sm transition-colors"
        >
          {t("detail.close")}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* CVE ID */}
        <div>
          <span className="text-sm font-mono font-bold text-athena-accent">
            {vuln.cve_id}
          </span>
        </div>

        {/* Title */}
        <h4 className="text-sm font-mono text-athena-text leading-relaxed">
          {vuln.title}
        </h4>

        {/* Severity + CVSS row */}
        <div className="flex items-center gap-3">
          <span
            className="text-xs font-mono font-bold uppercase px-2 py-1 rounded-athena-sm"
            style={{
              color: sevColor,
              backgroundColor: sevColor + "20",
              border: `1px solid ${sevColor}40`,
            }}
          >
            {t(`severity.${vuln.severity}`)}
          </span>
          <span className="text-xs font-mono text-athena-text-secondary">CVSS</span>
          <span
            className="text-sm font-mono font-bold"
            style={{
              color: cvssColor(vuln.cvss_score),
              textShadow:
                vuln.cvss_score >= 9.0
                  ? `0 0 8px ${cvssColor(vuln.cvss_score)}60`
                  : "none",
            }}
          >
            {vuln.cvss_score.toFixed(1)}
          </span>
        </div>

        {/* Target */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-athena-text-secondary">
            {t("columns.target")}:
          </span>
          <span className="text-xs font-mono text-athena-text">
            {vuln.target_ip}
          </span>
        </div>

        {/* Description */}
        <div>
          <h5 className="text-xs font-mono font-bold text-athena-text-secondary uppercase mb-2">
            {t("detail.description")}
          </h5>
          <p className="text-sm font-mono text-athena-text-secondary leading-relaxed">
            {vuln.description}
          </p>
        </div>

        {/* Timeline */}
        <div>
          <h5 className="text-xs font-mono font-bold text-athena-text-secondary uppercase mb-3">
            {t("detail.timeline")}
          </h5>
          <div className="space-y-0">
            {timeline.map((entry, i) => {
              const isActive = !!entry.time;
              const isLast = i === timeline.length - 1;
              return (
                <div key={entry.label} className="flex items-start gap-3">
                  {/* Vertical line + dot */}
                  <div className="flex flex-col items-center">
                    <div
                      className="w-2 h-2 rounded-full mt-1.5"
                      style={{
                        backgroundColor: isActive ? "#00ff88" : "#8a8a9a40",
                        boxShadow: isActive ? "0 0 6px #00ff8860" : "none",
                      }}
                    />
                    {!isLast && (
                      <div
                        className="w-px h-6"
                        style={{
                          backgroundColor: isActive ? "#00ff8840" : "#8a8a9a20",
                        }}
                      />
                    )}
                  </div>
                  {/* Label + time */}
                  <div className="pb-2">
                    <div
                      className="text-xs font-mono font-bold"
                      style={{ color: isActive ? "#e0e0e0" : "#8a8a9a60" }}
                    >
                      {entry.label}
                    </div>
                    {entry.time && (
                      <div className="text-xs font-mono text-athena-text-tertiary">
                        {new Date(entry.time).toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Status Actions */}
        {onStatusChange && vuln.status !== "reported" && (
          <div>
            <h5 className="text-xs font-mono font-bold text-athena-text-secondary uppercase mb-3">
              {t("detail.actions")}
            </h5>
            <div className="flex flex-wrap gap-2">
              {vuln.status === "discovered" && (
                <>
                  <button
                    onClick={() => onStatusChange(vuln.id, "confirmed")}
                    className="text-xs font-mono uppercase px-3 py-1.5 border border-athena-border rounded-athena-sm hover:bg-athena-elevated transition-colors text-athena-accent"
                  >
                    {t("detail.markConfirmed")}
                  </button>
                  <button
                    onClick={() => onStatusChange(vuln.id, "false_positive")}
                    className="text-xs font-mono uppercase px-3 py-1.5 border border-athena-border rounded-athena-sm hover:bg-athena-elevated transition-colors text-athena-text-secondary"
                  >
                    {t("detail.markFalsePositive")}
                  </button>
                </>
              )}
              {vuln.status === "confirmed" && (
                <>
                  <button
                    onClick={() => onStatusChange(vuln.id, "exploited")}
                    className="text-xs font-mono uppercase px-3 py-1.5 border border-athena-border rounded-athena-sm hover:bg-athena-elevated transition-colors text-athena-warning"
                  >
                    {t("detail.markExploited")}
                  </button>
                  <button
                    onClick={() => onStatusChange(vuln.id, "false_positive")}
                    className="text-xs font-mono uppercase px-3 py-1.5 border border-athena-border rounded-athena-sm hover:bg-athena-elevated transition-colors text-athena-text-secondary"
                  >
                    {t("detail.markFalsePositive")}
                  </button>
                </>
              )}
              {vuln.status === "exploited" && (
                <button
                  onClick={() => onStatusChange(vuln.id, "reported")}
                  className="text-xs font-mono uppercase px-3 py-1.5 border border-athena-border rounded-athena-sm hover:bg-athena-elevated transition-colors text-athena-success"
                >
                  {t("detail.markReported")}
                </button>
              )}
              {vuln.status === "false_positive" && (
                <button
                  onClick={() => onStatusChange(vuln.id, "discovered")}
                  className="text-xs font-mono uppercase px-3 py-1.5 border border-athena-border rounded-athena-sm hover:bg-athena-elevated transition-colors text-athena-accent"
                >
                  {t("detail.reopenDiscovered")}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
