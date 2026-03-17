"use client";

import React, {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { useVulns } from "@/hooks/useVulns";
import { api } from "@/lib/api";
import type {
  Vulnerability,
  VulnSeverity,
  VulnStatus,
  VulnSummary,
} from "@/types/vulnerability";
import PocEvidencePanel from "@/components/vulns/PocEvidencePanel";

/* ── Constants ── */

const SEVERITY_ORDER: VulnSeverity[] = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
];

const SEVERITY_COLORS: Record<VulnSeverity, string> = {
  critical: "#EF4444",
  high: "#F97316",
  medium: "#EAB308",
  low: "#22C55E",
  info: "#6B7280",
};

const STATUS_COLORS: Record<VulnStatus, string> = {
  discovered: "#3B82F6",
  confirmed: "#22C55E",
  exploited: "#F97316",
  reported: "#A855F7",
  false_positive: "#6B7280",
};

const STATUS_LIST: VulnStatus[] = [
  "discovered",
  "confirmed",
  "exploited",
  "reported",
  "false_positive",
];

/* ── Severity Heat Strip ── */

function SeverityHeatStrip({
  bySeverity,
  total,
}: {
  bySeverity: Record<VulnSeverity, number>;
  total: number;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span
        className="font-mono uppercase tracking-[1.5px]"
        style={{ fontSize: 8, fontWeight: 700, color: "#FFFFFF40" }}
      >
        SEVERITY DISTRIBUTION
      </span>
      <div className="flex gap-0.5" style={{ height: 24 }}>
        {SEVERITY_ORDER.map((sev) => {
          const count = bySeverity[sev] ?? 0;
          if (count === 0) return null;
          const widthPct = total > 0 ? (count / total) * 100 : 0;
          return (
            <div
              key={sev}
              className="flex items-center justify-center rounded-athena-sm transition-all duration-300"
              style={{
                width: `${widthPct}%`,
                minWidth: count > 0 ? 24 : 0,
                backgroundColor: SEVERITY_COLORS[sev],
              }}
            >
              {widthPct > 6 && (
                <span
                  className="font-mono athena-tabular-nums"
                  style={{
                    fontSize: 8,
                    fontWeight: 700,
                    color: sev === "medium" || sev === "low" ? "#000" : "#FFF",
                  }}
                >
                  {sev.toUpperCase().slice(0, 4)} {count}
                </span>
              )}
            </div>
          );
        })}
        {total === 0 && (
          <div
            className="flex-1 rounded-athena-sm"
            style={{ backgroundColor: "var(--color-bg-elevated)" }}
          />
        )}
      </div>
    </div>
  );
}

/* ── Status Pipeline ── */

