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

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { PageHeader } from "@/components/layout/PageHeader";
import { SeverityHeatStrip } from "@/components/vulns/SeverityHeatStrip";
import { VulnStatusPipeline } from "@/components/vulns/VulnStatusPipeline";
import { VulnTable } from "@/components/vulns/VulnTable";
import { VulnDetailPanel } from "@/components/vulns/VulnDetailPanel";
import { useVulns } from "@/hooks/useVulns";
import { useOperationId } from "@/contexts/OperationContext";
import { api } from "@/lib/api";
import type { VulnSeverity, VulnStatus, VulnSummary, Vulnerability } from "@/types/vulnerability";

interface VulnSummaryResponse {
  total: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
}

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

function toVulnSummary(resp: VulnSummaryResponse): VulnSummary {
  const bySeverity: Record<VulnSeverity, number> = {
    critical: resp.by_severity["critical"] ?? 0,
    high: resp.by_severity["high"] ?? 0,
    medium: resp.by_severity["medium"] ?? 0,
    low: resp.by_severity["low"] ?? 0,
    info: resp.by_severity["info"] ?? 0,
  };
  const byStatus: Record<VulnStatus, number> = {
    discovered: resp.by_status["discovered"] ?? 0,
    confirmed: resp.by_status["confirmed"] ?? 0,
    exploited: resp.by_status["exploited"] ?? 0,
    reported: resp.by_status["reported"] ?? 0,
    false_positive: resp.by_status["false_positive"] ?? 0,
  };
  return { total: resp.total, by_severity: bySeverity, by_status: byStatus };
}

export default function VulnsPage() {
  const t = useTranslations("Vulns");
  const operationId = useOperationId();
  const searchParams = useSearchParams();
  const { vulns, loading, error, updateStatus } = useVulns(operationId);
  const [selectedVuln, setSelectedVuln] = useState<Vulnerability | null>(null);
  const [serverSummary, setServerSummary] = useState<VulnSummary | null>(null);

  // Fetch server-computed summary; fall back to client-side compute on failure
  const fetchSummary = useCallback(async () => {
    try {
      const resp = await api.get<VulnSummaryResponse>(
        `/operations/${operationId}/vulnerabilities/summary`,
      );
      setServerSummary(toVulnSummary(resp));
    } catch {
      // Silently fall back to client-side summary
      setServerSummary(null);
    }
  }, [operationId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  // Deep link: auto-select vuln from ?id= query param
  useEffect(() => {
    const vulnId = searchParams.get("id");
    if (vulnId && vulns.length > 0 && !selectedVuln) {
      const match = vulns.find((v) => v.id === vulnId || v.cve_id === vulnId);
      if (match) setSelectedVuln(match);
    }
  }, [searchParams, vulns, selectedVuln]);

  const clientSummary = useMemo(() => computeSummary(vulns), [vulns]);
  const summary = serverSummary ?? clientSummary;

  const handleStatusChange = useCallback(
    async (vulnId: string, newStatus: VulnStatus) => {
      await updateStatus(vulnId, newStatus);
      if (selectedVuln && selectedVuln.id === vulnId) {
        setSelectedVuln({ ...selectedVuln, status: newStatus });
      }
      // Refresh server summary after a status change
      fetchSummary();
    },
    [updateStatus, selectedVuln, fetchSummary],
  );

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
              {t("noVulns")}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full athena-grid-bg">
      <PageHeader
        title={t("title")}
        operationCode={`${t("total")}: ${summary.total}`}
      />

      <div className="flex-1 overflow-hidden flex flex-col p-4 gap-4 min-h-0">
        {/* Severity heat strip */}
        <SeverityHeatStrip bySeverity={summary.by_severity} total={summary.total} />

        {/* Status pipeline */}
        <div className="bg-athena-surface border border-athena-border rounded-athena-sm p-3 shrink-0">
          <VulnStatusPipeline byStatus={summary.by_status} />
        </div>

        {/* Table + detail panel side-by-side */}
        <div className="flex flex-1 gap-4 min-h-0 overflow-hidden">
          {/* Vulnerability table */}
          <div className="flex-1 bg-athena-surface border border-athena-border rounded-athena-sm overflow-y-auto min-w-0">
            <VulnTable
              vulns={vulns}
              selectedId={selectedVuln?.id ?? null}
              onSelect={setSelectedVuln}
            />
          </div>

          {/* Inline detail panel — only rendered when a vuln is selected */}
          {selectedVuln && (
            <div className="w-[380px] shrink-0 overflow-y-auto">
              <VulnDetailPanel
                vuln={selectedVuln}
                onClose={() => setSelectedVuln(null)}
                onStatusChange={handleStatusChange}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
