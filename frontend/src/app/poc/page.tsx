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

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { api } from "@/lib/api";
import type { PocRecord, PocSummary } from "@/types/poc";

/* ── Constants ── */

const POLL_MS = 30_000;

/* ── Color helpers ── */

function reproducibleColor(
  status: PocRecord["reproducible"],
): { bg: string; border: string; text: string } {
  switch (status) {
    case "reproducible":
      return { bg: "#22C55E20", border: "#22C55E40", text: "#22C55E" };
    case "partial":
      return { bg: "#FFA50020", border: "#FFA50040", text: "#FFA500" };
    default:
      return { bg: "#EF444420", border: "#EF444440", text: "#EF4444" };
  }
}

function reproducibleLabel(status: PocRecord["reproducible"]): string {
  switch (status) {
    case "reproducible":
      return "REPRODUCIBLE";
    case "partial":
      return "PARTIAL";
    default:
      return "NOT REPRODUCIBLE";
  }
}

/* ── Summary Card ── */

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div
      className="flex-1 min-w-0 rounded-lg flex flex-col gap-1"
      style={{
        backgroundColor: "#111827",
        border: "1px solid #FFFFFF08",
        padding: "14px 16px",
      }}
    >
      <span
        className="font-mono text-[8px] font-bold uppercase tracking-wider"
        style={{ color: "#FFFFFF40" }}
      >
        {label}
      </span>
      <span
        className="font-mono text-[28px] font-bold leading-tight athena-tabular-nums"
        style={{ color }}
      >
        {value}
      </span>
    </div>
  );
}

/* ── PoC Card ── */

function PocCard({ record, index }: { record: PocRecord; index: number }) {
  const repColor = reproducibleColor(record.reproducible);

  return (
    <div
      className="rounded-lg flex flex-col gap-3"
      style={{
        backgroundColor: "#111827",
        border: "1px solid #FFFFFF08",
        padding: "16px 20px",
      }}
    >
      {/* Header row: ID + badges + vuln ref */}
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-xs font-bold" style={{ color: "#3B82F6" }}>
            POC-{String(index + 1).padStart(3, "0")}
          </span>
          <span
            className="font-mono text-[9px] font-bold rounded px-2 py-0.5"
            style={{ ...repColor, backgroundColor: repColor.bg, border: `1px solid ${repColor.border}`, color: repColor.text }}
          >
            {reproducibleLabel(record.reproducible)}
          </span>
        </div>
        {record.techniqueId && (
          <span className="font-mono text-[9px]" style={{ color: "#FFFFFF40" }}>
            {record.techniqueId}
          </span>
        )}
      </div>

      {/* Title */}
      <span className="font-mono text-[13px] font-bold" style={{ color: "#FFFFFF" }}>
        {record.techniqueName || record.techniqueId}
      </span>

      {/* Metadata row */}
      <div className="flex items-center gap-6 w-full">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[9px]" style={{ color: "#FFFFFF40" }}>
            Target:
          </span>
          <span className="font-mono text-[9px]" style={{ color: "#FFFFFF80" }}>
            {record.targetIp}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[9px]" style={{ color: "#FFFFFF40" }}>
            Technique:
          </span>
          <span className="font-mono text-[9px]" style={{ color: "#FFFFFF80" }}>
            {record.techniqueId} - {record.techniqueName}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[9px]" style={{ color: "#FFFFFF40" }}>
            Time:
          </span>
          <span className="font-mono text-[9px]" style={{ color: "#FFFFFF80" }}>
            {new Date(record.timestamp).toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
              timeZone: "UTC",
            })}{" "}
            UTC
          </span>
        </div>
      </div>

      {/* Description / output snippet */}
      {record.outputSnippet && (
        <p
          className="font-mono text-[9px] leading-relaxed"
          style={{ color: "#FFFFFF60" }}
        >
          {record.outputSnippet}
        </p>
      )}
    </div>
  );
}

/* ── Empty State ── */

