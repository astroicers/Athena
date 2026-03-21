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

/* Tailwind class maps for severity heat-strip backgrounds */
const SEVERITY_BG_CLASSES: Record<VulnSeverity, string> = {
  critical: "bg-[#B91C1C]",
  high: "bg-[#B45309]",
  medium: "bg-[#B45309]",
  low: "bg-[#059669]",
  info: "bg-[#52525B]",
};

/* Tailwind badge classes for severity badges */
const SEVERITY_BADGE_CLASSES: Record<VulnSeverity, string> = {
  critical: "bg-[#B91C1C]/12 border-[#B91C1C]/25 text-[#B91C1C]",
  high: "bg-[#B45309]/12 border-[#B45309]/25 text-[#B45309]",
  medium: "bg-[#B45309]/12 border-[#B45309]/25 text-[#B45309]",
  low: "bg-[#059669]/12 border-[#059669]/25 text-[#059669]",
  info: "bg-[#52525B]/12 border-[#52525B]/25 text-[#52525B]",
};

/* Text-only color classes for inline severity references */
const SEVERITY_TEXT_CLASSES: Record<VulnSeverity, string> = {
  critical: "text-[#B91C1C]",
  high: "text-[#B45309]",
  medium: "text-[#B45309]",
  low: "text-[#059669]",
  info: "text-[#52525B]",
};

const STATUS_CSS: Record<VulnStatus, string> = {
  discovered: "var(--color-accent)",
  confirmed: "var(--color-success)",
  exploited: "var(--color-error)",
  reported: "var(--color-phase-orient)",
  false_positive: "var(--color-text-secondary)",
};

