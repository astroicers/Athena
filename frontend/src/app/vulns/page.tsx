"use client";

import {
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

/* ── Constants ── */

const SEVERITY_ORDER: VulnSeverity[] = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
];

const SEVERITY_COLORS: Record<VulnSeverity, string> = {
  critical: "#FF0000",
  high: "#FF8800",
  medium: "#FFD700",
  low: "#22C55E",
  info: "#999999",
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
  by_severity,
  total,
}: {
  by_severity: Record<VulnSeverity, number>;
  total: number;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span
        className="font-mono uppercase tracking-[1.5px]"
        style={{ fontSize: 8, color: "#FFFFFF40" }}
      >
        SEVERITY DISTRIBUTION
      </span>
      <div className="flex gap-0.5" style={{ height: 24 }}>
        {SEVERITY_ORDER.map((sev) => {
          const count = by_severity[sev] ?? 0;
          if (count === 0) return null;
          const widthPct = total > 0 ? (count / total) * 100 : 0;
          return (
            <div
              key={sev}
              className="flex items-center justify-center rounded-sm transition-all duration-300"
              style={{
                width: `${widthPct}%`,
                minWidth: count > 0 ? 24 : 0,
                backgroundColor: SEVERITY_COLORS[sev],
              }}
            >
              {widthPct > 6 && (
                <span
                  className="font-mono font-bold text-[11px] athena-tabular-nums"
                  style={{
                    color: sev === "medium" || sev === "low" ? "#000" : "#FFF",
                  }}
                >
                  {count}
                </span>
              )}
            </div>
          );
        })}
        {total === 0 && (
          <div
            className="flex-1 rounded-sm"
            style={{ backgroundColor: "#1f2937" }}
          />
        )}
      </div>
    </div>
  );
}

/* ── Status Pipeline ── */