function EmptyState({ t }: { t: (key: string) => string }) {
  return (
    <div className="flex gap-6 flex-1 min-h-0 p-6">
      <div
        className="flex-1 rounded-lg flex flex-col items-center justify-center gap-3"
        style={{
          backgroundColor: "#111827",
          border: "1px solid #FFFFFF08",
        }}
      >
        <span
          className="font-mono text-[8px] font-bold rounded px-3 py-1"
          style={{ backgroundColor: "#3B82F620", color: "#3B82F6" }}
        >
          EMPTY STATE
        </span>
        <span
          className="font-mono text-5xl font-bold"
          style={{ color: "#FFFFFF12" }}
        >
          {"{ }"}
        </span>
        <span
          className="font-mono text-sm font-semibold"
          style={{ color: "#FFFFFF40" }}
        >
          {t("emptyTitle")}
        </span>
        <span
          className="font-mono text-[10px] text-center leading-relaxed max-w-xs"
          style={{ color: "#FFFFFF20" }}
        >
          {t("emptySubtitle")}
        </span>
      </div>
    </div>
  );
}

/* ── Error State ── */

function ErrorState({
  t,
  errorMsg,
  onRetry,
}: {
  t: (key: string) => string;
  errorMsg: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex gap-6 flex-1 min-h-0 p-6">
      <div
        className="flex-1 rounded-lg flex flex-col items-center justify-center gap-3"
        style={{
          backgroundColor: "#111827",
          border: "1px solid #EF444420",
        }}
      >
        <span
          className="font-mono text-[8px] font-bold rounded px-3 py-1"
          style={{ backgroundColor: "#EF444420", color: "#EF4444" }}
        >
          ERROR STATE
        </span>
        <span
          className="font-mono text-5xl font-bold"
          style={{ color: "#EF444425" }}
        >
          ! !
        </span>
        <span
          className="font-mono text-sm font-semibold"
          style={{ color: "#EF4444" }}
        >
          {t("errorTitle")}
        </span>
        <span
          className="font-mono text-[10px] text-center leading-relaxed max-w-xs"
          style={{ color: "#FFFFFF30" }}
        >
          {errorMsg || t("errorSubtitle")}
        </span>
        <button
          onClick={onRetry}
          className="font-mono text-[10px] font-bold rounded px-5 py-2 transition-colors hover:brightness-110"
          style={{
            backgroundColor: "#EF444420",
            border: "1px solid #EF444440",
            color: "#EF4444",
          }}
        >
          {t("retry")}
        </button>
      </div>
    </div>
  );
}

/* ── Export Dropdown ── */