const STATUS_TEXT_CLASSES: Record<VulnStatus, string> = {
  discovered: "text-[var(--color-accent)]",
  confirmed: "text-[var(--color-success)]",
  exploited: "text-[var(--color-error)]",
  reported: "text-[var(--color-phase-orient)]",
  false_positive: "text-[var(--color-text-secondary)]",
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
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[11px] font-bold uppercase tracking-[2px] text-[var(--color-text-secondary)]">
        SEVERITY DISTRIBUTION
      </span>
      <div className="flex gap-0.5 h-6 rounded-[var(--radius)]">
        {SEVERITY_ORDER.map((sev) => {
          const count = bySeverity[sev] ?? 0;
          if (count === 0) return null;
          const widthPct = total > 0 ? (count / total) * 100 : 0;
          return (
            <div
              key={sev}
              className={`flex items-center justify-center rounded-[var(--radius)] transition-all duration-300 ${SEVERITY_BG_CLASSES[sev]}`}
              style={{ width: `${widthPct}%`, minWidth: count > 0 ? 24 : 0 }}
            >
              {widthPct > 6 && (
                <span className="font-mono text-[8px] font-bold athena-tabular-nums text-white">
                  {sev.toUpperCase().slice(0, 4)} {count}
                </span>
              )}
            </div>
          );
        })}
        {total === 0 && (
          <div className="flex-1 rounded-[var(--radius)] bg-[var(--color-bg-elevated)]" />
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
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[11px] font-bold uppercase tracking-[2px] text-[var(--color-text-secondary)]">
        STATUS PIPELINE
      </span>
      <div className="flex items-center justify-around">
        {STATUS_LIST.map((status, idx) => (
          <React.Fragment key={status}>
            <div className="flex flex-col items-center gap-0.5">
              <span
                className={`font-mono text-[28px] font-bold athena-tabular-nums ${STATUS_TEXT_CLASSES[status]}`}
              >
                {byStatus[status] ?? 0}
              </span>
              <span className="font-mono text-[8px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                {t(`status.${status}`)}
              </span>
              <div
                className="w-full h-[3px] rounded-[2px]"
                style={{ backgroundColor: STATUS_CSS[status] }}
              />
            </div>
            {idx < STATUS_LIST.length - 1 && (
              <span className="font-mono text-[16px] font-bold text-[#3F3F46]">
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
      className={`font-mono text-[10px] font-bold uppercase rounded-[var(--radius)] px-2 py-0.5 w-[70px] text-center border ${SEVERITY_BADGE_CLASSES[severity]}`}
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
      className="flex-1 min-w-0 rounded-[var(--radius)] overflow-hidden flex flex-col bg-[var(--color-bg-surface)] border border-[var(--color-border)]"
    >
      {/* Table header */}
      <div className="flex items-center gap-3 px-4 h-9 shrink-0 bg-[var(--color-bg-surface)] border-b border-[var(--color-border)]">
        <span className="w-1 shrink-0" />
        <span className="font-mono text-[10px] font-bold uppercase tracking-[1px] w-[120px] shrink-0 text-[var(--color-text-secondary)]">
          {t("columns.cveId")}
        </span>
        <span className="font-mono text-[10px] font-bold uppercase tracking-[1px] flex-1 min-w-0 text-[var(--color-text-secondary)]">
          Title
        </span>
        <span className="font-mono text-[10px] font-bold uppercase tracking-[1px] w-[80px] shrink-0 text-center text-[var(--color-text-secondary)]">
          {t("columns.severity")}
        </span>
        <span className="font-mono text-[10px] font-bold uppercase tracking-[1px] w-[90px] shrink-0 text-center text-[var(--color-text-secondary)]">
          {t("columns.status")}
        </span>
      </div>

      {/* Table body */}
      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <span
              className="font-mono text-xs text-[var(--color-text-tertiary)]"
            >
              {t("noVulns")}
            </span>
          </div>
        ) : (
          sorted.map((vuln, idx) => {
            const isSelected = vuln.id === selectedId;
            return (
              <button
                key={vuln.id}
                type="button"
                onClick={() => onSelect(vuln)}
                className={`flex items-center gap-3 w-full px-4 h-11 text-left transition-colors border-l-4 hover:bg-[var(--color-bg-surface-hover)] ${
                  isSelected
                    ? "border-l-[#1E6091] bg-[#1E609115]"
                    : "border-l-transparent"
                } ${idx % 2 === 0 ? "bg-[rgba(255,255,255,0.03)]" : "bg-transparent"}`}
              >
                {/* Severity color bar */}
                <span
                  className={`w-1 h-5 rounded-full shrink-0 ${SEVERITY_BG_CLASSES[vuln.severity]}`}
                />

                {/* CVE ID */}
                <span
                  className={`font-mono text-[9px] w-[120px] shrink-0 truncate text-[var(--color-text-primary)] ${isSelected ? "font-bold" : "font-normal"}`}
                >
                  {vuln.cveId ?? "N/A"}
                </span>

                {/* Title */}
                <span className="font-mono text-[9px] flex-1 min-w-0 truncate text-[var(--color-text-primary)]">
                  {vuln.title}
                </span>

                {/* Severity */}
                <span className="w-[80px] shrink-0 flex justify-center">
                  <SeverityBadge severity={vuln.severity} />
                </span>

                {/* Status */}
                <span className="font-mono text-[9px] uppercase w-[90px] shrink-0 text-center text-[var(--color-text-secondary)]">
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
      className="rounded-[var(--radius)] flex flex-col gap-4 shrink-0 overflow-y-auto bg-[var(--color-bg-surface)] p-4 w-[380px] border border-[var(--color-border)]"
    >
      {/* Header with close button */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-2 min-w-0">
          <span
            className="font-mono text-sm font-bold truncate text-[var(--color-accent)]"
          >
            {vuln.cveId ?? "N/A"}
          </span>
          <SeverityBadge severity={vuln.severity} />
        </div>
        <button
          type="button"
          onClick={onClose}
          className="font-mono text-sm shrink-0 w-7 h-7 flex items-center justify-center rounded-[var(--radius)] hover:bg-[var(--color-bg-elevated)] transition-colors text-[var(--color-text-tertiary)]"
          aria-label={t("detail.close")}
        >
          X
        </button>
      </div>

      {/* Title */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-[14px] font-bold text-[var(--color-text-primary)]"
        >
          {vuln.title}
        </span>
      </div>

      {/* Description */}
      {vuln.description && (
        <div className="flex flex-col gap-1">
          <span
            className="font-mono text-[11px] font-bold uppercase tracking-[2px] text-[var(--color-text-secondary)]"
          >
            {t("detail.description")}
          </span>
          <p
            className="font-mono text-[9px] leading-relaxed text-[var(--color-text-primary)]"
          >
            {vuln.description}
          </p>
        </div>
      )}

      {/* Status */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-[11px] font-bold uppercase tracking-[2px] text-[var(--color-text-secondary)]"
        >
          {t("columns.status")}
        </span>
        <span
          className="font-mono text-xs uppercase text-[var(--color-text-primary)]"
        >
          {t(`status.${vuln.status}`)}
        </span>
      </div>

      {/* Affected component (service) */}
      {vuln.service && (
        <div className="flex flex-col gap-1">
          <span
            className="font-mono text-[11px] font-bold uppercase tracking-[2px] text-[var(--color-text-secondary)]"
          >
            {t("detail.service")}
          </span>
          <span
            className="font-mono text-xs text-[var(--color-text-secondary)]"
          >
            {vuln.service}
          </span>
        </div>
      )}

      {/* Target */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-[11px] font-bold uppercase tracking-[2px] text-[var(--color-text-secondary)]"
        >
          {t("columns.target")}
        </span>
        <span
          className="font-mono text-xs text-[var(--color-text-secondary)]"
        >
          {vuln.targetHostname ?? vuln.targetIp}
        </span>
      </div>

      {/* CVSS */}
      {vuln.cvssScore !== null && vuln.cvssScore !== undefined && (
        <div className="flex flex-col gap-1">
          <span
            className="font-mono text-[11px] font-bold uppercase tracking-[2px] text-[var(--color-text-secondary)]"
          >
            {t("columns.cvss")}
          </span>
          <span
            className={`font-mono text-xs font-bold athena-tabular-nums ${SEVERITY_TEXT_CLASSES[vuln.severity]}`}
          >
            {vuln.cvssScore.toFixed(1)}
          </span>
        </div>
      )}

      {/* Timeline */}
      <div className="flex flex-col gap-1">
        <span
          className="font-mono text-[11px] font-bold uppercase tracking-[2px] text-[var(--color-text-secondary)]"
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
          className="font-mono text-[11px] font-bold uppercase tracking-[2px] text-[var(--color-text-secondary)]"
        >
          STATUS TRANSITIONS
        </span>
        <div className="flex flex-wrap gap-1.5">
          {statusActions.map((action) => (
            <button
              key={action.status}
              type="button"
              disabled={changingStatus}
              onClick={() => handleStatusChange(action.status)}
              className="font-mono text-[10px] uppercase px-2.5 py-1 rounded-[var(--radius)] transition-colors disabled:opacity-50 text-[var(--color-text-primary)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] hover:bg-[var(--color-bg-elevated)]"
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
        className="font-mono text-[10px] text-[var(--color-text-tertiary)]"
      >
        {label}:
      </span>
      <span
        className="font-mono text-[10px] athena-tabular-nums text-[var(--color-text-secondary)]"
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
        <p className="text-sm font-mono text-[var(--color-text-tertiary)]">
          {t("title")}...
        </p>
      </div>
    );
  }

  // -- Error state --
  if (error && vulns.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-[var(--color-error)]">
          {error}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto bg-[var(--color-bg-primary)]">
      {/* Page Header */}
      <div className="flex items-center justify-between h-12 px-6 shrink-0 bg-[var(--color-bg-surface)]">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[13px] font-bold text-[var(--color-text-primary)]">
            VULNERABILITIES
          </span>
          <span className="font-mono text-[11px] font-semibold rounded-[var(--radius)] px-2.5 py-1 bg-[var(--color-accent-bg)] text-[var(--color-accent)]">
            {operationId?.slice(0, 12).toUpperCase()}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] font-semibold text-[var(--color-text-secondary)]">
            Total: {computedSummary.total}
          </span>
          <div className="relative">
            <span className="font-mono text-sm text-[var(--color-text-tertiary)]">
              &#x1F514;
            </span>
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-[var(--color-error)]" />
          </div>
        </div>
      </div>

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
        <div className="flex flex-col gap-2 shrink-0 px-6">
          <div className="flex items-center gap-2 border-t border-[var(--color-border)] pt-3">
            <span className="font-mono text-[8px] font-bold uppercase tracking-[1.5px] text-[var(--color-text-tertiary)]">
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
          <p className="text-sm font-mono text-[var(--color-text-tertiary)]">
            Loading Vulnerability Dashboard...
          </p>
        </div>
      }
    >
      <VulnsContent />
    </Suspense>
  );
}
