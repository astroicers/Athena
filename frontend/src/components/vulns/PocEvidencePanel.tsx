// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Button } from "@/components/atoms/Button";
import type { PocRecord, PocSummary } from "@/types/poc";

/* ── Constants ── */

const POLL_MS = 30_000;

/* ── Color helpers ── */

function reproducibleClasses(status: PocRecord["reproducible"]): string {
  switch (status) {
    case "reproducible":
      return "bg-athena-success/12 border border-athena-success/25 text-athena-success";
    case "partial":
      return "bg-athena-warning/12 border border-athena-warning/25 text-athena-warning";
    default:
      return "bg-athena-error/12 border border-athena-error/25 text-athena-error";
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
  colorClass,
}: {
  label: string;
  value: number;
  colorClass: string;
}) {
  return (
    <div className="flex-1 min-w-0 rounded-athena flex flex-col gap-1 bg-athena-surface border border-athena-border px-3 py-2.5">
      <span className="font-mono text-[8px] font-bold uppercase tracking-wider text-athena-text-tertiary">
        {label}
      </span>
      <span
        className={`font-mono text-[28px] font-bold leading-tight athena-tabular-nums ${colorClass}`}
      >
        {value}
      </span>
    </div>
  );
}

/* ── PoC Card ── */

function PocCard({ record, index }: { record: PocRecord; index: number }) {
  return (
    <div className="rounded-athena flex flex-col gap-2 bg-athena-surface border border-athena-border px-4 py-3">
      {/* Header row: ID + badges + vuln ref */}
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-athena-accent">
            POC-{String(index + 1).padStart(3, "0")}
          </span>
          <span
            className={`font-mono text-[9px] font-bold rounded-athena px-2 py-0.5 ${reproducibleClasses(record.reproducible)}`}
          >
            {reproducibleLabel(record.reproducible)}
          </span>
        </div>
        {record.techniqueId && (
          <span className="font-mono text-[9px] text-athena-text-tertiary">
            {record.techniqueId}
          </span>
        )}
      </div>

      {/* Title */}
      <span className="font-mono text-[13px] font-bold text-athena-text-light">
        {record.techniqueName || record.techniqueId}
      </span>

      {/* Metadata row */}
      <div className="flex items-center gap-4 w-full">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[9px] text-athena-text-tertiary">
            Target:
          </span>
          <span className="font-mono text-[9px] text-athena-text-secondary">
            {record.targetIp}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[9px] text-athena-text-tertiary">
            Technique:
          </span>
          <span className="font-mono text-[9px] text-athena-text-secondary">
            {record.techniqueId} - {record.techniqueName}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[9px] text-athena-text-tertiary">
            Time:
          </span>
          <span className="font-mono text-[9px] text-athena-text-secondary">
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
          className="font-mono text-[9px] leading-relaxed text-athena-text-secondary"
        >
          {record.outputSnippet}
        </p>
      )}
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
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setOpen(!open)}
        className="text-[10px] font-bold"
      >
        EXPORT .MD
      </Button>
      {open && (
        <div
          className="absolute right-0 top-full mt-1 rounded-athena py-1 z-50 min-w-[180px] bg-athena-elevated border border-athena-border"
        >
          {exportOptions.map((opt) => (
            <button
              key={opt.path}
              onClick={() => handleExport(opt.path)}
              className="block w-full text-left font-mono text-[10px] px-3 py-2 hover:bg-athena-elevated transition-colors text-athena-text-light"
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Props ── */

interface PocEvidencePanelProps {
  operationId: string;
}

/* ── PocEvidencePanel ── */

interface PocApiResponse {
  pocRecords: PocRecord[];
  total: number;
}

export default function PocEvidencePanel({ operationId }: PocEvidencePanelProps) {
  const t = useTranslations("Poc");

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
      <div className="flex items-center justify-center py-12">
        <p className="text-sm font-mono text-athena-text-tertiary">
          {t("title")}...
        </p>
      </div>
    );
  }

  // Error with no data
  if (error && records.length === 0) {
    return (
      <div
        className="rounded-athena flex flex-col items-center justify-center gap-3 py-12 bg-athena-surface border border-athena-error-bg"
      >
        <span
          className="font-mono text-[8px] font-bold rounded-athena px-3 py-1 bg-athena-error-bg text-athena-error"
        >
          ERROR STATE
        </span>
        <span
          className="font-mono text-sm font-semibold text-athena-error"
        >
          {t("errorTitle")}
        </span>
        <span
          className="font-mono text-[10px] text-center leading-relaxed max-w-xs text-athena-text-tertiary"
        >
          {error || t("errorSubtitle")}
        </span>
        <Button
          variant="danger"
          size="sm"
          onClick={fetchRecords}
          className="text-[10px] font-bold"
        >
          {t("retry")}
        </Button>
      </div>
    );
  }

  // Empty
  if (records.length === 0) {
    return (
      <div
        className="rounded-athena flex flex-col items-center justify-center gap-3 py-12 bg-athena-surface border border-athena-border"
      >
        <span
          className="font-mono text-[8px] font-bold rounded-athena px-3 py-1 bg-athena-accent-bg text-athena-accent"
        >
          EMPTY STATE
        </span>
        <span
          className="font-mono text-5xl font-bold text-athena-text-tertiary"
        >
          {"{ }"}
        </span>
        <span
          className="font-mono text-sm font-semibold text-athena-text-tertiary"
        >
          {t("emptyTitle")}
        </span>
        <span
          className="font-mono text-[10px] text-center leading-relaxed max-w-xs text-athena-text-tertiary"
        >
          {t("emptySubtitle")}
        </span>
      </div>
    );
  }

  // Normal state
  return (
    <div className="flex flex-col gap-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-bold text-athena-text-light">
            PoC RECORDS
          </span>
          <span
            className="font-mono text-[10px] font-semibold rounded-athena px-2.5 py-1 bg-athena-accent-bg text-athena-accent"
          >
            {operationId?.slice(0, 12).toUpperCase()}
          </span>
        </div>
        <ExportDropdown t={t} operationId={operationId ?? ""} />
      </div>

      {/* Summary bar */}
      <div className="flex gap-3">
        <SummaryCard
          label={t("totalPocs").toUpperCase()}
          value={summary.total}
          colorClass="text-athena-text"
        />
        <SummaryCard
          label={t("reproducible").toUpperCase()}
          value={summary.reproducible}
          colorClass="text-athena-success"
        />
        <SummaryCard
          label={t("targets").toUpperCase()}
          value={summary.targets}
          colorClass="text-athena-accent"
        />
        <SummaryCard
          label={t("techniques").toUpperCase()}
          value={summary.techniques}
          colorClass="text-athena-warning"
        />
      </div>

      {/* PoC cards */}
      <div className="flex flex-col gap-2">
        {records.map((record, i) => (
          <PocCard key={record.id ?? i} record={record} index={i} />
        ))}
      </div>
    </div>
  );
}
