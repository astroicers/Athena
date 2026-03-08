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

import { useState, useMemo } from "react";
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

type SortField = "cve_id" | "target_ip" | "severity" | "cvss_score" | "status" | "discovered_at";
type SortDir = "asc" | "desc";

const SEVERITY_RANK: Record<VulnSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

interface VulnTableProps {
  vulns: Vulnerability[];
  selectedId: string | null;
  onSelect: (vuln: Vulnerability) => void;
}

export function VulnTable({ vulns, selectedId, onSelect }: VulnTableProps) {
  const t = useTranslations("Vulns");
  const [sortField, setSortField] = useState<SortField>("cvss_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const sorted = useMemo(() => {
    const arr = [...vulns];
    arr.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "cve_id":
          cmp = a.cve_id.localeCompare(b.cve_id);
          break;
        case "target_ip":
          cmp = a.target_ip.localeCompare(b.target_ip);
          break;
        case "severity":
          cmp = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
          break;
        case "cvss_score":
          cmp = a.cvss_score - b.cvss_score;
          break;
        case "status":
          cmp = a.status.localeCompare(b.status);
          break;
        case "discovered_at":
          cmp = a.discovered_at.localeCompare(b.discovered_at);
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [vulns, sortField, sortDir]);

  const columns: { key: SortField; label: string }[] = [
    { key: "cve_id", label: t("columns.cveId") },
    { key: "target_ip", label: t("columns.target") },
    { key: "severity", label: t("columns.severity") },
    { key: "cvss_score", label: t("columns.cvss") },
    { key: "status", label: t("columns.status") },
    { key: "discovered_at", label: t("columns.discovered") },
  ];

  const sortIndicator = (key: SortField) => {
    if (sortField !== key) return "";
    return sortDir === "asc" ? " \u25B2" : " \u25BC";
  };

  if (vulns.length === 0) {
    return (
      <div className="text-center py-12 text-athena-text-secondary font-mono text-sm">
        {t("noVulns")}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="border-b border-athena-border">
            {columns.map((col) => (
              <th
                key={col.key}
                className="text-left px-3 py-2 text-xs text-athena-text-secondary font-bold uppercase cursor-pointer hover:text-athena-accent select-none"
                onClick={() => handleSort(col.key)}
              >
                {col.label}
                {sortIndicator(col.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((vuln) => {
            const isCritical = vuln.severity === "critical";
            const isSelected = vuln.id === selectedId;
            return (
              <tr
                key={vuln.id}
                className={`border-b border-athena-border/30 cursor-pointer transition-colors hover:bg-athena-elevated/50 ${
                  isSelected ? "bg-athena-elevated" : ""
                }`}
                style={isCritical ? { borderLeft: "2px solid #ff0040" } : undefined}
                onClick={() => onSelect(vuln)}
              >
                <td className="px-3 py-2 text-athena-accent">{vuln.cve_id}</td>
                <td className="px-3 py-2 text-athena-text-secondary">{vuln.target_ip}</td>
                <td className="px-3 py-2">
                  <span
                    className="text-xs font-bold uppercase px-2 py-0.5 rounded"
                    style={{
                      color: SEVERITY_COLORS[vuln.severity],
                      backgroundColor: SEVERITY_COLORS[vuln.severity] + "20",
                    }}
                  >
                    {t(`severity.${vuln.severity}`)}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <span
                    className="font-bold"
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
                </td>
                <td className="px-3 py-2">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="inline-block w-2 h-2 rounded-full"
                      style={{ backgroundColor: STATUS_COLORS[vuln.status] }}
                    />
                    <span style={{ color: STATUS_COLORS[vuln.status] }} className="text-xs">
                      {t(`status.${vuln.status}`)}
                    </span>
                  </span>
                </td>
                <td className="px-3 py-2 text-athena-text-tertiary text-xs">
                  {new Date(vuln.discovered_at).toLocaleTimeString()}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
