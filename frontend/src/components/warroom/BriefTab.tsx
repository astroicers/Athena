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
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/atoms/Button";

/* ── Types ── */

interface BriefResponse {
  markdown: string;
  iterationNumber: number;
  generatedAt: string;
}

interface BriefTabProps {
  operationId: string;
}

/* ── Constants ── */

const POLL_MS = 15_000;

/* ── Markdown components ── */

const mdComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-lg font-bold font-mono text-[var(--color-accent)] mb-2">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-base font-bold font-mono text-[var(--color-text-primary)] mt-4 mb-2">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-sm font-semibold font-mono text-[var(--color-text-secondary)] mt-3 mb-1">{children}</h3>
  ),
  table: ({ children }: { children?: React.ReactNode }) => (
    <table className="w-full text-athena-floor font-mono border-collapse border border-[var(--color-border)] my-2">{children}</table>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="text-left px-2 py-1 border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)]">{children}</th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="px-2 py-1 border border-[var(--color-border)] text-[var(--color-text-primary)]">{children}</td>
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="border-l-2 border-[var(--color-accent)] pl-3 text-athena-floor font-mono text-[var(--color-text-secondary)] my-2">{children}</blockquote>
  ),
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="bg-[var(--color-bg-elevated)] px-1 py-0.5 rounded text-[var(--color-accent)] font-mono text-athena-floor">{children}</code>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="text-athena-floor font-mono text-[var(--color-text-primary)] mb-2">{children}</p>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="text-athena-floor font-mono text-[var(--color-text-primary)] ml-4">{children}</li>
  ),
};

/* ── Component ── */

export function BriefTab({ operationId }: BriefTabProps) {
  const t = useTranslations("Brief");
  const tErrors = useTranslations("Errors");
  const { addToast } = useToast();
  const [brief, setBrief] = useState<BriefResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchBrief = useCallback(async () => {
    if (!operationId) return;
    try {
      const data = await api.get<BriefResponse>(
        `/operations/${operationId}/brief`,
      );
      setBrief(data);
    } catch (err: unknown) {
      console.warn("[BriefTab] brief fetch failed:", err);
      addToast(tErrors("failedLoadBrief"), "error");
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [operationId, addToast, tErrors]);

  useEffect(() => {
    fetchBrief();
    timerRef.current = setInterval(fetchBrief, POLL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchBrief]);

  /** Expose refresh for parent WebSocket triggers */
  useEffect(() => {
    const w = window as unknown as Record<string, unknown>;
    w.__briefRefresh = fetchBrief;
    return () => { delete w.__briefRefresh; };
  }, [fetchBrief]);

  const handleCopy = useCallback(async () => {
    if (!brief?.markdown) return;
    await navigator.clipboard.writeText(brief.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [brief]);

  const handleDownload = useCallback(() => {
    if (!brief?.markdown) return;
    const blob = new Blob([brief.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `operation-brief-ooda-${brief.iterationNumber}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [brief]);

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-athena-floor font-mono text-[var(--color-text-tertiary)]">
          {t("generating")}
        </span>
      </div>
    );
  }

  /* ── Error state ── */
  if (error && !brief?.markdown) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-athena-floor font-mono text-[var(--color-error)]">
          {tErrors("failedLoadBrief")}
        </span>
      </div>
    );
  }

  /* ── Empty state ── */
  if (!brief?.markdown) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-athena-floor font-mono text-[var(--color-text-tertiary)]">
          {t("empty")}
        </span>
      </div>
    );
  }

  /* ── Render ── */
  return (
    <div className="px-6 py-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-athena-floor font-mono text-[var(--color-text-secondary)]">
          {t("lastUpdated", { num: brief.iterationNumber })}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={handleCopy}>
            {copied ? t("copied") : t("copy")}
          </Button>
          <Button variant="secondary" size="sm" onClick={handleDownload}>
            {t("download")}
          </Button>
        </div>
      </div>

      {/* Markdown content */}
      <div className="bg-athena-bg rounded-[var(--radius)] border border-[var(--color-border)] p-4 font-mono">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
          {brief.markdown}
        </ReactMarkdown>
      </div>
    </div>
  );
}