function ExportDropdown({
  t,
  operationId,
}: {
  t: (key: string) => string;
  operationId: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const exportOptions = [
    { label: t("exportJSON"), path: `/operations/${operationId}/report` },
    {
      label: t("exportStructured"),
      path: `/operations/${operationId}/report/structured`,
    },
    {
      label: t("exportMarkdown"),
      path: `/operations/${operationId}/report/markdown`,
    },
  ];

  async function handleExport(path: string) {
    setOpen(false);
    try {
      const data = await api.get<unknown>(path);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `poc-report-${operationId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent fail
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="font-mono text-[10px] font-bold rounded px-4 py-2 transition-colors hover:brightness-110"
        style={{
          backgroundColor: "#3B82F6",
          color: "#FFFFFF",
        }}
      >
        EXPORT JSON
      </button>
      {open && (
        <div
          className="absolute right-0 top-full mt-1 rounded-md py-1 z-50 min-w-[180px]"
          style={{
            backgroundColor: "#1F2937",
            border: "1px solid #FFFFFF10",
          }}
        >
          {exportOptions.map((opt) => (
            <button
              key={opt.path}
              onClick={() => handleExport(opt.path)}
              className="block w-full text-left font-mono text-[10px] px-3 py-2 hover:bg-[#374151] transition-colors"
              style={{ color: "#FFFFFF" }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Main Content ── */

interface PocApiResponse {
  pocRecords: PocRecord[];
  total: number;
}

function PocContent() {
  const t = useTranslations("Poc");
  const operationId = useOperationId();

  const [records, setRecords] = useState<PocRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRecords = useCallback(async () => {
    if (!operationId) return;
    try {
      const data = await api.get<PocApiResponse>(
        `/operations/${operationId}/poc`,
      );
      if (data && Array.isArray(data.pocRecords)) {
        setRecords(data.pocRecords);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [operationId]);

  useEffect(() => {
    fetchRecords();
    timerRef.current = setInterval(fetchRecords, POLL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchRecords]);

  const summary: PocSummary = {
    total: records.length,
    reproducible: records.filter((r) => r.reproducible === "reproducible")
      .length,
    targets: new Set(records.map((r) => r.targetIp)).size,
    techniques: new Set(records.map((r) => r.techniqueId)).size,
  };

  // Loading
  if (loading && records.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
          {t("title")}...
        </p>
      </div>
    );
  }

  // Error with no data
  if (error && records.length === 0) {
    return (
      <div className="flex flex-col h-full" style={{ backgroundColor: "#0A0E17" }}>
        {/* Header */}
        <div
          className="flex items-center justify-between shrink-0"
          style={{
            backgroundColor: "#111827",
            height: 56,
            padding: "0 24px",
          }}
        >
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm font-bold" style={{ color: "#FFFFFF" }}>
              {t("title")}
            </span>
          </div>
        </div>
        <ErrorState t={t} errorMsg={error} onRetry={fetchRecords} />
      </div>
    );
  }

  // Empty
  if (records.length === 0) {
    return (
      <div className="flex flex-col h-full" style={{ backgroundColor: "#0A0E17" }}>
        {/* Header */}
        <div
          className="flex items-center justify-between shrink-0"
          style={{
            backgroundColor: "#111827",
            height: 56,
            padding: "0 24px",
          }}
        >
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm font-bold" style={{ color: "#FFFFFF" }}>
              {t("title")}
            </span>
          </div>
        </div>
        <EmptyState t={t} />
      </div>
    );
  }

  // Normal state
  return (
    <div
      className="flex flex-col h-full overflow-y-auto"
      style={{ backgroundColor: "#0A0E17" }}
    >
      {/* Page header */}
      <div
        className="flex items-center justify-between shrink-0"
        style={{
          backgroundColor: "#111827",
          height: 56,
          padding: "0 24px",
        }}
      >
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-bold" style={{ color: "#FFFFFF" }}>
            PoC RECORDS
          </span>
          <span
            className="font-mono text-[10px] font-semibold rounded px-2.5 py-1"
            style={{ backgroundColor: "#3B82F620", color: "#3B82F6" }}
          >
            {operationId?.slice(0, 12).toUpperCase()}
          </span>
        </div>
        <ExportDropdown t={t} operationId={operationId ?? ""} />
      </div>

      {/* Summary bar */}
      <div className="flex gap-4 shrink-0" style={{ padding: "16px 24px" }}>
        <SummaryCard
          label={t("totalPocs").toUpperCase()}
          value={summary.total}
          color="#FFFFFF"
        />
        <SummaryCard
          label={t("reproducible").toUpperCase()}
          value={summary.reproducible}
          color="#22C55E"
        />
        <SummaryCard
          label={t("targets").toUpperCase()}
          value={summary.targets}
          color="#3B82F6"
        />
        <SummaryCard
          label={t("techniques").toUpperCase()}
          value={summary.techniques}
          color="#F97316"
        />
      </div>

      {/* PoC cards */}
      <div
        className="flex flex-col gap-3 flex-1"
        style={{ padding: "0 24px 16px 24px" }}
      >
        {records.map((record, i) => (
          <PocCard key={record.id ?? i} record={record} index={i} />
        ))}
      </div>
    </div>
  );
}

/* ── Page wrapper ── */

export default function PocPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <p className="text-sm font-mono" style={{ color: "#6B7280" }}>
            Loading PoC Report...
          </p>
        </div>
      }
    >
      <PocContent />
    </Suspense>
  );
}
