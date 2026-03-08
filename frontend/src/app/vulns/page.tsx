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
import { PageHeader } from "@/components/layout/PageHeader";
import { SeverityHeatStrip } from "@/components/vulns/SeverityHeatStrip";
import { VulnStatusPipeline } from "@/components/vulns/VulnStatusPipeline";
import { VulnTable } from "@/components/vulns/VulnTable";
import { VulnDetailPanel } from "@/components/vulns/VulnDetailPanel";
import type { Vulnerability, VulnSeverity, VulnStatus, VulnSummary } from "@/types/vulnerability";

const MOCK_VULNS: Vulnerability[] = [
  {
    id: "v-001",
    cve_id: "CVE-2024-21351",
    target_id: "t-001",
    target_ip: "10.0.1.5",
    severity: "critical",
    status: "exploited",
    cvss_score: 9.8,
    title: "Windows SmartScreen Security Feature Bypass",
    description:
      "Windows SmartScreen Security Feature Bypass Vulnerability allowing remote code execution.",
    discovered_at: "2026-03-08T10:00:00Z",
    confirmed_at: "2026-03-08T11:30:00Z",
    exploited_at: "2026-03-08T14:32:07Z",
  },
  {
    id: "v-002",
    cve_id: "CVE-2024-1709",
    target_id: "t-002",
    target_ip: "10.0.1.10",
    severity: "critical",
    status: "confirmed",
    cvss_score: 10.0,
    title: "ConnectWise ScreenConnect Authentication Bypass",
    description:
      "Authentication bypass using an alternate path or channel in ConnectWise ScreenConnect.",
    discovered_at: "2026-03-08T09:15:00Z",
    confirmed_at: "2026-03-08T12:00:00Z",
  },
  {
    id: "v-003",
    cve_id: "CVE-2024-3400",
    target_id: "t-003",
    target_ip: "10.0.1.1",
    severity: "high",
    status: "discovered",
    cvss_score: 8.1,
    title: "PAN-OS: OS Command Injection in GlobalProtect Gateway",
    description:
      "A command injection as a result of arbitrary file creation vulnerability in the GlobalProtect feature.",
    discovered_at: "2026-03-08T08:45:00Z",
  },
  {
    id: "v-004",
    cve_id: "CVE-2023-44487",
    target_id: "t-001",
    target_ip: "10.0.1.5",
    severity: "high",
    status: "reported",
    cvss_score: 7.5,
    title: "HTTP/2 Rapid Reset Attack",
    description:
      "HTTP/2 protocol allows a denial of service via rapid stream resets.",
    discovered_at: "2026-03-07T16:00:00Z",
    confirmed_at: "2026-03-07T18:00:00Z",
    exploited_at: "2026-03-08T09:00:00Z",
    reported_at: "2026-03-08T15:00:00Z",
  },
  {
    id: "v-005",
    cve_id: "CVE-2024-0012",
    target_id: "t-003",
    target_ip: "10.0.1.1",
    severity: "medium",
    status: "false_positive",
    cvss_score: 5.3,
    title: "PAN-OS Management Interface Information Disclosure",
    description:
      "Information disclosure vulnerability in PAN-OS management interface.",
    discovered_at: "2026-03-08T11:00:00Z",
  },
];

function computeSummary(vulns: Vulnerability[]): VulnSummary {
  const bySeverity: Record<VulnSeverity, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  };
  const byStatus: Record<VulnStatus, number> = {
    discovered: 0,
    confirmed: 0,
    exploited: 0,
    reported: 0,
    false_positive: 0,
  };
  for (const v of vulns) {
    bySeverity[v.severity]++;
    byStatus[v.status]++;
  }
  return { total: vulns.length, by_severity: bySeverity, by_status: byStatus };
}

export default function VulnsPage() {
  const t = useTranslations("Vulns");
  const [selectedVuln, setSelectedVuln] = useState<Vulnerability | null>(null);

  const summary = useMemo(() => computeSummary(MOCK_VULNS), []);

  return (
    <div className="flex flex-col h-full athena-grid-bg">
      <PageHeader title={t("title")} operationCode={t("subtitle", { operationId: "ALPHA-7" })} />

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Total count */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-athena-text-secondary uppercase">
            {t("total")}
          </span>
          <span className="text-sm font-mono font-bold text-athena-text">
            {summary.total}
          </span>
        </div>

        {/* Severity heat strip */}
        <SeverityHeatStrip bySeverity={summary.by_severity} total={summary.total} />

        {/* Status pipeline */}
        <div className="bg-athena-surface border border-athena-border rounded-athena-sm p-3">
          <VulnStatusPipeline byStatus={summary.by_status} />
        </div>

        {/* Vulnerability table */}
        <div className="bg-athena-surface border border-athena-border rounded-athena-sm">
          <VulnTable
            vulns={MOCK_VULNS}
            selectedId={selectedVuln?.id ?? null}
            onSelect={setSelectedVuln}
          />
        </div>
      </div>

      {/* Detail panel */}
      <VulnDetailPanel vuln={selectedVuln} onClose={() => setSelectedVuln(null)} />
    </div>
  );
}
