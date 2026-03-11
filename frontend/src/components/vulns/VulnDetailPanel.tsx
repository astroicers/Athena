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

const STATUS_COLORS: Record<VulnStatus, string> = {
  discovered: "#00d4ff",
  confirmed: "#ffaa00",
  exploited: "#ff0040",
  reported: "#00ff88",
  false_positive: "#8a8a9a",
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

interface StatusAction {
  label: string;
  target: VulnStatus;
  color: string;   // hex accent color
  variant: "filled" | "outlined";
}

function getStatusActions(status: VulnStatus): StatusAction[] {
  switch (status) {
    case "discovered":
      return [
        { label: "markConfirmed", target: "confirmed", color: "#ffaa00", variant: "filled" },
        { label: "markFalsePositive", target: "false_positive", color: "#8a8a9a", variant: "outlined" },
      ];
    case "confirmed":
      return [
        { label: "markExploited", target: "exploited", color: "#ff4444", variant: "filled" },
        { label: "markFalsePositive", target: "false_positive", color: "#8a8a9a", variant: "outlined" },
      ];
    case "exploited":
      return [
        { label: "markReported", target: "reported", color: "#7c3aed", variant: "filled" },
        { label: "markFalsePositive", target: "false_positive", color: "#8a8a9a", variant: "outlined" },
      ];
    case "false_positive":
      return [
        { label: "reopenDiscovered", target: "discovered", color: "#00d4ff", variant: "outlined" },
      ];
    case "reported":
      // Terminal state — no transitions out
      return [];
  }
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
  const statusColor = STATUS_COLORS[vuln.status];
  const statusActions = getStatusActions(vuln.status);

  return (
    <div className="flex flex-col h-full bg-[#111827] border border-[#FFFFFF08] rounded-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#FFFFFF08] shrink-0">
        <h3 className="text-sm font-mono font-bold text-athena-text">
          {t("detail.title")}
        </h3>
        <button
          onClick={onClose}
          className="text-xs font-mono text-athena-text-secondary hover:text-athena-accent px-2 py-1 border border-athena-border rounded-athena-sm transition-colors"
          aria-label={t("detail.close")}
        >
          {t("detail.close")}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* CVE ID */}
        {vuln.cve_id && (
          <div>
            <span className="text-sm font-mono font-bold text-athena-accent">
              {vuln.cve_id}
            </span>
          </div>
        )}

        {/* Title */}
        <h4 className="text-sm font-mono text-athena-text leading-relaxed">
          {vuln.title}
        </h4>

        {/* Severity + CVSS row */}
        <div className="flex items-center gap-3">
          <span
            className="text-xs font-mono font-bold uppercase px-2 py-1 rounded"
            style={{
              color: sevColor,
              backgroundColor: sevColor + "20",
              border: `1px solid ${sevColor}40`,
            }}
          >
            {t(`severity.${vuln.severity}`)}
          </span>
          {vuln.cvss !== null && (
            <>
              <span className="text-xs font-mono text-[#FFFFFF50]">CVSS</span>
              <span
                className="text-sm font-mono font-bold"
                style={{
                  color: cvssColor(vuln.cvss),
                  textShadow:
                    vuln.cvss >= 9.0
                      ? `0 0 8px ${cvssColor(vuln.cvss)}60`
                      : "none",
                }}
              >
                {vuln.cvss.toFixed(1)}
              </span>
            </>
          )}
        </div>

        {/* Metadata rows */}
        <div className="space-y-2">
          {/* Status */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-[#FFFFFF50] w-24 shrink-0">
              {t("columns.status")}
            </span>
            <span
              className="flex items-center gap-1.5 text-xs font-mono font-bold"
              style={{ color: statusColor }}
            >
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ backgroundColor: statusColor, boxShadow: `0 0 6px ${statusColor}80` }}
              />
              {t(`status.${vuln.status}`)}
            </span>
          </div>

          {/* Target */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-[#FFFFFF50] w-24 shrink-0">
              {t("columns.target")}
            </span>
            <span className="text-xs font-mono text-athena-text">
              {vuln.target_ip}
              {vuln.target_hostname && (
                <span className="text-athena-text-secondary ml-1">
                  ({vuln.target_hostname})
                </span>
              )}
            </span>
          </div>

          {/* Service */}
          {vuln.service && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-[#FFFFFF50] w-24 shrink-0">
                {t("detail.service")}
              </span>
              <span className="text-xs font-mono text-athena-text">{vuln.service}</span>
            </div>
          )}

          {/* Discovered at */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-[#FFFFFF50] w-24 shrink-0">
              {t("columns.discovered")}
            </span>
            <span className="text-xs font-mono text-athena-text-secondary">
              {new Date(vuln.discovered_at).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Description */}
        {vuln.description && (
          <div>
            <h5 className="text-xs font-mono font-bold text-[#FFFFFF50] uppercase mb-2">
              {t("detail.description")}
            </h5>
            <p className="text-xs font-mono text-athena-text-secondary leading-relaxed">
              {vuln.description}
            </p>
          </div>
        )}

        {/* Timeline */}
        <div>
          <h5 className="text-xs font-mono font-bold text-[#FFFFFF50] uppercase mb-3">
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
                      className="w-2 h-2 rounded-full mt-1.5 shrink-0"
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
                      <div className="text-xs font-mono text-athena-text-secondary">
                        {new Date(entry.time).toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Status transition actions */}
        {onStatusChange && statusActions.length > 0 && (
          <div>
            <h5 className="text-xs font-mono font-bold text-[#FFFFFF50] uppercase mb-3">
              {t("detail.actions")}
            </h5>
            <div className="flex flex-col gap-2">
              {statusActions.map((action) => {
                const isFilled = action.variant === "filled";
                return (
                  <button
                    key={action.target}
                    onClick={() => onStatusChange(vuln.id, action.target)}
                    className="w-full text-xs font-mono font-bold uppercase px-3 py-2 rounded transition-opacity hover:opacity-80 active:opacity-60"
                    style={
                      isFilled
                        ? {
                            color: action.color,
                            backgroundColor: action.color + "20",
                            border: `1px solid ${action.color}60`,
                          }
                        : {
                            color: action.color,
                            backgroundColor: "transparent",
                            border: `1px solid ${action.color}40`,
                          }
                    }
                  >
                    {t(`detail.${action.label}`)}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
