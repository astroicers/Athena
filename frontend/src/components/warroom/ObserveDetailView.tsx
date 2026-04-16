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

import { useTranslations } from "next-intl";
import type { PhaseDetail } from "@/types/ooda";

interface ParsedPort {
  port: string;
  protocol: string;
  service: string;
  version: string;
}

function parsePortFact(value: string): ParsedPort | null {
  // Expected format: "port/protocol/service/version" e.g. "21/tcp/ftp/vsftpd_2.3.4"
  const parts = value.split("/");
  if (parts.length >= 3) {
    return {
      port: parts[0],
      protocol: parts[1],
      service: parts[2],
      version: parts.slice(3).join("/").replace(/_/g, " "),
    };
  }
  return null;
}

interface ObserveDetailViewProps {
  detail: PhaseDetail;
}

export function ObserveDetailView({ detail }: ObserveDetailViewProps) {
  const t = useTranslations("WarRoom");

  if (!detail) return null;

  const facts = detail.facts ?? [];
  const portFacts: ParsedPort[] = [];
  const otherFacts: Array<{ trait: string; value: string; category: string }> =
    [];

  for (const fact of facts) {
    if (fact.trait === "service.open_port") {
      const parsed = parsePortFact(fact.value);
      if (parsed) {
        portFacts.push(parsed);
      } else {
        otherFacts.push(fact);
      }
    } else {
      otherFacts.push(fact);
    }
  }

  const totalCount = detail.factsCount ?? facts.length;

  return (
    <div className="font-mono space-y-3">
      {/* Port scan results table */}
      {portFacts.length > 0 && (
        <div>
          <h4 className="text-athena-floor font-bold uppercase tracking-wider text-[var(--color-text-primary)] mb-2">
            {t("portScanResults")}
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-athena-floor border-collapse">
              <thead>
                <tr className="border-b border-[var(--color-border)]">
                  <th className="text-left px-2 py-1.5 text-[var(--color-text-tertiary)] font-bold uppercase tracking-wider">
                    Port
                  </th>
                  <th className="text-left px-2 py-1.5 text-[var(--color-text-tertiary)] font-bold uppercase tracking-wider">
                    Service
                  </th>
                  <th className="text-left px-2 py-1.5 text-[var(--color-text-tertiary)] font-bold uppercase tracking-wider">
                    Version
                  </th>
                  <th className="text-left px-2 py-1.5 text-[var(--color-text-tertiary)] font-bold uppercase tracking-wider">
                    Protocol
                  </th>
                </tr>
              </thead>
              <tbody>
                {portFacts.map((port, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-[var(--color-border-subtle)]"
                  >
                    <td className="px-2 py-1.5 text-[var(--color-accent)] font-bold">
                      {port.port}
                    </td>
                    <td className="px-2 py-1.5 text-[var(--color-text-primary)]">
                      {port.service}
                    </td>
                    <td className="px-2 py-1.5 text-[var(--color-text-secondary)]">
                      {port.version || "-"}
                    </td>
                    <td className="px-2 py-1.5 text-[var(--color-text-tertiary)]">
                      {port.protocol}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Other intelligence facts */}
      {otherFacts.length > 0 && (
        <div>
          <h4 className="text-athena-floor font-bold uppercase tracking-wider text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
            <span>{t("intelligenceFacts")}</span>
            <span className="text-athena-floor bg-[var(--color-accent)]/[0.12] border border-[var(--color-accent)]/[0.25] text-[var(--color-accent)] px-2 py-1 rounded-[var(--radius)]">
              {totalCount}
            </span>
          </h4>
          <ul className="space-y-1">
            {otherFacts.map((fact, idx) => (
              <li
                key={idx}
                className="text-athena-floor text-[var(--color-text-secondary)] flex items-start gap-1"
              >
                <span className="text-[var(--color-text-tertiary)] shrink-0">
                  *
                </span>
                <span>
                  <span className="text-[var(--color-text-primary)] font-bold">
                    {fact.trait}
                  </span>
                  : {fact.value}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Fallback when no parsed facts but count exists */}
      {facts.length === 0 && totalCount > 0 && (
        <div className="text-athena-floor text-[var(--color-text-secondary)]">
          {t("intelligenceFacts")}: {totalCount}
        </div>
      )}
    </div>
  );
}