function StatusPipeline({
  by_status,
  t,
}: {
  by_status: Record<VulnStatus, number>;
  t: (key: string) => string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span
        className="font-mono uppercase tracking-[1.5px]"
        style={{ fontSize: 8, color: "#FFFFFF40" }}
      >
        STATUS PIPELINE
      </span>
      <div className="flex justify-around">
        {STATUS_LIST.map((status) => (
          <div
            key={status}
            className="flex flex-col items-center gap-0.5"
          >
            <span
              className="font-mono font-bold text-lg athena-tabular-nums"
              style={{ color: "#E5E7EB" }}
            >
              {by_status[status] ?? 0}
            </span>
            <span
              className="font-mono uppercase tracking-wider"
              style={{ fontSize: 9, color: "#6B7280" }}
            >
              {t(`status.${status}`)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Severity Badge ── */

function SeverityBadge({ severity }: { severity: VulnSeverity }) {
  return (
    <span
      className="font-mono text-[10px] font-bold uppercase px-1.5 py-0.5 rounded"
      style={{
        backgroundColor: `${SEVERITY_COLORS[severity]}20`,
        color: SEVERITY_COLORS[severity],
        border: `1px solid ${SEVERITY_COLORS[severity]}40`,
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
      className="flex-1 min-w-0 rounded-md overflow-hidden flex flex-col"
      style={{
        backgroundColor: "#111827",
        border: "1px solid #FFFFFF08",
      }}
    >
      {/* Table header */}
      <div
        className="flex items-center gap-3 px-3 py-2 shrink-0"
        style={{ borderBottom: "1px solid #FFFFFF08" }}
      >
        <span className="w-1 shrink-0" />
        <span
          className="font-mono text-[10px] uppercase tracking-wider w-[120px] shrink-0"
          style={{ color: "#6B7280" }}
        >
          {t("columns.cveId")}
        </span>
        <span
          className="font-mono text-[10px] uppercase tracking-wider flex-1 min-w-0"
          style={{ color: "#6B7280" }}
        >
          Title
        </span>
        <span
          className="font-mono text-[10px] uppercase tracking-wider w-[80px] shrink-0 text-center"
          style={{ color: "#6B7280" }}
        >
          {t("columns.severity")}
        </span>
        <span
          className="font-mono text-[10px] uppercase tracking-wider w-[90px] shrink-0 text-center"
          style={{ color: "#6B7280" }}
        >
          {t("columns.status")}
        </span>
      </div>

      {/* Table body */}
      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <span
              className="font-mono text-xs"
              style={{ color: "#6B7280" }}
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
                className="flex items-center gap-3 w-full px-3 py-2 text-left transition-colors"
                style={{
                  backgroundColor: isSelected ? "#1E293B" : "transparent",
                  borderBottom: "1px solid #FFFFFF08",
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = "#111827CC";
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
                  style={{ color: "#3B82F6" }}
                >
                  {vuln.cve_id ?? "N/A"}
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
                  className="font-mono text-[10px] uppercase w-[90px] shrink-0 text-center"
                  style={{ color: "#9CA3AF" }}
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
      className="rounded-md flex flex-col gap-5 shrink-0 overflow-y-auto"
      style={{
        width: 380,
        backgroundColor: "#111827",
        border: "1px solid #FFFFFF08",
        padding: 20,
      }}
    >
      {/* Header with close button */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-2 min-w-0">
          <span
            className="font-mono text-sm font-bold truncate"
            style={{ color: "#3B82F6" }}
          >
            {vuln.cve_id ?? "N/A"}
          </span>
          <SeverityBadge severity={vuln.severity} />
        </div>
        <button
          type="button"
          onClick={onClose}
          className="font-mono text-sm shrink-0 w-7 h-7 flex items-center justify-center rounded hover:bg-[#1f2937] transition-colors"
          style={{ color: "#6B7280" }}
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
            className="font-mono text-[10px] uppercase tracking-wider"
            style={{ color: "#6B7280" }}
          >
            {t("detail.description")}
          </span>
          <p
            className="font-mono text-xs leading-relaxed"
            style={{ color: "#9CA3AF" }}
          >
            {vuln.description}
          </p>
        </div>
      )}

      {/* Status */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-[10px] uppercase tracking-wider"
          style={{ color: "#6B7280" }}
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
            className="font-mono text-[10px] uppercase tracking-wider"
            style={{ color: "#6B7280" }}
          >
            {t("detail.service")}
          </span>
          <span
            className="font-mono text-xs"
            style={{ color: "#9CA3AF" }}
          >
            {vuln.service}
          </span>
        </div>
      )}

      {/* Target */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-[10px] uppercase tracking-wider"
          style={{ color: "#6B7280" }}
        >
          {t("columns.target")}
        </span>
        <span
          className="font-mono text-xs"
          style={{ color: "#9CA3AF" }}
        >
          {vuln.target_hostname ?? vuln.target_ip}
        </span>
      </div>

      {/* CVSS */}
      {vuln.cvssScore !== null && vuln.cvssScore !== undefined && (
        <div className="flex flex-col gap-1">
          <span
            className="font-mono text-[10px] uppercase tracking-wider"
            style={{ color: "#6B7280" }}
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
          className="font-mono text-[10px] uppercase tracking-wider"
          style={{ color: "#6B7280" }}
        >
          {t("detail.timeline")}
        </span>
        <div className="flex flex-col gap-0.5">
          <TimelineEntry
            label={t("status.discovered")}
            date={vuln.discovered_at}
          />
          {vuln.confirmed_at && (
            <TimelineEntry
              label={t("status.confirmed")}
              date={vuln.confirmed_at}
            />
          )}
          {vuln.exploited_at && (
            <TimelineEntry
              label={t("status.exploited")}
              date={vuln.exploited_at}
            />
          )}
          {vuln.reported_at && (
            <TimelineEntry
              label={t("status.reported")}
              date={vuln.reported_at}
            />
          )}
        </div>
      </div>

      {/* Status actions */}
      <div className="flex flex-col gap-2 mt-auto">
        <span
          className="font-mono text-[10px] uppercase tracking-wider"
          style={{ color: "#6B7280" }}
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
              className="font-mono text-[10px] uppercase px-2.5 py-1 rounded transition-colors disabled:opacity-50"
              style={{
                color: "#3B82F6",
                border: "1px solid #3B82F640",
                backgroundColor: "transparent",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#3B82F610";
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
        className="font-mono text-[10px]"
        style={{ color: "#6B7280" }}
      >
        {label}:
      </span>
      <span
        className="font-mono text-[10px] athena-tabular-nums"
        style={{ color: "#9CA3AF" }}
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
    const by_severity: Record<VulnSeverity, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      info: 0,
    };
    const by_status: Record<VulnStatus, number> = {
      discovered: 0,
      confirmed: 0,
      exploited: 0,
      reported: 0,
      false_positive: 0,
    };
    for (const v of vulns) {
      by_severity[v.severity] = (by_severity[v.severity] ?? 0) + 1;
      by_status[v.status] = (by_status[v.status] ?? 0) + 1;
    }
    return { total: vulns.length, by_severity, by_status };
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
        <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
          {t("title")}...
        </p>
      </div>
    );
  }

  // -- Error state --
  if (error && vulns.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono" style={{ color: "#EF4444" }}>
          {error}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ backgroundColor: "#0A0E17" }}>
      <div className="flex flex-col gap-4 p-4 h-full max-w-[1440px] w-full mx-auto">
        {/* Stats Row */}
        <div
          className="flex gap-6 rounded-md p-4 shrink-0"
          style={{
            backgroundColor: "#111827",
            border: "1px solid #FFFFFF08",
          }}
        >
          {/* Severity Heat Strip */}
          <div className="flex-1 min-w-0">
            <SeverityHeatStrip
              by_severity={computedSummary.by_severity}
              total={computedSummary.total}
            />
          </div>

          {/* Divider */}
          <div
            className="w-px shrink-0"
            style={{ backgroundColor: "#FFFFFF10" }}
          />

          {/* Status Pipeline */}
          <div className="flex-1 min-w-0">
            <StatusPipeline
              by_status={computedSummary.by_status}
              t={t}
            />
          </div>
        </div>

        {/* Body: Table + Detail Panel */}
        <div className="flex gap-4 flex-1 min-h-0">
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
          <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
            Loading Vulnerability Dashboard...
          </p>
        </div>
      }
    >
      <VulnsContent />
    </Suspense>
  );
}
