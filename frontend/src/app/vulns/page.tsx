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

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { PageHeader } from "@/components/layout/PageHeader";
import { SeverityHeatStrip } from "@/components/vulns/SeverityHeatStrip";
import { VulnStatusPipeline } from "@/components/vulns/VulnStatusPipeline";
import { VulnTable } from "@/components/vulns/VulnTable";
import { VulnDetailPanel } from "@/components/vulns/VulnDetailPanel";
import { useVulns } from "@/hooks/useVulns";
import { useOperationId } from "@/contexts/OperationContext";
import type { VulnSeverity, VulnStatus, VulnSummary, Vulnerability } from "@/types/vulnerability";

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
  const operationId = useOperationId();
  const searchParams = useSearchParams();
  const { vulns, loading, error, updateStatus } = useVulns(operationId);
  const [selectedVuln, setSelectedVuln] = useState<Vulnerability | null>(null);

  // Deep link: auto-select vuln from ?id= query param
  useEffect(() => {
    const vulnId = searchParams.get("id");
    if (vulnId && vulns.length > 0 && !selectedVuln) {
      const match = vulns.find((v) => v.id === vulnId || v.cve_id === vulnId);
      if (match) setSelectedVuln(match);
    }
  }, [searchParams, vulns, selectedVuln]);

  const summary = useMemo(() => computeSummary(vulns), [vulns]);

  if (loading) {
    return (
      <div className="space-y-6 p-6 animate-pulse athena-grid-bg min-h-full">
        <div className="h-8 w-64 bg-athena-surface rounded" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-athena-surface rounded-athena-md" />
          ))}
        </div>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-14 bg-athena-surface rounded-athena-sm" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-full athena-grid-bg">
        <PageHeader title={t("title")} operationCode={operationId} />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-3">
            <p className="text-sm font-mono text-athena-error">{error}</p>
            <p className="text-xs font-mono text-athena-text-secondary">
              {t("noRecords")}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full athena-grid-bg">
      <PageHeader title={t("title")} operationCode={t("subtitle", { operationId })} />

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
            vulns={vulns}
            selectedId={selectedVuln?.id ?? null}
            onSelect={setSelectedVuln}
          />
        </div>
      </div>

      {/* Detail panel */}
      <VulnDetailPanel
        vuln={selectedVuln}
        onClose={() => setSelectedVuln(null)}
        onStatusChange={async (vulnId, newStatus) => {
          await updateStatus(vulnId, newStatus);
          if (selectedVuln && selectedVuln.id === vulnId) {
            setSelectedVuln({ ...selectedVuln, status: newStatus });
          }
        }}
      />
    </div>
  );
}
