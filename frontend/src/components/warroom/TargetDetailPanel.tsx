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

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/atoms/Button";
import type { Target } from "@/types/target";
import type { OODATimelineEntry } from "@/types/ooda";
import type { ReconScanResult } from "@/types/recon";

/* ── Types ── */

interface Fact {
  trait: string;
  value: string;
  category: string;
}

interface ScanProgress {
  phase: string | null;
  step: number;
  totalSteps: number;
}

interface TargetDetailPanelProps {
  target: Target;
  facts: Fact[];
  timelineEntries: OODATimelineEntry[];
  onScan: () => void;
  onDeactivate: () => void;
  onActivate: () => void;
  onDelete: () => void;
  onOpenTerminal?: () => void;
  scanning?: boolean;
  scanProgress?: ScanProgress | null;
  scanResult?: ReconScanResult | null;
}

/* ── Markdown component overrides ── */

const MD_COMPONENTS = {
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-athena-body font-bold text-[var(--color-text-primary)] mt-5 mb-2 font-mono uppercase tracking-wider">
      {children}
    </h2>
  ),
  table: ({ children }: { children?: React.ReactNode }) => (
    <table className="w-full text-athena-floor font-mono border-collapse">{children}</table>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="text-left py-1.5 px-2 text-[var(--color-text-secondary)] border-b border-[var(--color-border)] font-semibold">
      {children}
    </th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="py-1.5 px-2 text-[var(--color-text-primary)] border-b border-[var(--color-border)]">
      {children}
    </td>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="text-athena-floor font-mono text-[var(--color-text-secondary)] ml-4 list-disc">
      {children}
    </li>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="text-athena-floor font-mono text-[var(--color-text-secondary)] leading-relaxed">
      {children}
    </p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="text-[var(--color-text-primary)]">{children}</strong>
  ),
};

/* ── Component ── */

