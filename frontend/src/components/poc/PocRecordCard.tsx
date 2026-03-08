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

import { useState } from "react";
import { useTranslations } from "next-intl";
import { PocCommandBlock } from "./PocCommandBlock";
import type { PocRecord } from "@/types/poc";

const STATUS_STYLES = {
  reproducible: "bg-athena-success/20 text-athena-success border-athena-success/50",
  partial: "bg-athena-warning/20 text-athena-warning border-athena-warning/50",
  not_reproducible: "bg-athena-error/20 text-athena-error border-athena-error/50",
} as const;

const STATUS_LABELS = {
  reproducible: "REPRODUCIBLE",
  partial: "PARTIAL",
  not_reproducible: "NOT REPRODUCIBLE",
} as const;

interface PocRecordCardProps {
  record: PocRecord;
}

export function PocRecordCard({ record }: PocRecordCardProps) {
  const t = useTranslations("Poc");
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border border-athena-border rounded-athena-sm overflow-hidden bg-athena-surface">
      {/* Header -- always visible */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-athena-elevated/50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <span className="text-xs font-mono text-athena-text-secondary">
            {isOpen ? "\u25BC" : "\u25BA"}
          </span>
          <span className="text-sm font-mono font-bold text-athena-accent">
            {record.technique_id}
          </span>
          <span className="text-sm font-mono text-athena-text">
            {record.target_ip}
          </span>
          <span className="text-xs font-mono text-athena-text-secondary uppercase">
            {record.engine}
          </span>
        </div>
        <span className={`px-3 py-1 text-xs font-mono font-bold uppercase border rounded-athena-sm ${STATUS_STYLES[record.reproducible]}`}>
          {STATUS_LABELS[record.reproducible]}
        </span>
      </button>

      {/* Expanded content */}
      {isOpen && (
        <div className="px-4 pb-4 space-y-4 border-t border-athena-border">
          {/* Technique name */}
          <div className="pt-3">
            <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider">
              {t("techniqueName")}
            </span>
            <p className="text-sm font-mono text-athena-text mt-1">{record.technique_name}</p>
          </div>

          {/* Commands */}
          <div>
            <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider">
              {t("commands")}
            </span>
            <div className="mt-2">
              <PocCommandBlock commands={record.commands_executed} />
            </div>
          </div>

          {/* Output */}
          {record.output_snippet && (
            <div>
              <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider">
                {t("output")}
              </span>
              <div className="mt-2 bg-athena-bg border border-athena-border rounded-athena-sm p-3">
                <pre className="text-xs font-mono text-athena-text-secondary whitespace-pre-wrap">{record.output_snippet}</pre>
              </div>
            </div>
          )}

          {/* Environment */}
          {Object.keys(record.environment).length > 0 && (
            <div>
              <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider">
                {t("environment")}
              </span>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(record.environment).map(([key, val]) => (
                  <span key={key} className="px-2 py-1 text-xs font-mono text-athena-text-secondary bg-athena-elevated rounded-athena-sm">
                    {key}: {val}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Timestamp */}
          <div className="text-xs font-mono text-athena-text-secondary">
            {record.timestamp}
          </div>
        </div>
      )}
    </div>
  );
}