function StatusPipeline({
  byStatus,
  t,
}: {
  byStatus: Record<VulnStatus, number>;
  t: (key: string) => string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span
        className="font-mono uppercase tracking-[1.5px]"
        style={{ fontSize: 8, fontWeight: 700, color: "#FFFFFF40" }}
      >
        STATUS PIPELINE
      </span>
      <div className="flex items-center justify-around">
        {STATUS_LIST.map((status, idx) => (
          <React.Fragment key={status}>
            <div className="flex flex-col items-center gap-0.5">
              <span
                className="font-mono athena-tabular-nums"
                style={{ fontSize: 28, fontWeight: 700, color: STATUS_COLORS[status] }}
              >
                {byStatus[status] ?? 0}
              </span>
              <span
                className="font-mono uppercase tracking-wider"
                style={{ fontSize: 8, fontWeight: 600, color: "#FFFFFF50" }}
              >
                {t(`status.${status}`)}
              </span>
              <div
                className="w-full rounded-[2px]"
                style={{ height: 3, backgroundColor: STATUS_COLORS[status] }}
              />
            </div>
            {idx < STATUS_LIST.length - 1 && (
              <span
                className="font-mono font-bold"
                style={{ fontSize: 16, color: "#FFFFFF20" }}
              >
                {">>"}
              </span>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

/* ── Severity Badge ── */

function SeverityBadge({ severity }: { severity: VulnSeverity }) {
  return (
    <span
      className="font-mono text-[10px] font-bold uppercase rounded-athena-sm px-2 py-0.5"
      style={{
        backgroundColor: SEVERITY_COLORS[severity],
        color: severity === "medium" || severity === "low" ? "#000" : "#FFF",
        border: "none",
        width: 70,
        textAlign: "center" as const,
      }}
    >
      {severity}
    </span>
  );
}

/* ── Vulnerability Table ── */

function VulnTable({
  vulns,
  selectedId,
  onSelect,
  t,
}: {
  vulns: Vulnerability[];
  selectedId: string | null;
  onSelect: (v: Vulnerability) => void;
  t: (key: string) => string;
}) {
  const sorted = useMemo(() => {
    return [...vulns].sort((a, b) => {
      const ai = SEVERITY_ORDER.indexOf(a.severity);
      const bi = SEVERITY_ORDER.indexOf(b.severity);
      return ai - bi;
    });
  }, [vulns]);

  return (
    <div
      className="flex-1 min-w-0 rounded-athena-md overflow-hidden flex flex-col bg-[#111827]"
      style={{
        border: "1px solid var(--color-white-8)",
      }}
    >
      {/* Table header */}
      <div
        className="flex items-center gap-3 px-3 py-2 shrink-0"
        style={{ backgroundColor: "#1F2937", borderBottom: "1px solid var(--color-white-8)" }}
      >
        <span className="w-1 shrink-0" />
        <span
          className="font-mono uppercase tracking-wider w-[120px] shrink-0"
          style={{ fontSize: 9, fontWeight: 700, color: "#FFFFFF50" }}
        >
          {t("columns.cveId")}
        </span>
        <span
          className="font-mono uppercase tracking-wider flex-1 min-w-0"
          style={{ fontSize: 9, fontWeight: 700, color: "#FFFFFF50" }}
        >
          Title
        </span>
        <span
          className="font-mono uppercase tracking-wider w-[80px] shrink-0 text-center"
          style={{ fontSize: 9, fontWeight: 700, color: "#FFFFFF50" }}
        >
          {t("columns.severity")}
        </span>
        <span
          className="font-mono uppercase tracking-wider w-[90px] shrink-0 text-center"
          style={{ fontSize: 9, fontWeight: 700, color: "#FFFFFF50" }}
        >
          {t("columns.status")}
        </span>
      </div>

      {/* Table body */}
      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <span
              className="font-mono text-xs text-[#9ca3af]"
            >
              {t("noVulns")}
            </span>
          </div>
        ) : (
          sorted.map((vuln) => {
            const isSelected = vuln.id === selectedId;
            return (
              <button
                key={vuln.id}
                type="button"
                onClick={() => onSelect(vuln)}
                className="flex items-center gap-3 w-full px-3 text-left transition-colors"
                style={{
                  height: 44,
                  backgroundColor: isSelected ? "#3B82F615" : "transparent",
                  border: isSelected ? "1px solid #3B82F630" : "1px solid transparent",
                  borderBottom: isSelected ? "1px solid #3B82F630" : "1px solid var(--color-white-8)",
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = "var(--color-bg-surface)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = "transparent";
                  }
                }}
              >
                {/* Severity color bar */}
                <span
                  className="w-1 h-6 rounded-full shrink-0"
                  style={{
                    backgroundColor: SEVERITY_COLORS[vuln.severity],
                  }}
                />

                {/* CVE ID */}
                <span
                  className="font-mono text-xs w-[120px] shrink-0 truncate"
                  style={{
                    color: isSelected ? "#3B82F6" : "var(--color-accent)",
                    fontWeight: isSelected ? 700 : 400,
                  }}
                >
                  {vuln.cveId ?? "N/A"}
                </span>

                {/* Title */}
                <span
                  className="font-mono text-xs flex-1 min-w-0 truncate"
                  style={{ color: "#E5E7EB" }}
                >
                  {vuln.title}
                </span>

                {/* Severity */}
                <span className="w-[80px] shrink-0 flex justify-center">
                  <SeverityBadge severity={vuln.severity} />
                </span>

                {/* Status */}
                <span
                  className="font-mono text-[10px] uppercase w-[90px] shrink-0 text-center text-[#6b7280]"
                >
                  {t(`status.${vuln.status}`)}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}

/* ── Detail Panel ── */

function DetailPanel({
  vuln,
  onClose,
  onStatusChange,
  t,
}: {
  vuln: Vulnerability;
  onClose: () => void;
  onStatusChange: (vulnId: string, status: VulnStatus) => void;
  t: (key: string) => string;
}) {
  const [changingStatus, setChangingStatus] = useState(false);

  const handleStatusChange = async (newStatus: VulnStatus) => {
    setChangingStatus(true);
    try {
      await onStatusChange(vuln.id, newStatus);
    } finally {
      setChangingStatus(false);
    }
  };

  const allActions: { status: VulnStatus; label: string }[] = [
    { status: "discovered" as const, label: t("detail.reopenDiscovered") },
    { status: "confirmed" as const, label: t("detail.markConfirmed") },
    { status: "exploited" as const, label: t("detail.markExploited") },
    { status: "reported" as const, label: t("detail.markReported") },
    { status: "false_positive" as const, label: t("detail.markFalsePositive") },
  ];
  const statusActions = allActions.filter((a) => a.status !== vuln.status);

  return (
    <div
      className="rounded-athena-md flex flex-col gap-5 shrink-0 overflow-y-auto bg-[#111827] p-5"
      style={{
        width: 380,
        border: "1px solid var(--color-white-8)",
      }}
    >
      {/* Header with close button */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-2 min-w-0">
          <span
            className="font-mono text-sm font-bold truncate text-[#3b82f6]"
          >
            {vuln.cveId ?? "N/A"}
          </span>
          <SeverityBadge severity={vuln.severity} />
        </div>
        <button
          type="button"
          onClick={onClose}
          className="font-mono text-sm shrink-0 w-7 h-7 flex items-center justify-center rounded-athena-sm hover:bg-[#1f2937] transition-colors text-[#9ca3af]"
          aria-label={t("detail.close")}
        >
          X
        </button>
      </div>

      {/* Title */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-xs font-bold"
          style={{ color: "#E5E7EB" }}
        >
          {vuln.title}
        </span>
      </div>

      {/* Description */}
      {vuln.description && (
        <div className="flex flex-col gap-1">
          <span
            className="font-mono text-[10px] uppercase tracking-wider text-[#9ca3af]"
          >
            {t("detail.description")}
          </span>
          <p
            className="font-mono text-xs leading-relaxed text-[#6b7280]"
          >
            {vuln.description}
          </p>
        </div>
      )}

      {/* Status */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-[10px] uppercase tracking-wider text-[#9ca3af]"
        >
          {t("columns.status")}
        </span>
        <span
          className="font-mono text-xs uppercase"
          style={{ color: "#E5E7EB" }}
        >
          {t(`status.${vuln.status}`)}
        </span>
      </div>

      {/* Affected component (service) */}
      {vuln.service && (
        <div className="flex flex-col gap-1">
          <span
            className="font-mono text-[10px] uppercase tracking-wider text-[#9ca3af]"
          >
            {t("detail.service")}
          </span>
          <span
            className="font-mono text-xs text-[#6b7280]"
          >
            {vuln.service}
          </span>
        </div>
      )}

      {/* Target */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-[10px] uppercase tracking-wider text-[#9ca3af]"
        >
          {t("columns.target")}
        </span>
        <span
          className="font-mono text-xs text-[#6b7280]"
        >
          {vuln.targetHostname ?? vuln.targetIp}
        </span>
      </div>

      {/* CVSS */}
      {vuln.cvssScore !== null && vuln.cvssScore !== undefined && (
        <div className="flex flex-col gap-1">
          <span
            className="font-mono text-[10px] uppercase tracking-wider text-[#9ca3af]"
          >
            {t("columns.cvss")}
          </span>
          <span
            className="font-mono text-xs font-bold athena-tabular-nums"
            style={{ color: SEVERITY_COLORS[vuln.severity] }}
          >
            {vuln.cvssScore.toFixed(1)}
          </span>
        </div>
      )}

      {/* Timeline */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-[10px] uppercase tracking-wider text-[#9ca3af]"
        >
          {t("detail.timeline")}
        </span>
        <div className="flex flex-col gap-0.5">
          <TimelineEntry
            label={t("status.discovered")}
            date={vuln.discoveredAt}
          />
          {vuln.confirmedAt && (
            <TimelineEntry
              label={t("status.confirmed")}
              date={vuln.confirmedAt}
            />
          )}
          {vuln.exploitedAt && (
            <TimelineEntry
              label={t("status.exploited")}
              date={vuln.exploitedAt}
            />
          )}
          {vuln.reportedAt && (
            <TimelineEntry
              label={t("status.reported")}
              date={vuln.reportedAt}
            />
          )}
        </div>
      </div>

      {/* Status actions */}
      <div className="flex flex-col gap-2 mt-auto">
        <span
          className="font-mono text-[10px] uppercase tracking-wider text-[#9ca3af]"
        >
          {t("detail.actions")}
        </span>
        <div className="flex flex-wrap gap-1.5">
          {statusActions.map((action) => (
            <button
              key={action.status}
              type="button"
              disabled={changingStatus}
              onClick={() => handleStatusChange(action.status)}
              className="font-mono text-[10px] uppercase px-2.5 py-1 rounded-athena-sm transition-colors disabled:opacity-50 text-[#3b82f6]"
              style={{
                border: "1px solid var(--color-accent-bg)",
                backgroundColor: "transparent",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "var(--color-accent-bg)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "transparent";
              }}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Timeline Entry helper ── */

function TimelineEntry({ label, date }: { label: string; date: string }) {
  const formatted = new Date(date).toLocaleString("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return (
    <div className="flex items-center gap-2">
      <span
        className="font-mono text-[10px] text-[#9ca3af]"
      >
        {label}:
      </span>
      <span
        className="font-mono text-[10px] athena-tabular-nums text-[#6b7280]"
      >
        {formatted}
      </span>
    </div>
  );
}

/* ── Main Page Content (uses hooks that need context + useSearchParams) ── */

function VulnsContent() {
  const t = useTranslations("Vulns");
  const operationId = useOperationId();
  const searchParams = useSearchParams();
  const { vulns, loading, error, updateStatus } = useVulns(operationId);

  // Server-side summary
  const [summary, setSummary] = useState<VulnSummary | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await api.get<VulnSummary>(
        `/operations/${operationId}/vulnerabilities/summary`,
      );
      setSummary(data);
    } catch {
      // Fall back to client-side computation
    }
  }, [operationId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  // Selected vulnerability (from URL param or click)
  const [selectedId, setSelectedId] = useState<string | null>(
    searchParams.get("id"),
  );

  // Sync URL param on mount
  useEffect(() => {
    const urlId = searchParams.get("id");
    if (urlId && urlId !== selectedId) {
      setSelectedId(urlId);
    }
    // Only sync on initial load / URL change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const selectedVuln = useMemo(() => {
    if (!selectedId) return null;
    return vulns.find((v) => v.id === selectedId) ?? null;
  }, [vulns, selectedId]);

  // Client-side computed summary as fallback
  const computedSummary = useMemo((): VulnSummary => {
    if (summary) return summary;
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
      bySeverity[v.severity] = (bySeverity[v.severity] ?? 0) + 1;
      byStatus[v.status] = (byStatus[v.status] ?? 0) + 1;
    }
    return { total: vulns.length, bySeverity, byStatus };
  }, [summary, vulns]);

  const handleSelect = useCallback((v: Vulnerability) => {
    setSelectedId((prev) => (prev === v.id ? null : v.id));
  }, []);

  const handleClose = useCallback(() => {
    setSelectedId(null);
  }, []);

  const handleStatusChange = useCallback(
    async (vulnId: string, newStatus: VulnStatus) => {
      await updateStatus(vulnId, newStatus);
      // Refresh server summary after status change
      fetchSummary();
    },
    [updateStatus, fetchSummary],
  );

  // -- Loading state --
  if (loading && vulns.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-[#9ca3af]">
          {t("title")}...
        </p>
      </div>
    );
  }

  // -- Error state --
  if (error && vulns.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-[#EF4444]">
          {error}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto bg-[#0A0E17]">
      <div className="flex flex-col gap-4 min-h-full max-w-[1440px] w-full mx-auto">
        {/* Stats Row */}
        <div className="flex gap-4 py-4 px-6 shrink-0">
          {/* Severity Heat Strip */}
          <div className="flex-1 min-w-0">
            <SeverityHeatStrip
              bySeverity={computedSummary.bySeverity}
              total={computedSummary.total}
            />
          </div>

          {/* Status Pipeline */}
          <div className="flex-1 min-w-0">
            <StatusPipeline
              byStatus={computedSummary.byStatus}
              t={t}
            />
          </div>
        </div>

        {/* Body: Table + Detail Panel */}
        <div className="flex gap-4 flex-1 min-h-0 px-6 pb-4">
          {/* Left: Vulnerability Table */}
          <VulnTable
            vulns={vulns}
            selectedId={selectedId}
            onSelect={handleSelect}
            t={t}
          />

          {/* Right: Detail Panel (conditional) */}
          {selectedVuln && (
            <DetailPanel
              vuln={selectedVuln}
              onClose={handleClose}
              onStatusChange={handleStatusChange}
              t={t}
            />
          )}
        </div>

        {/* PoC Evidence Section */}
        <div className="flex flex-col gap-3 shrink-0">
          <div
            className="flex items-center gap-2"
            style={{ borderTop: "1px solid var(--color-white-8)", paddingTop: 16 }}
          >
            <span
              className="font-mono text-[8px] font-bold uppercase tracking-[1.5px]"
              style={{ color: "var(--color-text-muted)" }}
            >
              POC EVIDENCE
            </span>
          </div>
          {operationId && (
            <PocEvidencePanel operationId={operationId} />
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Page wrapper with Suspense (required for useSearchParams) ── */

export default function VulnsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <p className="text-sm font-mono text-[#9ca3af]">
            Loading Vulnerability Dashboard...
          </p>
        </div>
      }
    >
      <VulnsContent />
    </Suspense>
  );
}