export function TargetDetailPanel({
  target,
  facts,
  timelineEntries,
  onScan,
  onDeactivate,
  onActivate,
  onDelete,
  onOpenTerminal,
  scanning = false,
  scanProgress,
  scanResult,
}: TargetDetailPanelProps) {
  const t = useTranslations("WarRoom");
  const tHostCard = useTranslations("HostCard");

  const markdown = useMemo(() => {
    const sections: string[] = [];

    /* ── Section 1: Target Info ── */
    const displayName = [target.ipAddress, target.hostname].filter(Boolean).join(" -- ");
    const statusLabel = target.isCompromised ? "Compromised ✓" : "Secure";
    sections.push(
      `## ${displayName}\n\n` +
        `**IP:** ${target.ipAddress}\n` +
        `**${tHostCard("role")}:** ${target.role}\n` +
        `**${tHostCard("privilege")}:** ${target.privilegeLevel ?? "N/A"}\n` +
        `**Status:** ${statusLabel}\n` +
        `**OS:** ${target.os ?? "Unknown"}\n`,
    );

    /* ── Section 2: Scan Results ── */
    const portFacts = facts.filter((f) => f.trait === "service.open_port");
    if (portFacts.length > 0) {
      const header = `## ${t("scanResults")}\n\n| Port | Protocol | Service | Version |\n|------|----------|---------|---------|`;
      const rows = portFacts
        .map((f) => {
          const parts = f.value.split("/");
          const port = parts[0] ?? "";
          const proto = parts[1] ?? "";
          const svc = parts[2] ?? "";
          const ver = (parts[3] ?? "").replace(/_/g, " ");
          return `\n| ${port} | ${proto} | ${svc} | ${ver} |`;
        })
        .join("");
      sections.push(header + rows + "\n");
    }

    /* ── Section 3: Credentials ── */
    const credFacts = facts.filter((f) => f.category === "credential");
    if (credFacts.length > 0) {
      const credLines = credFacts.map((f) => `- ${f.value}`).join("\n");
      sections.push(`## ${t("credentials")}\n\n${credLines}\n`);
    }

    /* ── Section 4: OODA History ── */
    const targetEntries = timelineEntries.filter(
      (e) => e.targetId === target.id || e.targetIp === target.ipAddress,
    );
    // Group by iteration number
    const iterMap = new Map<
      number,
      { observe: string; orient: string; decide: string; act: string; phase: string }
    >();
    for (const entry of targetEntries) {
      if (entry.iterationNumber === 0) continue; // skip recon entries
      if (!iterMap.has(entry.iterationNumber)) {
        iterMap.set(entry.iterationNumber, { observe: "", orient: "", decide: "", act: "", phase: "" });
      }
      const rec = iterMap.get(entry.iterationNumber)!;
      rec.phase = entry.phase;
      if (entry.phase === "observe") rec.observe = entry.summary || "";
      if (entry.phase === "orient") rec.orient = entry.summary || "";
      if (entry.phase === "decide") rec.decide = entry.summary || "";
      if (entry.phase === "act") rec.act = entry.summary || "";
    }

    if (iterMap.size > 0) {
      const header = `## ${t("oodaHistory")}\n\n| # | Observe | Orient | Decide | Act |\n|---|---------|--------|--------|-----|`;
      const rows = Array.from(iterMap.entries())
        .sort(([a], [b]) => a - b)
        .map(
          ([num, rec]) =>
            `\n| ${num} | ${rec.observe || "-"} | ${rec.orient || "-"} | ${rec.decide || "-"} | ${rec.act || "-"} |`,
        )
        .join("");
      sections.push(header + rows + "\n");
    }

    return sections.join("\n");
  }, [target, facts, timelineEntries, t, tHostCard]);

  return (
    <div className="h-full overflow-y-auto bg-[var(--color-bg-primary)] p-5">
      {/* Markdown content */}
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
        {markdown}
      </ReactMarkdown>

      {/* Action buttons */}
      <div className="flex items-center gap-2 mt-6 pt-4 border-t border-[var(--color-border)]">
        <Button
          variant="secondary"
          size="sm"
          onClick={onScan}
          disabled={scanning}
          className={`text-athena-floor border-[var(--color-accent)]/[0.25] bg-transparent uppercase tracking-wider ${
            scanning
              ? "text-[var(--color-text-tertiary)] cursor-wait"
              : "text-[var(--color-accent)] hover:bg-[var(--color-accent)]/10"
          }`}
        >
          {scanning ? (
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
              {t("scanning")}
            </span>
          ) : (
            tHostCard("reconScan")
          )}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={target.isActive ? onDeactivate : onActivate}
          className={`text-athena-floor uppercase tracking-wider bg-transparent ${
            target.isActive
              ? "text-[var(--color-warning)] border-[var(--color-warning)]/[0.25] hover:bg-[var(--color-warning)]/[0.12]"
              : "text-[var(--color-success)] border-[var(--color-success)]/[0.25] hover:bg-[var(--color-success)]/[0.12]"
          }`}
        >
          {target.isActive ? t("deactivateTarget") : t("activateTarget")}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={onDelete}
          className="text-athena-floor text-[var(--color-error)] border-[var(--color-error)]/[0.25] bg-transparent hover:bg-[var(--color-error)]/10 uppercase tracking-wider"
        >
          {tHostCard("delete")}
        </Button>
        {target.isCompromised && onOpenTerminal && (
          <button
            onClick={onOpenTerminal}
            className="px-3 py-1 rounded-[var(--radius)] border border-[var(--color-accent)]/[0.25] bg-[var(--color-accent)]/[0.12] text-[var(--color-accent)] text-athena-floor font-mono font-semibold hover:bg-[var(--color-accent)]/20 transition-colors"
          >
            {t("terminal")}
          </button>
        )}
      </div>

      {/* ── Scan Progress Bar ── */}
      {scanning && scanProgress && scanProgress.totalSteps > 0 && (
        <div className="mt-4 space-y-1.5">
          <div className="flex justify-between text-athena-floor font-mono">
            <span className="text-[var(--color-accent)]">
              {scanProgress.phase ?? t("scanning")}
            </span>
            <span className="text-[var(--color-text-tertiary)]">
              {scanProgress.step}/{scanProgress.totalSteps}
            </span>
          </div>
          <div className="h-1.5 bg-[var(--color-bg-elevated)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--color-accent)] rounded-full transition-all duration-500"
              style={{ width: `${(scanProgress.step / scanProgress.totalSteps) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Scanning with no progress yet — simple spinner */}
      {scanning && (!scanProgress || scanProgress.totalSteps === 0) && (
        <div className="mt-4 flex items-center gap-2 text-athena-floor font-mono text-[var(--color-accent)]">
          <span className="w-3.5 h-3.5 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
          {t("scanning")}...
        </div>
      )}

      {/* Scan results are rendered via Markdown Section 2 above (from facts) */}
    </div>
  );
}
