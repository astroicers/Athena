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

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { useOperationId } from "@/contexts/OperationContext";
import { PocSummaryBar } from "@/components/poc/PocSummaryBar";
import { PocRecordCard } from "@/components/poc/PocRecordCard";
import type { PocRecord, PocSummary } from "@/types/poc";

function LoadingSkeleton() {
  return (
    <div className="space-y-6 p-6 animate-pulse">
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

interface EmptyPanelProps {
  t: ReturnType<typeof useTranslations<"Poc">>;
}

function EmptyPanel({ t }: EmptyPanelProps) {
  return (
    <div className="flex-1 bg-[#111827] border border-[#FFFFFF08] rounded-lg p-10 flex flex-col items-center justify-center gap-4 text-center">
      <span className="text-2xl font-mono text-athena-text-secondary">
        {"{ . }"}
      </span>
      <div className="space-y-2">
        <p className="text-sm font-mono font-bold text-athena-text">
          {t("emptyTitle")}
        </p>
        <p className="text-xs font-mono text-athena-text-secondary max-w-xs">
          {t("emptySubtitle")}
        </p>
      </div>
    </div>
  );
}

interface ErrorPanelProps {
  t: ReturnType<typeof useTranslations<"Poc">>;
  onRetry: () => void;
}

function ErrorPanel({ t, onRetry }: ErrorPanelProps) {
  return (
    <div className="flex-1 bg-[#111827] border border-[#FFFFFF08] rounded-lg p-10 flex flex-col items-center justify-center gap-4 text-center">
      <span className="text-2xl font-mono text-athena-error">
        {"{ x }"}
      </span>
      <div className="space-y-2">
        <p className="text-sm font-mono font-bold text-athena-error">
          {t("errorTitle")}
        </p>
        <p className="text-xs font-mono text-athena-text-secondary max-w-xs">
          {t("errorSubtitle")}
        </p>
      </div>
      <button
        onClick={onRetry}
        className="border border-red-500/50 text-red-400 px-4 py-2 rounded text-xs font-mono uppercase hover:bg-red-500/10 transition-colors"
      >
        {t("retry")}
      </button>
    </div>
  );
}

export default function PocPage() {
  const t = useTranslations("Poc");
  const operationId = useOperationId();

  const searchParams = useSearchParams();
  const [records, setRecords] = useState<PocRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrolledRef = useRef(false);

  const fetchRecords = useCallback(() => {
    setIsLoading(true);
    setError(null);
    api
      .get<PocRecord[]>(`/operations/${operationId}/poc`)
      .then(setRecords)
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to load PoC records";
        setError(msg);
        setRecords([]);
      })
      .finally(() => setIsLoading(false));
  }, [operationId]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  const summary: PocSummary = useMemo(() => {
    const uniqueTargets = new Set(records.map((r) => r.target_ip));
    const uniqueTechniques = new Set(records.map((r) => r.technique_id));
    return {
      total: records.length,
      reproducible: records.filter((r) => r.reproducible === "reproducible").length,
      targets: uniqueTargets.size,
      techniques: uniqueTechniques.size,
    };
  }, [records]);

  // Deep link: scroll to record from ?id= query param
  useEffect(() => {
    const pocId = searchParams.get("id");
    if (pocId && records.length > 0 && !scrolledRef.current) {
      scrolledRef.current = true;
      const el = document.getElementById(`poc-${pocId}`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [searchParams, records]);

  const [exportOpen, setExportOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false);
      }
    }
    if (exportOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [exportOpen]);

  const downloadBlob = useCallback((blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const handleExportJSON = useCallback(() => {
    setExportOpen(false);
    api
      .get<unknown>(`/operations/${operationId}/report`)
      .then((data) => {
        downloadBlob(
          new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
          `athena-report-${operationId}.json`,
        );
      })
      .catch(() => {});
  }, [operationId, downloadBlob]);

  const handleExportStructured = useCallback(() => {
    setExportOpen(false);
    api
      .get<unknown>(`/operations/${operationId}/report/structured`)
      .then((data) => {
        downloadBlob(
          new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
          `athena-report-structured-${operationId}.json`,
        );
      })
      .catch(() => {});
  }, [operationId, downloadBlob]);

  const handleExportMarkdown = useCallback(() => {
    setExportOpen(false);
    // Markdown endpoint returns text with Content-Disposition header
    fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/operations/${operationId}/report/markdown`)
      .then((res) => res.text())
      .then((text) => {
        downloadBlob(
          new Blob([text], { type: "text/markdown" }),
          `athena-report-${operationId}.md`,
        );
      })
      .catch(() => {});
  }, [operationId, downloadBlob]);

  if (isLoading) return <LoadingSkeleton />;

  // Empty or error state: render dual-panel layout (or single empty panel if no error)
  if (records.length === 0 || error) {
    return (
      <div className="space-y-6 p-6 athena-grid-bg min-h-full">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-mono font-bold text-athena-text">
              {t("title")}
            </h1>
            <p className="text-sm font-mono text-athena-text-secondary mt-1">
              {t("subtitle", { operationId })}
            </p>
          </div>
          <div ref={exportRef} className="relative">
            <button
              onClick={() => setExportOpen((v) => !v)}
              className="px-4 py-2 text-xs font-mono font-bold uppercase border border-athena-border rounded-athena-sm bg-athena-surface hover:bg-athena-elevated text-athena-text transition-colors"
            >
              {t("export")} v
            </button>
            {exportOpen && (
              <div className="absolute right-0 top-full mt-1 z-20 w-48 border border-athena-border rounded-athena-sm bg-athena-surface shadow-lg">
                <button
                  onClick={handleExportJSON}
                  className="w-full text-left px-3 py-2 text-xs font-mono text-athena-text hover:bg-athena-elevated transition-colors"
                >
                  {t("exportJSON")}
                </button>
                <button
                  onClick={handleExportStructured}
                  className="w-full text-left px-3 py-2 text-xs font-mono text-athena-text hover:bg-athena-elevated transition-colors border-t border-athena-border/50"
                >
                  {t("exportStructured")}
                </button>
                <button
                  onClick={handleExportMarkdown}
                  className="w-full text-left px-3 py-2 text-xs font-mono text-athena-text hover:bg-athena-elevated transition-colors border-t border-athena-border/50"
                >
                  {t("exportMarkdown")}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Dual-panel empty/error state */}
        <div className="flex gap-4">
          <EmptyPanel t={t} />
          {error && <ErrorPanel t={t} onRetry={fetchRecords} />}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 athena-grid-bg min-h-full">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-mono font-bold text-athena-text">
            {t("title")}
          </h1>
          <p className="text-sm font-mono text-athena-text-secondary mt-1">
            {t("subtitle", { operationId })}
          </p>
        </div>
        <div ref={exportRef} className="relative">
          <button
            onClick={() => setExportOpen((v) => !v)}
            className="px-4 py-2 text-xs font-mono font-bold uppercase border border-athena-border rounded-athena-sm bg-athena-surface hover:bg-athena-elevated text-athena-text transition-colors"
          >
            {t("export")} v
          </button>
          {exportOpen && (
            <div className="absolute right-0 top-full mt-1 z-20 w-48 border border-athena-border rounded-athena-sm bg-athena-surface shadow-lg">
              <button
                onClick={handleExportJSON}
                className="w-full text-left px-3 py-2 text-xs font-mono text-athena-text hover:bg-athena-elevated transition-colors"
              >
                {t("exportJSON")}
              </button>
              <button
                onClick={handleExportStructured}
                className="w-full text-left px-3 py-2 text-xs font-mono text-athena-text hover:bg-athena-elevated transition-colors border-t border-athena-border/50"
              >
                {t("exportStructured")}
              </button>
              <button
                onClick={handleExportMarkdown}
                className="w-full text-left px-3 py-2 text-xs font-mono text-athena-text hover:bg-athena-elevated transition-colors border-t border-athena-border/50"
              >
                {t("exportMarkdown")}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Summary Bar */}
      <PocSummaryBar summary={summary} />

      {/* PoC Records */}
      <div className="space-y-3">
        {records.map((record) => (
          <div key={record.id} id={`poc-${record.id}`}>
            <PocRecordCard record={record} />
          </div>
        ))}
      </div>
    </div>
  );
}
